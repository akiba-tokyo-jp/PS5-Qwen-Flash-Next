// SPDX-License-Identifier: MIT
// Native startup, inference ownership and read-only VideoOut monitoring.
#include "http_app.h"
#include "llama_engine.h"
#include "indexed_vector.h"
#include "indexed_vector_admission.h"
#include "owned_mapped_probe.h"
#include "padded_bank_layout.h"
#include "padded_bank.h"
#include "padded_cache_bridge.h"
#include "predictive_cache_bridge.h"
#include "large_cache_policy.h"
#include "mapped_copy.h"
#include "expert_policy.h"
#include "completed_expert_routes.h"
#include "native_display.h"
#include "startup.h"
#include "gpu_admission.h"
#include "palette_gpu_admission.h"
#include "vector_bank_admission.h"
#include "device_state_admission.h"
#include "ple_slice_admission.h"
#include "operator_admission.h"
#include "moe_admission.h"
#include "runtime_admission.h"
#include "vulkan_admission.h"
#include "memory_admission.h"
#include "memory_probe.h"
#include "system_memory.h"
#include "boundary_memory_trace.h"
#include "direct_report.h"
#include "direct_bmp_native.h"
#include "source_contention.h"
#include "source_virtual_addresses.h"
#include "model_integrity.h"
#include "direct_integrity.h"
#include "direct_metadata.h"
#include "metadata_memory_probe.h"
#include "metadata_memory_policy.h"
#include "stage_memory_probe.h"
#include "shader_assets.h"
#include "prior_model_integrity.h"
#include "split_model_integrity.h"
#include "model_identity_namespace.h"
#include "model_receipt.h"
#include "model_mapping.h"
#include "validation_policy.h"
#include "native_gpu.h"
#include "mapped_source.h"
#include "mapped_source_bridge.h"
#include "bounded_demo.h"
#include "chat_prompt.h"
#include "model_cpu_budget.h"
#include "device_buffer_budget.h"
#include <fcntl.h>
#include <unistd.h>
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
#include "ggml-cpu.h"
#include "gguf.h"
#include "nlohmann/json.hpp"

#include <cstdlib>
#include <algorithm>
#include <array>
#include <cstring>
#include <chrono>
#include <cmath>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_set>
#include <sys/sysctl.h>
#include <sys/stat.h>

using Json = nlohmann::json;
static qwen_app::MetadataMemoryProbe metadata_memory;
static std::size_t metadata_file_index=0;
static void sample_metadata_memory(std::size_t phase) {
    if(!metadata_memory.enabled())return;
    qwen_app::MetadataMemoryProbe::Sample s;
    s.memory=qwen_app::observe_native_system_memory();
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    const auto direct=qwen_app::native_direct_metadata_stats();
    s.monotonic_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(
        qwen_app::ProfileClock::now().time_since_epoch()).count();
    s.heap_mapped=heap.mapped_bytes;s.heap_peak=heap.peak_bytes;
    s.direct_reads=direct.physical_reads;s.direct_bytes=direct.physical_bytes;
    metadata_memory.record(metadata_file_index,phase,s);
}
// A required link symbol prevents accidental use of an unpatched eager loader.
extern "C" bool llama_app_mmap_prefetch_disabled();
extern "C" bool ggml_app_bounded_staging_enabled();
extern "C" bool ggml_app_dispatch_contract_enabled();
extern "C" void qwen_native_set_fault_report(const char *);
extern "C" void qwen_native_stage(const char *);
extern "C" void qwen_native_log_bytes(const char *, std::size_t);

static bool boundary_memory_enabled=false;
static qwen_app::BoundaryMemoryTrace boundary_memory;
static void sample_boundary_memory(const char *phase) noexcept {
    if(!boundary_memory_enabled)return;
    boundary_memory.record(phase,[](auto &s){
        const auto memory=qwen_app::observe_native_system_memory();
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        s.monotonic_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(
            qwen_app::ProfileClock::now().time_since_epoch()).count();
        s.kernel_free=memory.kernel_free;s.flexible_bytes=memory.flexible_available;
        s.heap_mapped=heap.mapped_bytes;s.heap_peak=heap.peak_bytes;
        s.valid=s.monotonic_ns&&memory.page_size==16384&&memory.kernel_pages&&
            memory.kernel_free<=memory.kernel_pages&&memory.flexible_available;
    });
}
static void observed_inference_stage(const char *phase) {
    sample_boundary_memory(phase);qwen_native_stage(phase);
}
static Json boundary_memory_report() {
    Json rows=Json::array();
    for(std::size_t i=0;i<boundary_memory.size();++i){
        const auto &s=boundary_memory.at(i);
        rows.push_back({{"sequence",s.sequence},{"phase",s.phase},{"valid",s.valid},
            {"monotonic_ns",s.monotonic_ns},{"kernel_free_pages",s.kernel_free},
            {"Flexible_available_bytes",s.flexible_bytes},{"CPU_heap_mapped_bytes",s.heap_mapped},
            {"CPU_heap_peak_bytes",s.heap_peak}});
    }
    return {{"enabled",boundary_memory_enabled},{"capacity",boundary_memory.capacity},
        {"total_observations",boundary_memory.total()},{"invalid_observation",boundary_memory.invalid()},
        {"read_only",true},{"rows",rows}};
}

enum class ReportWriteMode {ordinary_heap,ordinary_stack,direct};
static ReportWriteMode report_write_mode=ReportWriteMode::ordinary_heap;
static bool report_CPU_probe=false;
static void report_before(const char *phase){if(report_CPU_probe)qwen_native_stage(phase);sample_boundary_memory(phase);}
static void report_after(const char *phase){sample_boundary_memory(phase);if(report_CPU_probe)qwen_native_stage(phase);}
static void metadata_direct_stage(const char *phase){
    char text[448]{};const char prefix[]="frame_capture_";
    if(std::strncmp(phase,prefix,sizeof(prefix)-1)==0)
        std::snprintf(text,sizeof(text),"report_capture_%s",phase+sizeof(prefix)-1);
    else std::snprintf(text,sizeof(text),"report_capture_detail_%s",phase);
    qwen_native_stage(text);
    char label[64]{};const auto length=std::strcspn(text," ");
    if(length<sizeof(label))std::memcpy(label,text,length);
    else std::memcpy(label,"report_capture_verbose_detail",sizeof("report_capture_verbose_detail"));
    sample_boundary_memory(label);
}
static void metadata_direct_guard(){
    if(qwen_app::qualified_system_headroom(qwen_app::observe_native_system_memory())<qwen_app::model_read_system_reserve)
        throw std::runtime_error("Metadata persistence must retain the original memory reserve");
}

static void native_log(enum ggml_log_level, const char * text, void *) {
    if (text) qwen_native_log_bytes(text, std::strlen(text));
}

static void write_fresh_report(const std::string & path, const Json & value) {
    report_before("report_before_dump");
    const auto bytes = value.dump(2) + "\n";
    report_after("report_dump_returned");
    if(report_write_mode==ReportWriteMode::direct) {
        void *window=nullptr;
        if(bytes.empty()||bytes.size()>qwen_app::frame_write_window||
           posix_memalign(&window,qwen_app::frame_write_alignment,qwen_app::frame_write_window)||
           !window||!ps5_heap_owns(window))
            throw std::runtime_error("Metadata evidence requires one bounded tracked Direct CPU window");
        qwen_app::NativeFrameSink sink(path,true,metadata_direct_stage,metadata_direct_guard,
            qwen_app::FrameMetadataABI::native_descriptor,bytes.size());
        qwen_app::stream_direct_report(bytes.data(),bytes.size(),sink,window);
        free(window);report_after("report_direct_closed_window_released");return;
    }
    alignas(64) char stack_bytes[16384];const char *data=bytes.data();
    if(report_write_mode==ReportWriteMode::ordinary_stack){
        if(bytes.size()>sizeof(stack_bytes))throw std::runtime_error("CPU report stack fixture exceeds its fixed window");
        std::memcpy(stack_bytes,bytes.data(),bytes.size());data=stack_bytes;
    }
    // Reports contain metadata and controlled validation output, never credentials.
    report_before("report_open_before_native_call");
    const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0644);
    report_after("report_open_native_call_returned");
    if (fd < 0) throw std::runtime_error("Fresh native report could not be created");
    report_before("report_mode_before_native_call");const int mode=fchmod(fd,0644);
    report_after("report_mode_native_call_returned");
    if(mode){close(fd);throw std::runtime_error("Native metadata report permissions could not be set");}
    report_before("report_write_before_native_call");const auto written=write(fd,data,bytes.size());
    report_after("report_write_native_call_returned");
    bool saved=written==static_cast<ssize_t>(bytes.size());
    if(saved){report_before("report_fsync_before_native_call");saved=fsync(fd)==0;report_after("report_fsync_native_call_returned");}
    report_before("report_close_before_native_call");
    const bool closed = close(fd) == 0;
    report_after("report_close_native_call_returned");
    if (!saved || !closed) throw std::runtime_error("Native report could not be persisted");
}

static Json performance_snapshot(const qwen_app::LlamaEngine & engine) {
    const auto source = qwen_app::native_model_source_stats();
    const auto adapter = engine.timing_stats();
    Json result = {{"source_bytes", source.bytes}, {"source_chunks", source.chunks},
        {"source_completed_windows", source.completed_windows},
        {"source_headroom_ns", source.headroom_ns}, {"source_handle_ns", source.handle_ns},
        {"source_read_ns", source.read_ns}, {"source_consumer_ns", source.consumer_ns},
        {"source_pipeline_batches", source.pipeline_batches},
        {"source_worker_read_ns", source.worker_read_ns}, {"source_worker_dispatch_ns", source.worker_dispatch_ns},
        {"process_calls", adapter.process_calls}, {"process_ns", adapter.process_ns},
        {"synchronize_ns", adapter.synchronize_ns}, {"checkpoint_ns", adapter.checkpoint_ns},
        {"work_guard_ns", adapter.work_guard_ns}, {"stage_observer_ns", adapter.stage_observer_ns}};
    if (source.schedule_enabled) result.update({
        {"source_parallel_batches", source.parallel_batches}, {"source_coalesced_batches", source.coalesced_batches},
        {"source_selected_serial_batches", source.selected_serial_batches},
        {"source_physical_read_bytes", source.physical_read_bytes}, {"source_physical_read_calls", source.physical_read_calls}});
    if(qwen_app_padded_cache_enabled())result.update({
        {"source_direct_bank_bytes",source.direct_bank_bytes},{"source_direct_bank_reads",source.direct_bank_reads},
        {"source_padded_scatter_bytes",source.padded_scatter_bytes}});
    return result;
}

static Json gpu_path_snapshot() {
    const auto path=qwen_app::gpu_path_stats();
    const auto copy=qwen_app::mapped_copy_stats();
    return {{"BF16_indexed_matrix_calls",path.bf16_matrix},{"BF16_indexed_vector_calls",path.bf16_vector},
        {"mapped_coherent_write_bytes",path.mapped_write_bytes},{"staging_write_bytes",path.staging_write_bytes},
        {"mapped_streaming_write_bytes",copy.bytes},{"mapped_streaming_write_calls",copy.calls}};
}

static Json performance_difference(const Json & before, const qwen_app::LlamaEngine & engine) {
    const auto after = performance_snapshot(engine);
    Json delta = Json::object();
    for (auto it = before.begin(); it != before.end(); ++it) {
        const auto first = it.value().get<std::uint64_t>();
        const auto last = after.at(it.key()).get<std::uint64_t>();
        if (last < first) throw std::runtime_error("Completed performance counters moved backwards");
        delta[it.key()] = last - first;
    }
    if (delta.at("source_chunks") != delta.at("source_completed_windows"))
        throw std::runtime_error("Performance reporting requires completed source windows");
    // process_ns includes source I/O and backend work. These are nested wall
    // intervals, not hardware GPU timestamps and must not be summed together.
    const bool selected = qwen_app::native_model_source_stats().schedule_enabled;
    Json report = {{"schema", selected ? "ps5-qwen-completed-performance-v4" : "ps5-qwen-completed-performance-v3"}, {"delta", delta},
        {"process_includes_source_and_backend_work", true}, {"GPU_timestamp_queries", false},
        {"hot_path_logs_added", false}, {"GPU_operations_added", false},
        {"source_read_ns_is_producer_wait_time", true}, {"maximum_parallel_source_reads", selected ? 2 : 1},
        {"file_range_schedule_enabled", selected}, {"physical_read_bytes_include_alignment", true},
        {"worker_times_overlap_consumers", true}};
    if (engine.prefill_batch_tokens() > 1) {
        if (!selected) throw std::runtime_error("Batched prefill requires selected-source accounting");
        report.update({{"schema", "ps5-qwen-completed-performance-v5"},
            {"prefill_batch_tokens", engine.prefill_batch_tokens()},
            {"generated_token_batch_tokens", 1}, {"all_prompt_outputs_requested", true}});
    }
    if(qwen_app_padded_cache_enabled())report["owned_padded_bank_IO"]=true;
    const auto speculation=engine.speculative_step_stats();
    if(speculation.controller_enabled) {
        report.erase("generated_token_batch_tokens");
        report.update({{"schema","ps5-qwen-completed-performance-v6"},
            {"ordinary_generated_token_batch_tokens",1},{"target_verification_batch_tokens",2},
            {"hot_path_logs_added",true},{"GPU_operations_added",true},
            {"speculation",{{"attempts",speculation.attempts},{"accepted",speculation.accepted},
                {"rejected",speculation.rejected},{"queued_bonus_samples",speculation.queued_bonus_samples}}}});
    }
    return report;
}

struct CompletedRouteEvidence {
    std::vector<qwen_app::CompletedExpertRoute> rows;
    std::uint64_t calls=0,unique=0,selected=0,hits=0,misses=0,uploaded=0,advice=0;
    bool complete=false;
    bool predictive=false;
    std::uint64_t predictive_bytes=0;
    std::string error;
};

static std::uint64_t predictive_cache_bytes() {
    qwen_predictive_cache_stats p{};qwen_app_predictive_cache_counters(&p);return p.logical_bytes;
}

static CompletedRouteEvidence completed_route_evidence(const qwen_app::LlamaEngine & engine,
        std::uint64_t before_calls,const qwen_app::ExpertCacheMetrics & before,std::uint64_t before_predictive) {
    CompletedRouteEvidence result;
    try {
    const auto calls=engine.timing_stats().process_calls;
    if(calls<before_calls)throw qwen_app::ExpertRouteCaptureError("Expert-route process counter moved backwards");
    const auto after=engine.expert_cache_metrics();
    if(!after||after->hits<before.hits||after->misses<before.misses||after->uploaded_bytes<before.uploaded_bytes||
       after->prefetch_advice_bytes<before.prefetch_advice_bytes)
        throw qwen_app::ExpertRouteCaptureError("Expert-route cache counters moved backwards");
    result.rows=qwen_app::finish_completed_expert_routes(calls-before_calls);
    for(const auto & row:result.rows){
        auto ids=row.ids;const auto end=ids.begin()+10*row.tokens;
        result.selected+=10*row.tokens;std::sort(ids.begin(),end);
        result.unique+=std::unique(ids.begin(),end)-ids.begin();
    }
    const auto hits=after->hits-before.hits,misses=after->misses-before.misses;
    const auto uploaded=after->uploaded_bytes-before.uploaded_bytes;
    const auto predictive_after=predictive_cache_bytes();
    if(predictive_after<before_predictive)throw qwen_app::ExpertRouteCaptureError("Predictive transfer counter moved backwards");
    result.predictive=qwen_app_predictive_cache_enabled();result.predictive_bytes=predictive_after-before_predictive;
    if(hits+misses!=result.unique||uploaded!=misses*9830400ull+result.predictive_bytes)
        throw qwen_app::ExpertRouteCaptureError("Complete expert routes disagree with actual cache transfers");
    result.calls=calls-before_calls;result.hits=hits;result.misses=misses;result.uploaded=uploaded;
    result.advice=after->prefetch_advice_bytes-before.prefetch_advice_bytes;result.complete=true;
    }catch(const qwen_app::ExpertRouteCaptureError & error){
        qwen_app::quarantine_completed_expert_routes();result.error=error.what();
    }
    return result;
}

static Json completed_route_report(const CompletedRouteEvidence & result) {
    if(!result.complete)return {{"schema","ps5-qwen-completed-expert-routes-v1"},{"complete",false},{"capture_failed",true},
        {"error",result.error},{"additional_GPU_downloads",0},{"routing_and_cache_policy_unchanged",true},
        {"original_model_validation_and_retirement_still_required",true}};
    Json events=Json::array();
    for(const auto & row:result.rows){
        std::vector<std::uint16_t> ids(row.ids.begin(),row.ids.begin()+10*row.tokens);
        events.push_back({{"layer",row.layer},{"tokens",row.tokens},{"ids",ids}});
    }
    Json report={{"schema","ps5-qwen-completed-expert-routes-v1"},{"process_calls",result.calls},
        {"complete",true},{"capture_failed",false},
        {"layers_per_process",48},{"experts",512},{"experts_per_token",10},
        {"cache_slots",qwen_app::selected_padded_cache_geometry().active_slots},
        {"maximum_records",qwen_app::expert_route_capacity},{"selected_indices",result.selected},{"unique_selected_experts",result.unique},
        {"cache_hits",result.hits},{"cache_misses",result.misses},{"uploaded_bytes",result.uploaded},
        {"prefetch_advice_bytes",result.advice},
        {"all_existing_downloads_and_synchronizations_returned",true},{"additional_GPU_downloads",0},
        {"routing_and_cache_policy_unchanged",true},{"records",std::move(events)}};
    if(result.predictive)report.update({{"schema","ps5-qwen-completed-expert-routes-v2"},
        {"routing_and_cache_policy_unchanged",false},{"original_routing_unchanged",true},
        {"predictive_cache_enabled",true},{"predictive_uploaded_bytes",result.predictive_bytes},
        {"demand_uploaded_bytes",result.uploaded-result.predictive_bytes}});
    return report;
}

static std::string model_file(const std::string & receipt, const std::string & name) {
    if (name.empty() || name.find_first_of("/\\:") != std::string::npos || name == "." || name == "..")
        throw std::runtime_error("Receipt model files must use relative basenames");
    const auto separator = receipt.find_last_of("/\\");
    return separator == std::string::npos ? name : receipt.substr(0, separator + 1) + name;
}

using ModelFileIdentity = std::array<std::uint64_t, 10>;
static ModelFileIdentity model_file_identity(const std::string & path, std::uint64_t bytes) {
    const int fd = open(path.c_str(), O_RDONLY | O_NOFOLLOW);
    if (fd < 0) throw std::runtime_error("Original model identity could not be observed read-only");
    struct stat info{};
    const bool observed = fstat(fd, &info) == 0;
    const bool closed = close(fd) == 0;
    if (!observed || !closed || !S_ISREG(info.st_mode) || !info.st_ino || info.st_size < 0 ||
        static_cast<std::uint64_t>(info.st_size) != bytes || (info.st_mode & 0022))
        throw std::runtime_error("Original model identity or owned file permissions are not admitted");
    return {std::uint64_t(info.st_dev), std::uint64_t(info.st_ino), std::uint64_t(info.st_mode),
        std::uint64_t(info.st_uid), std::uint64_t(info.st_gid), std::uint64_t(info.st_size),
        std::uint64_t(info.st_mtim.tv_sec), std::uint64_t(info.st_mtim.tv_nsec),
        std::uint64_t(info.st_ctim.tv_sec), std::uint64_t(info.st_ctim.tv_nsec)};
}

static void validate_prior_shader_CPU(const Json & r,const Json & prior,const qwen_app::ShaderAssetStats & assets) {
    if(prior.at("all_original_assets_completed_on_this_boot")!=true||
       prior.at("same_encoded_resources_and_per_use_decoder_in_current_SELF")!=true||
       prior.at("current_module_input_full_SHA256_required")!=true||
       r.at("schema")!=(assets.external_file.registered?"ps5-qwen-shader-storage-CPU-result-v3":"ps5-qwen-shader-storage-CPU-result-v1")||
       r.at("pid")!=prior.at("pid")||r.at("run_id")!=prior.at("run_id")||
       r.at("GPU_calls")!=0||r.at("Vulkan_initialized")!=false||r.at("model_loaded")!=false||
       r.at("active_lease")!=false||r.at("failed")!=false||r.at("persistent_caches_enabled")!=false||
       r.at("all_original_SPIRV_bytes_preserved")!=true||r.at("shader_count")!=assets.assets||
       r.at("CPU_verified_assets")!=assets.assets||r.at("lookup_entries")!=assets.lookup_entries||
       r.at("CPU_verified_lookups")!=assets.lookup_entries||r.at("original_bytes")!=assets.original_bytes||
       r.at("stored_bytes")!=assets.stored_bytes||r.at("registry_sha256")!=assets.registry_sha256)
        throw std::runtime_error("Prior complete native shader bytes do not bind the unchanged current resources and per-use SHA256");
    if(assets.external_file.registered&&(!assets.initialized||!assets.external_file.verified||assets.external_file.failed||
       assets.external_file.read_pending||assets.external_file.frame_requests||
       r.at("all_assets_verified_in_this_run")!=true||r.at("prior_CPU_verified_assets")!=0||
       r.at("verification_mode")!="all_assets_in_current_run"||r.at("external_file")!=true||
       r.at("external_file_SHA256_verified")!=true||r.at("external_read_pending")!=false||r.at("external_source_failed")!=false||
       r.at("external_file_bytes")!=assets.external_file.file_bytes||
       r.at("codec_input_window_bytes")!=assets.external_file.input_window_bytes||r.at("external_frame_requests")!=assets.assets))
        throw std::runtime_error("Prior external shader bytes require complete current file integrity and direct original-byte evidence");
}

static Json read_prior_shader_CPU(const Json & prior,const qwen_app::ShaderAssetStats & assets) {
    const auto path=prior.at("report_path").get<std::string>();const auto bytes=prior.at("report_bytes").get<std::uint64_t>();
    const auto run=prior.at("run_id").get<std::string>();
    if(run.size()!=32||run.find_first_not_of("0123456789abcdef")!=std::string::npos||
       path!="/app0/qwen-runtime/plan-"+run+".json.shader-assets.CPU"||!bytes||bytes>4096)
        throw std::runtime_error("Prior shader evidence must be the bounded completed native report");
    const auto before=model_file_identity(path,bytes);
    std::ifstream file(path,std::ios::binary);std::string raw(static_cast<std::size_t>(bytes),'\0');
    file.read(raw.data(),static_cast<std::streamsize>(bytes));
    if(file.gcount()!=static_cast<std::streamsize>(bytes)||file.peek()!=std::char_traits<char>::eof()||
       file.bad()||qwen_app::sha256_metadata_bytes(raw)!=prior.at("report_sha256")||model_file_identity(path,bytes)!=before)
        throw std::runtime_error("Prior shader evidence changed or failed its complete SHA256");
    const auto report=Json::parse(raw);validate_prior_shader_CPU(report,prior,assets);return report;
}

// Scope-specific callers validate the path and byte bound before this read.
static Json read_completed_native_report(const Json &proof) {
    const auto path=proof.at("report_path").get<std::string>();
    const auto bytes=proof.at("report_bytes").get<std::uint64_t>();
    const auto before=model_file_identity(path,bytes);
    std::ifstream file(path,std::ios::binary);std::string raw(static_cast<std::size_t>(bytes),'\0');
    file.read(raw.data(),static_cast<std::streamsize>(bytes));
    if(file.gcount()!=static_cast<std::streamsize>(bytes)||file.peek()!=std::char_traits<char>::eof()||
       file.bad()||qwen_app::sha256_metadata_bytes(raw)!=proof.at("report_sha256")||model_file_identity(path,bytes)!=before)
        throw std::runtime_error("Completed native evidence changed or failed complete SHA256");
    return Json::parse(raw);
}

static ModelFileIdentity model_directory_identity(const std::string & path) {
    const int fd = open(path.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
    if (fd < 0) throw std::runtime_error("Original model directory could not be observed");
    struct stat info{}; const bool observed = fstat(fd, &info) == 0; const bool closed = close(fd) == 0;
    if (!observed || !closed || !S_ISDIR(info.st_mode) || !info.st_ino || info.st_size <= 0 ||
        info.st_uid != 0 || info.st_gid != 0 || (info.st_mode & 07777) != 0755)
        throw std::runtime_error("Original model directory ownership is not admitted");
    return {std::uint64_t(info.st_dev), std::uint64_t(info.st_ino), std::uint64_t(info.st_mode),
        std::uint64_t(info.st_uid), std::uint64_t(info.st_gid), std::uint64_t(info.st_size),
        std::uint64_t(info.st_mtim.tv_sec), std::uint64_t(info.st_mtim.tv_nsec),
        std::uint64_t(info.st_ctim.tv_sec), std::uint64_t(info.st_ctim.tv_nsec)};
}

static void inspect_container(const std::string & path, bool first, qwen_app::ModelFootprint & footprint,
                              std::unordered_set<std::string> & names, std::uint64_t expected_bytes,
                              std::uint64_t physical_bytes) {
    sample_metadata_memory(0);
    std::ifstream file(path, std::ios::binary|std::ios::ate);
    if(!expected_bytes || !physical_bytes || physical_bytes>expected_bytes || !file || file.tellg()<0 ||
       static_cast<std::uint64_t>(file.tellg())!=physical_bytes)
        throw std::runtime_error("Transferred model size differs from the admitted physical source");
    sample_metadata_memory(1);
    footprint.mapped_files=qwen_app::checked_memory_sum(footprint.mapped_files,expected_bytes);
    std::unique_ptr<gguf_context, decltype(&gguf_free)> metadata(
        gguf_init_from_file(path.c_str(), {true, nullptr}), gguf_free);
    if (!metadata) throw std::runtime_error("GGUF metadata could not be read");
    sample_metadata_memory(2);
    if(first) {
        const auto layers=gguf_find_key(metadata.get(),"qwen4exp.block_count");
        const auto mtp=gguf_find_key(metadata.get(),"qwen4exp.nextn_predict_layers");
        if(layers<0||gguf_get_kv_type(metadata.get(),layers)!=GGUF_TYPE_UINT32||
           (mtp>=0&&gguf_get_kv_type(metadata.get(),mtp)!=GGUF_TYPE_UINT32))
            throw std::runtime_error("Model layer metadata is required for memory admission");
        const auto all=gguf_get_val_u32(metadata.get(),layers), next=mtp<0?0:gguf_get_val_u32(metadata.get(),mtp);
        if(!all||all>512||next>=all) throw std::runtime_error("Invalid model layer count");
        footprint.trunk_layers=all-next;
        for(const auto & requirement : {std::pair<const char *,std::uint32_t>{"qwen4exp.expert_count",512},
             {"qwen4exp.expert_used_count",10},{"qwen4exp.embedding_length",2560},
             {"qwen4exp.ple.ngram_size",3},{"qwen4exp.ple.heads_per_ngram",8},
             {"qwen4exp.embedding_length_per_layer_input",160}}) {
            const auto key=gguf_find_key(metadata.get(),requirement.first);
            if(key<0||gguf_get_kv_type(metadata.get(),key)!=GGUF_TYPE_UINT32||
               gguf_get_val_u32(metadata.get(),key)!=requirement.second)
                throw std::runtime_error("Original model dimensions and expert routing must be retained");
        }
        if(footprint.trunk_layers!=48) throw std::runtime_error("The original 48-layer text trunk is required");
    }
    for (std::int64_t i = 0; i < gguf_get_n_tensors(metadata.get()); ++i) {
        const auto type = gguf_get_tensor_type(metadata.get(), i);
        if (type != GGML_TYPE_BF16 && type != GGML_TYPE_F32)
            throw std::runtime_error("Only original BF16 or lossless F32 widening is accepted");
        const auto * name=gguf_get_tensor_name(metadata.get(),i);
        const auto bytes=gguf_get_tensor_size(metadata.get(),i);
        const auto end=qwen_app::checked_memory_sum(gguf_get_data_offset(metadata.get()),
            qwen_app::checked_memory_sum(gguf_get_tensor_offset(metadata.get(),i),bytes));
        if(!name||!names.insert(name).second||names.size()>8192||end>expected_bytes)
            throw std::runtime_error("Invalid or duplicate GGUF tensor span");
        footprint.tensor(name,bytes);
        if ((std::string(name) == "token_embd.weight" && gguf_get_tensor_ne(metadata.get(), i)[0] != 2560) ||
            (std::string(name) == "per_layer_token_embd.weight" && gguf_get_tensor_ne(metadata.get(), i)[0] != 160))
            throw std::runtime_error("The original CPU row-access dimensions differ from their admitted budget");
        if(std::strstr(name,".ffn_")&&std::strstr(name,"_exps.weight")&&gguf_get_tensor_ne(metadata.get(),i)[2]!=512)
            throw std::runtime_error("Every original expert must remain present");
    }
    sample_metadata_memory(3);
    if (!first) return;
    const auto architecture = gguf_find_key(metadata.get(), "general.architecture");
    if (architecture < 0 || gguf_get_kv_type(metadata.get(), architecture) != GGUF_TYPE_STRING ||
        std::string(gguf_get_val_str(metadata.get(), architecture)) != "qwen4exp")
        throw std::runtime_error("Qwen4Exp model architecture is required");
    for (const auto * key : {"qwen4exp.ple.layers", "qwen4exp.ple.layer_multipliers",
                            "qwen4exp.ple.head_offsets", "qwen4exp.ple.head_vocab_sizes"}) {
        const auto index = gguf_find_key(metadata.get(), key);
        if (index < 0 || gguf_get_kv_type(metadata.get(), index) != GGUF_TYPE_ARRAY || !gguf_get_arr_n(metadata.get(), index))
            throw std::runtime_error("Required PLE metadata is missing");
        const auto type = gguf_get_arr_type(metadata.get(), index);
        if (std::string(key) != "qwen4exp.ple.layers" && type != GGUF_TYPE_INT64 && type != GGUF_TYPE_UINT64)
            throw std::runtime_error("PLE hash constants must remain exact 64-bit integers");
    }
}

static std::uint64_t observed_system_headroom() {
    return qwen_app::qualified_system_headroom(qwen_app::admit_native_system_memory());
}
static Json memory_backpressure_report() {
    const auto s=qwen_app::native_memory_backpressure_stats();
    return {{"schema","ps5-qwen-memory-backpressure-v2"},{"enabled",s.enabled},
        {"maximum_boundary_wait_ms",20000},{"maximum_total_wait_ms",60000},{"poll_interval_ms",100},
        {"observations",s.observations},{"pressure_events",s.pressure_events},
        {"recovered_admissions",s.recovered_admissions},{"cumulative_wait_ns",s.wait_ns},
        {"pause_calls",s.pause_calls},{"last_qualified",s.last_qualified},
        {"kernel_free_pages",s.last.kernel_free},{"kernel_minimum_pages",s.last.kernel_minimum},
        {"kernel_reserved_pages",s.last.kernel_reserved},{"kernel_page_size",s.last.page_size},
        {"kernel_extra_margin_bytes",qwen_app::kernel_memory_margin},
        {"memory_reserves_unchanged",true},{"IO_or_GPU_operations_retried",false}};
}
static Json system_memory_report(const qwen_app::SystemMemoryObservation & memory, bool model_loaded=false) {
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    return {{"pid",getpid()},{"GPU_calls",0},{"model_loaded",model_loaded},
        {"Flexible_available_bytes",memory.flexible_available},
        {"kernel_page_size",memory.page_size},{"kernel_total_pages",memory.kernel_pages},
        {"kernel_free_pages",memory.kernel_free},{"kernel_minimum_pages",memory.kernel_minimum},
        {"kernel_target_pages",memory.kernel_target},{"kernel_reserved_pages",memory.kernel_reserved},
        {"kernel_extra_margin_bytes",qwen_app::kernel_memory_margin},
        {"CPU_heap_mapped_bytes",heap.mapped_bytes},{"CPU_heap_peak_bytes",heap.peak_bytes},
        {"CPU_heap_libc_fallbacks",heap.libc_fallbacks},
        {"CPU_heap_uses_Direct_pool",true},{"inactive_pages_counted_as_available",false}};
}

static Json diagnostic_VM_population() {
    Json result=Json::object();
    for(const auto & field : {std::pair<const char *,const char *>{"free","vm.stats.vm0.v_free_count"},
        {"active","vm.stats.vm0.v_active_count"},{"inactive","vm.stats.vm0.v_inactive_count"},
        {"wired","vm.stats.vm0.v_wire_count"},{"total","vm.stats.vm0.v_page_count"}}) {
        struct {std::uint64_t first;std::uint32_t value;std::uint64_t last;} g{0x725b725b725b725bull,0,0x725b725b725b725bull};
        std::size_t bytes=sizeof(g.value);
        if(sysctlbyname(field.second,&g.value,&bytes,nullptr,0)||bytes!=sizeof(g.value)||
           g.first!=0x725b725b725b725bull||g.last!=0x725b725b725b725bull)
            throw std::runtime_error("CPU-only VM population observation is unavailable");
        result[field.first]=g.value;
    }
    // Sequential observations classify page movement; they are not an atomic
    // snapshot, a reclaim operation, or a replacement for the original reserve.
    return result;
}

struct LoadProgress {
    std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
    unsigned reported=0;
};
static void require_model_CPU_budget() {
    sample_boundary_memory("CPU_work_guard_before");
    struct ps5_heap_stats heap{}; ps5_heap_stats(&heap);
    if (heap.libc_fallbacks || heap.mapped_bytes > qwen_app::maximum_model_CPU_heap_bytes ||
        heap.peak_bytes > qwen_app::maximum_model_CPU_heap_bytes)
        throw std::runtime_error("CPU Direct heap admission failed: mapped="+std::to_string(heap.mapped_bytes)+
            " peak="+std::to_string(heap.peak_bytes)+" limit="+std::to_string(qwen_app::maximum_model_CPU_heap_bytes)+
            " libc_fallbacks="+std::to_string(heap.libc_fallbacks));
    const auto flexible=observed_system_headroom();
    if (flexible < qwen_app::model_read_system_reserve)
        throw std::runtime_error("Flexible memory admission failed: available="+std::to_string(flexible)+
            " required="+std::to_string(qwen_app::model_read_system_reserve));
    sample_boundary_memory("CPU_work_guard_completed");
}
static void wait_for_initial_model_CPU_budget() {
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(20);
    bool reported=false;
    for(;;) {
        try {require_model_CPU_budget();return;}
        catch(const qwen_app::KernelMemoryPressure &) {
            if(!reported) {reported=true;qwen_native_stage("waiting_for_initial_kernel_page_headroom GPU_not_started=1 model_loaded=0");}
            if(std::chrono::steady_clock::now()>=deadline)throw;
            // Only observe independent kernel paging progress. No allocation,
            // cache purge, mapping or GPU operation is retried in this loop.
            (void)usleep(250000);
        }
    }
}
static bool observe_model_load(float progress,void * opaque) {
    auto & state=*static_cast<LoadProgress *>(opaque);
    if(!std::isfinite(progress)||progress<0||progress>1) return false;
    try { require_model_CPU_budget(); }
    catch (...) { qwen_native_stage("model_load_CPU_memory_bound_reached_at_completed_boundary"); return false; }
    // Cancellation happens only at the loader's completed transfer boundaries.
    if(std::chrono::steady_clock::now()-state.started>std::chrono::minutes(20)) {
        qwen_native_stage("model_load_deadline_reached_at_completed_boundary");return false;
    }
    const unsigned tick=static_cast<unsigned>(progress*10);
    if(tick>state.reported) {state.reported=tick;qwen_native_stage("model_load_progress_advanced");}
    return true;
}

static void admit_shader_storage_CPU(const Json &policy,const std::string &report_path,bool allow_storage,const Json &run_id) {
    sample_boundary_memory("shader_CPU_admission_begin");
    if(qwen_app::native_shader_assets_registered()!=policy.contains("native_shader_storage"))
        throw std::runtime_error("Packed shader resources require explicit prior CPU validation");
    if(policy.contains("native_shader_storage")) {
        const auto &storage=policy.at("native_shader_storage");
        if(!allow_storage||storage.at("schema")!="ps5-qwen-shader-storage-policy-v1"||
           storage.at("enabled")!=true||
           storage.at("model_and_shader_precision_unchanged")!=true||storage.at("persistent_caches_enabled")!=false)
            throw std::runtime_error("Lossless shader storage CPU admission is not authorized");
        const bool external=qwen_app::native_shader_file_registered();
        const bool verify_all=storage.at("verify_all_original_assets_before_Vulkan").get<bool>();
        if(external!=storage.contains("external_file"))
            throw std::runtime_error("External shader resources require their exact explicit private file policy");
        if(external) {
            const auto &file=storage.at("external_file");
            if(file.at("schema")!="ps5-qwen-external-shader-file-policy-v1"||
               file.at("single_read_only_descriptor")!=true||file.at("new_model_source_window")!=false||
               verify_all==storage.contains("prior_native_CPU"))
                throw std::runtime_error("External shader resources require complete current file and original-byte verification");
            sample_boundary_memory("shader_file_initialization_before");
            qwen_app::initialize_native_shader_file(file.at("path").get<std::string>(),file.at("bytes").get<std::uint64_t>(),
                file.at("sha256").get<std::string>());
            sample_boundary_memory("shader_file_initialization_returned");
            const auto admitted=qwen_app::native_shader_file_stats();
            if(!admitted.verified||admitted.failed||admitted.read_pending||admitted.input_window_bytes!=file.at("input_window_bytes"))
                throw std::runtime_error("External shader file admission did not complete inside its exact tracked window");
            qwen_native_stage("complete_external_shader_file_SHA256_passed GPU_not_started=1");
        }
        sample_boundary_memory("shader_registry_initialization_before");
        qwen_app::initialize_native_shader_assets();
        sample_boundary_memory("shader_registry_initialization_returned");
        const auto declared=qwen_app::native_shader_asset_stats();
        if(declared.assets!=storage.at("shader_count")||declared.original_bytes!=storage.at("original_bytes")||
           declared.stored_bytes!=storage.at("stored_bytes")||declared.lookup_entries!=storage.at("lookup_entries")||
           declared.registry_sha256!=storage.at("registry_sha256"))
            throw std::runtime_error("Shader CPU verification exceeds the exact private resource plan");
        Json prior_shader;
        sample_boundary_memory("shader_prior_proof_before");
        if(!verify_all)prior_shader=read_prior_shader_CPU(storage.at("prior_native_CPU"),declared);
        sample_boundary_memory("shader_prior_proof_returned");
        const auto shaders=verify_all?qwen_app::verify_native_shader_assets_CPU():declared;
        if(shaders.failed||shaders.active_lease||(verify_all&&shaders.CPU_verified_assets!=shaders.assets)||
           (verify_all&&shaders.CPU_verified_lookups!=shaders.lookup_entries)||shaders.assets!=storage.at("shader_count")||
           shaders.original_bytes!=storage.at("original_bytes")||shaders.stored_bytes!=storage.at("stored_bytes")||
           shaders.registry_sha256!=storage.at("registry_sha256"))
            throw std::runtime_error("Lossless shader CPU bytes or lookup identity did not match the private plan");
        if(external&&shaders.external_file.frame_requests!=shaders.CPU_verified_assets)
            throw std::runtime_error("External shader CPU verification did not restore every current original input");
        require_model_CPU_budget();
        write_fresh_report(report_path+".shader-assets.CPU",{
            {"schema",external?"ps5-qwen-shader-storage-CPU-result-v3":"ps5-qwen-shader-storage-CPU-result-v2"},{"pid",getpid()},
            {"verification_mode",verify_all?"all_assets_in_current_run":"prior_all_assets_and_current_use_SHA256"},
            {"all_assets_verified_in_this_run",verify_all},
            {"prior_CPU_verified_assets",verify_all?Json(0):prior_shader.at("CPU_verified_assets")},
            {"prior_report_sha256",verify_all?Json(nullptr):storage.at("prior_native_CPU").at("report_sha256")},
            {"run_id",run_id},
            {"shader_count",shaders.assets},{"original_bytes",shaders.original_bytes},{"stored_bytes",shaders.stored_bytes},
            {"CPU_verified_assets",shaders.CPU_verified_assets},{"lookup_entries",shaders.lookup_entries},
            {"CPU_verified_lookups",shaders.CPU_verified_lookups},{"registry_sha256",shaders.registry_sha256},
            {"codec_output_bytes",shaders.codec_output_bytes},{"codec_ordering_bytes",shaders.codec_ordering_bytes},
            {"codec_scratch_bytes",shaders.codec_scratch_bytes},
            {"external_file",shaders.external_file.registered},{"external_file_SHA256_verified",shaders.external_file.verified},
            {"external_file_bytes",shaders.external_file.file_bytes},{"codec_input_window_bytes",shaders.external_file.input_window_bytes},
            {"external_read_calls",shaders.external_file.read_calls},{"external_returned_bytes",shaders.external_file.returned_bytes},
            {"external_frame_requests",shaders.external_file.frame_requests},
            {"external_read_pending",shaders.external_file.read_pending},{"external_source_failed",shaders.external_file.failed},
            {"active_lease",false},{"failed",false},{"all_original_SPIRV_bytes_preserved",true},
            {"GPU_calls",0},{"Vulkan_initialized",false},{"model_loaded",false},{"persistent_caches_enabled",false}});
        qwen_native_stage(verify_all?"all_original_shader_CPU_bytes_and_lookups_verified_before_Vulkan":
            "prior_all_original_shader_CPU_bytes_bound_current_module_SHA256_required_before_Vulkan");
    }
    sample_boundary_memory("shader_CPU_admission_returned");
}

static Json padded_layout_result(const qwen_app::PaddedLayoutResult &probe,const Json &policy,bool display) {
    const auto geometry=qwen_app::selected_padded_cache_geometry();
    const auto ledger=qwen_app::native_model_device_stats();
    if(ledger.live)throw std::runtime_error("Padded layout device buffers remain live after retirement");
    Json cases=Json::array();
    for(const auto &row:probe.cases)cases.push_back({{"columns",row.columns},{"rows",row.rows},
        {"input_vectors",row.input_vectors},{"residue",row.residue},
        {"maximum_absolute_error",row.maximum_absolute_error},
        {"non_BF16_exact_F32_inputs",row.non_BF16_exact_F32_inputs},
        {"matrix_passed",row.matrix_passed},{"vector_passed",row.vector_passed},
        {"non_dyadic_vector_passed",row.non_dyadic_vector_passed},{"padding_intact",row.padding_intact}});
    const auto &owner=policy.at("native_first_generation_validation");
    Json report={{"schema","ps5-qwen-padded-bank-layout-result-v1"},{"pid",getpid()},
        {"run_id",owner.at("run_id")},{"eligible",probe.eligible},{"all_started_IO_closed",probe.all_IO_closed},
        {"Direct_reads",probe.Direct_reads},{"GPU_graphs",probe.GPU_graphs},
        {"descriptor_alignment",probe.descriptor_alignment},{"memory_flags",probe.memory_flags},
        {"cases",cases},{"maximum_absolute_error_limit",1e-6},{"reference_accumulation","F64"},
        {"device_ledger_peak_bytes",ledger.peak},{"device_ledger_allocations",ledger.allocations},
        {"device_ledger_live_bytes",ledger.live},{"positive_resource_retirement",probe.positive_retirement},
        {"source_workers_stopped",false},{"model_loaded",false},{"VideoOut_started",display},
        {"automatic_retries",0},{"active_slots",geometry.active_slots},{"physical_planes",geometry.physical_slots()},
        {"bank_stride",qwen_app::padded_bank_stride},
        {"source_SHA256",policy.at("native_padded_bank_layout_probe").at("source_SHA256")}};
    if(policy.contains("native_large_cache_scope"))report.update({{"schema","ps5-qwen-padded-bank-layout-result-v2"},
        {"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},{"driver_revision",owner.at("driver_revision")},
        {"profile",owner.at("profile")},{"native_archive_sha256",owner.at("native_archive_sha256")}});
    return report;
}

static void isolated_large_cache_layout(const qwen_app::Startup &startup,const Json &policy,bool &resources_started) {
    qwen_app::require_large_cache_layout_phase_scope(policy,startup.first_generation_validation,false,1);
    const auto receipt=qwen_app::read_model_receipt(startup.model_receipt);
    (void)qwen_app::validate_model_receipt(receipt);
    const auto path=model_file(startup.model_receipt,receipt.at("files").at(7).at("path").get<std::string>());
    const auto identity=model_file_identity(path,512ull<<20);
    require_model_CPU_budget();
    qwen_app::select_experimental_padded_cache_128();
    // Only the one positively owned first part is needed for the fixed slice.
    // No whole-model GGUF parser, protected source mapping or worker is started.
    qwen_app::start_native_model_sources({{path,512ull<<20,identity}});
    const auto CPU=qwen_app::admit_native_system_memory();
    const auto required=qwen_app::large_cache_layout_kernel_requirement(CPU);
    const auto VM_before_GPU=diagnostic_VM_population();
    write_fresh_report(startup.admission_report+".layout-phase-memory",{
        {"schema","ps5-qwen-cache-layout-phase-memory-result-v1"},{"pid",getpid()},
        {"run_id",policy.at("native_first_generation_validation").at("run_id")},
        {"CPU_completed",system_memory_report(CPU)},{"CPU_VM",VM_before_GPU},
        {"GPU_required_free_pages",required},{"additional_operational_pages",512},
        {"regular_startup_target_pages",CPU.kernel_target},{"whole_model_metadata_files",0},
        {"virtual_source_probes",0},{"source_workers",0},{"model_loaded",false},{"GPU_started",false}});
    if(CPU.kernel_free<required)throw std::runtime_error("The isolated layout cannot retain its operational reserve and 512 extra kernel pages");
    qwen_native_stage("isolated_layout_CPU_slice_owner_completed_scoped_GPU_headroom_admitted");
    qwen_app::inspect_vulkan_globals();
    if(!qwen_native_gpu_frontend_linked()||setenv("GGML_VK_SUBALLOCATION_BLOCK_SIZE","2147483648",1))
        throw std::runtime_error("The original native Vulkan frontend and batching policy are required");
    resources_started=true;
    qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());
    qwen_native_driver_begin();llama_backend_init();
    auto device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
    if(!device)device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
    if(!device)throw std::runtime_error("A qualified native Vulkan device is required for layout");
    std::size_t estimated=0,total=0;ggml_backend_dev_memory(device,&estimated,&total);
    const auto native=qwen_native_allocator_budget(total);
    std::int64_t physical=0;std::size_t direct=0;const auto pool=sceKernelGetDirectMemorySize();
    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&direct)<0)
        throw std::runtime_error("A fresh isolated-layout Direct observation is required");
    const auto type=ggml_backend_dev_buffer_type(device);
    qwen_app::MemoryBudget budget;budget.cpu_working=512ull<<20;budget.workspace=256ull<<20;
    const auto memory=qwen_app::admit_native_system_memory();
    qwen_app::admit_large_cache_layout_memory(budget,{native.available,direct,qwen_app::qualified_system_headroom(memory),
        ggml_backend_buft_get_max_size(type),ggml_backend_buft_get_alignment(type)});
    qwen_app::enforce_native_model_compute_limits();
    if(qwen_app::native_model_device_stats().live)throw std::runtime_error("An empty isolated layout ledger is required");
    qwen_native_stage("padded_layout_empty_device_ledger_admitted_before_allocation");
    const auto probe=qwen_app::admit_padded_bank_layout(path,
        policy.at("native_padded_bank_layout_probe").at("source_SHA256").get<std::string>(),
        qwen_native_driver_checkpoint,qwen_native_stage);
    if(model_file_identity(path,512ull<<20)!=identity)
        throw std::runtime_error("The completed original layout source changed");
    require_model_CPU_budget();
    auto report=padded_layout_result(probe,policy,false);
    report["scoped_GPU_phase_memory"]=true;
    report["VM_before_GPU"]=VM_before_GPU;
    write_fresh_report(startup.admission_report+".padded-layout.preliminary",report);
    qwen_native_driver_complete();qwen_app::stop_native_model_sources();
    report["source_workers_stopped"]=true;
    report["VM_after_GPU_and_retirement"]=diagnostic_VM_population();
    write_fresh_report(startup.admission_report+".padded-layout",report);
    qwen_native_stage("padded_layout_completed_model_not_loaded_waiting_for_ordinary_close");
    for(;;)(void)usleep(1000000);
}

int main(int argc, char ** argv) {
    qwen_native_stage("main_entered GPU_not_started=1 model_loaded=0");
    llama_model * model = nullptr;
    llama_context * context = nullptr;
    std::unique_ptr<qwen_app::LlamaEngine> engine;
    std::unique_ptr<qwen_app::NativeDisplay> display;
    qwen_app::MonitorSnapshot screen;
    bool native_resources_started = false;
    std::string validation_report;
    try {
        const auto startup = qwen_app::read_startup(argc, argv);
        qwen_native_stage("configuration_read GPU_not_started=1 model_loaded=0");
        validation_report = startup.admission_report;
        std::ifstream policy_file(startup.development_policy);
        const auto policy = Json::parse(policy_file);
        if (!policy.at("console_operations_enabled").get<bool>())
            throw std::runtime_error("Console execution is disabled for this application integration phase");
        const auto mode = startup.PLE_slice_validation ? "PLE-slice-validation" : startup.device_state_validation ? "device-state-validation" : startup.vector_bank_validation ? "vector-bank-validation" : startup.palette_validation ? "palette-validation" : startup.memory_validation ? "native-memory-validation" : startup.display_validation ? "display-validation" : startup.runtime_validation ? "runtime-validation" : startup.monitor_validation ? "monitor-validation" : startup.model_validation ? "model-validation" : startup.operator_validation ? "operator-validation" : startup.moe_validation ? "moe-validation" : startup.first_generation_validation ? "first-generation-validation" : "inference";
        if (!policy.contains("allowed_modes") || !policy.at("allowed_modes").is_array() ||
            std::find(policy.at("allowed_modes").begin(), policy.at("allowed_modes").end(), Json(mode)) == policy.at("allowed_modes").end())
            throw std::runtime_error("This application mode has not passed the preceding qualification stage");
        // A frozen fixture policy does not replace the launcher's fresh console
        // guards. Full-model inference remains independently rejected here.
        qwen_app::require_native_validation_policy(policy, mode, startup.native_display);
        if(startup.PLE_slice_validation&&qwen_app::PLE_slice_CPU_bootstrap(policy))
            throw std::runtime_error("CPU-only PLE shader bootstrap requires the isolated CPU entry point");
        std::uint32_t prefill_tokens = 1;
        const bool expert_routes=policy.contains("native_expert_routes");
        if(expert_routes){
            const auto & p=policy.at("native_expert_routes");
            if(!startup.first_generation_validation||!p.is_object()||p.size()!=5||
               p.at("schema")!="ps5-qwen-completed-expert-routes-policy-v1"||!p.at("enabled").is_boolean()||p.at("enabled")!=true||
               !p.at("maximum_records").is_number_unsigned()||p.at("maximum_records")!=qwen_app::expert_route_capacity||
               !p.at("require_complete_48_layer_processes").is_boolean()||p.at("require_complete_48_layer_processes")!=true||
               !p.at("additional_GPU_downloads").is_number_unsigned()||p.at("additional_GPU_downloads")!=0)
                throw std::runtime_error("The completed expert-route observer requires its exact bounded policy");
        }
        if (policy.contains("native_prefill")) {
            const auto & p = policy.at("native_prefill");
            if (!startup.first_generation_validation || !p.is_object() || p.size() != 4 ||
                p.at("schema") != "ps5-qwen-bounded-prefill-v1" ||
                !p.at("tokens").is_number_unsigned() ||
                p.at("tokens").get<std::uint64_t>() > 4 ||
                !p.at("all_prompt_outputs_requested").is_boolean() ||
                p.at("all_prompt_outputs_requested") != true ||
                !p.at("generated_token_batch_tokens").is_number_unsigned() ||
                p.at("generated_token_batch_tokens") != 1)
                throw std::runtime_error("The private bounded prefill policy differs");
            prefill_tokens = p.at("tokens").get<std::uint32_t>();
            if (prefill_tokens != 1 && prefill_tokens != 2 && prefill_tokens != 4)
                throw std::runtime_error("The prefill width exceeds qualified cache geometry");
        }
        if (startup.first_generation_validation && startup.port != 8086)
            throw std::runtime_error("The bounded external demonstration requires its exact admitted port");
        if (startup.first_generation_validation && (!llama_app_mapped_source_hooks() ||
            !llama_app_bounded_expert_advice_hooks() || !ggml_app_mapped_upload_hooks() ||
            !ggml_app_mapped_async_hooks() || !ggml_app_bounded_cpu_fallback_hooks() || !ggml_app_bounded_device_buffers_hooks() ||
            !ggml_app_bounded_workspace_hooks()))
            throw std::runtime_error("Every bounded source-read engine integration hook is required");
        if(policy.contains("native_boundary_memory_diagnostic")) {
            const Json expected{{"schema","ps5-qwen-boundary-memory-v1"},{"enabled",true},
                {"capacity",64},{"read_only",true},{"GPU_calls",0},{"automatic_retries",0}};
            if(!startup.first_generation_validation||policy.at("native_boundary_memory_diagnostic")!=expected)
                throw std::runtime_error("The inference-boundary memory diagnostic policy differs");
            boundary_memory_enabled=true;
        }
        // Headless delivery probes use the admitted monotonic clock and
        // publishes no monitor UTC state. Other modes keep their UTC guard.
        if(!startup.palette_validation&&!startup.vector_bank_validation&&!startup.device_state_validation&&!startup.PLE_slice_validation)qwen_app::monitor_clock().initialize(startup.clock_calibration);
        qwen_native_stage("policy_admitted GPU_not_started=1 model_loaded=0");
        llama_log_set(native_log, nullptr); ggml_log_set(native_log, nullptr);
        qwen_native_set_fault_report((startup.admission_report + ".fatal").c_str());
        if(startup.memory_validation) {
            if(!policy.value("console_validation_enabled",false))
                throw std::runtime_error("Native memory validation is not enabled");
            write_fresh_report(startup.admission_report+".before",qwen_app::observe_native_memory());
            auto result=qwen_app::run_native_memory_probe(policy);
            result["schema"]="ps5-qwen-native-memory-result-v1";result["pid"]=getpid();
            write_fresh_report(startup.admission_report,result);
            qwen_native_stage("memory_validation_completed_waiting_for_ordinary_close GPU_not_started=1 model_loaded=0");
            for(;;) (void)usleep(1000000);
        }
        if(startup.palette_validation||startup.vector_bank_validation||startup.device_state_validation||startup.PLE_slice_validation) {
            if(!policy.value("console_validation_enabled",false))
                throw std::runtime_error("Native delivery validation is not enabled");
            if(setenv("MESA_SHADER_CACHE_DISABLE","true",1))
                throw std::runtime_error("Delivery diagnostics require disabled persistent caches");
            (void)qwen_app::admit_native_startup_memory();
            qwen_app::admit_cpu_runtime(qwen_native_stage);qwen_app::inspect_vulkan_globals();
            std::int64_t physical=0;std::size_t available=0,flexible=0;
            const auto pool=sceKernelGetDirectMemorySize();
            if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&available)<0||
               sceKernelAvailableFlexibleMemorySize(&flexible)<0||available<(1ull<<30)||flexible<(64u<<20))
                throw std::runtime_error("Delivery diagnostic memory headroom is insufficient");
            if(!qwen_native_gpu_frontend_linked())throw std::runtime_error("Native driver frontend is not linked");
            if(startup.device_state_validation&&!qwen_app::device_state_fixture_linked())
                throw std::runtime_error("Host-qualified device-state fixture inputs are not linked");
            if(startup.vector_bank_validation||startup.device_state_validation||startup.PLE_slice_validation) {
                qwen_native_stage(startup.PLE_slice_validation?"PLE_slice_before_shared_shader_CPU_admission GPU_not_started=1":startup.device_state_validation?"device_state_before_shared_shader_CPU_admission GPU_not_started=1":"vector_bank_before_shared_shader_CPU_admission GPU_not_started=1");
                admit_shader_storage_CPU(policy,startup.admission_report,true,Json(startup.admission_report));
                qwen_native_stage(startup.PLE_slice_validation?"PLE_slice_shared_shader_CPU_admission_completed GPU_not_started=1":startup.device_state_validation?"device_state_shared_shader_CPU_admission_completed GPU_not_started=1":"vector_bank_shared_shader_CPU_admission_completed GPU_not_started=1");
            }
            native_resources_started=true;
            auto report=startup.PLE_slice_validation?qwen_app::admit_PLE_slice_fixture(policy,startup.admission_report+".driver.log"):startup.device_state_validation?qwen_app::admit_device_state_fixture(policy,startup.admission_report+".driver.log"):startup.vector_bank_validation?
                qwen_app::admit_vector_bank(policy,startup.admission_report+".driver.log"):
                qwen_app::admit_palette_gpu(policy,startup.admission_report+".driver.log");
            qwen_native_driver_complete();
            if(startup.vector_bank_validation||startup.device_state_validation||startup.PLE_slice_validation) {
                const auto shaders=qwen_app::native_shader_asset_stats();
                const bool prior_PLE=startup.PLE_slice_validation&&qwen_app::PLE_slice_prior_proof(policy);
                const auto current_CPU=prior_PLE?0u:shaders.assets;
                if(!shaders.initialized||shaders.failed||shaders.active_lease||shaders.external_file.read_pending||
                   !shaders.external_file.verified||shaders.CPU_verified_assets!=current_CPU||
                   shaders.decoded_calls+shaders.raw_calls<shaders.CPU_verified_assets||
                   ((startup.vector_bank_validation||startup.PLE_slice_validation)&&shaders.decoded_calls+shaders.raw_calls==shaders.CPU_verified_assets)||
                   shaders.external_file.frame_requests!=shaders.decoded_calls+shaders.raw_calls)
                    throw std::runtime_error("Vector bank shader inputs lack complete CPU and per-use retirement");
                report["shader_CPU_verified_assets"]=shaders.CPU_verified_assets;
                if(prior_PLE) {
                    report["prior_all_shader_CPU_report_SHA256"]=policy.at("native_shader_storage").at("prior_native_CPU").at("report_sha256");
                    report["prior_all_shader_CPU_assets"]=shaders.assets;
                    report["current_complete_external_file_SHA256_checked"]=true;
                }
                report["shader_module_inputs_after_CPU_verification"]=shaders.decoded_calls+shaders.raw_calls-shaders.CPU_verified_assets;
                report["all_used_shader_inputs_SHA256_checked"]=true;
                report["all_shader_input_leases_returned"]=true;
            }
            report["pid"]=getpid();report["positive_device_idle_and_epoch_retirement"]=true;
            write_fresh_report(startup.admission_report,report);
            qwen_native_stage(startup.PLE_slice_validation?"PLE_slice_validation_completed_waiting_for_ordinary_close model_loaded=0":startup.device_state_validation?"device_state_validation_completed_waiting_for_ordinary_close model_loaded=0":startup.vector_bank_validation?
                "vector_bank_validation_completed_waiting_for_ordinary_close model_loaded=0":
                "palette_validation_completed_waiting_for_ordinary_close model_loaded=0");
            for(;;)(void)usleep(1000000);
        }
        if (setenv("MESA_SHADER_CACHE_DISABLE", "true", 1) || setenv("LLAMA_APP_NO_MMAP_PREFETCH", "1", 1) ||
            setenv("GGML_VK_BOUNDED_STAGING", "1", 1) ||
            setenv("LLAMA_APP_EXPERT_POLICY", "maya-aged-lfu", 1) ||
            setenv("GGML_VK_DISABLE_ASYNC", "1", 1) || setenv("GGML_VK_SERIALIZE_SUBMISSIONS", "1", 1) ||
            setenv("GGML_VK_MAX_NODES_PER_SUBMIT", "1", 1))
            throw std::runtime_error("Required cache policy could not be set");
        if (!llama_app_mmap_prefetch_disabled()) throw std::runtime_error("The streaming loader patch is required");
        if (!llama_app_expert_policy_enabled()) throw std::runtime_error("The adaptive expert cache patch is required");
        if (!ggml_app_bounded_staging_enabled()) throw std::runtime_error("Bounded native transfer staging is required");
        if (!ggml_app_dispatch_contract_enabled()) throw std::runtime_error("The static Vulkan dispatch contract is required");
        if (startup.first_generation_validation &&
            (!ggml_app_bounded_cpu_rows_hooks() || !ggml_app_bounded_cpu_buffer_reads_hooks()))
            throw std::runtime_error("Bounded original CPU row and buffer readers are required before model admission");

        screen.state = startup.display_validation ? "display validation" : startup.runtime_validation ? "CPU runtime admission" : startup.monitor_validation || startup.operator_validation || startup.moe_validation ? "BF16 GPU admission" : "verifying model";
        screen.cpu_threads = std::thread::hardware_concurrency();
        char cpu_name[256] = {};
        std::size_t cpu_name_size = sizeof(cpu_name);
        if (!sysctlbyname("hw.model", cpu_name, &cpu_name_size, nullptr, 0) && cpu_name_size &&
            std::memchr(cpu_name, 0, sizeof(cpu_name))) screen.cpu_name = cpu_name;
        // Combined admission starts scanout only after the current graph has
        // passed numerical verification and positive completed retirement.
        if (startup.native_display && !startup.monitor_validation) {
            qwen_native_stage("before_display_start compute_dispatches=0 model_loaded=0");
            display = std::make_unique<qwen_app::NativeDisplay>();
            native_resources_started = true;
            display->start(screen);
            qwen_native_stage("first_display_frame_completed compute_dispatches=0 model_loaded=0");
        }
        if (startup.monitor_validation || startup.display_validation || startup.runtime_validation || startup.operator_validation || startup.moe_validation) {
            if (!policy.value("console_validation_enabled", false)) throw std::runtime_error("Native validation is not enabled");
            std::vector<std::uint16_t> original_weights;
            if (startup.operator_validation || startup.moe_validation) {
                qwen_native_stage("before_original_weight_fixture_hash GPU_not_started=1 model_loaded=0");
                original_weights = startup.moe_validation ? qwen_app::load_original_moe_fixture(startup.weight_fixture) :
                    qwen_app::load_original_weight_fixture(startup.weight_fixture, qwen_app::original_weight_fixture_sha256);
                qwen_native_stage("original_weight_fixture_hash_and_finite_check_passed GPU_not_started=1");
            }
            if (startup.display_validation) {
                if (!display) throw std::runtime_error("Display validation requires native presentation");
                struct ps5_heap_stats heap{}; ps5_heap_stats(&heap);
                write_fresh_report(startup.admission_report, {{"schema", "ps5-qwen-display-admission-v1"},
                    {"pid", getpid()}, {"first_frame_completed", true}, {"model_loaded", false},
                    {"Vulkan_initialized", false}, {"compute_dispatches", 0}, {"display_buffer_bytes", 32u << 20},
                    {"heap_mapped_bytes", heap.mapped_bytes}, {"heap_peak_bytes", heap.peak_bytes},
                    {"cpu_name", screen.cpu_name}, {"cpu_threads", screen.cpu_threads}});
            } else if (startup.runtime_validation) {
                write_fresh_report(startup.admission_report + ".started", {{"stage", "before_cpu_runtime_admission"},
                    {"pid", getpid()}, {"model_loaded", false}, {"Vulkan_initialized", false}});
                const auto admission = qwen_app::admit_cpu_runtime(qwen_native_stage);
                qwen_app::VulkanDiscovery discovery;
                if (startup.vulkan_global_discovery) discovery = qwen_app::inspect_vulkan_globals();
                write_fresh_report(startup.admission_report, {{"schema", "ps5-qwen-cpu-runtime-admission-v1"},
                    {"pid", getpid()}, {"model_loaded", false}, {"Vulkan_initialized", false},
                    {"metadata_bytes", admission.metadata_bytes}, {"exception_roundtrip", admission.exception_roundtrip},
                    {"Vulkan_global_queries_executed", startup.vulkan_global_discovery},
                    {"Vulkan_api_version", discovery.api_version}, {"Vulkan_instance_extensions", discovery.instance_extensions},
                    {"compute_dispatches", 0}});
            } else {
                screen.state = "checking original BF16 GPU operation";
                if (display) display->publish(screen);
                native_resources_started = true;
                std::int64_t physical = 0; std::size_t available = 0, flexible = 0;
                const auto pool = sceKernelGetDirectMemorySize();
                if (pool <= 0 || sceKernelAvailableDirectMemorySize(0, pool, 65536, &physical, &available) < 0 ||
                    sceKernelAvailableFlexibleMemorySize(&flexible) < 0 || available < (1ull << 30) ||
                    flexible < (startup.moe_validation ? (192u << 20) : (64u << 20)))
                    throw std::runtime_error("Observed memory headroom is insufficient for bounded GPU admission");
                const auto clock_start = std::chrono::steady_clock::now();
                if (usleep(250000)) throw std::runtime_error("Native clock interval observation failed");
                const double clock_interval_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - clock_start).count();
                if (clock_interval_ms < 200 || clock_interval_ms > 2000)
                    throw std::runtime_error("Native millisecond clock scale is not admitted");
                write_fresh_report(startup.admission_report + ".started", {{"stage", "before_gpu_admission"},
                    {"model_loaded", false}, {"pid", getpid()}, {"direct_largest_available_bytes", available},
                    {"flexible_available_bytes", flexible}, {"sleep_request_us", 250000}, {"observed_clock_interval_ms", clock_interval_ms}});
                qwen_native_stage("before_BF16_GPU_admission model_loaded=0");
                qwen_app::admit_cpu_runtime(qwen_native_stage);
                qwen_app::inspect_vulkan_globals();
                if(!qwen_native_gpu_frontend_linked())throw std::runtime_error("Native driver frontend is not linked");
                qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());
                qwen_native_driver_begin();
                qwen_native_stage("before_llama_backend_initialization model_loaded=0");
                llama_backend_init();
                qwen_native_stage("llama_backend_initialization_completed model_loaded=0");
                if (startup.moe_validation) {
                    const auto admission = qwen_app::admit_original_moe(original_weights, qwen_native_stage);
                    qwen_native_driver_complete();
                    const auto & metric = admission.metric;
                    write_fresh_report(startup.admission_report, {{"schema", "ps5-qwen-original-moe-admission-v1"},
                        {"pid", getpid()}, {"model_loaded", false}, {"full_model_inference", false},
                        {"fixture_sha256", qwen_app::moe_fixture_sha256}, {"fixture_bytes", original_weights.size() * 2},
                        {"matrix_columns", qwen_app::moe_columns}, {"matrix_rows", qwen_app::moe_rows},
                        {"experts", qwen_app::moe_experts}, {"selected_experts", qwen_app::moe_selected},
                        {"expert_ids", qwen_app::moe_expert_ids}, {"tokens", 1}, {"operation", "GGML_OP_MUL_MAT_ID"},
                        {"CPU_reference", "PS5 scalar double accumulation"},
                        {"absolute_tolerance", 1e-5}, {"relative_tolerance", 1e-5}, {"normalized_rmse_limit", 0.01},
                        {"graph_compute_calls", 1}, {"maximum_upload_chunk_bytes", 8u << 20},
                        {"backend", admission.backend}, {"passed", admission.passed}, {"values", metric.values},
                        {"finite", metric.finite},
                        {"max_absolute_error", metric.finite ? Json(metric.max_absolute_error) : Json(nullptr)},
                        {"normalized_rmse", std::isfinite(metric.normalized_rmse) ? Json(metric.normalized_rmse) : Json(nullptr)},
                        {"expected", admission.expected}, {"actual", admission.actual}, {"elapsed_ms", admission.elapsed_ms}});
                    if (!admission.passed) throw std::runtime_error("Original BF16 MoE admission failed fixed numerical gates");
                    qwen_native_stage("original_MoE_admission_passed model_loaded=0");
                } else if (startup.operator_validation) {
                    const auto admission = qwen_app::admit_original_weight_operations(original_weights, qwen_native_stage);
                    qwen_native_driver_complete();
                    auto metric = [](const qwen_app::OperatorMetric & value) {
                        return Json{{"values", value.values}, {"finite", value.finite}, {"passed", value.passed},
                            {"max_absolute_error", value.finite ? Json(value.max_absolute_error) : Json(nullptr)},
                            {"normalized_rmse", std::isfinite(value.normalized_rmse) ? Json(value.normalized_rmse) : Json(nullptr)}};
                    };
                    write_fresh_report(startup.admission_report + ".outputs", {
                        {"schema", "ps5-qwen-operation-readbacks-v1"}, {"pid", getpid()},
                        {"fixture_sha256", qwen_app::original_weight_fixture_sha256}, {"model_loaded", false},
                        {"matvec", admission.actual}, {"rms_norm", admission.norm_actual}, {"silu", admission.silu_actual}});
                    write_fresh_report(startup.admission_report, {{"schema", "ps5-qwen-original-operator-admission-v1"},
                        {"pid", getpid()}, {"model_loaded", false}, {"full_model_inference", false},
                        {"fixture_sha256", qwen_app::original_weight_fixture_sha256},
                        {"fixture_bytes", original_weights.size() * 2}, {"matrix_columns", qwen_app::operator_columns},
                        {"matrix_rows", qwen_app::operator_rows}, {"CPU_reference", "PS5 scalar double accumulation"},
                        {"absolute_tolerance", 1e-5}, {"relative_tolerance", 1e-5}, {"normalized_rmse_limit", 0.01},
                        {"graph_compute_calls", 1}, {"backend", admission.backend}, {"passed", admission.passed},
                        {"matvec", metric(admission.matvec)}, {"rms_norm", metric(admission.rms_norm)},
                        {"silu", metric(admission.silu)}, {"matvec_expected", admission.expected},
                        {"matvec_actual", admission.actual}, {"elapsed_ms", admission.elapsed_ms}});
                    if (!admission.passed) throw std::runtime_error("Original-weight operation admission failed fixed numerical gates");
                    qwen_native_stage("original_weight_operations_admission_passed model_loaded=0");
                } else {
                const auto admission = qwen_app::admit_bf16_gpu(qwen_native_stage);
                qwen_native_driver_complete();
                const bool finite = std::all_of(admission.actual.begin(), admission.actual.end(), [](float value) { return std::isfinite(value); });
                const Json record = {{"schema", "ps5-qwen-bf16-admission-v1"}, {"model_loaded", false}, {"pid", getpid()},
                    {"fixture", "BF16 32x16 weights times F32 32-vector; F32 output"},
                    {"absolute_tolerance", 1e-5}, {"relative_tolerance", 1e-5}, {"passed", admission.passed},
                    {"backend", admission.backend}, {"expected", admission.expected}, {"actual", admission.actual},
                    {"finite_outputs", finite}, {"graph_compute_calls", 1},
                    {"max_absolute_error", finite ? Json(admission.max_absolute_error) : Json(nullptr)}, {"elapsed_ms", admission.elapsed_ms}};
                write_fresh_report(startup.admission_report, record);
                if (!admission.passed) throw std::runtime_error("Original-BF16 GPU admission failed its fixed numerical gate");
                qwen_native_stage("BF16_GPU_admission_passed model_loaded=0");
                }
            }
            if (display && display->failed()) throw std::runtime_error("Native display completion failed; backing retained");
            qwen_app::HardwareInfo hardware;
            hardware.cpu_name = screen.cpu_name; hardware.logical_cpu_threads = screen.cpu_threads;
            // The native SDK declares CLOCKS_PER_SEC=128; the provider's clock
            // units have not passed qualification. Keep CPU percentage absent.
            hardware.sample_process_cpu = false;
            // Display-only admission must not enumerate or initialize Vulkan.
            auto device = startup.monitor_validation || startup.operator_validation || startup.moe_validation ? ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU) : nullptr;
            if ((startup.monitor_validation || startup.operator_validation || startup.moe_validation) && !device) device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
            if (device) {
                if (const auto * name = ggml_backend_dev_description(device)) hardware.gpu_name = name;
                std::size_t available = 0, total = 0; ggml_backend_dev_memory(device, &available, &total);
                if (total) { hardware.gpu_total_bytes = total; hardware.gpu_free_bytes = available; }
            }
            if (startup.monitor_validation && startup.native_display) {
                std::int64_t physical = 0; std::size_t available = 0;
                const auto pool = sceKernelGetDirectMemorySize();
                if (pool <= 0 || sceKernelAvailableDirectMemorySize(0, pool, 65536, &physical, &available) < 0 ||
                    available < (128u << 20))
                    throw std::runtime_error("Fresh post-compute display memory headroom is insufficient");
                screen.state = "BF16 validated / monitor idle";
                screen.gpu_name = hardware.gpu_name;
                screen.gpu_total_bytes = hardware.gpu_total_bytes; screen.gpu_free_bytes = hardware.gpu_free_bytes;
                qwen_native_stage("before_display_start_after_BF16_completed graph_compute_calls=1 model_loaded=0");
                display = std::make_unique<qwen_app::NativeDisplay>();
                display->start(screen);
                if (display->failed()) throw std::runtime_error("Post-compute native display failed; backing retained");
                qwen_native_stage("first_display_frame_after_BF16_completed graph_compute_calls=1 model_loaded=0");
                const auto & clock = qwen_app::monitor_clock();
                const auto uncertainty = clock.initial_uncertainty_ms();
                write_fresh_report(startup.admission_report + ".display", {
                    {"schema", "ps5-qwen-display-after-bf16-v1"}, {"pid", getpid()},
                    {"first_frame_completed", true}, {"BF16_passed_before_display", true},
                    {"positive_completion_and_retirement_before_display", true},
                    {"Vulkan_initialized", true}, {"model_loaded", false}, {"graph_compute_calls", 1},
                    {"display_buffer_bytes", 32u << 20}, {"pre_display_direct_available_bytes", available},
                    {"clock_source", clock.source()}, {"clock_calibrated", clock.calibrated()},
                    {"initial_clock_uncertainty_ms", uncertainty ? Json(*uncertainty) : Json(nullptr)},
                    {"monitor_epoch_ms", clock.now()}});
            }
            class NoInference final : public qwen_app::Engine {
                std::uint32_t tokenize(const std::string &) override { throw std::logic_error("No model loaded"); }
                void prefill(std::uint32_t) override { throw std::logic_error("No model loaded"); }
                qwen_app::Token next() override { throw std::logic_error("No model loaded"); }
                void finish() override {}
            } no_inference;
            qwen_native_stage("before_monitor_HTTP_service");
            const auto served = qwen_app::serve_http(no_inference, startup.web_assets, "{{ '' }}", startup.port, false, hardware,
                display ? std::function<void(const qwen_app::MonitorSnapshot &)>([&](const auto & snapshot) { display->publish(snapshot); })
                        : std::function<void(const qwen_app::MonitorSnapshot &)>{}, true);
            qwen_native_stage("monitor_HTTP_service_returned");
            throw std::runtime_error(served ? "Monitor HTTP listener failed" : "Monitor HTTP listener stopped unexpectedly");
        }
        if ((startup.model_validation || startup.first_generation_validation) && !policy.value("console_validation_enabled", false))
            throw std::runtime_error("Original model CPU validation is not enabled");
        bool model_CPU_runtime_admitted = false;
        const bool SELF_read_control=policy.contains("native_SELF_read_control");
        bool SELF_control_direct=true;
        if(SELF_read_control) {
            const auto &control=policy.at("native_SELF_read_control");
            const auto mode=control.at("read_mode").get<std::string>();
            if(!startup.first_generation_validation||control.at("schema")!="ps5-qwen-SELF-read-CPU-policy-v1"||
               control.at("CPU_only")!=true||control.at("maximum_read_window_bytes")!=(1u<<20)||
               control.at("quiet_seconds")!=5||control.at("automatic_retries")!=0||
               (mode!="direct"&&mode!="buffered"))
                throw std::runtime_error("The standalone SELF read CPU control is not admitted");
            SELF_control_direct=mode=="direct";
        }
        if (startup.first_generation_validation) {
            const auto & gate = policy.at("native_first_generation_validation");
            // This exclusive marker consumes the attempt before verification,
            // model loading or any GPU work. It is never overwritten or removed.
            write_fresh_report(startup.admission_report + ".first.start", {
                {"schema", "ps5-qwen-first-generation-start-v1"}, {"run_id", gate.at("run_id")}, {"pid", getpid()},
                {"candidate_SELF_sha256", gate.at("candidate_SELF_sha256")},
                {"model_receipt_sha256", gate.at("model_receipt_sha256")},
                {"model_loaded", false}, {"Vulkan_initialized", false}});
            if (policy.contains("native_source_schedule")) {
                if (policy.at("native_source_schedule").at("startup_integrity_direct") != true)
                    throw std::runtime_error("The selected source candidate requires bounded direct startup integrity");
                qwen_app::enable_native_memory_backpressure();
                qwen_native_stage("startup_integrity_memory_admission_before_IO GPU_not_started=1");
                (void)qwen_app::admit_native_system_memory();
                qwen_native_stage("startup_integrity_memory_admission_completed GPU_not_started=1");
                write_fresh_report(startup.admission_report+".system-memory.before-startup-integrity",
                    system_memory_report(qwen_app::observe_native_system_memory()));
                if(SELF_read_control)
                    qwen_app::verify_native_startup_file_control("/app0/eboot.bin",gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
                        gate.at("candidate_SELF_sha256").get<std::string>(),20,SELF_control_direct);
                else qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
                        gate.at("candidate_SELF_sha256").get<std::string>(),60);
                qwen_app::verify_native_startup_file_direct(startup.model_receipt,gate.at("model_receipt_bytes").get<std::uint64_t>(),
                    gate.at("model_receipt_sha256").get<std::string>(),30);
                write_fresh_report(startup.admission_report+".system-memory.after-startup-integrity",
                    system_memory_report(qwen_app::observe_native_system_memory()));
                qwen_native_stage("complete_SELF_and_receipt_direct_SHA256_passed GPU_not_started=1");
            } else {
                qwen_app::verify_model_file("/app0/eboot.bin", gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
                    gate.at("candidate_SELF_sha256").get<std::string>(), {}, 60);
                qwen_app::verify_model_file(startup.model_receipt, gate.at("model_receipt_bytes").get<std::uint64_t>(),
                    gate.at("model_receipt_sha256").get<std::string>(), {}, 30);
            }
            // Admit the CPU clock/context once, before metadata I/O can consume
            // kernel pages. All model metadata and GPU admission still follow.
            qwen_app::admit_cpu_runtime(qwen_native_stage);
            model_CPU_runtime_admitted = true;
            if (!policy.contains("native_source_schedule")) qwen_app::enable_native_memory_backpressure();
        }
        if(policy.contains("native_report_CPU_diagnostic")) {
            const Json expected={{"schema","ps5-qwen-report-CPU-diagnostic-v1"},{"enabled",true},
                {"files",6},{"maximum_JSON_bytes",16384},{"maximum_window_bytes",1048576},
                {"idle_control_ms",60},{"GPU_calls",0},{"model_payload_reads",0},{"automatic_retries",0}};
            if(!startup.first_generation_validation||policy.at("native_report_CPU_diagnostic")!=expected||!boundary_memory_enabled)
                throw std::runtime_error("The exact CPU-only metadata persistence policy is required");
            const Json fixture={{"schema","ps5-qwen-token-CPU-fixture-v1"},{"synthetic_not_inference",true},
                {"id","CPU-fixture"},{"type","CPU-fixture-token"},{"state","CPU validation"},{"ordinal",1},
                {"token_id",16},{"piece_bytes",{49}},{"elapsed_ms",57591.542362987995},{"error",0},
                {"metrics",{{"prompt_tokens",30},{"generated_tokens",1},{"prefill_ms",57563.821539998055},
                    {"total_ms",57591.542362987995},{"ttft_ms",57591.542362987995},{"decode_tokens_per_second",nullptr}}},
                {"expert_cache",{{"hits",127},{"misses",24960},{"uploaded_bytes",192056524800ull},{"prefetch_advice_bytes",0}}},
                {"completed_performance",{{"source_bytes",94558832640ull},{"source_chunks",12345},
                    {"source_completed_windows",12345},{"source_read_ns",50028106839ull},
                    {"source_consumer_ns",5707173866ull},{"process_calls",21},{"process_ns",59469428065ull},
                    {"source_physical_read_bytes",95012347200ull},{"source_physical_read_calls",12999},
                    {"source_parallel_batches",1024},{"source_coalesced_batches",512},{"source_selected_serial_batches",256}}},
                {"completed_path_counters",{{"BF16_indexed_matrix_calls",3024},{"BF16_indexed_vector_calls",0},
                    {"mapped_coherent_write_bytes",94539859548ull},{"staging_write_bytes",0}}}};
            sample_boundary_memory("report_CPU_initial_serialization_before");
            const auto fixture_bytes=fixture.dump(2)+"\n";
            sample_boundary_memory("report_CPU_initial_serialization_returned");
            if(fixture_bytes.size()>16384||!ps5_heap_owns(fixture_bytes.data()))
                throw std::runtime_error("The report CPU fixture requires a small tracked Direct source");
            const auto prelude=boundary_memory_report();Json reports=Json::array();
            const auto begun=qwen_app::ProfileClock::now();
            const std::array<ReportWriteMode,6> modes{{ReportWriteMode::ordinary_heap,ReportWriteMode::ordinary_stack,
                ReportWriteMode::direct,ReportWriteMode::direct,ReportWriteMode::ordinary_stack,ReportWriteMode::ordinary_heap}};
            qwen_native_stage("report_CPU_fixture_started_GPU_not_started");
            for(std::size_t i=0;i<modes.size();++i) {
                if(qwen_app::ProfileClock::now()-begun>std::chrono::seconds(60))
                    throw std::runtime_error("CPU metadata persistence diagnostic exceeded its finite bound");
                metadata_direct_guard();sample_boundary_memory("report_CPU_idle_before");
                const struct timespec quiet{0,60000000};
                if(nanosleep(&quiet,nullptr))throw std::runtime_error("CPU metadata idle control did not return");
                sample_boundary_memory("report_CPU_idle_returned");
                const auto path=startup.admission_report+".report-CPU-"+std::to_string(i);
                report_write_mode=modes[i];report_CPU_probe=true;write_fresh_report(path,fixture);
                report_CPU_probe=false;report_write_mode=ReportWriteMode::ordinary_heap;
                reports.push_back({{"ordinal",i},{"mode",static_cast<unsigned>(modes[i])},{"native_path",path},
                    {"JSON_bytes",fixture_bytes.size()},{"memory",boundary_memory_report()},{"all_file_calls_returned",true}});
            }
            write_fresh_report(startup.admission_report+".report-CPU",{
                {"schema","ps5-qwen-report-CPU-result-v1"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"uid",getuid()},{"euid",geteuid()},{"fixture_JSON_bytes",fixture_bytes.size()},
                {"initial_serialization",prelude},{"reports",reports},{"GPU_calls",0},{"model_payload_reads",0},
                {"model_loaded",false},{"Vulkan_initialized",false},{"VideoOut_started",false},
                {"all_six_files_closed",true},{"state","CPU_report_completed_waiting_for_ordinary_close"}});
            qwen_native_stage("report_CPU_diagnostic_completed_GPU_not_started_waiting_for_ordinary_close");
            for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        if(policy.contains("native_frame_CPU_diagnostic")) {
            const Json expected={{"schema","ps5-qwen-frame-CPU-diagnostic-v1"},{"enabled",true},
                {"frame_bytes",8294454},{"maximum_window_bytes",1048576},{"GPU_calls",0},
                {"model_payload_reads",0},{"automatic_retries",0}};
            if(!startup.first_generation_validation || policy.at("native_frame_CPU_diagnostic")!=expected)
                throw std::runtime_error("The exact standalone CPU frame diagnostic policy is required");
            const auto &gate=policy.at("native_first_generation_validation");
            write_fresh_report(startup.admission_report+".frame-CPU-start",{
                {"pid",getpid()},{"run_id",gate.at("run_id")},{"uid",getuid()},{"euid",geteuid()},
                {"GPU_calls",0},{"model_loaded",false}});
            qwen_native_stage("frame_CPU_fixture_started_GPU_not_started");
            qwen_app::NativeDisplay::write_CPU_frame_fixture(startup.admission_report+".frame-CPU.bmp");
            write_fresh_report(startup.admission_report+".frame-CPU",{
                {"schema","ps5-qwen-frame-CPU-result-v1"},{"pid",getpid()},{"run_id",gate.at("run_id")},
                {"frame_bytes",8294454},{"all_frame_calls_returned",true},{"GPU_calls",0},
                {"model_loaded",false},{"Vulkan_initialized",false},{"VideoOut_started",false},
                {"state","CPU_frame_completed_waiting_for_ordinary_close"}});
            qwen_native_stage("frame_CPU_diagnostic_completed_GPU_not_started_waiting_for_ordinary_close");
            for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        if(SELF_read_control) {
            const auto before=diagnostic_VM_population();
            const auto begun=qwen_app::ProfileClock::now();std::this_thread::sleep_for(std::chrono::seconds(5));
            const auto elapsed=qwen_app::profile_elapsed_ns(begun);const auto after=diagnostic_VM_population();
            const auto &gate=policy.at("native_first_generation_validation");
            write_fresh_report(startup.admission_report+".SELF-read-control",{
                {"schema","ps5-qwen-SELF-read-CPU-result-v1"},{"pid",getpid()},{"run_id",gate.at("run_id")},
                {"read_mode",SELF_control_direct?"direct":"buffered"},{"maximum_read_window_bytes",1u<<20},
                {"SELF_bytes_verified",gate.at("candidate_SELF_bytes")},{"SELF_sha256",gate.at("candidate_SELF_sha256")},
                {"all_startup_SHA256_passed",true},{"all_native_read_calls_returned",true},{"quiet_ns",elapsed},
                {"VM_before_quiet",before},{"VM_after_quiet",after},
                {"original_memory_predicate_before_every_SELF_read",true},{"memory_predicates_or_reserves_relaxed",false},
                {"model_metadata_files",0},{"source_virtual_calls",0},{"source_workers",0},{"GPU_calls",0},
                {"shader_storage_initialized",false},{"Vulkan_initialized",false},{"model_loaded",false},
                {"state","CPU_SELF_control_completed_waiting_for_ordinary_close"}});
            qwen_native_stage("startup_SELF_CPU_control_completed_GPU_not_started_waiting_for_ordinary_close");
            for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        const bool shader_startup_memory_diagnostic=policy.contains("native_shader_startup_memory_diagnostic");
        Json shader_startup_VM_before;
        if(shader_startup_memory_diagnostic) {
            qwen_app::require_shader_startup_memory_policy(policy);
            if(!startup.first_generation_validation||!boundary_memory_enabled||display)
                throw std::runtime_error("Shader startup attribution requires the independent headless CPU path");
            shader_startup_VM_before=diagnostic_VM_population();
            if(!qwen_app::begin_native_stage_memory_probe())
                throw std::runtime_error("Shader startup stage attribution cannot be reentered");
        }
        admit_shader_storage_CPU(policy,startup.admission_report,startup.first_generation_validation,
            policy.contains("native_first_generation_validation")?policy.at("native_first_generation_validation").at("run_id"):Json(nullptr));
        if(policy.contains("native_cache_layout_phase_memory"))
            isolated_large_cache_layout(startup,policy,native_resources_started);
        if(shader_startup_memory_diagnostic) {
            const bool complete=qwen_app::end_native_stage_memory_probe();
            if(!complete)throw std::runtime_error("Shader startup stage observations did not completely return");
            const auto VM_after=diagnostic_VM_population();Json samples=Json::array();
            for(std::size_t i=0;i<qwen_app::native_stage_memory_probe_count();++i) {
                const auto *s=qwen_app::native_stage_memory_probe_sample(i);
                if(!s||!s->valid)throw std::runtime_error("Shader startup stage observation is missing or invalid");
                samples.push_back({{"phase",s->phase},{"idle_before_ns",s->idle_before_ns},{"before_ns",s->before_ns},
                    {"write_after_ns",s->write_after_ns},{"after_ns",s->after_ns},{"free_idle_before",s->free_idle_before},
                    {"free_before",s->free_before},{"free_after_write",s->free_after_write},{"free_after",s->free_after},{"valid",true}});
            }
            const auto operations=boundary_memory_report();
            const auto shader_input=qwen_app::native_shader_file_stats();
            if(!shader_input.verified||shader_input.failed||shader_input.read_pending)
                throw std::runtime_error("Shader startup file ownership did not positively return");
            write_fresh_report(startup.admission_report+".shader-startup-memory",{
                {"schema","ps5-qwen-shader-startup-memory-result-v1"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"VM_before",shader_startup_VM_before},{"VM_after",VM_after},{"samples",samples},
                {"operation_boundaries",operations},{"matched_idle_ns",qwen_app::stage_memory_probe_idle_ns},
                {"shader_read_calls",shader_input.read_calls},{"shader_returned_bytes",shader_input.returned_bytes},
                {"shader_file_bytes",shader_input.file_bytes},{"shader_input_window_bytes",shader_input.input_window_bytes},
                {"all_shader_input_calls_returned",true},{"CPU_only",true},{"GPU_calls",0},{"source_workers",0},
                {"model_metadata_files",0},{"model_loaded",false},{"ordinary_OS_close_required",true}});
            qwen_native_stage("shader_startup_memory_CPU_completed_GPU_not_started_waiting_for_ordinary_close");
            for(;;)(void)usleep(1000000);
        }
        if(startup.model_validation || startup.first_generation_validation) {
            const bool selected_startup = startup.first_generation_validation && policy.contains("native_source_schedule");
            if (selected_startup && policy.at("native_source_schedule").at("require_kernel_target_before_metadata") != true)
                throw std::runtime_error("The selected source candidate requires stronger startup memory admission");
            const auto memory=selected_startup ? qwen_app::admit_native_startup_memory() :
                startup.first_generation_validation ? qwen_app::admit_native_system_memory() : qwen_app::observe_native_system_memory();
            auto initial_memory_report=system_memory_report(memory);
            if (selected_startup) initial_memory_report["startup_kernel_target_required"]=true;
            write_fresh_report(startup.admission_report+".system-memory.before-integrity",initial_memory_report);
            wait_for_initial_model_CPU_budget();
            qwen_native_stage("scoped_CPU_Flexible_kernel_memory_admitted_before_model_integrity GPU_not_started=1 model_loaded=0");
        }
        const auto receipt = qwen_app::read_model_receipt(startup.model_receipt);
        const auto expected_mapped_files=qwen_app::validate_model_receipt(receipt);
        const auto split_integrity = startup.first_generation_validation ?
            qwen_app::split_model_integrity(policy.at("native_first_generation_validation"),receipt,expected_mapped_files) :
            std::optional<qwen_app::SplitModelIntegrity>{};
        const auto prior_integrity = split_integrity ? std::optional<qwen_app::PriorModelIntegrity>(split_integrity->prior) :
            startup.first_generation_validation ?
            qwen_app::prior_model_integrity(policy.at("native_first_generation_validation"), receipt, expected_mapped_files) :
            std::optional<qwen_app::PriorModelIntegrity>{};
        const auto receipt_separator = startup.model_receipt.find_last_of('/');
        const auto model_directory = startup.model_receipt.substr(0, receipt_separator);
        bool identity_report_written = false;
        std::optional<qwen_app::ModelIdentityNamespace> identity_namespace;
        auto require_prior_metadata = [&] {
            if (!prior_integrity) return;
            if (receipt_separator == std::string::npos) throw std::runtime_error("The sealed model requires its canonical directory");
            const auto directory = model_directory_identity(model_directory);
            const auto receipt_identity = model_file_identity(startup.model_receipt,
                policy.at("native_first_generation_validation").at("model_receipt_bytes").get<std::uint64_t>());
            if (!identity_report_written) {
                Json report{{"schema","ps5-qwen-native-model-identity-v1"},{"pid",getpid()},
                    {"model_receipt_path",startup.model_receipt},{"directory",directory},{"receipt",receipt_identity},
                    {"expected_directory",prior_integrity->directory},{"expected_receipt",prior_integrity->receipt},
                    {"model_loaded",false},{"Vulkan_initialized",false}};
                try {
                    report["app0_directory"] = model_directory_identity("/app0/qwen-runtime/model");
                    report["app0_receipt"] = model_file_identity("/app0/qwen-runtime/model/model-receipt.json",
                        policy.at("native_first_generation_validation").at("model_receipt_bytes").get<std::uint64_t>());
                } catch (const std::exception & error) { report["app0_metadata_error"] = error.what(); }
                write_fresh_report(startup.admission_report + ".identity", report);
                identity_report_written = true;
            }
            if (!identity_namespace) {
                const auto & gate = policy.at("native_first_generation_validation");
                const bool allow_translation = gate.value("allow_app0_model_device_translation", false);
                if (allow_translation && startup.model_receipt != "/app0/qwen-runtime/model/model-receipt.json")
                    throw std::runtime_error("Model device translation requires the exact original app0 model path");
                identity_namespace.emplace(prior_integrity->directory, directory, prior_integrity->receipt,
                    receipt_identity, allow_translation);
                write_fresh_report(startup.admission_report + ".namespace", {
                    {"schema","ps5-qwen-native-model-namespace-v1"},{"pid",getpid()},
                    {"canonical_source_device",identity_namespace->source_device()},
                    {"application_device",identity_namespace->application_device()},
                    {"inode_mode_owner_size_and_all_timestamps_exact",true},
                    {"candidate_SELF_and_receipt_SHA_verified",true},
                    {"model_loaded",false},{"Vulkan_initialized",false}});
            }
            if (!identity_namespace->matches(directory, prior_integrity->directory) ||
                !identity_namespace->matches(receipt_identity, prior_integrity->receipt))
                throw std::runtime_error("Sealed original model directory or receipt changed after native SHA verification");
            if(split_integrity&&!identity_namespace->matches(model_directory_identity(
                    model_directory+"/"+split_integrity->part_directory),split_integrity->part_directory_identity))
                throw std::runtime_error("Sealed split-part directory changed after complete logical SHA verification");
        };
        require_prior_metadata();
        const bool direct_metadata=policy.contains("native_direct_metadata");
        if(policy.contains("native_metadata_memory_diagnostic")) {
            qwen_app::require_metadata_memory_policy(policy);
            if(!startup.first_generation_validation||receipt.at("files").size()!=qwen_app::MetadataMemoryProbe::files||display)
                throw std::runtime_error("Metadata memory diagnostic requires the exact headless CPU-only scope");
            metadata_memory.enable();
        }
        if(direct_metadata) {
            const auto &candidate=policy.at("native_direct_metadata");
            if(!startup.first_generation_validation||!prior_integrity||!policy.contains("native_source_schedule")||
               candidate.at("schema")!="ps5-qwen-direct-metadata-policy-v1"||candidate.at("enabled")!=true||
               candidate.at("window_bytes")!=qwen_app::metadata_direct_window||
               candidate.at("maximum_metadata_prefix_bytes")!=qwen_app::metadata_direct_limit||
               candidate.at("reuse_active_source_window")!=true||candidate.at("unchanged_memory_and_integrity_guards")!=true)
                throw std::runtime_error("Bounded original GGUF Direct metadata policy is not admitted");
            qwen_app::enable_native_direct_metadata();
        }
        // A receipt records host conversion provenance, not a fresh console hash
        // check. Deployment must independently verify every transferred file.
        qwen_app::ModelFootprint footprint; std::unordered_set<std::string> tensor_names;
        std::vector<qwen_app::ModelMappingFile> mapping_files;
        std::vector<ModelFileIdentity> file_identities;
        const auto verification_started = std::chrono::steady_clock::now();
        const auto verification_deadline = verification_started +
            std::chrono::seconds(prior_integrity ? 60 : qwen_app::native_model_verification_seconds);
        bool first = true;
        unsigned file_index=0;
        std::uint64_t fully_verified_bytes=0;
        for (const auto & file : receipt.at("files")) {
            ++file_index;
            const auto file_bytes=file.at("bytes").get<std::uint64_t>();
            if (startup.first_generation_validation)
                file_identities.push_back(model_file_identity(
                    model_file(startup.model_receipt,file.at("path").get<std::string>()),
                    split_integrity?split_integrity->prior.files.at(file_index-1)[5]:file_bytes));
            if (prior_integrity && !identity_namespace->matches(file_identities.back(), prior_integrity->files.at(file_index - 1)))
                throw std::runtime_error("Sealed original model file changed after native SHA verification");
            if(direct_metadata)qwen_app::register_native_direct_metadata(
                model_file(startup.model_receipt,file.at("path").get<std::string>()),file_identities.back(),file_bytes);
            screen.state="verifying original model bytes";
            const auto remaining = std::chrono::duration_cast<std::chrono::seconds>(
                verification_deadline - std::chrono::steady_clock::now()).count();
            if (remaining <= 0) throw std::runtime_error("Complete original-model verification deadline expired before backend initialization");
            if (!prior_integrity) {
            qwen_native_stage("model_file_integrity_started_before_backend_initialization");
            qwen_app::verify_model_file(model_file(startup.model_receipt,file.at("path").get<std::string>()),
                file_bytes,file.at("sha256").get<std::string>(),[&](std::uint64_t verified){
                    screen.message="File "+std::to_string(file_index)+"/"+std::to_string(receipt.at("files").size())+
                        ": "+std::to_string(verified>>20)+" MiB verified";
                    if(display)display->publish(screen);
                    const auto elapsed=std::chrono::duration_cast<std::chrono::milliseconds>(
                        std::chrono::steady_clock::now()-verification_started).count();
                    const auto total=qwen_app::checked_memory_sum(fully_verified_bytes,verified);
                    if(verified>file_bytes||total>expected_mapped_files)
                        throw std::runtime_error("Original-model integrity progress escaped its admitted byte count");
                    const auto stage="model_file_integrity_progress file="+std::to_string(file_index)+
                        " files="+std::to_string(receipt.at("files").size())+
                        " verified_file_bytes="+std::to_string(verified)+" file_bytes="+std::to_string(file_bytes)+
                        " total_verified_bytes="+std::to_string(total)+" total_bytes="+std::to_string(expected_mapped_files)+
                        " elapsed_ms="+std::to_string(elapsed)+" deadline_seconds="+
                        std::to_string(qwen_app::native_model_verification_seconds);
                    qwen_native_stage(stage.c_str());
                }, static_cast<unsigned>(remaining));
            }
            fully_verified_bytes=qwen_app::checked_memory_sum(fully_verified_bytes,file_bytes);
            const auto completed=std::string(prior_integrity ? "model_file_prior_integrity_reused file=" : "model_file_integrity_completed file=")+std::to_string(file_index)+
                " bytes="+std::to_string(file_bytes)+" total_verified_bytes="+std::to_string(fully_verified_bytes)+
                (prior_integrity ? " prior_native_SHA256_matched=1 sealed_identity_unchanged=1" : " SHA256_matched=1");
            qwen_native_stage(completed.c_str());
            inspect_container(model_file(startup.model_receipt, file.at("path").get<std::string>()), first,
                footprint,tensor_names,file_bytes,split_integrity?file_identities.back()[5]:file_bytes); first = false;
            sample_metadata_memory(4);++metadata_file_index;
            if (startup.first_generation_validation) require_model_CPU_budget();
            mapping_files.push_back({model_file(startup.model_receipt, file.at("path").get<std::string>()),
                                     file.at("bytes").get<std::uint64_t>()});
        }
        if (std::chrono::steady_clock::now() > verification_deadline)
            throw std::runtime_error("Complete original-model verification deadline expired before backend initialization");
        qwen_app::validate_original_footprint(footprint,expected_mapped_files);
        if(direct_metadata) {
            const auto s=qwen_app::native_direct_metadata_stats();
            if(s.completed_files!=file_index||s.borrowed_files)
                throw std::runtime_error("Direct metadata startup did not complete every original file before source startup");
            write_fresh_report(startup.admission_report+".source.metadata",{{"schema","ps5-qwen-direct-metadata-admission-v1"},
                {"completed_files",s.completed_files},{"physical_bytes",s.physical_bytes},{"physical_reads",s.physical_reads},
                {"maximum_metadata_prefix_bytes",s.maximum_prefix},{"window_bytes",qwen_app::metadata_direct_window},
                {"buffer_retired_before_source_startup",true},{"original_identities_and_parser_preserved",true},
                {"model_loaded",false},{"Vulkan_initialized",false},{"inactive_pages_counted_as_available",false}});
        }
        require_prior_metadata();
        const auto first_path = model_file(startup.model_receipt, receipt.at("files").at(0).at("path").get<std::string>());
        write_fresh_report(startup.admission_report+".integrity",{{"schema","ps5-qwen-model-integrity-v1"},
            {"pid",getpid()},{"files_verified",file_index},{"all_SHA256_matched",true},
            {"mapped_file_bytes",footprint.mapped_files},{"verified_file_bytes",fully_verified_bytes},
            {"maximum_verification_seconds",qwen_app::native_model_verification_seconds},
            {"verification_mode",split_integrity ? "prior_complete_split_logical_SHA_and_unchanged_physical_identities" :
                prior_integrity ? "prior_native_SHA_and_unchanged_sealed_identity" : "complete_native_SHA_this_run"},
            {"payload_SHA_computed_in_this_run",!prior_integrity},
            {"metadata_validation_deadline_seconds",prior_integrity ? 60 : qwen_app::native_model_verification_seconds},
            {"prior_native_integrity_report_sha256",prior_integrity ? Json(prior_integrity->report_sha256) : Json(nullptr)},
            {"sealed_identity_snapshot_sha256",prior_integrity ? Json(prior_integrity->snapshot_sha256) : Json(nullptr)},
            {"prior_native_verification_elapsed_ms",prior_integrity ? Json(prior_integrity->original_elapsed_ms) : Json(nullptr)},
            {"verification_elapsed_ms",std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now()-verification_started).count()},
            {"model_loaded",false},{"Vulkan_initialized",false}});
        screen.message.clear();

        auto require_unchanged_model = [&] {
            if (!startup.first_generation_validation) return;
            if (file_identities.size() != mapping_files.size())
                throw std::runtime_error("Complete original-model identity binding is missing");
            require_prior_metadata();
            for (std::size_t i = 0; i < mapping_files.size(); ++i)
                if (model_file_identity(mapping_files[i].path,
                        split_integrity?file_identities[i][5]:mapping_files[i].bytes) != file_identities[i])
                    throw std::runtime_error("Original model changed after its native verification");
            if(split_integrity)for(const auto &part:split_integrity->physical)
                if(!identity_namespace->matches(model_file_identity(model_directory+"/"+part.path,part.bytes),part.identity))
                    throw std::runtime_error("A split physical source changed after complete native verification");
        };
        require_unchanged_model();

        if(metadata_memory.enabled()) {
            if(!metadata_memory.complete())throw std::runtime_error("Every metadata phase must positively complete");
            static const char *phases[]={"before_size","after_size","after_parser","after_tensor_scan","after_container_returned"};
            Json rows=Json::array();
            for(std::size_t i=0;i<metadata_memory.size();++i) {
                const auto &s=metadata_memory.at(i);
                rows.push_back({{"file_index",i/qwen_app::MetadataMemoryProbe::phases},
                    {"phase",phases[i%qwen_app::MetadataMemoryProbe::phases]},
                    {"monotonic_ns",s.monotonic_ns},{"kernel_free_pages",s.memory.kernel_free},
                    {"Flexible_available_bytes",s.memory.flexible_available},{"CPU_heap_mapped_bytes",s.heap_mapped},
                    {"CPU_heap_peak_bytes",s.heap_peak},{"cumulative_Direct_reads",s.direct_reads},
                    {"cumulative_Direct_bytes",s.direct_bytes}});
            }
            write_fresh_report(startup.admission_report+".metadata-memory",{
                {"schema","ps5-qwen-metadata-memory-result-v1"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"complete",true},{"files",76},{"records",rows},{"all_original_integrity_and_footprint_checks_passed",true},
                {"all_metadata_parsers_and_descriptors_returned",true},{"GPU_calls",0},{"source_workers",0},
                {"virtual_source_calls",0},{"model_loaded",false},{"ordinary_OS_close_required",true}});
            qwen_native_stage("metadata_memory_CPU_diagnostic_completed_GPU_not_started_waiting_for_ordinary_close");
            for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        if (startup.model_validation || startup.first_generation_validation) {
            qwen_native_stage("source_virtual_CPU_memory_admission_before_probe GPU_not_started=1 model_loaded=0");
            const auto memory=startup.first_generation_validation ? qwen_app::admit_native_system_memory() : qwen_app::observe_native_system_memory();
            write_fresh_report(startup.admission_report+".system-memory.before-virtual-sources",system_memory_report(memory));
            (void)qwen_app::qualified_system_headroom(memory);
            // A source-address admission can enter an opaque OS call. Check
            // the existing CPU/OS reserve first, including unsupported counters.
            // Keep that rejection; vm0 free/inactive are not a qualified
            // substitute for process-available or immediately reclaimable RAM.
            require_model_CPU_budget();
            qwen_native_stage("source_virtual_CPU_memory_admission_passed_before_probe GPU_not_started=1 model_loaded=0");
            const bool stage_memory_diagnostic=policy.contains("native_source_stage_memory_diagnostic");
            if(policy.contains("native_CPU_phase_control")&&!stage_memory_diagnostic)
                throw std::runtime_error("CPU phase controls require the explicit CPU-only diagnostic");
            Json VM_before;
            if(stage_memory_diagnostic) {
                const auto & diagnostic=policy.at("native_source_stage_memory_diagnostic");
                if(!startup.first_generation_validation||!policy.contains("native_source_schedule")||
                   diagnostic.at("schema")!="ps5-qwen-native-stage-memory-policy-v3"||diagnostic.at("enabled")!=true||
                   diagnostic.at("CPU_only")!=true||diagnostic.at("maximum_records")!=qwen_app::stage_memory_probe_capacity||
                   diagnostic.at("matched_idle_ns")!=qwen_app::stage_memory_probe_idle_ns||diagnostic.at("split_write_and_sync")!=true||
                   diagnostic.at("VM_population_snapshots")!=true||diagnostic.at("settled_idle_seconds")!=2||
                   diagnostic.at("ordinary_OS_close_required")!=true)
                    throw std::runtime_error("Bounded CPU-only stage memory diagnostic is not admitted");
                if(policy.contains("native_CPU_phase_control")) {
                    const auto &control=policy.at("native_CPU_phase_control");
                    if(control.at("schema")!="ps5-qwen-CPU-phase-control-v1"||control.at("enabled")!=true||
                       control.at("quiet_seconds")!=5||control.at("maximum_journal_lines")!=256||
                       control.at("idle_microseconds_per_line")!=2000||control.at("extra_kernel_pages_before_next_line")!=512)
                        throw std::runtime_error("Finite quiet/journal CPU control is not admitted");
                    const auto quiet_started=qwen_app::ProfileClock::now();
                    const auto before_quiet=diagnostic_VM_population();
                    std::this_thread::sleep_for(std::chrono::seconds(5));
                    const auto after_quiet=diagnostic_VM_population();
                    const auto quiet_ns=qwen_app::profile_elapsed_ns(quiet_started);
                    const auto journal_started=qwen_app::ProfileClock::now();
                    unsigned lines=0;bool stopped=false;
                    for(;lines<256;++lines) {
                        const auto fresh=qwen_app::observe_native_system_memory();
                        (void)qwen_app::qualified_system_headroom(fresh);
                        const auto floor=std::uint64_t(fresh.kernel_minimum)+std::max<std::uint64_t>(fresh.kernel_reserved,
                            (qwen_app::kernel_memory_margin+fresh.page_size-1)/fresh.page_size)+512;
                        if(fresh.kernel_free<floor){stopped=true;break;}
                        char line[160];const int count=std::snprintf(line,sizeof(line),
                            "CPU_journal_control_only line=%u source_operations=0 reservations=0 GPU_calls=0 model_loaded=0",lines);
                        if(count<=0||std::size_t(count)>=sizeof(line))throw std::runtime_error("CPU journal control line bound failed");
                        qwen_native_stage(line);
                        if(usleep(2000))throw std::runtime_error("CPU journal control idle did not complete");
                    }
                    const auto after_journal=diagnostic_VM_population();
                    write_fresh_report(startup.admission_report+".source.CPU-prelude",{
                        {"schema","ps5-qwen-CPU-phase-control-result-v1"},{"pid",getpid()},
                        {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                        {"VM_before_quiet",before_quiet},{"VM_after_quiet",after_quiet},{"VM_after_journal",after_journal},
                        {"quiet_ns",quiet_ns},{"journal_ns",qwen_app::profile_elapsed_ns(journal_started)},
                        {"completed_journal_lines",lines},{"maximum_journal_lines",256},
                        {"stopped_at_completed_boundary_before_next_line",stopped},
                        {"source_operations",0},{"GPU_calls",0},{"source_workers",0},{"model_loaded",false},
                        {"inactive_pages_counted_as_available",false}});
                    // The control must not enter the real opaque reservation
                    // interval with less than the existing stronger target.
                    (void)qwen_app::admit_native_startup_memory();
                }
                if(!qwen_app::begin_native_stage_memory_probe())
                    throw std::runtime_error("Bounded CPU-only stage sampler cannot be reentered");
                VM_before=diagnostic_VM_population();
            }
            const auto mapping = qwen_app::admit_native_model_mapping(mapping_files,
                [](const std::string & stage) { qwen_native_stage(stage.c_str()); });
            if(stage_memory_diagnostic) {
                const bool complete=qwen_app::end_native_stage_memory_probe();
                const auto VM_after=diagnostic_VM_population();
                std::this_thread::sleep_for(std::chrono::seconds(2));
                const auto VM_settled=diagnostic_VM_population();
                Json samples=Json::array();
                for(std::size_t i=0;i<qwen_app::native_stage_memory_probe_count();++i) {
                    const auto * sample=qwen_app::native_stage_memory_probe_sample(i);
                    if(!sample)throw std::runtime_error("Native stage memory sample ownership is not idle");
                    samples.push_back({{"phase",sample->phase},{"idle_before_ns",sample->idle_before_ns},
                        {"before_ns",sample->before_ns},{"write_after_ns",sample->write_after_ns},{"after_ns",sample->after_ns},
                        {"free_idle_before",sample->free_idle_before},{"free_before",sample->free_before},
                        {"free_after_write",sample->free_after_write},{"free_after",sample->free_after},{"valid",sample->valid}});
                }
                write_fresh_report(startup.admission_report+".source.stage-memory",{
                    {"schema","ps5-qwen-native-stage-memory-result-v3"},{"pid",getpid()},
                    {"VM_before",VM_before},{"VM_after",VM_after},{"VM_settled_after_two_seconds",VM_settled},
                    {"inactive_pages_counted_as_available",false},
                    {"matched_idle_ns",qwen_app::stage_memory_probe_idle_ns},{"split_write_and_sync",true},
                    {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                    {"samples_valid_and_complete",complete},{"samples",samples},
                    {"mapped_files",mapping.files},{"completed_unmaps",mapping.unmapped},{"mapped_file_bytes",mapping.bytes},
                    {"model_loaded",false},{"Vulkan_initialized",false},{"GPU_calls",0},{"source_workers",0},
                    {"state","CPU_diagnostic_completed_waiting_for_ordinary_close"}});
                if(!complete)throw std::runtime_error("Native stage memory diagnostic did not complete all bounded observations");
                qwen_native_stage("source_stage_memory_CPU_diagnostic_completed_GPU_not_started_waiting_for_ordinary_close");
                for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
            }
            qwen_native_stage("source_virtual_probe_all_reservations_and_releases_completed_before_backend GPU_not_started=1");
            write_fresh_report(startup.admission_report+".system-memory.after-virtual-probe-before-admission",
                system_memory_report(qwen_app::observe_native_system_memory()));
            // The whole rehearsal has positively returned. Require recovery to
            // the existing startup target before creating driver/device state.
            // This shares the same passive wait budget and issues no reclaim.
            const auto after_sources=startup.first_generation_validation ?
                (policy.contains("native_source_schedule") ? qwen_app::admit_native_startup_memory() : qwen_app::admit_native_system_memory()) :
                qwen_app::observe_native_system_memory();
            write_fresh_report(startup.admission_report+".system-memory.after-virtual-sources",system_memory_report(after_sources));
            (void)qwen_app::qualified_system_headroom(after_sources);
            require_model_CPU_budget();
            write_fresh_report(startup.admission_report + (startup.first_generation_validation ? ".mapping" : ""), {{"schema", "ps5-qwen-model-virtual-source-admission-v1"},
                {"pid", getpid()}, {"all_SHA256_matched", true}, {"original_footprint_matched", true},
                {"mapped_files", mapping.files}, {"mapped_file_bytes", mapping.bytes},
                {"completed_unmaps", mapping.unmapped}, {"model_loaded", false},
                {"Vulkan_initialized", false}, {"GPU_compute_calls", 0}, {"mapped_payload_reads", 0},
                {"file_backed_model_mmap_calls", 0}, {"source_virtual_protection", "none"},
                {"source_virtual_base",qwen_app::source_key_base},{"source_virtual_capacity",qwen_app::source_key_bytes},
                {"source_virtual_fixed_no_overwrite",true},
                {"resident_set_qualified", false}, {"state", startup.first_generation_validation ?
                    "virtual_sources_completed_before_backend" : "completed_waiting_for_ordinary_close"}});
            qwen_native_stage("model_validation_completed GPU_not_started=1 model_loaded=0");
            // Successful validation is explicit idle ownership. Returning from
            // main would intentionally enter the CRT's fault-retention hook.
            if (startup.model_validation)
                for (;;) std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        require_unchanged_model();

        screen.state = "admitting original BF16 memory";
        if (startup.first_generation_validation) {
            std::vector<qwen_app::SourceFile> sources;
            std::vector<qwen_app::LogicalSourceFile> logical;
            if(split_integrity) {
                for(const auto &part:split_integrity->physical) {
                    const auto path=model_directory+"/"+part.path;
                    const auto actual=model_file_identity(path,part.bytes);
                    if(!identity_namespace->matches(actual,part.identity))
                        throw std::runtime_error("Split source admission requires every exact current physical identity");
                    sources.push_back({path,part.bytes,actual});
                }
                logical=split_integrity->logical;
                for(auto &file:logical)file.path=model_directory+"/"+file.path;
            } else for (std::size_t i = 0; i < mapping_files.size(); ++i)
                sources.push_back({mapping_files[i].path, mapping_files[i].bytes, file_identities[i]});
            const auto physical_count=sources.size();
            qwen_app::start_native_model_sources(std::move(sources),std::move(logical));
            write_fresh_report(startup.admission_report + ".source", {
                {"schema", "ps5-qwen-bounded-source-admission-v1"}, {"pid", getpid()},
                {"direct_read_preflight_passed", true}, {"maximum_window_bytes", qwen_app::model_read_window},
                {"CPU_source_read_window_in_Direct_heap", true},
                {"maximum_open_handles", 8}, {"mapped_source_upload_dereferences_enabled", false},
                {"logical_files",mapping_files.size()},{"physical_files",physical_count},
                {"split512_layout",bool(split_integrity)},
                {"CPU_matrix_fallback_enabled", false}, {"maximum_CPU_workspace_bytes", 16u << 20},
                {"bounded_CPU_rows_enabled", true}, {"CPU_source_pointer_dereferences_enabled", false},
                {"model_loaded", false}, {"Vulkan_initialized", false}});
            qwen_native_stage("bounded_model_source_preflight_passed_before_backend");
        }
        if (display) display->publish(screen);
        native_resources_started = true;
        if (!model_CPU_runtime_admitted) qwen_app::admit_cpu_runtime(qwen_native_stage);
        if (startup.first_generation_validation) {
            qwen_native_stage("source_pipeline_CPU_preflight_before_Vulkan GPU_not_started=1");
            qwen_app::start_native_source_parallel_reads();
            const bool selected = policy.contains("native_source_schedule");
            if (selected) {
                const auto & candidate = policy.at("native_source_schedule");
                if (candidate.at("schema") != "ps5-qwen-file-range-source-policy-v1" ||
                    candidate.at("enabled") != true || candidate.at("maximum_outstanding_reads") != 2 ||
                    candidate.at("source_window_bytes") != qwen_app::model_read_window ||
                    candidate.at("region_bytes") != qwen_app::source_schedule_region_bytes ||
                    candidate.at("boundary_margin_bytes") != qwen_app::source_schedule_boundary_margin ||
                    candidate.at("coalesce_adjacent_original_bytes") != true ||
                    candidate.at("require_kernel_target_before_metadata") != true ||
                    candidate.at("startup_integrity_direct") != true ||
                    candidate.at("unchanged_memory_precision_driver_and_cache_policy") != true ||
                    policy.contains("native_source_contention_probe"))
                    throw std::runtime_error("The private file/range source candidate policy is not admitted");
                qwen_app::enable_native_source_schedule();
            }
            require_model_CPU_budget();
            (void)observed_system_headroom();
            Json source_admission = {
                {"schema", selected ? "ps5-qwen-source-schedule-admission-v1" : "ps5-qwen-source-pipeline-admission-v1"},
                {"source_window_bytes", qwen_app::model_read_window}, {"CPU_IO_workers", 1},
                {"maximum_outstanding_reads", selected ? 2 : 1}, {"preflight_equal_bytes", true},
                {"preflight_bytes_per_read", qwen_app::model_read_alignment}, {"Vulkan_initialized", false}};
            if (selected) source_admission.update({
                {"file_range_schedule_enabled", true}, {"coalesced_and_parallel_CPU_paths_passed", true},
                {"region_bytes", qwen_app::source_schedule_region_bytes},
                {"boundary_margin_bytes", qwen_app::source_schedule_boundary_margin}});
            write_fresh_report(startup.admission_report + ".source.pipeline", source_admission);
            qwen_native_stage("source_pipeline_CPU_preflight_passed_before_Vulkan GPU_not_started=1");
        }
        const bool large_cache_candidate=policy.contains("native_large_cache_scope");
        const bool predictive_cache_candidate=policy.contains("native_predictive_cache");
        const bool speculative_model_candidate=policy.contains("native_model_free_speculation");
        if(speculative_model_candidate) {
            const auto &proof=policy.at("native_model_free_speculation").at("complete_checkpoint_qualification");
            qwen_app::require_model_free_checkpoint_report(read_completed_native_report(proof),proof);
        }
        if(large_cache_candidate) {
            const bool layout=qwen_app::require_large_cache_scope(policy,startup.first_generation_validation,
                bool(display),prefill_tokens);
            if(!layout) {
                const auto &proof=policy.at("native_large_cache_scope").at("layout_qualification");
                qwen_app::require_large_cache_layout_report(read_completed_native_report(proof),proof);
            }
            qwen_app::select_experimental_padded_cache_128();
            qwen_native_stage("experimental_128_slot_geometry_selected_before_backend_initialization");
        }
        const auto cache_geometry=qwen_app::selected_padded_cache_geometry();
        qwen_app::inspect_vulkan_globals();
        const bool indexed_candidate=policy.contains("native_bf16_indexed_vector");
        const bool padded_cache_candidate=policy.contains("native_padded_expert_cache");
        if(padded_cache_candidate) {
            Json expected={{"schema","ps5-qwen-owned-padded-expert-cache-v1"},{"enabled",true},
                {"active_slots",53},{"physical_planes",54},{"bank_stride",3293184},{"cache_cap_bytes",536870912},
                {"preserve_coalesced_source_reads",true},{"pre_IO_split_EOF_fallback",true},
                {"require_owned_synchronous_bank_lease",true},{"automatic_retries",0},{"precision_unchanged",true},
                {"layout_qualification_SELF_SHA256","5bb22cdf4603b038d8247597caafe8b08479c2e9bcc1fda44982b777ae2018db"},
                {"layout_qualification_result_SHA256","d277b1d03fcabe981408b8027a559e16134eb8b7e746bef366bb20ea63703cb5"}};
            if(large_cache_candidate) {
                const auto &proof=policy.at("native_large_cache_scope").at("layout_qualification");
                expected.update({{"schema","ps5-qwen-owned-padded-expert-cache-v2"},
                    {"active_slots",128},{"physical_planes",129},{"cache_cap_bytes",cache_geometry.cache_bytes()},
                    {"layout_qualification_SELF_SHA256",proof.at("SELF_sha256")},
                    {"layout_qualification_result_SHA256",proof.at("report_sha256")}});
            }
            if(!startup.first_generation_validation||policy.at("native_padded_expert_cache")!=expected||
               !indexed_candidate||!policy.contains("native_indexed_vector_fixture")||
               policy.contains("native_padded_bank_layout_probe")||policy.contains("native_owned_mapped_probe")||
               policy.contains("native_mapped_streaming_copy"))
                throw std::runtime_error("The exact separately qualified owned padded-cache policy is required");
        }
        if(policy.contains("native_mapped_streaming_copy")) {
            const Json expected={{"schema","ps5-qwen-mapped-streaming-copy-v1"},{"enabled",true},
                {"decode_only",true},{"minimum_bytes",1048576},{"require_owned_completed_source_window",true},
                {"require_device_local_coherent_mapping",true},{"precision_unchanged",true}};
            if(!startup.first_generation_validation||policy.at("native_mapped_streaming_copy")!=expected)
                throw std::runtime_error("The exact owned decode-copy policy is required");
            qwen_app::configure_mapped_copy(true);
        }
        const bool padded_layout_candidate=policy.contains("native_padded_bank_layout_probe");
        if(padded_layout_candidate) {
            Json expected={{"schema","ps5-qwen-padded-bank-layout-v1"},{"enabled",true},
                {"model_member_index",7},{"source_offset",131072},{"envelope_bytes",3293184},
                {"source_SHA256","16fffd6b293d7d218adff19ba8a4f2d5176341b43b15fda3c9d63aa3f0677b1a"},
                {"maximum_Direct_reads",1},{"maximum_GPU_graphs",360},{"CPU_deadline_seconds",120},
                {"actual_residues",30},{"layouts",4},{"active_slots",53},{"physical_planes",54},
                {"model_loads",0},{"VideoOut_starts",0},{"automatic_retries",0}};
            if(large_cache_candidate)expected.update({{"schema","ps5-qwen-padded-bank-layout-v2"},
                {"active_slots",128},{"physical_planes",129}});
            if(!startup.first_generation_validation||policy.at("native_padded_bank_layout_probe")!=expected||
               indexed_candidate||policy.contains("native_indexed_vector_fixture")||
               policy.contains("native_owned_mapped_probe")||policy.contains("native_mapped_streaming_copy")||display)
                throw std::runtime_error("The exact isolated padded-layout policy is required");
        }
        const bool owned_probe_candidate=policy.contains("native_owned_mapped_probe");
        if(owned_probe_candidate) {
            const Json expected={{"schema","ps5-qwen-owned-mapped-probe-v1"},{"enabled",true},
                {"model_member_index",7},{"source_offset",131072},{"payload_bytes",3276800},
                {"source_SHA256","0507102a20a1dae5a1a2b99ad421fcb70cb1e349a38b4124cd7715dc806f8dc6"},
                {"maximum_Direct_reads",1},{"maximum_GPU_graphs",7},{"model_loads",0},{"automatic_retries",0}};
            if(!startup.first_generation_validation||policy.at("native_owned_mapped_probe")!=expected||
               indexed_candidate||policy.contains("native_indexed_vector_fixture"))
                throw std::runtime_error("The exact isolated owned-mapping probe policy is required");
        }
        const bool indexed_fixture_requested=policy.contains("native_indexed_vector_fixture");
        if(indexed_fixture_requested) {
            const Json expected={{"schema","ps5-qwen-indexed-fixture-admission-v1"},{"enabled",true},
                {"require_non_dyadic_F32",true},{"post_fixture_kernel_target_pages",2974}};
            if(!startup.first_generation_validation||policy.at("native_indexed_vector_fixture")!=expected)
                throw std::runtime_error("The matched indexed-fixture admission policy differs");
        }
        const bool direct_frame_candidate=policy.contains("native_direct_frame_evidence");
        if(direct_frame_candidate) {
            const Json expected={{"schema","ps5-qwen-direct-frame-evidence-v2"},{"enabled",true},
                {"window_bytes",1048576},{"exact_original_BMP_bytes",8294454},
                {"deadline_seconds",8},{"require_owned_new_file",true},
                {"metadata_ABI","native_descriptor"},{"exclusive_creator_UID",1}};
            if(!startup.first_generation_validation || policy.at("native_direct_frame_evidence")!=expected)
                throw std::runtime_error("The exact bounded Direct frame evidence policy is required");
        }
        if(indexed_candidate) {
            const Json expected={{"schema","ps5-qwen-BF16-indexed-vector-v1"},{"enabled",true},
                {"decode_only",true},{"maximum_tokens",1},{"original_shape_fixture_required",true},
                {"weights_BF16",true},{"activations_F32",true},{"accumulation_F32",true}};
            if(!startup.first_generation_validation || policy.at("native_bf16_indexed_vector")!=expected)
                throw std::runtime_error("The exact decode-only indexed-vector policy is required");
        }
        if(!qwen_native_gpu_frontend_linked())throw std::runtime_error("Native driver frontend is not linked");
        // Upstream get_max_size is its batching target, not a hard tensor limit.
        // The 1,271,398,400-byte original output exceeds its 1 GiB default.
        // The requested 2 GiB target is reduced by upstream to the queried hard
        // allocation/buffer limit. Admission below requires every tensor to fit
        // that reduced target; no physical feature or hard limit is overridden.
        if(setenv("GGML_VK_SUBALLOCATION_BLOCK_SIZE","2147483648",1))
            throw std::runtime_error("The conservative native buffer batching target could not be set");
        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());
        qwen_native_driver_begin();
        llama_backend_init();
        auto device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
        if (!device) device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
        std::size_t driver_free = 0, driver_total = 0,vulkan_reported_free=0;
        if(!device) throw std::runtime_error("A qualified native Vulkan device is required");
        ggml_backend_dev_memory(device, &vulkan_reported_free, &driver_total);
        const auto native_budget_before=qwen_native_allocator_budget(driver_total);
        driver_free=native_budget_before.available;
        std::int64_t physical=0;std::size_t direct=0;const auto pool=sceKernelGetDirectMemorySize();
        if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&direct)<0)
            throw std::runtime_error("A fresh Direct-memory observation is required before model loading");
        qwen_app::MemoryBudget memory_budget;
        if (startup.first_generation_validation) {
            memory_budget.cpu_working = qwen_app::model_CPU_budget_bytes;
            memory_budget.workspace = 256ull << 20;
        }
        if(large_cache_candidate) {
            // This distinct context-256 scope retains the CPU cap, device
            // ledger, staging, platform and Direct reserves. The 256 MiB
            // context allowance exceeds the completed control's non-bank /
            // non-workspace device peak; checkpoint/prefix scopes are excluded.
            memory_budget.expert_cache=cache_geometry.cache_bytes();
            memory_budget.context=256ull<<20;
        }
        const auto buffer_type=ggml_backend_dev_buffer_type(device);
        const auto system_memory=qwen_app::admit_native_system_memory();
        const qwen_app::MemoryObservation memory_observation{driver_free,direct,qwen_app::qualified_system_headroom(system_memory),
            ggml_backend_buft_get_max_size(buffer_type),ggml_backend_buft_get_alignment(buffer_type)};
        const bool isolated_large_layout=large_cache_candidate&&padded_layout_candidate;
        if(isolated_large_layout)qwen_app::admit_large_cache_layout_memory(memory_budget,memory_observation);
        else memory_budget.admit(footprint,memory_observation);
        write_fresh_report(startup.admission_report+".memory",{{"schema","ps5-qwen-memory-admission-v1"},
            {"pid",getpid()},{"model_loaded",false},{"device_weights_bytes",footprint.device_weights},
            {"mapped_experts_bytes",footprint.mapped_experts},{"required_lazy_PLE_bytes",footprint.lazy_ple},
            {"mapped_embedding_bytes",footprint.mapped_embeddings},{"mapped_file_bytes",footprint.mapped_files},
            {"planned_resident_headroom_bytes",isolated_large_layout?
                qwen_app::large_cache_layout_requirement(memory_budget):memory_budget.device_requirement(footprint)},
            {"full_resident_model_charged",!isolated_large_layout},
            {"CPU_budget_bytes",memory_budget.cpu_working},
            {"maximum_explicitly_addressed_CPU_model_page_bytes",qwen_app::maximum_addressed_model_CPU_bytes},
            {"maximum_resident_CPU_model_source_bytes",qwen_app::maximum_resident_model_CPU_source_bytes},
            {"CPU_heap_budget_includes_source_read_window",true},
            {"maximum_CPU_heap_bytes",qwen_app::maximum_model_CPU_heap_bytes},
            {"maximum_postload_device_buffer_bytes",qwen_app::model_postload_single_buffer},
            {"maximum_aggregate_postload_device_buffer_bytes",qwen_app::model_postload_device_budget},
            {"driver_free_bytes",memory_observation.driver_free},
            {"device_budget_source","canary-validated native Direct allocator"},
            {"Vulkan_estimated_free_bytes",vulkan_reported_free},
            {"native_Direct_owned_bytes",native_budget_before.owned},
            {"Direct_largest_available_bytes",memory_observation.direct_largest},
            {"Flexible_available_bytes",memory_observation.flexible_available},
            {"Flexible_reserve_bytes",memory_budget.flexible_reserve},
            {"additional_Direct_platform_margin_bytes",memory_budget.platform_margin},
            {"kernel_vm0_free_pages",system_memory.kernel_free}, {"kernel_vm0_minimum_pages",system_memory.kernel_minimum},
            {"kernel_vm0_reserved_pages",system_memory.kernel_reserved},
            {"kernel_extra_margin_bytes",qwen_app::kernel_memory_margin},
            {"device_buffer_batch_limit_bytes",memory_observation.device_max_buffer},
            {"device_buffer_alignment_bytes",memory_observation.device_buffer_alignment},
            {"resident_set_qualified",false}});
        qwen_native_stage("model_memory_preflight_passed_before_model_load");
        if(padded_layout_candidate) {
            qwen_app::enforce_native_model_compute_limits();
            if(qwen_app::native_model_device_stats().live)
                throw std::runtime_error("Padded layout requires an empty admitted device ledger");
            qwen_native_stage("padded_layout_empty_device_ledger_admitted_before_allocation");
            const auto &gate=policy.at("native_padded_bank_layout_probe");
            const auto probe=qwen_app::admit_padded_bank_layout(mapping_files.at(7).path,
                gate.at("source_SHA256").get<std::string>(),qwen_native_driver_checkpoint,qwen_native_stage);
            require_unchanged_model();require_model_CPU_budget();
            const auto ledger=qwen_app::native_model_device_stats();
            if(ledger.live)throw std::runtime_error("Padded layout device buffers remain live after retirement");
            Json cases=Json::array();
            for(const auto &row:probe.cases)cases.push_back({{"columns",row.columns},{"rows",row.rows},
                {"input_vectors",row.input_vectors},{"residue",row.residue},
                {"maximum_absolute_error",row.maximum_absolute_error},
                {"non_BF16_exact_F32_inputs",row.non_BF16_exact_F32_inputs},
                {"matrix_passed",row.matrix_passed},{"vector_passed",row.vector_passed},
                {"non_dyadic_vector_passed",row.non_dyadic_vector_passed},{"padding_intact",row.padding_intact}});
            Json report={{"schema","ps5-qwen-padded-bank-layout-result-v1"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"eligible",probe.eligible},{"all_started_IO_closed",probe.all_IO_closed},
                {"Direct_reads",probe.Direct_reads},{"GPU_graphs",probe.GPU_graphs},
                {"descriptor_alignment",probe.descriptor_alignment},{"memory_flags",probe.memory_flags},
                {"cases",cases},{"maximum_absolute_error_limit",1e-6},{"reference_accumulation","F64"},
                {"device_ledger_peak_bytes",ledger.peak},{"device_ledger_allocations",ledger.allocations},
                {"device_ledger_live_bytes",ledger.live},{"positive_resource_retirement",probe.positive_retirement},
                {"source_workers_stopped",false},{"model_loaded",false},{"VideoOut_started",bool(display)},
                {"automatic_retries",0},{"active_slots",cache_geometry.active_slots},
                {"physical_planes",cache_geometry.physical_slots()},
                {"bank_stride",qwen_app::padded_bank_stride},{"source_SHA256",gate.at("source_SHA256")}};
            if(large_cache_candidate) {
                const auto &owner=policy.at("native_first_generation_validation");
                report.update({{"schema","ps5-qwen-padded-bank-layout-result-v2"},
                    {"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
                    {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")},
                    {"native_archive_sha256",owner.at("native_archive_sha256")}});
            }
            write_fresh_report(startup.admission_report+".padded-layout.preliminary",report);
            qwen_native_driver_complete();qwen_app::stop_native_model_sources();
            report["source_workers_stopped"]=true;
            write_fresh_report(startup.admission_report+".padded-layout",report);
            qwen_native_stage("padded_layout_completed_model_not_loaded_waiting_for_ordinary_close");
            for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        if(owned_probe_candidate) {
            const auto &gate=policy.at("native_owned_mapped_probe");
            // This isolated path never reaches the model-load enable point.
            // Admit the unchanged ledger before any fixture allocation instead.
            qwen_app::enforce_native_model_compute_limits();
            if(qwen_app::native_model_device_stats().live)
                throw std::runtime_error("Owned probe requires an empty admitted device ledger before allocation");
            qwen_native_stage("owned_probe_empty_device_ledger_admitted_before_allocation");
            const auto probe=qwen_app::admit_owned_mapped_probe(mapping_files.at(7).path,
                gate.at("source_SHA256").get<std::string>(),qwen_native_driver_checkpoint,qwen_native_stage);
            require_unchanged_model();require_model_CPU_budget();
            const auto ledger=qwen_app::native_model_device_stats();
            if(ledger.live)throw std::runtime_error("Owned probe device buffers remain live after positive retirement");
            Json copies=Json::array();
            for(const auto &row:probe.copies)copies.push_back({{"streaming",row.streaming},
                {"five_copies_ms",row.milliseconds},{"exact_bytes",row.exact}});
            Json probe_report={
                {"schema","ps5-qwen-owned-mapped-result-v1"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"eligible",probe.eligible},{"all_started_IO_returned",probe.all_IO_returned},
                {"Direct_read_result",probe.read_result},{"Direct_read_errno",probe.read_errno},
                {"memory_flags",probe.memory_flags},{"GPU_numerics_passed",probe.GPU_numerics},
                {"GPU_graphs",probe.graphs},{"maximum_absolute_error",probe.maximum_absolute_error},
                {"copies",copies},{"payload_bytes",qwen_app::owned_probe_bytes},
                {"device_ledger_peak_bytes",ledger.peak},{"device_ledger_allocations",ledger.allocations},
                {"device_ledger_live_bytes",ledger.live},
                {"source_offset",131072},{"source_SHA256",gate.at("source_SHA256")},
                {"positive_resource_retirement",probe.retired},{"source_workers_stopped",false},
                {"model_loaded",false},{"full_model_inference_executed",false},
                {"VideoOut_started",bool(display)},{"automatic_retries",0}};
            write_fresh_report(startup.admission_report+".owned-mapped.preliminary",probe_report);
            qwen_native_driver_complete();
            qwen_app::stop_native_model_sources();
            probe_report["source_workers_stopped"]=true;
            write_fresh_report(startup.admission_report+".owned-mapped",probe_report);
            qwen_native_stage("owned_mapped_probe_completed_model_not_loaded_waiting_for_ordinary_close");
            for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        if(indexed_candidate||indexed_fixture_requested) {
            qwen_native_stage("indexed_vector_fixture_started_before_model_load");
            const auto fixtures=qwen_app::admit_indexed_vectors(qwen_native_driver_checkpoint,qwen_native_stage);
            Json cases=Json::array();
            for(const auto & fixture:fixtures) {
                if(!fixture.passed)throw std::runtime_error("Original-shape indexed-vector fixture refused");
                cases.push_back({{"columns",fixture.columns},{"rows",fixture.rows},{"input_vectors",fixture.input_vectors},
                    {"first_ms",fixture.first_ms},{"warm_mean_ms",fixture.warm_ms},
                    {"non_BF16_exact_F32_inputs",fixture.non_dyadic_F32_inputs},
                    {"max_absolute_error",fixture.max_absolute_error},{"passed",fixture.passed}});
            }
            write_fresh_report(startup.admission_report+".indexed-vector",{
                {"schema","ps5-qwen-BF16-indexed-vector-fixture-v2"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"cases",cases},{"strategies",{"matrix","vector"}},{"graphs_per_strategy",3},
                {"additional_non_dyadic_vector_graphs_per_layout",1},{"timed_strategy_inputs_identical",true},
                {"reference_accumulation","F64"},{"maximum_absolute_error_limit",1e-6},
                {"decode_candidate_enabled",indexed_candidate},{"matched_fixture_admission_requested",indexed_fixture_requested},
                {"selected_experts",10},{"repeated_and_boundary_IDs",true},{"maximum_BF16_bank_bytes",32768000},
                {"model_loaded",false},{"positive_completion_and_retirement",true},{"path_counters",gpu_path_snapshot()}});
            qwen_app::configure_bf16_indexed_vector(indexed_candidate);
            require_model_CPU_budget();
            // Both comparison arms warm and retire the same finite GPU work,
            // then retain the existing stronger startup target before loading.
            const auto after_fixture=qwen_app::admit_native_startup_memory();
            write_fresh_report(startup.admission_report+".system-memory.after-indexed-fixture",
                system_memory_report(after_fixture));
            qwen_native_stage("indexed_vector_original_shape_numerics_and_startup_target_passed");
        }
        screen.state="loading original BF16 model";if(display)display->publish(screen);
        auto model_params=qwen_app::streaming_model_params(ggml_backend_cpu_buffer_type());
        LoadProgress load_progress;model_params.progress_callback=observe_model_load;model_params.progress_callback_user_data=&load_progress;
        qwen_native_stage("model_load_started_after_memory_admission");
        require_unchanged_model();
        if (startup.first_generation_validation) require_model_CPU_budget();
        model = llama_model_load_from_file(first_path.c_str(), model_params);
        if (!model) throw std::runtime_error("Model load failed; restart through the ordinary OS path");
        qwen_native_stage("model_load_completed");
        qwen_native_driver_checkpoint();
        require_unchanged_model();
        if (startup.first_generation_validation) qwen_app::enforce_native_model_compute_limits();
        write_fresh_report(startup.admission_report+".system-memory.after-load",
            system_memory_report(qwen_app::observe_native_system_memory(),true));
        if (startup.first_generation_validation) require_model_CPU_budget();
        ggml_backend_dev_memory(device, &vulkan_reported_free, &driver_total);
        const auto native_budget_after=qwen_native_allocator_budget(driver_total);
        driver_free=native_budget_after.available;
        // Initial, unqualified limits: do not infer extra RAM from the GPU pool.
        const auto remaining=qwen_app::checked_memory_sum(memory_budget.context,
            qwen_app::checked_memory_sum(memory_budget.workspace,memory_budget.staging+memory_budget.direct_reserve));
        write_fresh_report(startup.admission_report+".memory.after-load",{{"model_loaded",true},
            {"Vulkan_estimated_free_bytes",vulkan_reported_free},{"native_Direct_available_bytes",driver_free},
            {"native_Direct_pool_bytes",native_budget_after.pool},{"native_Direct_owned_bytes",native_budget_after.owned},
            {"remaining_context_workspace_staging_reserve_bytes",remaining},
            {"expert_cache_requested_bytes",memory_budget.expert_cache},
            {"device_budget_source","canary-validated native Direct allocator"}});
        if(driver_free<remaining) throw std::runtime_error("Insufficient headroom after model load");
        const auto cache_bytes = qwen_app::native_direct_cache_budget(memory_budget.expert_cache, driver_free-remaining,
            observed_system_headroom(), memory_budget.flexible_reserve);
        if (cache_bytes < (128u << 20)) throw std::runtime_error("Insufficient observed UMA cache headroom");
        if(padded_cache_candidate) {
            if(cache_bytes!=cache_geometry.cache_bytes())
                throw std::runtime_error("Padded cache requires its complete selected request");
            qwen_app::configure_native_padded_cache(true,memory_observation.device_buffer_alignment);
            if(predictive_cache_candidate)qwen_app_configure_predictive_cache(true);
            qwen_native_stage("owned_padded_cache_admitted_before_context_creation");
        }
        screen.state = "admitting inference context";
        if (display) display->publish(screen);
        const auto context_started = std::chrono::steady_clock::now();
        context = llama_init_from_model(model, qwen_app::streaming_context_params(
            startup.first_generation_validation ? qwen_app::first_context_tokens : 4096, cache_bytes, prefill_tokens));
        if (!context) throw std::runtime_error("Context admission failed; restart through the ordinary OS path");
        write_fresh_report(startup.admission_report+".system-memory.after-context",
            system_memory_report(qwen_app::observe_native_system_memory(),true));
        if (startup.first_generation_validation) require_model_CPU_budget();
        if (startup.first_generation_validation && std::chrono::steady_clock::now() - context_started > std::chrono::seconds(600))
            throw std::runtime_error("Context creation exceeded its first-generation boundary deadline");
        engine = std::make_unique<qwen_app::LlamaEngine>(model, context, prefill_tokens);
        engine->set_stage_observer(observed_inference_stage);
        engine->set_gpu_boundaries(qwen_native_driver_begin,qwen_native_driver_complete,qwen_native_driver_retain,qwen_native_driver_checkpoint);
        const auto * chat_template = llama_model_chat_template(model, nullptr);
        if (!chat_template || !*chat_template) throw std::runtime_error("The original chat template is required");
        qwen_app::HardwareInfo hardware;
        hardware.cpu_name = screen.cpu_name;
        hardware.logical_cpu_threads = screen.cpu_threads;
        hardware.sample_process_cpu = false;
        if (device) {
            const char * description = ggml_backend_dev_description(device);
            if (description) hardware.gpu_name = description;
            std::size_t free = 0, total = 0;
            ggml_backend_dev_memory(device, &free, &total);
            if (total) { const auto native=qwen_native_allocator_budget(total);
                hardware.gpu_total_bytes = native.pool; hardware.gpu_free_bytes = native.available; }
        }
        qwen_native_driver_complete();
        if (startup.first_generation_validation) {
            require_unchanged_model();
            const auto & gate = policy.at("native_first_generation_validation");
            qwen_app::FirstGeneration trial(*engine);
            // Keep bounded route evidence in the tracked CPU heap while the
            // model is resident. Publish its sidecars only after positive model
            // and source retirement, avoiding extra file-cache pressure between
            // requests. Existing token/performance/monitoring records remain.
            std::array<CompletedRouteEvidence,3> completed_expert_reports;
            qwen_app::CheckpointValidationStats completed_checkpoint_validation;
            Json completed_speculative_requests=Json::array();
            std::vector<std::int32_t> speculative_reference_ids;
            std::vector<unsigned char> speculative_reference_bytes;
            bool speculative_tokens_exact=false;
            const bool checkpoint_model_candidate=policy.contains("native_model_checkpoint_validation");
            const bool prefix_model_validation=policy.contains("native_prefix_validation");
            const bool prefix_reuse_enabled=prefix_model_validation&&policy.at("native_prefix_validation").at("prefix_reuse_enabled").get<bool>();
            std::array<std::array<std::array<std::uint8_t,32>,33>,2> prefix_logit_fingerprints{};
            std::array<std::uint32_t,2> prefix_logit_counts{};
            std::array<qwen_app::PrefixReuseStats,2> completed_prefix_stats{};
            qwen_app::CheckpointValidationStats prefix_allocation_stats;
            std::uint32_t prefix_route_rows_compared=0;
            if(checkpoint_model_candidate&&(!expert_routes||prefill_tokens!=4))
                throw std::runtime_error("Complete checkpoint comparison requires original route observation and prefill four");
            if(prefix_model_validation&&(!expert_routes||prefill_tokens!=4||checkpoint_model_candidate))
                throw std::runtime_error("Prefix validation requires original route observation and an independent saved state");
            const auto admit_complete_checkpoint=[&](std::uint64_t bytes) {
                require_model_CPU_budget();require_unchanged_model();
                if(bytes<118038528u||bytes>142606336u)
                    throw std::runtime_error("Complete original KV/recurrent/PLE snapshot exceeds its priced payload");
                const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);
                const auto stats=qwen_app::native_model_device_stats();
                if(rounded>qwen_app::model_postload_device_budget-stats.live)
                    throw std::runtime_error("Complete checkpoint cannot retain the existing aggregate device cap");
                if(!hardware.gpu_total_bytes)throw std::runtime_error("Checkpoint requires an admitted native Direct pool identity");
                const auto available=qwen_native_allocator_budget(*hardware.gpu_total_bytes);
                if(available.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                    throw std::runtime_error("Complete checkpoint cannot retain observed Direct/Flexible/kernel reserve");
            };
            engine->set_work_guard([&] {
                trial.require_time();
                require_model_CPU_budget();
                // A fresh OS reserve is checked before and after each completed
                // single-token graph. This is not a page-cache residency proof.
                if (observed_system_headroom() < memory_budget.flexible_reserve)
                    throw std::runtime_error("First-generation OS reserve is no longer available");
            }, qwen_app::first_prompt_tokens);
            qwen_app::Request request{gate.at("run_id").get<std::string>(),
                qwen_app::render_first_generation_prompt(chat_template),
                qwen_app::first_context_tokens, qwen_app::first_output_tokens};
            const bool source_probe = policy.contains("native_source_contention_probe");
            if (source_probe) {
                const auto & diagnostic = policy.at("native_source_contention_probe");
                if (diagnostic.at("schema") != "ps5-qwen-completed-source-contention-policy-v1" ||
                    diagnostic.at("enabled") != true || diagnostic.at("completed_trace_pairs") != 32 ||
                    diagnostic.at("trace_sampling_interval") != 512 ||
                    diagnostic.at("maximum_diagnostic_outstanding_reads") != 2 ||
                    diagnostic.at("production_outstanding_reads") != 1 ||
                    diagnostic.at("additional_source_payload_buffers") != 0 ||
                    diagnostic.at("unchanged_memory_precision_driver_and_cache_policy") != true)
                    throw std::runtime_error("An explicit bounded source diagnostic policy is required");
                qwen_app::enable_native_completed_source_trace();
            }
            const auto first_performance = performance_snapshot(*engine);
            const auto first_cache=engine->expert_cache_metrics();
            const auto first_predictive=predictive_cache_bytes();
            if(expert_routes){
                if(!first_cache)throw std::runtime_error("Actual expert cache counters are required before route capture");
                if(!qwen_app::completed_expert_routes_pending())qwen_app::begin_completed_expert_routes();
            }
            const auto & result = trial.run(request, [&](const auto & bound) {
                write_fresh_report(startup.admission_report + ".first.intent", {
                    {"schema", "ps5-qwen-first-generation-intent-v1"}, {"run_id", bound.id}, {"pid", getpid()},
                    {"rendered_prompt", bound.rendered_prompt}, {"enable_thinking", false},
                    {"context_tokens", bound.context_tokens}, {"maximum_prompt_tokens", qwen_app::first_prompt_tokens},
                    {"maximum_output_tokens", bound.max_output_tokens},
                    {"maximum_generation_seconds", qwen_app::first_generation_seconds}});
            }, [&](const auto & token, const auto & metrics) {
                sample_boundary_memory("first_token_before_report");
                write_fresh_report(startup.admission_report + ".first.token-" + std::to_string(metrics.generated_tokens), {
                    {"schema", "ps5-qwen-first-generation-token-v1"}, {"run_id", request.id},
                    {"ordinal", metrics.generated_tokens}, {"token_id", token.id},
                    {"piece_bytes", std::vector<unsigned char>(token.piece.begin(), token.piece.end())},
                    {"elapsed_ms", metrics.total_ms},{"completed_performance",performance_snapshot(*engine)},
                    {"completed_path_counters",gpu_path_snapshot()}});
                sample_boundary_memory("first_token_after_report");
            }, observed_inference_stage);
            require_unchanged_model();
            engine->set_work_guard({});
            write_fresh_report(startup.admission_report + ".first.performance",
                performance_difference(first_performance, *engine));
            if(expert_routes){
                completed_expert_reports[0]=completed_route_evidence(*engine,
                    first_performance.at("process_calls").get<std::uint64_t>(),*first_cache,first_predictive);
            }
            Json metrics{{"prompt_tokens", result.metrics.prompt_tokens}, {"generated_tokens", result.metrics.generated_tokens},
                {"prefill_ms", result.metrics.prefill_ms}, {"total_ms", result.metrics.total_ms},
                {"TTFT_ms", nullptr}, {"decode_tokens_per_second", nullptr}};
            if (result.metrics.ttft_ms) metrics["TTFT_ms"] = *result.metrics.ttft_ms;
            if (result.metrics.decode_tokens_per_second) metrics["decode_tokens_per_second"] = *result.metrics.decode_tokens_per_second;
            write_fresh_report(startup.admission_report + ".first.result", {
                {"schema", "ps5-qwen-first-request-result-v1"}, {"pid", getpid()}, {"run_id", request.id},
                {"stop_reason", result.stop_reason}, {"token_ids", result.token_ids},
                {"output_bytes", result.output_bytes}, {"metrics", metrics}, {"prefill_batch_tokens", prefill_tokens},
                {"request_reset_completed", result.request_reset_completed}, {"model_loaded", true}});
            const std::string answer(result.output_bytes.begin(), result.output_bytes.end());
            const auto first = answer.find_first_not_of(" \t\r\n"), last = answer.find_last_not_of(" \t\r\n");
            if (first == std::string::npos || answer.substr(first, last - first + 1) != "4")
                throw std::runtime_error("The first original-model arithmetic smoke response was not the expected answer");
            if (source_probe) {
                // Observe only after a fresh positive GPU completion. This
                // diagnostic submits no GPU work and owns the existing source
                // window until every repeated read positively completes.
                qwen_native_driver_begin();qwen_native_driver_complete();
                require_model_CPU_budget();require_unchanged_model();
                qwen_native_stage("source_contention_trace_started_after_positive_GPU_completion");
                auto diagnostic = Json::parse(qwen_app::run_native_completed_source_trace());
                diagnostic["positive_GPU_completion_preceded_diagnostic"] = true;
                diagnostic["original_arithmetic_output"] = "4";
                write_fresh_report(startup.admission_report + ".contention", diagnostic);
                require_model_CPU_budget();require_unchanged_model();
                qwen_native_stage("source_contention_trace_completed_source_window_released");
            }
            // Recreate only the completed context. Resident model weights and
            // verified mappings stay alive; the first benchmark starts with an
            // empty expert cache while file pages/pipelines may already be warm.
            qwen_native_driver_begin();
            engine.reset(); llama_free(context); context = nullptr;
            qwen_native_driver_complete();
            require_model_CPU_budget(); require_unchanged_model();
            const auto benchmark_context_started = std::chrono::steady_clock::now();
            qwen_native_driver_begin();
            context = llama_init_from_model(model, qwen_app::streaming_context_params(qwen_app::first_context_tokens, cache_bytes, prefill_tokens));
            if (!context || std::chrono::steady_clock::now() - benchmark_context_started > std::chrono::seconds(600))
                throw std::runtime_error("The bounded cold-cache context recreation did not complete");
            engine = std::make_unique<qwen_app::LlamaEngine>(model, context, prefill_tokens);
            engine->set_stage_observer(observed_inference_stage);
            engine->set_gpu_boundaries(qwen_native_driver_begin, qwen_native_driver_complete,
                qwen_native_driver_retain, qwen_native_driver_checkpoint);
            qwen_native_driver_complete(); require_model_CPU_budget();
            write_fresh_report(startup.admission_report + ".demo.cache", {
                {"schema", "ps5-qwen-demo-cold-cache-admission-v1"}, {"pid", getpid()}, {"run_id", request.id},
                {"context_recreated_after_positive_completion", true}, {"expert_cache_initially_empty", true},
                {"model_reloaded", false}, {"model_loaded", true}, {"file_pages_and_pipelines_cold", false}});
            std::int64_t display_physical = 0; std::size_t display_available = 0;
            const auto display_pool = sceKernelGetDirectMemorySize();
            if (display_pool <= 0 || sceKernelAvailableDirectMemorySize(0, display_pool, 65536,
                &display_physical, &display_available) < 0 || display_available < memory_budget.direct_reserve + (32u << 20))
                throw std::runtime_error("Fresh model-resident display headroom is insufficient");
            screen.state = "original BF16 model ready"; screen.model_loaded = true;
            screen.gpu_name = hardware.gpu_name; screen.gpu_total_bytes = hardware.gpu_total_bytes;
            screen.gpu_free_bytes = hardware.gpu_free_bytes;
            display = std::make_unique<qwen_app::NativeDisplay>(direct_frame_candidate); display->start(screen);
            qwen_native_stage("model_resident_native_first_frame_completed");
            const auto demo = qwen_app::serve_bounded_demo(request.id, startup.web_assets, "0.0.0.0", startup.port, hardware,
                [&](unsigned ordinal, const std::function<bool()> & alive, const std::function<void(const Json &)> & publish) {
                    require_unchanged_model();
                    qwen_app::FirstGeneration attempt(*engine);
                    engine->set_work_guard([&] {
                        attempt.require_time();
                        require_model_CPU_budget();
                        if (!alive() || display->failed() || observed_system_headroom() < memory_budget.flexible_reserve)
                            throw std::runtime_error("The bounded inference observer, display or memory reserve failed");
                    }, qwen_app::first_prompt_tokens);
                    const auto prefix = startup.admission_report + ".demo" + std::to_string(ordinal);
                    qwen_app::Request external{request.id + "-" + std::to_string(ordinal),
                        qwen_app::render_bounded_user_prompt(chat_template, qwen_app::demo_prompt),
                        qwen_app::first_context_tokens, qwen_app::first_output_tokens};
                    auto external_metrics = [](const qwen_app::Metrics & value) {
                        return Json{{"prompt_tokens", value.prompt_tokens}, {"generated_tokens", value.generated_tokens},
                            {"prefill_ms", value.prefill_ms}, {"total_ms", value.total_ms},
                            {"ttft_ms", value.ttft_ms ? Json(*value.ttft_ms) : Json(nullptr)},
                            {"decode_tokens_per_second", value.decode_tokens_per_second ? Json(*value.decode_tokens_per_second) : Json(nullptr)}};
                    };
                    const auto external_performance = performance_snapshot(*engine);
                    const auto external_cache=engine->expert_cache_metrics();
                    const auto external_predictive=predictive_cache_bytes();
                    if(speculative_model_candidate&&ordinal==2) {
                        if(policy.at("native_model_free_speculation").contains("verification_policy")) {
                            struct OnlineCostState {
                                qwen_app::OnlineExpertVerification planner;
                                std::uint64_t source_before=0;
                            };
                            auto online=std::make_shared<OnlineCostState>();
                            qwen_app::ExpertVerificationHooks hooks;
                            hooks.before_process=[online] {
                                online->source_before=qwen_app::native_model_source_stats().read_ns;
                            };
                            hooks.completed_ordinary=[online](int token,std::uint64_t elapsed) {
                                const auto after=qwen_app::native_model_source_stats().read_ns;
                                if(after<online->source_before||!elapsed)
                                    throw std::runtime_error("Completed online source timing is inconsistent");
                                online->planner.observe(token,qwen_app::last_completed_single_token_routes(),
                                    double(elapsed)/1e9,double(std::min(after-online->source_before,elapsed))/1e9);
                            };
                            hooks.choose=[online](int pending,int draft){return online->planner.choose(pending,draft);};
                            hooks.verified=[online](bool accepted,double capture,double restore) {
                                online->planner.verified(accepted,capture,restore);
                            };
                            engine->enable_expert_aware_speculation(admit_complete_checkpoint,std::move(hooks));
                        }else engine->enable_model_free_speculation(admit_complete_checkpoint);
                    }
                    if(checkpoint_model_candidate&&ordinal==2) {
                        engine->enable_checkpoint_validation(admit_complete_checkpoint,
                            qwen_app::completed_expert_route_cursor,qwen_app::compare_completed_expert_route_ranges);
                    }
                    if(prefix_model_validation) {
                        if(ordinal==1&&prefix_reuse_enabled)engine->enable_prefix_reuse(admit_complete_checkpoint);
                        engine->set_logits_observer([&,ordinal](const float *values,std::size_t count) {
                            auto &next=prefix_logit_counts.at(ordinal-1);
                            if(next>=33)throw std::runtime_error("Completed prefix logit trace exceeds its fixed request bound");
                            prefix_logit_fingerprints.at(ordinal-1).at(next++)=qwen_app::model_logit_fingerprint(values,count);
                        });
                    }
                    if(expert_routes){
                        if(!external_cache)throw std::runtime_error("Actual expert cache counters are required before route capture");
                        if(!qwen_app::completed_expert_routes_pending())qwen_app::begin_completed_expert_routes();
                    }
                    const auto & generated = attempt.run(external, [&](const auto & bound) {
                        write_fresh_report(prefix + ".intent", {{"schema", "ps5-qwen-demo-request-intent-v1"},
                            {"pid", getpid()}, {"run_id", request.id}, {"ordinal", ordinal}, {"id", bound.id},
                            {"rendered_prompt", bound.rendered_prompt}, {"prompt", qwen_app::demo_prompt},
                            {"context_tokens", bound.context_tokens}, {"maximum_prompt_tokens", qwen_app::first_prompt_tokens},
                            {"maximum_output_tokens", bound.max_output_tokens}, {"enable_thinking", false},
                            {"maximum_generation_seconds", qwen_app::first_generation_seconds}});
                    }, [&](const auto & token, const auto & current) {
                        sample_boundary_memory("external_token_before_report");
                        const auto counter = engine->expert_cache_metrics();
                        Json event{{"id", external.id}, {"type", "token"}, {"state", "generating"},
                            {"ordinal", current.generated_tokens}, {"token_id", token.id},
                            {"piece_bytes", std::vector<unsigned char>(token.piece.begin(), token.piece.end())},
                            {"elapsed_ms", current.total_ms}, {"metrics", external_metrics(current)}, {"error", 0}};
                        if (counter) event["expert_cache"] = {{"hits", counter->hits}, {"misses", counter->misses},
                            {"uploaded_bytes", counter->uploaded_bytes}, {"prefetch_advice_bytes", counter->prefetch_advice_bytes}};
                        event["completed_performance"]=performance_snapshot(*engine);
                        event["completed_path_counters"]=gpu_path_snapshot();
                        write_fresh_report(prefix + ".token-" + std::to_string(current.generated_tokens), event);
                        sample_boundary_memory("external_token_after_report");
                        publish(event);
                        sample_boundary_memory("external_token_after_publish");
                    }, observed_inference_stage);
                    engine->set_work_guard({});
                    if(speculative_model_candidate) {
                        if(ordinal==1) {
                            speculative_reference_ids=generated.token_ids;
                            speculative_reference_bytes=generated.output_bytes;
                        }else {
                            if(generated.token_ids!=speculative_reference_ids||generated.output_bytes!=speculative_reference_bytes)
                                throw std::runtime_error("Causal width-two output token IDs or bytes differ from this case's original target control");
                            speculative_tokens_exact=true;
                        }
                        const auto s=engine->speculative_step_stats();
                        completed_speculative_requests.push_back({{"ordinal",ordinal},{"controller_enabled",s.controller_enabled},
                            {"attempts",s.attempts},{"accepted",s.accepted},{"rejected",s.rejected},
                            {"queued_bonus_samples",s.queued_bonus_samples},{"proposal_checks",s.proposal_checks},
                            {"no_draft",s.no_draft},{"prompt_proposals",s.prompt_proposals},{"generated_proposals",s.generated_proposals},
                            {"expert_cost_enabled",s.expert_cost_enabled},{"cost_checks",s.cost_checks},
                            {"cost_ordinary",s.cost_ordinary},{"cost_width_two",s.cost_width_two},
                            {"request_reset_completed",generated.request_reset_completed}});
                    }
                    if(prefix_model_validation) {
                        engine->set_logits_observer({});
                        if(generated.stop_reason!="end_of_generation"||generated.metrics.prompt_tokens!=30||
                           prefix_logit_counts.at(ordinal-1)!=generated.token_ids.size()+1)
                            throw std::runtime_error("Prefix logit trace must include every original sampled state and EOG");
                        completed_prefix_stats.at(ordinal-1)=engine->prefix_reuse_stats();
                        prefix_allocation_stats=engine->checkpoint_validation_stats();
                    }
                    if(checkpoint_model_candidate&&ordinal==2) {
                        completed_checkpoint_validation=engine->checkpoint_validation_stats();
                        const auto &c=completed_checkpoint_validation;
                        if(!c.completed||c.prefill_replays!=2||c.next_replays!=generated.token_ids.size()+1||c.captures!=c.restores||
                           c.captures!=c.prefill_replays+c.next_replays||c.captures>34)
                            throw std::runtime_error("Complete-model checkpoint comparison did not cover prefill, generated states and EOG");
                    }
                    if(expert_routes){
                        completed_expert_reports.at(ordinal)=completed_route_evidence(*engine,
                            external_performance.at("process_calls").get<std::uint64_t>(),*external_cache,external_predictive);
                    }
                    write_fresh_report(prefix + ".performance",
                        performance_difference(external_performance, *engine));
                    qwen_app::require_demo_sequence(generated.output_bytes);
                    if (display->failed() || generated.token_ids.size() < 2 ||
                        !generated.metrics.decode_tokens_per_second || !generated.metrics.ttft_ms)
                        throw std::runtime_error("The external request did not produce a measurable completed token sequence");
                    const Json report{{"schema", "ps5-qwen-demo-request-result-v1"}, {"pid", getpid()},
                        {"run_id", request.id}, {"id", external.id}, {"ordinal", ordinal},
                        {"cache_condition", ordinal == 1 ? "empty expert cache" : "retained expert cache"},
                        {"prefill_batch_tokens", prefill_tokens},
                        {"stop_reason", generated.stop_reason}, {"token_ids", generated.token_ids},
                        {"output_bytes", generated.output_bytes}, {"metrics", external_metrics(generated.metrics)},
                        {"request_reset_completed", generated.request_reset_completed},
                        {"GPU_completion_and_retirement_passed", true}, {"model_loaded", true}};
                    write_fresh_report(prefix + ".result", report);
                    publish({{"id", external.id}, {"type", "completion_pending"}, {"state", "finalizing frame evidence"}, {"error", 0},
                        {"metrics", report.at("metrics")}, {"stop_reason", generated.stop_reason}});
                    const auto frame = display->capture(prefix + ".display.bmp", external.id, generated.token_ids.size());
                    write_fresh_report(prefix + ".display.json", {{"schema", "ps5-qwen-displayed-frame-v1"},
                        {"pid", getpid()}, {"run_id", request.id}, {"id", frame.request_id},
                        {"width", 1920}, {"height", 1080}, {"BMP_bytes", 8294454},
                        {"generated_tokens", frame.generated_tokens}, {"epoch_ms", frame.epoch_ms},
                        {"clock_calibrated", frame.clock_calibrated}, {"model_loaded", frame.model_loaded},
                        {"TTFT_ms", frame.ttft_ms ? Json(*frame.ttft_ms) : Json(nullptr)},
                        {"decode_tokens_per_second", frame.tokens_per_second ? Json(*frame.tokens_per_second) : Json(nullptr)},
                        {"positive_VideoOut_completion", true}, {"evidence", "CPU raster after the matching completed VideoOut flip"}});
                    publish({{"id", external.id}, {"type", "finished"}, {"state", "completed"}, {"error", 0},
                        {"metrics", report.at("metrics")}, {"stop_reason", generated.stop_reason}});
                    return report;
                }, [&](const auto & snapshot) {
                    if (display->failed()) throw std::runtime_error("The passive native display failed");
                    display->publish(snapshot);
                }, [&](const auto & ready) { write_fresh_report(startup.admission_report + ".demo.ready", ready); });
            if(prefix_model_validation) {
                const auto &first=completed_prefix_stats[0],&second=completed_prefix_stats[1];
                if(prefix_logit_counts[0]!=23||prefix_logit_counts[1]!=23||prefix_logit_fingerprints[0]!=prefix_logit_fingerprints[1]||
                   first.enabled!=prefix_reuse_enabled||second.enabled!=prefix_reuse_enabled||first.request_hit||
                   first.captures!=(prefix_reuse_enabled?1u:0u)||first.restores||
                   second.captures!=(prefix_reuse_enabled?1u:0u)||second.restores!=(prefix_reuse_enabled?1u:0u)||
                   second.request_hit!=prefix_reuse_enabled||second.last_reused_prompt_tokens!=(prefix_reuse_enabled?30u:0u)||
                   demo.at("requests").at(0).at("token_ids")!=demo.at("requests").at(1).at("token_ids")||
                   demo.at("requests").at(0).at("output_bytes")!=demo.at("requests").at(1).at("output_bytes"))
                    throw std::runtime_error("Prefix continuation logits, emitted tokens or state reuse differ");
                const auto &ordinary=completed_expert_reports[1],&repeated=completed_expert_reports[2];
                const std::size_t offset=prefix_reuse_enabled?8*48:0;
                if(!ordinary.complete||!repeated.complete||ordinary.rows.size()!=offset+repeated.rows.size())
                    throw std::runtime_error("Prefix continuation route geometry differs");
                for(std::size_t i=0;i<repeated.rows.size();++i) {
                    const auto &a=ordinary.rows[i+offset],&b=repeated.rows[i];
                    if(a.layer!=b.layer||a.tokens!=b.tokens||!std::equal(a.ids.begin(),a.ids.begin()+10*a.tokens,b.ids.begin()))
                        throw std::runtime_error("Prefix continuation original expert selections differ");
                }
                prefix_route_rows_compared=std::uint32_t(repeated.rows.size());
            }
            write_fresh_report(startup.admission_report + ".demo.result", demo);
            require_unchanged_model();
            require_model_CPU_budget();
            if (display->failed()) throw std::runtime_error("Native presentation failed before model retirement");
            // All requests and the listener completed before model retirement.
            if(predictive_cache_candidate)qwen_app_complete_predictive_expert();
            qwen_native_driver_begin();
            engine.reset(); llama_free(context); context = nullptr; llama_model_free(model); model = nullptr;
            qwen_native_driver_complete();
            const auto source_stats = qwen_app::native_model_source_stats();
            const auto device_stats = qwen_app::native_model_device_stats();
            struct ps5_heap_stats final_heap{}; ps5_heap_stats(&final_heap);
            qwen_app::stop_native_model_sources();
            if(prefix_model_validation) {
                if(device_stats.live)throw std::runtime_error("Prefix snapshot owner has not positively retired with its context");
                Json traces=Json::array(),requests=Json::array();
                for(std::size_t ordinal=0;ordinal<2;++ordinal) {
                    Json hashes=Json::array();
                    for(std::uint32_t i=0;i<prefix_logit_counts[ordinal];++i) {
                        std::string value;value.reserve(64);
                        for(const auto byte:prefix_logit_fingerprints[ordinal][i]) {
                            value.push_back("0123456789abcdef"[byte>>4]);value.push_back("0123456789abcdef"[byte&15]);
                        }
                        hashes.push_back(value);
                    }
                    traces.push_back(hashes);const auto &p=completed_prefix_stats[ordinal];
                    requests.push_back({{"ordinal",ordinal+1},{"prefix_hit",p.request_hit},{"reused_prompt_tokens",p.last_reused_prompt_tokens},
                        {"cumulative_captures",p.captures},{"cumulative_restores",p.restores},
                        {"cumulative_capture_ns",p.capture_ns},{"cumulative_restore_ns",p.restore_ns}});
                }
                write_fresh_report(startup.admission_report+".prefix-reuse",{
                    {"schema","ps5-qwen-exact-prefix-validation-result-v1"},{"pid",getpid()},{"run_id",request.id},{"complete",true},
                    {"prefix_reuse_enabled",prefix_reuse_enabled},{"requests",requests},{"request_logit_SHA256",traces},
                    {"full_F32_logit_arrays_compared",23},{"all_F32_logit_fingerprints_exact",true},
                    {"original_route_rows_compared",prefix_route_rows_compared},{"all_original_expert_selections_exact",true},
                    {"all_emitted_tokens_and_bytes_exact",true},{"emitted_once",true},{"additional_GPU_downloads",0},
                    {"saved_state_payload_bytes",prefix_allocation_stats.maximum_payload_bytes},{"CPU_metadata_bytes",prefix_allocation_stats.maximum_metadata_bytes},
                    {"device_ledger_peak_bytes",device_stats.peak},{"device_ledger_live_bytes",device_stats.live},
                    {"all_model_source_and_snapshot_owners_retired",true},{"speedup_qualified",false}});
            }
            if(checkpoint_model_candidate) {
                const auto &c=completed_checkpoint_validation;
                if(!c.completed||device_stats.live)throw std::runtime_error("Complete checkpoint owner has not positively retired with the model");
                std::vector<std::int32_t> positions(c.capture_positions.begin(),c.capture_positions.begin()+c.captures);
                write_fresh_report(startup.admission_report+".model-checkpoint",{
                    {"schema","ps5-qwen-model-checkpoint-validation-result-v1"},{"pid",getpid()},{"run_id",request.id},
                    {"captures",c.captures},{"restores",c.restores},{"capture_positions",positions},{"prefill_replays",c.prefill_replays},
                    {"next_replays_including_EOG",c.next_replays},{"original_route_rows_compared",c.route_rows_compared},
                    {"maximum_state_payload_bytes",c.maximum_payload_bytes},{"maximum_CPU_metadata_bytes",c.maximum_metadata_bytes},
                    {"maximum_absolute_logit_error",c.maximum_absolute_logit_error},{"absolute_tolerance",1e-5},{"relative_tolerance",1e-5},
                    {"effective_F32_logits_positions_pending_prompt_and_greedy_state_restored",true},
                    {"all_original_expert_selections_exact",true},{"all_continuation_tokens_and_bytes_exact",true},{"emitted_once",true},
                    {"device_ledger_peak_bytes",device_stats.peak},{"device_ledger_live_bytes",device_stats.live},
                    {"all_model_source_and_checkpoint_owners_retired",true},{"performance_adoption_enabled",false},
                    {"prefix_reuse_qualified",false},{"speculative_verification_qualified",false}});
            }
            if(speculative_model_candidate) {
                if(!speculative_tokens_exact||completed_speculative_requests.size()!=2||device_stats.live)
                    throw std::runtime_error("The finite causal width-two control or positive owner retirement is incomplete");
                write_fresh_report(startup.admission_report+".model-free-speculation",{
                    {"schema","ps5-qwen-causal-width-two-result-v1"},{"pid",getpid()},{"run_id",request.id},
                    {"requests",completed_speculative_requests},{"all_control_token_IDs_and_bytes_exact",true},
                    {"target_width_two_exercised",completed_speculative_requests.at(1).at("attempts").get<std::uint32_t>()>0},
                    {"expert_cost_policy",policy.at("native_model_free_speculation").value("verification_policy","fixed-width-two")},
                    {"all_model_source_and_checkpoint_owners_retired",true},{"device_ledger_live_bytes",device_stats.live},
                    {"cache_condition_comparison_is_not_speed_qualification",true},{"speedup_qualified",false},
                    {"complete_checkpoint_qualification_SHA256","e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7"}});
            }
            if(predictive_cache_candidate) {
                qwen_predictive_cache_stats p{};qwen_app_predictive_cache_counters(&p);
                if(p.loads!=p.useful+p.unused||p.loads!=source_stats.predictive_experts||device_stats.live)
                    throw std::runtime_error("Predictive cache evidence lacks completed original reads or retired owners");
                write_fresh_report(startup.admission_report+".predictive-cache",{
                    {"schema","ps5-qwen-predictive-cache-result-v1"},{"pid",getpid()},{"run_id",request.id},
                    {"proposals",p.proposals},{"loads",p.loads},{"useful_next_layer",p.useful},
                    {"unused_next_layer",p.unused},{"ineligible",p.ineligible},{"logical_bytes",p.logical_bytes},
                    {"foreground_wait_ns",source_stats.predictive_wait_ns},{"worker_read_ns",source_stats.predictive_read_ns},
                    {"all_read_jobs_completed",true},{"actual_bank_leases_retired",true},
                    {"all_model_owners_retired",true},{"device_ledger_live_bytes",device_stats.live},
                    {"speedup_qualified",false}});
            }
            if(expert_routes){
                const std::array<const char *,3> suffixes{{".first",".demo1",".demo2"}};
                for(std::size_t i=0;i<completed_expert_reports.size();++i){
                    auto routes=completed_route_report(completed_expert_reports[i]);
                    routes.update({{"pid",getpid()},{"run_id",request.id},{"cache_reset_before_request",i<2},
                        {"sidecar_written_after_model_and_source_retirement",true},
                        {"JSON_created_after_model_and_source_retirement",true}});
                    if(i)routes["ordinal"]=i;
                    write_fresh_report(startup.admission_report+suffixes[i]+".expert-routes",routes);
                    completed_expert_reports[i]=CompletedRouteEvidence{};
                }
            }
            if(policy.contains("native_shader_storage")) {
                const auto shaders=qwen_app::native_shader_asset_stats();
                if(shaders.failed||shaders.active_lease||shaders.external_file.read_pending||
                   (shaders.external_file.registered&&!shaders.external_file.verified)||
                   (shaders.external_file.registered&&shaders.external_file.frame_requests!=shaders.decoded_calls+shaders.raw_calls)||
                   shaders.decoded_calls+shaders.raw_calls<=shaders.CPU_verified_assets)
                    throw std::runtime_error("The completed Vulkan plan lacks positively retired original shader inputs");
                write_fresh_report(startup.admission_report+".shader-assets.Vulkan",{
                    {"schema",shaders.external_file.registered?"ps5-qwen-shader-storage-Vulkan-result-v2":"ps5-qwen-shader-storage-Vulkan-result-v1"},
                    {"pid",getpid()},{"run_id",request.id},
                    {"registry_sha256",shaders.registry_sha256},{"CPU_verified_assets_in_this_run",shaders.CPU_verified_assets},
                    {"module_input_restorations_after_CPU_verification",shaders.decoded_calls+shaders.raw_calls-shaders.CPU_verified_assets},
                    {"active_lease",false},{"failed",false},{"all_used_original_SPIRV_SHA256_checked",true},
                    {"external_file",shaders.external_file.registered},{"external_file_SHA256_verified",shaders.external_file.verified},
                    {"codec_input_window_bytes",shaders.external_file.input_window_bytes},{"external_read_pending",shaders.external_file.read_pending},
                    {"external_read_calls",shaders.external_file.read_calls},{"external_returned_bytes",shaders.external_file.returned_bytes},
                    {"external_frame_requests",shaders.external_file.frame_requests},
                    {"positive_plan_GPU_completion_and_retirement",true},{"persistent_caches_enabled",false}});
            }
            write_fresh_report(startup.admission_report + ".memory.backpressure", memory_backpressure_report());
            if(boundary_memory_enabled)write_fresh_report(startup.admission_report+".boundary-memory",boundary_memory_report());
            write_fresh_report(startup.admission_report, {
                {"schema", "ps5-qwen-plan-validation-result-v1"}, {"run_id", request.id},
                {"pid", getpid()}, {"candidate_SELF_sha256", gate.at("candidate_SELF_sha256")},
                {"model_receipt_sha256", gate.at("model_receipt_sha256")},
                {"driver_revision", gate.at("driver_revision")}, {"profile", gate.at("profile")},
                {"native_archive_sha256", gate.at("native_archive_sha256")},
                {"source_IO_completed", true}, {"source_read_bytes", source_stats.bytes},
                {"source_read_chunks", source_stats.chunks}, {"maximum_source_read_bytes", source_stats.maximum_chunk},
                {"source_pipeline_worker_stopped", true},
                {"postload_device_peak_bytes", device_stats.peak}, {"postload_device_live_bytes", device_stats.live},
                {"postload_device_allocations", device_stats.allocations},
                {"CPU_heap_peak_bytes", final_heap.peak_bytes}, {"untracked_libc_heap_fallbacks", final_heap.libc_fallbacks},
                {"state", "completed_waiting_for_ordinary_close"}, {"stop_reason", result.stop_reason},
                {"token_ids", result.token_ids}, {"output_bytes", result.output_bytes}, {"metrics", metrics},
                {"request_reset_completed", result.request_reset_completed}, {"GPU_completion_and_retirement_passed", true},
                {"model_resources_released_after_completion", true}, {"model_loaded", false},
                {"full_model_inference_executed", true}, {"answer_quality_qualified", false},
                {"text_generation_observed", !result.output_bytes.empty()},
                {"native_display_started", true}, {"external_requests_accepted", 2}, {"demonstration", demo},
                {"arithmetic_smoke_passed", true}});
            screen.state = "validation requests finished"; screen.model_loaded = false;
            screen.message = "CLOSE THE TITLE THROUGH THE ORDINARY OS PATH"; display->publish(screen);
            qwen_native_stage("plan_requests_completed_waiting_for_ordinary_close");
            for (;;) std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        qwen_native_stage("inference_before_HTTP_listener_after_model_and_context_admission");
        const int result = qwen_app::serve_http(*engine, startup.web_assets, chat_template, startup.port, false, hardware,
            display ? std::function<void(const qwen_app::MonitorSnapshot &)>([&](const auto & snapshot) { display->publish(snapshot); })
                    : std::function<void(const qwen_app::MonitorSnapshot &)>{});
        if (result) throw std::runtime_error("Inference HTTP listener failed");
        if (engine->failed()) throw std::runtime_error("Model resources retained after an uncertain backend result");
        qwen_native_driver_begin();
        engine.reset(); llama_free(context); context = nullptr; llama_model_free(model); model = nullptr;
        qwen_native_driver_complete();
        if (display) {
            screen.state = "service stopped"; screen.message = "CLOSE THE TITLE THROUGH THE ORDINARY OS PATH";
            display->publish(screen);
            for (;;) std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        return result;
    } catch (const std::exception & error) {
        if(native_resources_started)qwen_native_driver_retain();
        // No manual release or automatic retry after a failed native admission.
        // The owning process must remain available for ordinary OS shutdown.
        sample_boundary_memory("native_exception_after_work_stopped");
        qwen_native_stage("native_exception_admission_failed");
        qwen_native_log_bytes(error.what(), std::strlen(error.what()));
        qwen_native_log_bytes("\n", 1);
        if (!validation_report.empty()) {
            try { write_fresh_report(validation_report + ".failure", {{"stage", "native_exception"},
                {"message", error.what()}, {"model_loaded", model!=nullptr},
                {"memory_backpressure",memory_backpressure_report()},
                {"boundary_memory",boundary_memory_report()}}); } catch (...) {}
        }
        if (native_resources_started) {
            engine.release();
            try {
                screen.state = "admission failed"; screen.message = error.what(); screen.quarantined = true;
                if (display) display->publish(screen);
            } catch (...) {}
            // Keep the resource graph alive, without issuing more GPU operations.
            for (;;) std::this_thread::sleep_for(std::chrono::seconds(60));
        }
        return 1;
    } catch (...) {
        if (native_resources_started) {
            qwen_native_driver_retain();
            engine.release();
            for (;;) (void) usleep(1000000);
        }
        return 1;
    }
}
