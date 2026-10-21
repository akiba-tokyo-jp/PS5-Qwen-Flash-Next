// SPDX-License-Identifier: MIT
// Execute the real display owner against stubbed VideoOut/Direct APIs.
#include "native_display.h"
#include <ps5platform/videoout.h>
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <thread>
#ifdef _WIN32
#include <malloc.h>
#endif

static std::atomic<int> flips{0};
static std::atomic<std::int64_t> shown{0};
static std::atomic<bool> fail{false};
static std::atomic<bool> faulted{false};
static void * backing;
static void check(bool value) { if (!value) throw std::runtime_error("Native display API contract failed"); }
extern "C" {
bool qwen_native_faulted() { return faulted; }
void qwen_native_mark_fault() { faulted = true; }
int sceSystemServiceHideSplashScreen() { return 0; }
std::int64_t sceKernelGetDirectMemorySize() { return 1LL << 30; }
int sceKernelAllocateDirectMemory(std::int64_t start, std::int64_t, std::size_t bytes, std::size_t alignment, int type, std::int64_t * physical) {
    check(start == 0 && bytes == (32u << 20) && alignment == (2u << 20) && type == 3); *physical = 0; return 0;
}
int sceKernelMapDirectMemory(void ** result, std::size_t bytes, int protection, int flags, std::int64_t, std::size_t alignment) {
    check(protection == 0x33 && flags == 0);
#ifdef _WIN32
    backing = _aligned_malloc(bytes, alignment);
#else
    backing = std::aligned_alloc(alignment, bytes);
#endif
    *result = backing; return backing ? 0 : -1;
}
int sceVideoOutOpen(std::int32_t user, std::int32_t bus, std::int32_t index, const void * option) {
    check(user == 255 && bus == 0 && index == 0 && !option); return 7;
}
int sceVideoOutSetFlipRate(std::int32_t handle, std::int32_t rate) { check(handle == 7 && rate == 0); return 0; }
void sceVideoOutSetBufferAttribute2(void *, std::uint64_t format, std::uint32_t tiling, std::uint32_t width,
    std::uint32_t height, std::uint64_t, std::uint32_t, std::uint64_t) { check(format == PS5_VIDEO_OUT_PIXEL_FORMAT_B8G8R8A8_SDR && !tiling && width == 1920 && height == 1080); }
int sceVideoOutRegisterBuffers2(std::int32_t handle, std::int32_t, std::int32_t, ps5_video_out_buffer * buffers,
    std::int32_t count, void *, std::int32_t, void *) { check(handle == 7 && count == 2 && buffers[0].data == backing && buffers[1].data == static_cast<unsigned char *>(backing) + (16u << 20)); return 0; }
int sceVideoOutSubmitFlip(std::int32_t handle, std::int32_t buffer, std::uint32_t mode, std::int64_t marker) {
    check(handle == 7 && mode == 1 && buffer == int((marker - 1) % 2)); ++flips;
    if (fail && marker > 1) return -1;
    shown = marker; return 0;
}
int sceVideoOutGetFlipStatus(std::int32_t, std::uint64_t * status) { status[3] = shown.load(); return 0; }
int sceVideoOutIsFlipPending(std::int32_t) { return 0; }
}
int main() {
    try {
        {
            qwen_app::NativeDisplay display; display.start({});
            check(flips >= 2 && !display.failed());
            qwen_app::MonitorSnapshot data; data.state = "host fixture"; display.publish(data);
        }
        // Only the host fixture frees its synthetic backing after its worker joins.
#ifdef _WIN32
        _aligned_free(backing);
#else
        std::free(backing);
#endif
        flips = 0; shown = 0; fail = true;
        {
            qwen_app::NativeDisplay display;
            bool rejected = false; try { display.start({}); } catch (const std::exception &) { rejected = true; }
            check(rejected && display.failed() && faulted && flips == 2);
            std::this_thread::sleep_for(std::chrono::milliseconds(20)); check(flips == 2);
        }
#ifdef _WIN32
        _aligned_free(backing);
#else
        std::free(backing);
#endif
        std::cout << "Native display initialization, first-frame completion and no-retry fault retention passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
