// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
namespace qwen_app {
inline constexpr std::size_t owned_probe_bytes=3276800;
struct OwnedCopyCase { bool streaming=false; double milliseconds=0; bool exact=false; };
struct OwnedMappedProbe {
    bool eligible=false,all_IO_returned=false,GPU_numerics=false,retired=false;
    int read_result=0,read_errno=0;unsigned graphs=0;
    std::uint64_t memory_flags=0;double maximum_absolute_error=0;
    std::array<OwnedCopyCase,6> copies{};
};
OwnedMappedProbe admit_owned_mapped_probe(const std::string &,const std::string &,
    void (*checkpoint)(),void (*stage)(const char *));
}
// The backend validates an exact fixture tensor and keeps its actual vk_buffer
// alive across this synchronous callback. No generic pointer is imported.
extern "C" int ggml_app_vk_probe_owned_matvec(ggml_tensor *,
    int (*)(void *,std::size_t,std::uint64_t,void *),void *);
