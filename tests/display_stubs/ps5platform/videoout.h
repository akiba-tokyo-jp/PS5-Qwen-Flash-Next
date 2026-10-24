// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#define PS5_VIDEO_OUT_USER_SYSTEM 255
#define PS5_VIDEO_OUT_PIXEL_FORMAT_B8G8R8A8_SDR UINT64_C(0x8000000000000000)
#define PS5_VIDEO_OUT_TILING_64KB_R_X 0
#define PS5_VIDEO_OUT_ATTRIBUTE_BYTES 80
#define PS5_VIDEO_OUT_FLIP_STATUS_WORDS 16
#define PS5_VIDEO_OUT_FLIP_STATUS_SHOWN_ARGUMENT 3
#define PS5_VIDEO_OUT_FLIP_VSYNC 1
struct ps5_video_out_buffer { void *data; void *metadata; void *reserved[2]; };
extern "C" {
int sceVideoOutOpen(std::int32_t, std::int32_t, std::int32_t, const void *);
int sceVideoOutSetFlipRate(std::int32_t, std::int32_t);
void sceVideoOutSetBufferAttribute2(void *, std::uint64_t, std::uint32_t, std::uint32_t, std::uint32_t, std::uint64_t, std::uint32_t, std::uint64_t);
int sceVideoOutRegisterBuffers2(std::int32_t, std::int32_t, std::int32_t, ps5_video_out_buffer *, std::int32_t, void *, std::int32_t, void *);
int sceVideoOutSubmitFlip(std::int32_t, std::int32_t, std::uint32_t, std::int64_t);
int sceVideoOutGetFlipStatus(std::int32_t, std::uint64_t *);
int sceVideoOutIsFlipPending(std::int32_t);
}
