// SPDX-License-Identifier: MIT
// CPU VideoOut presentation uses the pinned public platform declarations.
#include "native_display.h"
#include "tiled_frame.h"
#include "monitor_clock.h"
#include <ps5platform/kernel.h>
#include <ps5platform/videoout.h>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <thread>
extern "C" int sceSystemServiceHideSplashScreen();
extern "C" bool qwen_native_faulted();
extern "C" void qwen_native_mark_fault();

namespace qwen_app {
struct NativeDisplay::Impl {
    static constexpr std::size_t frame_bytes = 16u << 20, memory_bytes = 2 * frame_bytes, alignment = 2u << 20;
    std::mutex mutex;
    std::condition_variable changed;
    MonitorSnapshot snapshot;
    std::atomic<bool> stop{false}, fault{false};
    bool ready = false;
    std::string error;
    std::thread worker;
    int video = -1, front = 0;
    std::int64_t physical = 0, marker = 0;
    void * mapped = nullptr;

    static void flush(void * data, std::size_t bytes) {
        for (auto * at = static_cast<unsigned char *>(data), *end = at + bytes; at < end; at += 64)
            __asm__ volatile("clflush (%0)" : : "r"(at) : "memory");
        __asm__ volatile("mfence" ::: "memory");
    }
    bool wait_shown(std::int64_t expected) {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
        while (std::chrono::steady_clock::now() < deadline) {
            std::uint64_t status[PS5_VIDEO_OUT_FLIP_STATUS_WORDS] = {};
            if (sceVideoOutGetFlipStatus(video, status) < 0) return false;
            const int pending = sceVideoOutIsFlipPending(video);
            if (pending < 0) return false;
            if (status[PS5_VIDEO_OUT_FLIP_STATUS_SHOWN_ARGUMENT] == std::uint64_t(expected) && pending == 0) return true;
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        return false;
    }
    void initialize() {
        video = sceVideoOutOpen(PS5_VIDEO_OUT_USER_SYSTEM, 0, 0, nullptr);
        if (video < 0) throw std::runtime_error("VideoOut open failed");
        const auto pool = sceKernelGetDirectMemorySize();
        if (pool <= 0 || sceKernelAllocateDirectMemory(0, pool, memory_bytes, alignment, 3, &physical) < 0)
            throw std::runtime_error("Display direct-memory allocation failed");
        if (sceKernelMapDirectMemory(&mapped, memory_bytes, 0x33, 0, physical, alignment) < 0 || !mapped)
            throw std::runtime_error("Display direct-memory mapping failed");
        std::memset(mapped, 0, memory_bytes); flush(mapped, memory_bytes);
        ps5_video_out_buffer buffers[2] = {{mapped, nullptr, {}}, {static_cast<unsigned char *>(mapped) + frame_bytes, nullptr, {}}};
        alignas(8) unsigned char attribute[PS5_VIDEO_OUT_ATTRIBUTE_BYTES] = {};
        sceVideoOutSetBufferAttribute2(attribute, PS5_VIDEO_OUT_PIXEL_FORMAT_B8G8R8A8_SDR,
            PS5_VIDEO_OUT_TILING_64KB_R_X, MonitorRaster::width, MonitorRaster::height, 0, 0, 0);
        if (sceVideoOutSetFlipRate(video, 0) < 0 || sceVideoOutRegisterBuffers2(video, 0, 0, buffers, 2, attribute, 0, nullptr) < 0)
            throw std::runtime_error("Display buffer registration failed");
        if (sceVideoOutSubmitFlip(video, 0, PS5_VIDEO_OUT_FLIP_VSYNC, ++marker) < 0 || !wait_shown(marker))
            throw std::runtime_error("Initial display completion is uncertain; backing retained");
        (void) sceSystemServiceHideSplashScreen();
    }
    void run() {
        try {
            initialize();
            MonitorRaster raster;
            while (!stop) {
                MonitorSnapshot current;
                { std::lock_guard<std::mutex> lock(mutex); current = snapshot; }
                if (qwen_native_faulted()) {
                    current.quarantined = true; current.state = "native operation failed";
                    current.message = "CLOSE THE TITLE NORMALLY / RESOURCE BACKING IS RETAINED";
                }
                current.epoch_ms = monitor_clock().now();
                current.clock_calibrated = monitor_clock().calibrated();
                raster.draw(current);
                const int target = 1 - front;
                auto * output = static_cast<unsigned char *>(mapped) + target * frame_bytes;
                for (unsigned y = 0; y < MonitorRaster::height; ++y)
                    for (unsigned x = 0; x < MonitorRaster::width; ++x)
                        *reinterpret_cast<std::uint32_t *>(output + video_tiled_offset(x, y)) = raster.pixels()[y * MonitorRaster::width + x];
                constexpr std::size_t tile_bytes = ((MonitorRaster::width + 127) / 128) * ((MonitorRaster::height + 127) / 128) * 65536;
                flush(output, tile_bytes);
                if (sceVideoOutSubmitFlip(video, target, PS5_VIDEO_OUT_FLIP_VSYNC, ++marker) < 0 || !wait_shown(marker))
                    throw std::runtime_error("Display completion is uncertain; backing retained");
                front = target;
                std::unique_lock<std::mutex> lock(mutex);
                if (!ready) { ready = true; changed.notify_all(); }
                changed.wait_for(lock, std::chrono::seconds(1), [&] { return stop.load(); });
            }
        } catch (const std::exception & failure) {
            qwen_native_mark_fault();
            { std::lock_guard<std::mutex> lock(mutex); error = failure.what(); fault = true; ready = true; }
            changed.notify_all();
        }
        // No unregister, unmap, release or retry. OS title close owns backing.
    }
};
NativeDisplay::NativeDisplay() : impl_(new Impl) {}
NativeDisplay::~NativeDisplay() {
    impl_->stop = true; impl_->changed.notify_all();
    if (impl_->worker.joinable()) impl_->worker.join();
}
void NativeDisplay::start(MonitorSnapshot initial) {
    if (impl_->worker.joinable()) throw std::logic_error("Display already started");
    impl_->snapshot = std::move(initial);
    impl_->worker = std::thread([this] { impl_->run(); });
    std::unique_lock<std::mutex> lock(impl_->mutex);
    impl_->changed.wait(lock, [&] { return impl_->ready; });
    if (impl_->fault) throw std::runtime_error(impl_->error);
}
void NativeDisplay::publish(const MonitorSnapshot & snapshot) { std::lock_guard<std::mutex> lock(impl_->mutex); impl_->snapshot = snapshot; }
bool NativeDisplay::failed() const { return impl_->fault; }
} // namespace qwen_app
