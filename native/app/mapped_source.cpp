// SPDX-License-Identifier: MIT
#include "mapped_source.h"
#include "mapped_source_bridge.h"
#include "device_buffer_budget.h"
#include "system_memory.h"
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
#include <atomic>
#include <cstdlib>
#include <fcntl.h>
#include <memory>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <unistd.h>

namespace {
class NativeReads final : public qwen_app::SourceReadOps {
public:
    qwen_app::SourceIdentity identity(int fd) override {
        struct stat info{};
        if (fstat(fd, &info) || !S_ISREG(info.st_mode) || !info.st_ino || info.st_size <= 0 || (info.st_mode & 0022))
            throw std::runtime_error("Native source descriptor identity is not admitted");
        return {std::uint64_t(info.st_dev), std::uint64_t(info.st_ino), std::uint64_t(info.st_mode),
            std::uint64_t(info.st_uid), std::uint64_t(info.st_gid), std::uint64_t(info.st_size),
            std::uint64_t(info.st_mtim.tv_sec), std::uint64_t(info.st_mtim.tv_nsec),
            std::uint64_t(info.st_ctim.tv_sec), std::uint64_t(info.st_ctim.tv_nsec)};
    }
    int open_direct(const std::string & path) override { return open(path.c_str(), O_RDONLY | O_NOFOLLOW | O_DIRECT); }
    bool close_file(int fd) override { return close(fd) == 0; }
    std::int64_t read_at(int fd, void * target, std::size_t bytes, std::uint64_t offset) override {
        static_assert(sizeof(off_t) == 8, "Original model source offsets require 64-bit native I/O");
        if (bytes > qwen_app::model_read_window || offset > std::uint64_t(std::numeric_limits<off_t>::max()))
            throw std::runtime_error("Native source read exceeds its fixed window");
        return pread(fd, target, bytes, static_cast<off_t>(offset));
    }
    std::uint64_t system_headroom() override {
        return qwen_app::qualified_system_headroom(qwen_app::observe_native_system_memory());
    }
};
NativeReads ops;
std::unique_ptr<qwen_app::MappedSourceReader> reader;
void * window = nullptr;
std::atomic<bool> active{false};
std::atomic<bool> compute_limits{false};
qwen_app::DeviceBufferBudget device_budget;
qwen_app::MappedSourceReader & required() {
    if (!active.load(std::memory_order_acquire) || !reader)
        throw std::runtime_error("The bounded model source reader is not active");
    return *reader;
}
}

namespace qwen_app {
void start_native_model_sources(std::vector<SourceFile> files) {
    if (reader || window || active.load() || sysconf(_SC_PAGESIZE) != long(model_read_alignment))
        throw std::runtime_error("A new native source reader and qualified page size are required");
    if (posix_memalign(&window, model_read_alignment, model_read_window) || !window)
        throw std::runtime_error("The fixed native source window could not be allocated");
    if (!ps5_heap_owns(window))
        throw std::runtime_error("The source read window is outside the tracked Direct CPU heap");
    // Keep the window/descriptors on failed setup. Ordinary OS close owns the
    // complete retained process, including failures before GPU initialization.
    reader = std::make_unique<MappedSourceReader>(std::move(files), ops, window);
    reader->preflight();
    active.store(true, std::memory_order_release);
}
SourceReadStats native_model_source_stats() { return required().stats(); }
void enforce_native_model_compute_limits() {
    required().require_completed_window();
    device_budget.enable();
    compute_limits.store(true, std::memory_order_release);
}
void stop_native_model_sources() {
    device_budget.close_completed();
    required().close_completed();
    active.store(false, std::memory_order_release);
    compute_limits.store(false, std::memory_order_release);
    reader.reset(); free(window); window = nullptr;
}
DeviceBufferStats native_model_device_stats() { return device_budget.stats(); }
}

extern "C" bool qwen_app_model_reads_enabled() { return active.load(std::memory_order_acquire); }
extern "C" bool qwen_app_model_compute_limits_enabled() { return compute_limits.load(std::memory_order_acquire); }
extern "C" void qwen_app_model_mapping_open(void * at, std::size_t bytes, int fd) {
    if (qwen_app_model_reads_enabled()) required().register_mapping(reinterpret_cast<std::uintptr_t>(at), bytes, fd);
}
extern "C" void qwen_app_model_mapping_before_unmap(void * at, std::size_t bytes) {
    if (qwen_app_model_reads_enabled()) required().before_unmap(reinterpret_cast<std::uintptr_t>(at), bytes);
}
extern "C" void qwen_app_model_mapping_after_unmap(void * at, std::size_t bytes) {
    if (qwen_app_model_reads_enabled()) required().after_unmap(reinterpret_cast<std::uintptr_t>(at), bytes);
}
extern "C" bool qwen_app_model_source_range(const void * at, std::size_t bytes) {
    return qwen_app_model_reads_enabled() && required().contains(reinterpret_cast<std::uintptr_t>(at), bytes);
}
extern "C" bool qwen_app_model_source_range_metadata(const void * at, std::size_t bytes) {
    return qwen_app_model_reads_enabled() && required().contains_metadata(reinterpret_cast<std::uintptr_t>(at), bytes);
}
extern "C" void qwen_app_model_source_read_CPU(void * target, const void * at, std::size_t bytes) {
    if (!target || !bytes || qwen_app_model_source_range_metadata(target, bytes))
        throw std::runtime_error("A CPU source copy requires owned writable destination memory");
    for (std::size_t done=0;done<bytes;) {
        std::size_t copied=0;const auto * source=required().prepare(reinterpret_cast<std::uintptr_t>(at)+done,bytes-done,copied);
        if (!copied || copied>bytes-done) throw std::runtime_error("The bounded CPU source copy did not advance");
        std::memcpy(static_cast<unsigned char *>(target)+done,source,copied);required().completed();done+=copied;
    }
}
extern "C" const void * qwen_app_model_source_chunk(const void * at, std::size_t wanted, std::size_t * copied) {
    if (!copied) throw std::invalid_argument("A completed source byte count is required");
    return required().prepare(reinterpret_cast<std::uintptr_t>(at), wanted, *copied);
}
extern "C" void qwen_app_model_source_chunk_completed() { required().completed(); }
extern "C" void qwen_app_model_device_buffer_reserve(std::size_t bytes) {
    if (!qwen_app_model_compute_limits_enabled()) return;
    required().require_completed_window();
    const auto reserved = device_budget.reserve(bytes);
    const auto pool = sceKernelGetDirectMemorySize();
    std::int64_t physical = 0; std::size_t available = 0;
    if (pool <= 0 || sceKernelAvailableDirectMemorySize(0, pool, 65536, &physical, &available) < 0 ||
        available < reserved + (512ull << 20))
        throw std::runtime_error("Fresh Direct reserve cannot admit the post-load device buffer");
}
extern "C" void qwen_app_model_workspace_admit(const void * key, const std::size_t * capacities, std::size_t largest_new) {
    if (!qwen_app_model_compute_limits_enabled()) return;
    required().require_completed_window();
    if (!capacities || largest_new > qwen_app::model_internal_workspace_budget)
        throw std::runtime_error("The internal Vulkan workspace plan is invalid");
    device_budget.workspace(key, {capacities[0], capacities[1], capacities[2], capacities[3]});
    const auto pool = sceKernelGetDirectMemorySize();
    std::int64_t physical = 0; std::size_t available = 0;
    const auto aligned = largest_new ? ((largest_new + (2u << 20) - 1) & ~std::size_t((2u << 20) - 1)) : 0;
    if (pool <= 0 || sceKernelAvailableDirectMemorySize(0, pool, 65536, &physical, &available) < 0 ||
        available < aligned + (512ull << 20))
        throw std::runtime_error("Fresh Direct reserve cannot admit the internal Vulkan workspace");
}
extern "C" void qwen_app_model_device_buffer_commit(const void * key) {
    if (qwen_app_model_compute_limits_enabled()) device_budget.commit(key);
}
extern "C" void qwen_app_model_device_buffer_released(const void * key) {
    if (qwen_app_model_compute_limits_enabled()) device_budget.released(key);
}
