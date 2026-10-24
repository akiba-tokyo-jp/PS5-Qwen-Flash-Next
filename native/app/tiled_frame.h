/* SPDX-License-Identifier: GPL-3.0-or-later
 * Adapted from PS5-Vulkan-Inference src/demo_renderer.cpp.
 * Copyright (C) 2026 BlackBearReloaded
 * Copyright (C) 2026 Mihawk-99
 */
#pragma once
#include <cstddef>
#include <cstdint>

namespace qwen_app {
inline std::size_t video_tiled_offset(unsigned x, unsigned y, unsigned width = 1920) {
    const std::uint32_t offset = ((y << 4) & 0x70U) ^ ((y << 5) & 0xf00U) ^ ((y << 9) & 0x1000U) ^
        ((y << 8) & 0x4000U) ^ ((x << 2) & 0xcU) ^ ((x << 5) & 0x380U) ^ ((x << 4) & 0x400U) ^
        ((x << 6) & 0x800U) ^ ((x << 9) & 0xa000U);
    return (std::size_t((y >> 7) * ((width + 127) >> 7) + (x >> 7)) << 16) + offset;
}
} // namespace qwen_app
