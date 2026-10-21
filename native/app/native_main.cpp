// SPDX-License-Identifier: MIT
// Native startup, inference ownership and read-only VideoOut monitoring.
#include "http_app.h"
#include "llama_engine.h"
#include "expert_policy.h"
#include "native_display.h"
#include "startup.h"
#include "gpu_admission.h"
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
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <sys/sysctl.h>

using Json = nlohmann::json;
// A required link symbol prevents accidental use of an unpatched eager loader.
extern "C" bool llama_app_mmap_prefetch_disabled();
extern "C" void qwen_native_set_fault_report(const char *);

static void write_fresh_report(const std::string & path, const Json & value) {
    const auto bytes = value.dump(2) + "\n";
    const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) throw std::runtime_error("Fresh native report could not be created");
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

static void inspect_container(const std::string & path, bool first) {
    std::unique_ptr<gguf_context, decltype(&gguf_free)> metadata(
        gguf_init_from_file(path.c_str(), {true, nullptr}), gguf_free);
    if (!metadata) throw std::runtime_error("GGUF metadata could not be read");
    for (std::int64_t i = 0; i < gguf_get_n_tensors(metadata.get()); ++i) {
        const auto type = gguf_get_tensor_type(metadata.get(), i);
        if (type != GGML_TYPE_BF16 && type != GGML_TYPE_F32)
            throw std::runtime_error("Only original BF16 or lossless F32 widening is accepted");
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

int main(int argc, char ** argv) {
    llama_model * model = nullptr;
    llama_context * context = nullptr;
    std::unique_ptr<qwen_app::LlamaEngine> engine;
    std::unique_ptr<qwen_app::NativeDisplay> display;
    qwen_app::MonitorSnapshot screen;
    bool native_resources_started = false;
    std::string validation_report;
    try {
        const auto startup = qwen_app::read_startup(argc, argv);
        if (startup.monitor_validation || startup.display_validation) validation_report = startup.admission_report;
        std::ifstream policy_file(startup.development_policy);
        const auto policy = Json::parse(policy_file);
        if (!policy.at("console_operations_enabled").get<bool>())
            throw std::runtime_error("Console execution is disabled for this application integration phase");
        const auto mode = startup.display_validation ? "display-validation" : startup.monitor_validation ? "monitor-validation" : "inference";
        if (!policy.contains("allowed_modes") || !policy.at("allowed_modes").is_array() ||
            std::find(policy.at("allowed_modes").begin(), policy.at("allowed_modes").end(), Json(mode)) == policy.at("allowed_modes").end())
            throw std::runtime_error("This application mode has not passed the preceding qualification stage");
        qwen_native_set_fault_report((startup.admission_report + ".fatal").c_str());
        if (setenv("MESA_SHADER_CACHE_DISABLE", "true", 1) || setenv("LLAMA_APP_NO_MMAP_PREFETCH", "1", 1) ||
            setenv("LLAMA_APP_EXPERT_POLICY", "maya-aged-lfu", 1) ||
            setenv("GGML_VK_DISABLE_ASYNC", "1", 1) || setenv("GGML_VK_SERIALIZE_SUBMISSIONS", "1", 1) ||
            setenv("GGML_VK_MAX_NODES_PER_SUBMIT", "1", 1))
            throw std::runtime_error("Required cache policy could not be set");
        if (!llama_app_mmap_prefetch_disabled()) throw std::runtime_error("The streaming loader patch is required");
        if (!llama_app_expert_policy_enabled()) throw std::runtime_error("The adaptive expert cache patch is required");

        screen.state = "verifying model";
        screen.cpu_threads = std::thread::hardware_concurrency();
        char cpu_name[256] = {};
        std::size_t cpu_name_size = sizeof(cpu_name);
        if (!sysctlbyname("hw.model", cpu_name, &cpu_name_size, nullptr, 0) && cpu_name_size &&
            std::memchr(cpu_name, 0, sizeof(cpu_name))) screen.cpu_name = cpu_name;
        if (startup.native_display) {
            display = std::make_unique<qwen_app::NativeDisplay>();
            native_resources_started = true;
            display->start(screen);
        }
        if (startup.monitor_validation || startup.display_validation) {
            if (!policy.value("console_validation_enabled", false)) throw std::runtime_error("Native validation is not enabled");
            if (startup.display_validation) {
                if (!display) throw std::runtime_error("Display validation requires native presentation");
                struct ps5_heap_stats heap{}; ps5_heap_stats(&heap);
                write_fresh_report(startup.admission_report, {{"schema", "ps5-qwen-display-admission-v1"},
                    {"pid", getpid()}, {"first_frame_completed", true}, {"model_loaded", false},
                    {"Vulkan_initialized", false}, {"compute_dispatches", 0}, {"display_buffer_bytes", 32u << 20},
                    {"heap_mapped_bytes", heap.mapped_bytes}, {"heap_peak_bytes", heap.peak_bytes},
                    {"cpu_name", screen.cpu_name}, {"cpu_threads", screen.cpu_threads}});
            } else {
                screen.state = "checking original BF16 GPU operation";
                if (display) display->publish(screen);
                native_resources_started = true;
                std::int64_t physical = 0; std::size_t available = 0, flexible = 0;
                const auto pool = sceKernelGetDirectMemorySize();
                if (pool <= 0 || sceKernelAvailableDirectMemorySize(0, pool, 65536, &physical, &available) < 0 ||
                    sceKernelAvailableFlexibleMemorySize(&flexible) < 0 || available < (1ull << 30) || flexible < (64u << 20))
                    throw std::runtime_error("Observed memory headroom is insufficient for bounded GPU admission");
                write_fresh_report(startup.admission_report + ".started", {{"stage", "before_gpu_admission"},
                    {"model_loaded", false}, {"pid", getpid()}, {"direct_largest_available_bytes", available},
                    {"flexible_available_bytes", flexible}});
                llama_backend_init();
                const auto admission = qwen_app::admit_bf16_gpu();
                const Json record = {{"schema", "ps5-qwen-bf16-admission-v1"}, {"model_loaded", false},
                    {"fixture", "BF16 32x16 weights times F32 32-vector; F32 output"},
                    {"absolute_tolerance", 1e-5}, {"relative_tolerance", 1e-5}, {"passed", admission.passed},
                    {"backend", admission.backend}, {"expected", admission.expected}, {"actual", admission.actual},
                    {"max_absolute_error", admission.max_absolute_error}, {"elapsed_ms", admission.elapsed_ms}};
                write_fresh_report(startup.admission_report, record);
                if (!admission.passed) throw std::runtime_error("Original-BF16 GPU admission failed its fixed numerical gate");
            }
            if (display && display->failed()) throw std::runtime_error("Native display completion failed; backing retained");
            qwen_app::HardwareInfo hardware;
            hardware.cpu_name = screen.cpu_name; hardware.logical_cpu_threads = screen.cpu_threads;
            hardware.sample_process_cpu = true;
            // Display-only admission must not enumerate or initialize Vulkan.
            auto device = startup.display_validation ? nullptr : ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
            if (!startup.display_validation && !device) device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
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
            qwen_app::serve_http(no_inference, startup.web_assets, "{{ '' }}", startup.port, false, hardware,
                display ? std::function<void(const qwen_app::MonitorSnapshot &)>([&](const auto & snapshot) { display->publish(snapshot); })
                        : std::function<void(const qwen_app::MonitorSnapshot &)>{}, true);
            for (;;) std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        std::ifstream receipt_file(startup.model_receipt);
        const auto receipt = Json::parse(receipt_file);
        if (receipt.at("schema") != "ps5-qwen-bf16-conversion-v1" ||
            receipt.at("original_revision") != "de4b8e4d43b917e7706784d8bb445c9af86a3540" ||
            receipt.at("outtype") != "bf16" || !receipt.at("original_shards_verified").get<bool>() ||
            !receipt.at("files").is_array() || receipt.at("files").empty())
            throw std::runtime_error("Verified original BF16 conversion receipt required");
        // A receipt records host conversion provenance, not a fresh console hash
        // check. Deployment must independently verify every transferred file.
        bool first = true;
        for (const auto & file : receipt.at("files")) {
            inspect_container(model_file(startup.model_receipt, file.at("path").get<std::string>()), first); first = false;
        }
        const auto first_path = model_file(startup.model_receipt, receipt.at("files").at(0).at("path").get<std::string>());

        screen.state = "loading original BF16 model";
        if (display) display->publish(screen);
        native_resources_started = true;
        llama_backend_init();
        model = llama_model_load_from_file(first_path.c_str(), qwen_app::streaming_model_params(ggml_backend_cpu_buffer_type()));
        if (!model) throw std::runtime_error("Model load failed; restart through the ordinary OS path");
        auto device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
        if (!device) device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
        std::size_t driver_free = 0, driver_total = 0;
        if (device) ggml_backend_dev_memory(device, &driver_free, &driver_total);
        std::uint32_t free_pages = 0, page_size = 0;
        std::size_t free_size = sizeof(free_pages), page_size_size = sizeof(page_size);
        if (sysctlbyname("vm.stats.vm.v_free_count", &free_pages, &free_size, nullptr, 0) ||
            sysctlbyname("vm.stats.vm.v_page_size", &page_size, &page_size_size, nullptr, 0) ||
            free_size != sizeof(free_pages) || page_size_size != sizeof(page_size))
            throw std::runtime_error("OS free-memory observation is required for UMA cache admission");
        // Initial, unqualified limits: do not infer extra RAM from the GPU pool.
        const auto cache_bytes = qwen_app::uma_cache_budget(512u << 20, driver_free,
            std::uint64_t(free_pages) * page_size, 256u << 20);
        if (cache_bytes < (128u << 20)) throw std::runtime_error("Insufficient observed UMA cache headroom");
        screen.state = "admitting inference context";
        if (display) display->publish(screen);
        context = llama_init_from_model(model, qwen_app::streaming_context_params(4096, cache_bytes));
        if (!context) throw std::runtime_error("Context admission failed; restart through the ordinary OS path");
        engine = std::make_unique<qwen_app::LlamaEngine>(model, context);
        const auto * chat_template = llama_model_chat_template(model, nullptr);
        if (!chat_template || !*chat_template) throw std::runtime_error("The original chat template is required");
        qwen_app::HardwareInfo hardware;
        hardware.cpu_name = screen.cpu_name;
        hardware.logical_cpu_threads = screen.cpu_threads;
        hardware.sample_process_cpu = true;
        if (device) {
            const char * description = ggml_backend_dev_description(device);
            if (description) hardware.gpu_name = description;
            std::size_t free = 0, total = 0;
            ggml_backend_dev_memory(device, &free, &total);
            if (total) { hardware.gpu_total_bytes = total; hardware.gpu_free_bytes = free; }
        }
        const int result = qwen_app::serve_http(*engine, startup.web_assets, chat_template, startup.port, false, hardware,
            display ? std::function<void(const qwen_app::MonitorSnapshot &)>([&](const auto & snapshot) { display->publish(snapshot); })
                    : std::function<void(const qwen_app::MonitorSnapshot &)>{});
        if (engine->failed()) throw std::runtime_error("Model resources retained after an uncertain backend result");
        engine.reset(); llama_free(context); context = nullptr; llama_model_free(model); model = nullptr;
        if (display) {
            screen.state = "service stopped"; screen.message = "CLOSE THE TITLE THROUGH THE ORDINARY OS PATH";
            display->publish(screen);
            for (;;) std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        return result;
    } catch (const std::exception & error) {
        // No manual release or automatic retry after a failed native admission.
        // The owning process must remain available for ordinary OS shutdown.
        std::cerr << error.what() << '\n';
        if (!validation_report.empty()) {
            try { write_fresh_report(validation_report + ".failure", {{"stage", "native_exception"},
                {"message", error.what()}, {"model_loaded", false}}); } catch (...) {}
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
            engine.release();
            for (;;) (void) usleep(1000000);
        }
        return 1;
    }
}
