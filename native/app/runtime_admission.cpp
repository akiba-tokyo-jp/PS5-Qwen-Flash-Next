// SPDX-License-Identifier: MIT
#include "runtime_admission.h"
#include "ggml.h"
#include <stdexcept>
namespace qwen_app {
RuntimeAdmission admit_cpu_runtime(void (*stage)(const char *)) {
    if (!stage) throw std::invalid_argument("Runtime admission requires a durable phase observer");
    RuntimeAdmission result;
    stage("CPU_runtime_before_time_init GPU_not_started=1");
    ggml_time_init();
    stage("CPU_runtime_time_init_completed GPU_not_started=1");
    ggml_init_params params{};
    params.mem_size = 32768;
    params.no_alloc = true;
    stage("CPU_runtime_before_context_init GPU_not_started=1");
    auto * context = ggml_init(params);
    if (!context) throw std::runtime_error("CPU runtime metadata allocation failed");
    result.metadata_bytes = ggml_get_mem_size(context);
    if (result.metadata_bytes < params.mem_size)
        throw std::runtime_error("CPU runtime metadata capacity is invalid");
    stage("CPU_runtime_context_init_completed GPU_not_started=1");
    ggml_free(context);
    stage("CPU_runtime_context_release_completed GPU_not_started=1");
    // This validates the linked native exception personality before depending
    // on C++ error handling in the Vulkan backend or model loader.
    try { throw std::runtime_error("CPU runtime exception probe"); }
    catch (const std::runtime_error &) { result.exception_roundtrip = true; }
    stage("CPU_runtime_exception_roundtrip_completed GPU_not_started=1");
    return result;
}
}
