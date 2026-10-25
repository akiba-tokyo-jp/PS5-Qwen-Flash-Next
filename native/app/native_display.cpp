// SPDX-License-Identifier: MIT
// CPU VideoOut presentation uses the pinned public platform declarations.
#include "native_display.h"
#include "tiled_frame.h"
#include "monitor_clock.h"
#include "direct_bmp_native.h"
#include "system_memory.h"
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
#include <ps5platform/videoout.h>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <cstdlib>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <fcntl.h>
#include <unistd.h>
#ifdef _WIN32
#include <io.h>
#endif
extern "C" int sceSystemServiceHideSplashScreen();
extern "C" bool qwen_native_faulted();
extern "C" void qwen_native_mark_fault();
extern "C" void qwen_native_stage(const char *);

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
    std::string capture_path, capture_request;
    std::uint64_t capture_minimum = 0;
    bool capture_ready = false;
    bool direct_frame_evidence = false;
    MonitorSnapshot captured;
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
    static void frame_guard() {
        if(qualified_system_headroom(observe_native_system_memory()) < (264u << 20))
            throw std::runtime_error("Frame persistence must preserve the original Flexible reserve");
    }
    static void save_frame_direct(const std::string & path, const MonitorRaster & raster) {
        static_assert(MonitorRaster::width == frame_width && MonitorRaster::height == frame_height,
                      "Direct frame evidence must preserve the original raster geometry");
        frame_guard();
        void *window = nullptr;
        if(posix_memalign(&window,frame_write_alignment,frame_write_window) || !window || !ps5_heap_owns(window))
            throw std::runtime_error("Frame persistence requires one tracked Direct CPU window");
        struct Source {
            const MonitorRaster &raster;
            void copy_row(unsigned y,std::size_t at,unsigned char *target,std::size_t bytes) {
                if(y>=frame_height || at>frame_row_bytes || bytes>frame_row_bytes-at)
                    throw std::runtime_error("Frame persistence row bounds refused");
                const auto *row=reinterpret_cast<const unsigned char*>(raster.pixels().data()+y*frame_width);
                std::memcpy(target,row+at,bytes);
            }
        } source{raster};
        // Failure retains the descriptor/window for ordinary OS title close.
        // Only an exact returned write, durable commit and close permit release.
        NativeFrameSink sink(path,true,qwen_native_stage,frame_guard,FrameMetadataABI::native_descriptor);
        stream_direct_bmp(source,sink,window);
        free(window);
    }
    void save_frame(const std::string & path, const MonitorRaster & raster) {
        if(direct_frame_evidence) { save_frame_direct(path,raster); return; }
        constexpr std::uint32_t image_bytes = MonitorRaster::width * MonitorRaster::height * 4;
        unsigned char header[54] = {'B', 'M'};
        auto u16 = [&](unsigned offset, std::uint16_t value) {
            header[offset] = value & 255; header[offset + 1] = value >> 8;
        };
        auto u32 = [&](unsigned offset, std::uint32_t value) {
            for (unsigned i = 0; i < 4; ++i) header[offset + i] = (value >> (8 * i)) & 255;
        };
        u32(2, sizeof(header) + image_bytes); u32(10, sizeof(header)); u32(14, 40);
        u32(18, MonitorRaster::width); u32(22, MonitorRaster::height); u16(26, 1); u16(28, 32); u32(34, image_bytes);
        int flags = O_WRONLY | O_CREAT | O_EXCL;
#ifdef _WIN32
        flags |= O_BINARY;
#endif
        const int fd = open(path.c_str(), flags, 0644);
        if (fd < 0) throw std::runtime_error("Fresh displayed-frame evidence could not be created");
        bool saved = write(fd, header, sizeof(header)) == static_cast<ssize_t>(sizeof(header));
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(8);
        for (unsigned y = MonitorRaster::height; saved && y; --y) {
            if (std::chrono::steady_clock::now() > deadline) { saved = false; break; }
            const auto * row = raster.pixels().data() + (y - 1) * MonitorRaster::width;
            saved = write(fd, row, MonitorRaster::width * 4) == static_cast<ssize_t>(MonitorRaster::width * 4);
        }
#ifdef _WIN32
        saved = saved && _commit(fd) == 0;
#else
        saved = saved && fsync(fd) == 0;
#endif
        const bool closed = close(fd) == 0;
        if (!saved || !closed) throw std::runtime_error("Displayed-frame persistence did not complete");
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
                std::string capture;
                {
                    std::lock_guard<std::mutex> lock(mutex);
                    if (!capture_path.empty() && current.request_id == capture_request &&
                        current.generated_tokens >= capture_minimum) capture = capture_path;
                }
                if (!capture.empty()) {
                    save_frame(capture, raster);
                    std::lock_guard<std::mutex> lock(mutex);
                    captured = current; capture_path.clear(); capture_ready = true; changed.notify_all();
                }
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
NativeDisplay::NativeDisplay(bool direct_frame_evidence) : impl_(new Impl) {
    impl_->direct_frame_evidence = direct_frame_evidence;
}
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
MonitorSnapshot NativeDisplay::capture(const std::string & path, const std::string & request, std::uint64_t tokens) {
    if (path.empty() || path.size() > 512 || path.find('\0') != std::string::npos || path.find("..") != std::string::npos ||
        request.empty() || request.size() > 128 || !tokens || tokens > 32)
        throw std::invalid_argument("A fresh bounded displayed-frame request is required");
    std::unique_lock<std::mutex> lock(impl_->mutex);
    if (!impl_->ready || impl_->fault || !impl_->capture_path.empty())
        throw std::runtime_error("The display cannot accept a frame-evidence request");
    impl_->capture_path = path; impl_->capture_request = request; impl_->capture_minimum = tokens;
    impl_->capture_ready = false; impl_->changed.notify_all();
    if (!impl_->changed.wait_for(lock, std::chrono::seconds(10), [&] { return impl_->fault || impl_->capture_ready; }))
        throw std::runtime_error("Positive displayed-frame evidence is missing; backing retained");
    if(impl_->fault)throw std::runtime_error("Displayed-frame persistence failed: "+impl_->error);
    return impl_->captured;
}
bool NativeDisplay::failed() const { return impl_->fault; }
void NativeDisplay::write_CPU_frame_fixture(const std::string & path) {
    MonitorRaster raster; // A deterministic, all-zero raster for full-byte SHA admission.
    Impl::save_frame_direct(path,raster);
}
} // namespace qwen_app
