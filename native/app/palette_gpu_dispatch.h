// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
namespace qwen_app {
// One independent diagnostic device. The native frontend owns its lifetime;
// it must remain alive until the frontend's final positive idle/epoch boundary.
class PaletteGpuDispatch {
    struct State;
    State *state_;
public:
    PaletteGpuDispatch(const std::uint32_t *copy_spirv,std::size_t copy_bytes,
        const std::uint32_t *palette_spirv,std::size_t palette_bytes);
    PaletteGpuDispatch(const PaletteGpuDispatch &)=delete;
    PaletteGpuDispatch &operator=(const PaletteGpuDispatch &)=delete;
    ~PaletteGpuDispatch()=default;
    static constexpr std::size_t buffer_bytes=4u<<20;
    unsigned char *source();
    unsigned char *target();
    // Includes host visibility, recording, submit and positive fence completion.
    // A failed result never resets or releases possibly in-flight resources.
    std::uint64_t dispatch(bool palette,std::uint32_t values,std::uint32_t encoded_bytes);
};
}
