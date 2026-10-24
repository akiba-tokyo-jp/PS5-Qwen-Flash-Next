// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
namespace qwen_app {
struct RuntimeAdmission {
    bool exception_roundtrip = false;
    std::size_t metadata_bytes = 0;
};
// Exercise CPU allocator, synchronization and unwinding before any backend
// registry access, Vulkan initialization or model allocation.
RuntimeAdmission admit_cpu_runtime(void (*stage)(const char *));
}
