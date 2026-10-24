// SPDX-License-Identifier: MIT
// Native startup, inference ownership and read-only VideoOut monitoring.
#include "http_app.h"
#include "llama_engine.h"
#include "expert_policy.h"
#include "native_display.h"
#include "startup.h"
#include "gpu_admission.h"
#include "operator_admission.h"
#include "moe_admission.h"
#include "runtime_admission.h"
#include "vulkan_admission.h"
#include "memory_admission.h"
#include "memory_probe.h"
#include "system_memory.h"
#include "source_contention.h"
#include "source_virtual_addresses.h"
#include "model_integrity.h"
#include "direct_integrity.h"
#include "direct_metadata.h"
#include "stage_memory_probe.h"
#include "shader_assets.h"
#include "prior_model_integrity.h"
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
// A required link symbol prevents accidental use of an unpatched eager loader.
extern "C" bool llama_app_mmap_prefetch_disabled();
extern "C" bool ggml_app_bounded_staging_enabled();
extern "C" bool ggml_app_dispatch_contract_enabled();
extern "C" void qwen_native_set_fault_report(const char *);
extern "C" void qwen_native_stage(const char *);
extern "C" void qwen_native_log_bytes(const char *, std::size_t);

static void native_log(enum ggml_log_level, const char * text, void *) {
    if (text) qwen_native_log_bytes(text, std::strlen(text));
}

static void write_fresh_report(const std::string & path, const Json & value) {
    const auto bytes = value.dump(2) + "\n";
    // Reports contain metadata and controlled validation output, never credentials.
    const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0) throw std::runtime_error("Fresh native report could not be created");
    if (fchmod(fd, 0644)) { close(fd); throw std::runtime_error("Native metadata report permissions could not be set"); }
    const bool saved = write(fd, bytes.data(), bytes.size()) == static_cast<ssize_t>(bytes.size()) && fsync(fd) == 0;
    const bool closed = close(fd) == 0;
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
    return result;
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
    return {{"schema", selected ? "ps5-qwen-completed-performance-v4" : "ps5-qwen-completed-performance-v3"}, {"delta", delta},
        {"process_includes_source_and_backend_work", true}, {"GPU_timestamp_queries", false},
        {"hot_path_logs_added", false}, {"GPU_operations_added", false},
        {"source_read_ns_is_producer_wait_time", true}, {"maximum_parallel_source_reads", selected ? 2 : 1},
        {"file_range_schedule_enabled", selected}, {"physical_read_bytes_include_alignment", true},
        {"worker_times_overlap_consumers", true}};
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
                              std::unordered_set<std::string> & names, std::uint64_t expected_bytes) {
    std::ifstream file(path, std::ios::binary|std::ios::ate);
    if(!file || file.tellg()<0 || static_cast<std::uint64_t>(file.tellg())!=expected_bytes)
        throw std::runtime_error("Transferred model size differs from the conversion receipt");
    footprint.mapped_files=qwen_app::checked_memory_sum(footprint.mapped_files,expected_bytes);
    std::unique_ptr<gguf_context, decltype(&gguf_free)> metadata(
        gguf_init_from_file(path.c_str(), {true, nullptr}), gguf_free);
    if (!metadata) throw std::runtime_error("GGUF metadata could not be read");
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
        const auto mode = startup.memory_validation ? "native-memory-validation" : startup.display_validation ? "display-validation" : startup.runtime_validation ? "runtime-validation" : startup.monitor_validation ? "monitor-validation" : startup.model_validation ? "model-validation" : startup.operator_validation ? "operator-validation" : startup.moe_validation ? "moe-validation" : startup.first_generation_validation ? "first-generation-validation" : "inference";
        if (!policy.contains("allowed_modes") || !policy.at("allowed_modes").is_array() ||
            std::find(policy.at("allowed_modes").begin(), policy.at("allowed_modes").end(), Json(mode)) == policy.at("allowed_modes").end())
            throw std::runtime_error("This application mode has not passed the preceding qualification stage");
        // A frozen fixture policy does not replace the launcher's fresh console
        // guards. Full-model inference remains independently rejected here.
        qwen_app::require_native_validation_policy(policy, mode, startup.native_display);
        if (startup.first_generation_validation && startup.port != 8086)
            throw std::runtime_error("The bounded external demonstration requires its exact admitted port");
        if (startup.first_generation_validation && (!llama_app_mapped_source_hooks() ||
            !llama_app_bounded_expert_advice_hooks() || !ggml_app_mapped_upload_hooks() ||
            !ggml_app_mapped_async_hooks() || !ggml_app_bounded_cpu_fallback_hooks() || !ggml_app_bounded_device_buffers_hooks() ||
            !ggml_app_bounded_workspace_hooks()))
            throw std::runtime_error("Every bounded source-read engine integration hook is required");
        qwen_app::monitor_clock().initialize(startup.clock_calibration);
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
                write_fresh_report(startup.admission_report+".system-memory.before-startup-integrity",
                    system_memory_report(qwen_app::observe_native_system_memory()));
                qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
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
            qwen_app::enable_native_memory_backpressure();
        }
        if(qwen_app::native_shader_assets_registered()!=policy.contains("native_shader_storage"))
            throw std::runtime_error("Packed shader resources require explicit prior CPU validation");
        if(policy.contains("native_shader_storage")) {
            const auto &storage=policy.at("native_shader_storage");
            if(!startup.first_generation_validation||storage.at("schema")!="ps5-qwen-shader-storage-policy-v1"||
               storage.at("enabled")!=true||storage.at("verify_all_original_assets_before_Vulkan")!=true||
               storage.at("model_and_shader_precision_unchanged")!=true||storage.at("persistent_caches_enabled")!=false)
                throw std::runtime_error("Lossless shader storage CPU admission is not authorized");
            qwen_app::initialize_native_shader_assets();
            const auto declared=qwen_app::native_shader_asset_stats();
            if(declared.assets!=storage.at("shader_count")||declared.original_bytes!=storage.at("original_bytes")||
               declared.stored_bytes!=storage.at("stored_bytes")||declared.lookup_entries!=storage.at("lookup_entries")||
               declared.registry_sha256!=storage.at("registry_sha256"))
                throw std::runtime_error("Shader CPU verification exceeds the exact private resource plan");
            const auto shaders=qwen_app::verify_native_shader_assets_CPU();
            if(shaders.failed||shaders.active_lease||shaders.CPU_verified_assets!=shaders.assets||
               shaders.CPU_verified_lookups!=shaders.lookup_entries||shaders.assets!=storage.at("shader_count")||
               shaders.original_bytes!=storage.at("original_bytes")||shaders.stored_bytes!=storage.at("stored_bytes")||
               shaders.registry_sha256!=storage.at("registry_sha256"))
                throw std::runtime_error("Lossless shader CPU bytes or lookup identity did not match the private plan");
            require_model_CPU_budget();
            write_fresh_report(startup.admission_report+".shader-assets.CPU",{
                {"schema","ps5-qwen-shader-storage-CPU-result-v1"},{"pid",getpid()},
                {"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"shader_count",shaders.assets},{"original_bytes",shaders.original_bytes},{"stored_bytes",shaders.stored_bytes},
                {"CPU_verified_assets",shaders.CPU_verified_assets},{"lookup_entries",shaders.lookup_entries},
                {"CPU_verified_lookups",shaders.CPU_verified_lookups},{"registry_sha256",shaders.registry_sha256},
                {"codec_output_bytes",shaders.codec_output_bytes},{"codec_scratch_bytes",shaders.codec_scratch_bytes},
                {"active_lease",false},{"failed",false},{"all_original_SPIRV_bytes_preserved",true},
                {"GPU_calls",0},{"Vulkan_initialized",false},{"model_loaded",false},{"persistent_caches_enabled",false}});
            qwen_native_stage("all_original_shader_CPU_bytes_and_lookups_verified_before_Vulkan");
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
        const auto prior_integrity = startup.first_generation_validation ?
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
        };
        require_prior_metadata();
        const bool direct_metadata=policy.contains("native_direct_metadata");
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
                    model_file(startup.model_receipt,file.at("path").get<std::string>()), file_bytes));
            if (prior_integrity && !identity_namespace->matches(file_identities.back(), prior_integrity->files.at(file_index - 1)))
                throw std::runtime_error("Sealed original model file changed after native SHA verification");
            if(direct_metadata)qwen_app::register_native_direct_metadata(
                model_file(startup.model_receipt,file.at("path").get<std::string>()),file_identities.back());
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
                footprint,tensor_names,file.at("bytes").get<std::uint64_t>()); first = false;
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
            {"verification_mode",prior_integrity ? "prior_native_SHA_and_unchanged_sealed_identity" : "complete_native_SHA_this_run"},
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
                if (model_file_identity(mapping_files[i].path, mapping_files[i].bytes) != file_identities[i])
                    throw std::runtime_error("Original model changed after its native verification");
        };
        require_unchanged_model();

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
            for (std::size_t i = 0; i < mapping_files.size(); ++i)
                sources.push_back({mapping_files[i].path, mapping_files[i].bytes, file_identities[i]});
            qwen_app::start_native_model_sources(std::move(sources));
            write_fresh_report(startup.admission_report + ".source", {
                {"schema", "ps5-qwen-bounded-source-admission-v1"}, {"pid", getpid()},
                {"direct_read_preflight_passed", true}, {"maximum_window_bytes", qwen_app::model_read_window},
                {"CPU_source_read_window_in_Direct_heap", true},
                {"maximum_open_handles", 8}, {"mapped_source_upload_dereferences_enabled", false},
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
        qwen_app::inspect_vulkan_globals();
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
        const auto buffer_type=ggml_backend_dev_buffer_type(device);
        const auto system_memory=qwen_app::admit_native_system_memory();
        const qwen_app::MemoryObservation memory_observation{driver_free,direct,qwen_app::qualified_system_headroom(system_memory),
            ggml_backend_buft_get_max_size(buffer_type),ggml_backend_buft_get_alignment(buffer_type)};
        memory_budget.admit(footprint,memory_observation);
        write_fresh_report(startup.admission_report+".memory",{{"schema","ps5-qwen-memory-admission-v1"},
            {"pid",getpid()},{"model_loaded",false},{"device_weights_bytes",footprint.device_weights},
            {"mapped_experts_bytes",footprint.mapped_experts},{"required_lazy_PLE_bytes",footprint.lazy_ple},
            {"mapped_embedding_bytes",footprint.mapped_embeddings},{"mapped_file_bytes",footprint.mapped_files},
            {"planned_resident_headroom_bytes",memory_budget.device_requirement(footprint)},
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
        screen.state = "admitting inference context";
        if (display) display->publish(screen);
        const auto context_started = std::chrono::steady_clock::now();
        context = llama_init_from_model(model, qwen_app::streaming_context_params(
            startup.first_generation_validation ? qwen_app::first_context_tokens : 4096, cache_bytes));
        if (!context) throw std::runtime_error("Context admission failed; restart through the ordinary OS path");
        write_fresh_report(startup.admission_report+".system-memory.after-context",
            system_memory_report(qwen_app::observe_native_system_memory(),true));
        if (startup.first_generation_validation) require_model_CPU_budget();
        if (startup.first_generation_validation && std::chrono::steady_clock::now() - context_started > std::chrono::seconds(600))
            throw std::runtime_error("Context creation exceeded its first-generation boundary deadline");
        engine = std::make_unique<qwen_app::LlamaEngine>(model, context);
        engine->set_stage_observer(qwen_native_stage);
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
            const auto & result = trial.run(request, [&](const auto & bound) {
                write_fresh_report(startup.admission_report + ".first.intent", {
                    {"schema", "ps5-qwen-first-generation-intent-v1"}, {"run_id", bound.id}, {"pid", getpid()},
                    {"rendered_prompt", bound.rendered_prompt}, {"enable_thinking", false},
                    {"context_tokens", bound.context_tokens}, {"maximum_prompt_tokens", qwen_app::first_prompt_tokens},
                    {"maximum_output_tokens", bound.max_output_tokens},
                    {"maximum_generation_seconds", qwen_app::first_generation_seconds}});
            }, [&](const auto & token, const auto & metrics) {
                write_fresh_report(startup.admission_report + ".first.token-" + std::to_string(metrics.generated_tokens), {
                    {"schema", "ps5-qwen-first-generation-token-v1"}, {"run_id", request.id},
                    {"ordinal", metrics.generated_tokens}, {"token_id", token.id},
                    {"piece_bytes", std::vector<unsigned char>(token.piece.begin(), token.piece.end())},
                    {"elapsed_ms", metrics.total_ms}});
            }, qwen_native_stage);
            require_unchanged_model();
            engine->set_work_guard({});
            write_fresh_report(startup.admission_report + ".first.performance",
                performance_difference(first_performance, *engine));
            Json metrics{{"prompt_tokens", result.metrics.prompt_tokens}, {"generated_tokens", result.metrics.generated_tokens},
                {"prefill_ms", result.metrics.prefill_ms}, {"total_ms", result.metrics.total_ms},
                {"TTFT_ms", nullptr}, {"decode_tokens_per_second", nullptr}};
            if (result.metrics.ttft_ms) metrics["TTFT_ms"] = *result.metrics.ttft_ms;
            if (result.metrics.decode_tokens_per_second) metrics["decode_tokens_per_second"] = *result.metrics.decode_tokens_per_second;
            write_fresh_report(startup.admission_report + ".first.result", {
                {"schema", "ps5-qwen-first-request-result-v1"}, {"pid", getpid()}, {"run_id", request.id},
                {"stop_reason", result.stop_reason}, {"token_ids", result.token_ids},
                {"output_bytes", result.output_bytes}, {"metrics", metrics},
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
            context = llama_init_from_model(model, qwen_app::streaming_context_params(qwen_app::first_context_tokens, cache_bytes));
            if (!context || std::chrono::steady_clock::now() - benchmark_context_started > std::chrono::seconds(600))
                throw std::runtime_error("The bounded cold-cache context recreation did not complete");
            engine = std::make_unique<qwen_app::LlamaEngine>(model, context);
            engine->set_stage_observer(qwen_native_stage);
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
            display = std::make_unique<qwen_app::NativeDisplay>(); display->start(screen);
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
                    const auto & generated = attempt.run(external, [&](const auto & bound) {
                        write_fresh_report(prefix + ".intent", {{"schema", "ps5-qwen-demo-request-intent-v1"},
                            {"pid", getpid()}, {"run_id", request.id}, {"ordinal", ordinal}, {"id", bound.id},
                            {"rendered_prompt", bound.rendered_prompt}, {"prompt", qwen_app::demo_prompt},
                            {"context_tokens", bound.context_tokens}, {"maximum_prompt_tokens", qwen_app::first_prompt_tokens},
                            {"maximum_output_tokens", bound.max_output_tokens}, {"enable_thinking", false},
                            {"maximum_generation_seconds", qwen_app::first_generation_seconds}});
                    }, [&](const auto & token, const auto & current) {
                        const auto counter = engine->expert_cache_metrics();
                        Json event{{"id", external.id}, {"type", "token"}, {"state", "generating"},
                            {"ordinal", current.generated_tokens}, {"token_id", token.id},
                            {"piece_bytes", std::vector<unsigned char>(token.piece.begin(), token.piece.end())},
                            {"elapsed_ms", current.total_ms}, {"metrics", external_metrics(current)}, {"error", 0}};
                        if (counter) event["expert_cache"] = {{"hits", counter->hits}, {"misses", counter->misses},
                            {"uploaded_bytes", counter->uploaded_bytes}, {"prefetch_advice_bytes", counter->prefetch_advice_bytes}};
                        write_fresh_report(prefix + ".token-" + std::to_string(current.generated_tokens), event);
                        publish(event);
                    }, qwen_native_stage);
                    engine->set_work_guard({});
                    write_fresh_report(prefix + ".performance",
                        performance_difference(external_performance, *engine));
                    qwen_app::require_demo_sequence(generated.output_bytes);
                    if (display->failed() || generated.token_ids.size() < 2 ||
                        !generated.metrics.decode_tokens_per_second || !generated.metrics.ttft_ms)
                        throw std::runtime_error("The external request did not produce a measurable completed token sequence");
                    const Json report{{"schema", "ps5-qwen-demo-request-result-v1"}, {"pid", getpid()},
                        {"run_id", request.id}, {"id", external.id}, {"ordinal", ordinal},
                        {"cache_condition", ordinal == 1 ? "empty expert cache" : "retained expert cache"},
                        {"stop_reason", generated.stop_reason}, {"token_ids", generated.token_ids},
                        {"output_bytes", generated.output_bytes}, {"metrics", external_metrics(generated.metrics)},
                        {"request_reset_completed", generated.request_reset_completed},
                        {"GPU_completion_and_retirement_passed", true}, {"model_loaded", true}};
                    write_fresh_report(prefix + ".result", report);
                    publish({{"id", external.id}, {"type", "finished"}, {"state", "completed"}, {"error", 0},
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
                    return report;
                }, [&](const auto & snapshot) {
                    if (display->failed()) throw std::runtime_error("The passive native display failed");
                    display->publish(snapshot);
                }, [&](const auto & ready) { write_fresh_report(startup.admission_report + ".demo.ready", ready); });
            write_fresh_report(startup.admission_report + ".demo.result", demo);
            require_unchanged_model();
            require_model_CPU_budget();
            if (display->failed()) throw std::runtime_error("Native presentation failed before model retirement");
            // All requests and the listener completed before model retirement.
            qwen_native_driver_begin();
            engine.reset(); llama_free(context); context = nullptr; llama_model_free(model); model = nullptr;
            qwen_native_driver_complete();
            const auto source_stats = qwen_app::native_model_source_stats();
            const auto device_stats = qwen_app::native_model_device_stats();
            struct ps5_heap_stats final_heap{}; ps5_heap_stats(&final_heap);
            qwen_app::stop_native_model_sources();
            write_fresh_report(startup.admission_report + ".memory.backpressure", memory_backpressure_report());
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
        qwen_native_stage("native_exception_admission_failed");
        qwen_native_log_bytes(error.what(), std::strlen(error.what()));
        qwen_native_log_bytes("\n", 1);
        if (!validation_report.empty()) {
            try { write_fresh_report(validation_report + ".failure", {{"stage", "native_exception"},
                {"message", error.what()}, {"model_loaded", model!=nullptr},
                {"memory_backpressure",memory_backpressure_report()}}); } catch (...) {}
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
