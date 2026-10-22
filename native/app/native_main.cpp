// SPDX-License-Identifier: MIT
// Native startup, inference ownership and read-only VideoOut monitoring.
#include "http_app.h"
#include "llama_engine.h"
#include "expert_policy.h"
#include "native_display.h"
#include "startup.h"
#include "gpu_admission.h"
#include "runtime_admission.h"
#include "vulkan_admission.h"
#include "memory_admission.h"
#include "model_integrity.h"
#include "model_receipt.h"
#include "validation_policy.h"
#include "native_gpu.h"
#include <fcntl.h>
#include <unistd.h>
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
#include "ggml-cpu.h"
#include "gguf.h"
#include "nlohmann/json.hpp"

#include <cstdlib>
#include <algorithm>
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
    // Reports contain status/fixture metadata only, never prompts or secrets.
    const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0) throw std::runtime_error("Fresh native report could not be created");
    if (fchmod(fd, 0644)) { close(fd); throw std::runtime_error("Native metadata report permissions could not be set"); }
    const bool saved = write(fd, bytes.data(), bytes.size()) == static_cast<ssize_t>(bytes.size()) && fsync(fd) == 0;
    const bool closed = close(fd) == 0;
    if (!saved || !closed) throw std::runtime_error("Native report could not be persisted");
}

static std::string model_file(const std::string & receipt, const std::string & name) {
    if (name.empty() || name.find_first_of("/\\:") != std::string::npos || name == "." || name == "..")
        throw std::runtime_error("Receipt model files must use relative basenames");
    const auto separator = receipt.find_last_of("/\\");
    return separator == std::string::npos ? name : receipt.substr(0, separator + 1) + name;
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
             {"qwen4exp.expert_used_count",10},{"qwen4exp.embedding_length",2560}}) {
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

static std::uint64_t observed_os_free() {
    std::uint32_t pages=0, page_size=0;std::size_t a=sizeof(pages),b=sizeof(page_size);
    if(sysctlbyname("vm.stats.vm.v_free_count",&pages,&a,nullptr,0)||
       sysctlbyname("vm.stats.vm.v_page_size",&page_size,&b,nullptr,0)||a!=sizeof(pages)||b!=sizeof(page_size)||
       !pages||page_size<4096||page_size>(1u<<20))
        throw std::runtime_error("A valid fresh OS free-memory observation is required");
    return std::uint64_t(pages)*page_size;
}

struct LoadProgress {
    std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
    unsigned reported=0;
};
static bool observe_model_load(float progress,void * opaque) {
    auto & state=*static_cast<LoadProgress *>(opaque);
    if(!std::isfinite(progress)||progress<0||progress>1) return false;
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
        const auto mode = startup.display_validation ? "display-validation" : startup.runtime_validation ? "runtime-validation" : startup.monitor_validation ? "monitor-validation" : "inference";
        if (!policy.contains("allowed_modes") || !policy.at("allowed_modes").is_array() ||
            std::find(policy.at("allowed_modes").begin(), policy.at("allowed_modes").end(), Json(mode)) == policy.at("allowed_modes").end())
            throw std::runtime_error("This application mode has not passed the preceding qualification stage");
        // A frozen fixture policy does not replace the launcher's fresh console
        // guards. Full-model inference remains independently rejected here.
        qwen_app::require_native_validation_policy(policy, mode, startup.native_display);
        qwen_native_stage("policy_admitted GPU_not_started=1 model_loaded=0");
        llama_log_set(native_log, nullptr); ggml_log_set(native_log, nullptr);
        qwen_native_set_fault_report((startup.admission_report + ".fatal").c_str());
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

        screen.state = startup.display_validation ? "display validation" : startup.runtime_validation ? "CPU runtime admission" : startup.monitor_validation ? "BF16 GPU admission" : "verifying model";
        screen.cpu_threads = std::thread::hardware_concurrency();
        char cpu_name[256] = {};
        std::size_t cpu_name_size = sizeof(cpu_name);
        if (!sysctlbyname("hw.model", cpu_name, &cpu_name_size, nullptr, 0) && cpu_name_size &&
            std::memchr(cpu_name, 0, sizeof(cpu_name))) screen.cpu_name = cpu_name;
        if (startup.native_display) {
            qwen_native_stage("before_display_start compute_dispatches=0 model_loaded=0");
            display = std::make_unique<qwen_app::NativeDisplay>();
            native_resources_started = true;
            display->start(screen);
            qwen_native_stage("first_display_frame_completed compute_dispatches=0 model_loaded=0");
        }
        if (startup.monitor_validation || startup.display_validation || startup.runtime_validation) {
            if (!policy.value("console_validation_enabled", false)) throw std::runtime_error("Native validation is not enabled");
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
                    sceKernelAvailableFlexibleMemorySize(&flexible) < 0 || available < (1ull << 30) || flexible < (64u << 20))
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
            if (display && display->failed()) throw std::runtime_error("Native display completion failed; backing retained");
            qwen_app::HardwareInfo hardware;
            hardware.cpu_name = screen.cpu_name; hardware.logical_cpu_threads = screen.cpu_threads;
            // The native SDK declares CLOCKS_PER_SEC=128; the provider's clock
            // units have not passed qualification. Keep CPU percentage absent.
            hardware.sample_process_cpu = false;
            // Display-only admission must not enumerate or initialize Vulkan.
            auto device = startup.monitor_validation ? ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU) : nullptr;
            if (startup.monitor_validation && !device) device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
            if (device) {
                if (const auto * name = ggml_backend_dev_description(device)) hardware.gpu_name = name;
                std::size_t available = 0, total = 0; ggml_backend_dev_memory(device, &available, &total);
                if (total) { hardware.gpu_total_bytes = total; hardware.gpu_free_bytes = available; }
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
        const auto receipt = qwen_app::read_model_receipt(startup.model_receipt);
        const auto expected_mapped_files=qwen_app::validate_model_receipt(receipt);
        // A receipt records host conversion provenance, not a fresh console hash
        // check. Deployment must independently verify every transferred file.
        qwen_app::ModelFootprint footprint; std::unordered_set<std::string> tensor_names;
        bool first = true;
        unsigned file_index=0;
        for (const auto & file : receipt.at("files")) {
            ++file_index;
            screen.state="verifying original model bytes";
            qwen_native_stage("model_file_integrity_started_before_backend_initialization");
            qwen_app::verify_model_file(model_file(startup.model_receipt,file.at("path").get<std::string>()),
                file.at("bytes").get<std::uint64_t>(),file.at("sha256").get<std::string>(),[&](std::uint64_t verified){
                    screen.message="File "+std::to_string(file_index)+"/"+std::to_string(receipt.at("files").size())+
                        ": "+std::to_string(verified>>20)+" MiB verified";
                    if(display)display->publish(screen);
                    qwen_native_stage("model_file_integrity_progress");
                });
            qwen_native_stage("model_file_integrity_completed");
            inspect_container(model_file(startup.model_receipt, file.at("path").get<std::string>()), first,
                footprint,tensor_names,file.at("bytes").get<std::uint64_t>()); first = false;
        }
        qwen_app::validate_original_footprint(footprint,expected_mapped_files);
        const auto first_path = model_file(startup.model_receipt, receipt.at("files").at(0).at("path").get<std::string>());
        write_fresh_report(startup.admission_report+".integrity",{{"schema","ps5-qwen-model-integrity-v1"},
            {"pid",getpid()},{"files_verified",file_index},{"all_SHA256_matched",true},
            {"mapped_file_bytes",footprint.mapped_files},{"model_loaded",false},{"Vulkan_initialized",false}});
        screen.message.clear();

        screen.state = "admitting original BF16 memory";
        if (display) display->publish(screen);
        native_resources_started = true;
        qwen_app::admit_cpu_runtime(qwen_native_stage);
        qwen_app::inspect_vulkan_globals();
        if(!qwen_native_gpu_frontend_linked())throw std::runtime_error("Native driver frontend is not linked");
        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());
        qwen_native_driver_begin();
        llama_backend_init();
        auto device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
        if (!device) device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
        std::size_t driver_free = 0, driver_total = 0;
        if(!device) throw std::runtime_error("A qualified native Vulkan device is required");
        ggml_backend_dev_memory(device, &driver_free, &driver_total);
        std::int64_t physical=0;std::size_t direct=0;const auto pool=sceKernelGetDirectMemorySize();
        if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&direct)<0)
            throw std::runtime_error("A fresh Direct-memory observation is required before model loading");
        qwen_app::MemoryBudget memory_budget;
        memory_budget.admit(footprint,{driver_free,direct,observed_os_free(),
            ggml_backend_buft_get_max_size(ggml_backend_dev_buffer_type(device))});
        write_fresh_report(startup.admission_report+".memory",{{"schema","ps5-qwen-memory-admission-v1"},
            {"pid",getpid()},{"model_loaded",false},{"device_weights_bytes",footprint.device_weights},
            {"mapped_experts_bytes",footprint.mapped_experts},{"required_lazy_PLE_bytes",footprint.lazy_ple},
            {"mapped_embedding_bytes",footprint.mapped_embeddings},{"mapped_file_bytes",footprint.mapped_files},
            {"planned_resident_headroom_bytes",memory_budget.device_requirement(footprint)},
            {"resident_set_qualified",false}});
        qwen_native_stage("model_memory_preflight_passed_before_model_load");
        screen.state="loading original BF16 model";if(display)display->publish(screen);
        auto model_params=qwen_app::streaming_model_params(ggml_backend_cpu_buffer_type());
        LoadProgress load_progress;model_params.progress_callback=observe_model_load;model_params.progress_callback_user_data=&load_progress;
        qwen_native_stage("model_load_started_after_memory_admission");
        model = llama_model_load_from_file(first_path.c_str(), model_params);
        if (!model) throw std::runtime_error("Model load failed; restart through the ordinary OS path");
        qwen_native_stage("model_load_completed");
        qwen_native_driver_checkpoint();
        ggml_backend_dev_memory(device, &driver_free, &driver_total);
        // Initial, unqualified limits: do not infer extra RAM from the GPU pool.
        const auto remaining=qwen_app::checked_memory_sum(memory_budget.context,
            qwen_app::checked_memory_sum(memory_budget.workspace,memory_budget.staging+memory_budget.direct_reserve));
        if(driver_free<remaining) throw std::runtime_error("Insufficient headroom after model load");
        const auto cache_bytes = qwen_app::uma_cache_budget(memory_budget.expert_cache, driver_free-remaining,
            observed_os_free(), memory_budget.os_reserve);
        if (cache_bytes < (128u << 20)) throw std::runtime_error("Insufficient observed UMA cache headroom");
        screen.state = "admitting inference context";
        if (display) display->publish(screen);
        context = llama_init_from_model(model, qwen_app::streaming_context_params(4096, cache_bytes));
        if (!context) throw std::runtime_error("Context admission failed; restart through the ordinary OS path");
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
            if (total) { hardware.gpu_total_bytes = total; hardware.gpu_free_bytes = free; }
        }
        qwen_native_driver_complete();
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
                {"message", error.what()}, {"model_loaded", model!=nullptr}}); } catch (...) {}
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
