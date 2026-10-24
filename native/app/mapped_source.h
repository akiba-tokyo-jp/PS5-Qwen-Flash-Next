// SPDX-License-Identifier: MIT
#pragma once
#include "profile_clock.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace qwen_app {
inline constexpr std::size_t model_read_window = 8u << 20;
inline constexpr std::size_t model_read_alignment = 16384;
inline constexpr std::uint64_t model_read_system_reserve = 256ull << 20;
inline constexpr std::uint64_t model_read_flexible_metadata_margin = 8ull << 20;
using SourceIdentity = std::array<std::uint64_t, 10>;
struct SourceFile { std::string path; std::uint64_t bytes; SourceIdentity identity; };
struct SourceReadStats {
    std::uint64_t bytes = 0, chunks = 0, maximum_chunk = 0, mappings = 0, retired_ranges = 0;
    std::uint64_t headroom_ns = 0, handle_ns = 0, read_ns = 0, consumer_ns = 0, completed_windows = 0;
    std::uint64_t parallel_batches = 0;
};
struct SourceReadRequest { int fd = -1; void * target = nullptr; std::size_t bytes = 0; std::uint64_t offset = 0; };
struct SourceReadOps {
    virtual ~SourceReadOps() = default;
    virtual SourceIdentity identity(int fd) = 0;
    virtual int open_direct(const std::string &) = 0;
    virtual bool close_file(int) = 0;
    virtual std::int64_t read_at(int, void *, std::size_t, std::uint64_t) = 0;
    virtual std::array<std::int64_t, 2> read_pair(const std::array<SourceReadRequest, 2> & requests) {
        std::array<std::int64_t, 2> results{};
        for (unsigned i = 0; i < 2; ++i)
            results[i] = read_at(requests[i].fd, requests[i].target, requests[i].bytes, requests[i].offset);
        return results;
    }
    // Native providers return Flexible availability only after the separate
    // kernel free/minimum/reserved predicate passes. CPU buffers use Direct.
    virtual std::uint64_t system_headroom() = 0;
};

// Owns metadata and at most eight descriptors. The caller owns the aligned
// scratch buffer and retains it after an uncertain upload. Model pointers are
// address/offset keys only: this reader never dereferences mapped model bytes.
class MappedSourceReader {
public:
    MappedSourceReader(std::vector<SourceFile> files, SourceReadOps & ops, void * scratch)
        : files_(std::move(files)), ops_(ops), scratch_(scratch), owner_(std::this_thread::get_id()) {
        if (files_.empty() || files_.size() > 256 || !scratch_ ||
            reinterpret_cast<std::uintptr_t>(scratch_) % model_read_alignment)
            throw std::invalid_argument("A complete source plan and aligned 8 MiB read window are required");
        std::uint64_t total = 0;
        for (std::size_t i = 0; i < files_.size(); ++i) {
            const auto & file = files_[i];
            if (file.path.empty() || file.path.size() > 1024 || file.path.find('\0') != std::string::npos ||
                !file.bytes || file.bytes > (512ull << 30) - total || file.identity[5] != file.bytes)
                throw std::invalid_argument("Invalid original-model source identity");
            for (std::size_t j = 0; j < i; ++j)
                if (files_[j].path == file.path || files_[j].identity == file.identity)
                    throw std::invalid_argument("Original-model sources must be distinct");
            total += file.bytes;
        }
    }
    MappedSourceReader(const MappedSourceReader &) = delete;
    MappedSourceReader & operator=(const MappedSourceReader &) = delete;
    const SourceReadStats & stats() const { return stats_; }
    void require_completed_window() { healthy(); if (busy_) fail("The model source window has not completed"); }

    void register_mapping(std::uintptr_t at, std::uint64_t bytes, int fd) {
        healthy();
        const auto identity = ops_.identity(fd);
        const auto match = std::find_if(files_.begin(), files_.end(), [&](const auto & file) {
            return file.identity == identity && file.bytes == bytes;
        });
        if (match == files_.end()) fail("An engine mapping is not a verified original-model file");
        const auto span = rounded(bytes);
        if (!at || at % model_read_alignment || at >= (1ull << 47) || span > (1ull << 47) - at)
            fail("An engine mapping has an invalid native range");
        for (const auto & range : ranges_)
            if (at < range.at + range.bytes && range.at < at + span) fail("Engine model mappings overlap");
        if (ranges_.size() >= 8192) fail("Engine mapping metadata exceeds its bound");
        ranges_.push_back({at, span, 0, std::size_t(match - files_.begin())}); ++stats_.mappings;
    }

    bool contains(std::uintptr_t at, std::uint64_t bytes) {
        healthy();
        try { return contains_metadata(at, bytes); }
        catch (...) { failed_ = true; throw; }
    }
    // Graph workers may inspect immutable ranges. Only the producer changes
    // their metadata, between completed CPU/GPU graph epochs.
    bool contains_metadata(std::uintptr_t at, std::uint64_t bytes) const {
        if (!bytes) return false;
        if (at > std::numeric_limits<std::uintptr_t>::max() - bytes) throw std::runtime_error("Source pointer arithmetic overflow");
        for (const auto & range : ranges_) {
            if (at < range.at + range.bytes && range.at < at + bytes) {
                if (at < range.at || bytes > range.at + range.bytes - at)
                    throw std::runtime_error("A model upload crosses an unowned or retired mapping range");
                const auto offset = range.offset + at - range.at;
                if (offset > files_[range.file].bytes || bytes > files_[range.file].bytes - offset)
                    throw std::runtime_error("A model upload exceeds its original file payload");
                return true;
            }
        }
        return false;
    }

    const void * prepare(std::uintptr_t at, std::size_t wanted, std::size_t & copied) {
        healthy();
        if (busy_ || !contains(at, wanted)) fail("A source window is busy or unowned");
        const auto range = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & candidate) {
            return at >= candidate.at && at < candidate.at + candidate.bytes;
        });
        return read_window(range->file, range->offset + at - range->at, wanted, copied);
    }

    std::array<const void *, 2> prepare_pair(const std::array<std::uintptr_t, 2> & addresses, std::size_t bytes) {
        healthy();
        if (busy_ || !bytes || bytes > model_read_window / 2 - model_read_alignment)
            fail("A source pair exceeds its two fixed half windows");
        std::array<std::size_t, 2> files{};
        std::array<std::uint64_t, 2> offsets{};
        for (unsigned i = 0; i < 2; ++i) {
            if (!contains(addresses[i], bytes)) fail("A paired source range is unowned");
            const auto range = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & candidate) {
                return addresses[i] >= candidate.at && addresses[i] < candidate.at + candidate.bytes;
            });
            files[i] = range->file; offsets[i] = range->offset + addresses[i] - range->at;
        }
        return read_pair_windows(files, offsets, bytes);
    }

    void preflight_parallel() {
        healthy();
        const auto bytes = std::size_t(std::min<std::uint64_t>(files_.front().bytes, model_read_alignment));
        const auto windows = read_pair_windows({0, 0}, {0, 0}, bytes);
        if (std::memcmp(windows[0], windows[1], bytes)) fail("Concurrent source preflight bytes differ");
        completed();
    }

    // CPU-only capability/read check, before any backend initialization.
    void preflight() {
        healthy(); std::size_t copied = 0;
        const auto bytes = std::min<std::uint64_t>(files_.front().bytes, model_read_alignment);
        (void) read_window(0, 0, std::size_t(bytes), copied); completed();
        (void) read_window(0, files_.front().bytes - bytes, std::size_t(bytes), copied); completed();
    }

    void completed() {
        healthy();
        if (!busy_) fail("A source window has no positive completed upload");
        stats_.consumer_ns += profile_elapsed_ns(consumer_started_);
        stats_.completed_windows += pending_windows_;
        pending_windows_ = 0;
        busy_ = false;
    }

    void before_unmap(std::uintptr_t at, std::uint64_t bytes) {
        healthy();
        if (busy_ || !bytes || at % model_read_alignment) fail("Model unmap overlaps an active source window");
        const auto span = rounded(bytes);
        if (at >= (1ull << 47) || span > (1ull << 47) - at) fail("Invalid model unmap range");
        std::uint64_t covered = 0;
        for (const auto & range : ranges_) {
            const auto lo = std::max(at, range.at), hi = std::min(at + span, range.at + range.bytes);
            if (lo < hi) covered += hi - lo;
        }
        if (covered != span) fail("Model unmap includes an unowned virtual range");
    }
    void after_unmap(std::uintptr_t at, std::uint64_t bytes) {
        before_unmap(at, bytes);
        const auto end = at + rounded(bytes);
        std::vector<Range> kept;
        for (const auto & range : ranges_) {
            const auto range_end = range.at + range.bytes;
            if (range_end <= at || range.at >= end) { kept.push_back(range); continue; }
            if (range.at < at) kept.push_back({range.at, at - range.at, range.offset, range.file});
            if (range_end > end) kept.push_back({end, range_end - end, range.offset + end - range.at, range.file});
        }
        if (kept.size() > 8192) fail("Retired mapping metadata exceeds its bound");
        ranges_ = std::move(kept); ++stats_.retired_ranges;
    }
    void close_completed() {
        healthy();
        if (busy_ || !ranges_.empty()) fail("Source cleanup requires every mapping and upload to be completed");
        for (auto & entry : handles_) if (entry.fd >= 0) {
            const int fd = entry.fd; entry.fd = -1;
            if (!ops_.close_file(fd)) fail("Source descriptor close was uncertain; no retry");
        }
    }
private:
    struct Range { std::uintptr_t at; std::uint64_t bytes, offset; std::size_t file; };
    struct Handle { int fd = -1; std::size_t file = 0; std::uint64_t age = 0; };
    std::vector<SourceFile> files_;
    SourceReadOps & ops_;
    void * scratch_;
    std::thread::id owner_;
    std::vector<Range> ranges_;
    std::array<Handle, 8> handles_{};
    std::uint64_t age_ = 0;
    bool busy_ = false, failed_ = false;
    ProfileClock::time_point consumer_started_{};
    unsigned pending_windows_ = 0;
    SourceReadStats stats_;
    [[noreturn]] void fail(const char * message) { failed_ = true; throw std::runtime_error(message); }
    void healthy() {
        if (failed_ || owner_ != std::this_thread::get_id()) fail("The bounded source reader is quarantined or has another producer");
    }
    std::uint64_t rounded(std::uint64_t bytes) {
        if (bytes > (512ull << 30)) fail("Source mapping size exceeds its bound");
        return (bytes + model_read_alignment - 1) & ~(std::uint64_t(model_read_alignment) - 1);
    }
    int handle(std::size_t file) {
        for (auto & entry : handles_) if (entry.fd >= 0 && entry.file == file) {
            if (ops_.identity(entry.fd) != files_[file].identity) fail("An open model source changed");
            entry.age = ++age_; return entry.fd;
        }
        auto target = std::find_if(handles_.begin(), handles_.end(), [](const auto & item) { return item.fd < 0; });
        if (target == handles_.end()) {
            target = std::min_element(handles_.begin(), handles_.end(), [](const auto & a, const auto & b) { return a.age < b.age; });
            const int old = target->fd; target->fd = -1;
            if (!ops_.close_file(old)) fail("Model source eviction close was uncertain");
        }
        const int fd = ops_.open_direct(files_[file].path);
        if (fd < 0) fail("Direct model source access is unavailable");
        *target = {fd, file, ++age_};
        if (ops_.identity(fd) != files_[file].identity) fail("Direct model source identity changed");
        return fd;
    }
    std::array<const void *, 2> read_pair_windows(const std::array<std::size_t, 2> & files,
            const std::array<std::uint64_t, 2> & offsets, std::size_t bytes) {
        if (busy_ || !bytes || bytes > model_read_window / 2 - model_read_alignment)
            fail("Invalid paired source windows");
        std::array<SourceReadRequest, 2> requests{};
        std::array<const void *, 2> windows{};
        std::array<std::uint64_t, 2> available{};
        for (unsigned i = 0; i < 2; ++i) {
            if (files[i] >= files_.size() || offsets[i] >= files_[files[i]].bytes ||
                bytes > files_[files[i]].bytes - offsets[i]) fail("A paired read exceeds its sealed file");
            {
                ProfileScope timing(stats_.headroom_ns);
                if (ops_.system_headroom() < model_read_system_reserve + model_read_flexible_metadata_margin)
                    fail("Fresh Flexible/kernel reserve cannot admit a paired read");
            }
            const auto skip = std::size_t(offsets[i] % model_read_alignment);
            const auto requested = std::size_t(rounded(skip + bytes));
            if (requested > model_read_window / 2) fail("An aligned paired window exceeds its half buffer");
            int fd;
            { ProfileScope timing(stats_.handle_ns); fd = handle(files[i]); }
            auto * target = static_cast<unsigned char *>(scratch_) + i * (model_read_window / 2);
            requests[i] = {fd, target, requested, offsets[i] - skip};
            windows[i] = target + skip;
            available[i] = std::min<std::uint64_t>(requested, files_[files[i]].bytes - requests[i].offset);
        }
        busy_ = true; pending_windows_ = 2;
        std::array<std::int64_t, 2> got{};
        { ProfileScope timing(stats_.read_ns); got = ops_.read_pair(requests); }
        for (unsigned i = 0; i < 2; ++i) {
            if (got[i] < 0 || std::uint64_t(got[i]) != available[i] ||
                std::uint64_t(got[i]) < offsets[i] % model_read_alignment + bytes)
                fail("A paired direct read did not complete its exact window");
            stats_.maximum_chunk = std::max<std::uint64_t>(stats_.maximum_chunk, requests[i].bytes);
        }
        stats_.bytes += 2 * bytes; stats_.chunks += 2; ++stats_.parallel_batches;
        consumer_started_ = ProfileClock::now();
        return windows;
    }
    const void * read_window(std::size_t file, std::uint64_t offset, std::size_t wanted, std::size_t & copied) {
        if (busy_ || !wanted || offset >= files_[file].bytes || wanted > files_[file].bytes - offset)
            fail("Invalid bounded model source read");
        {
            ProfileScope timing(stats_.headroom_ns);
            if (ops_.system_headroom() < model_read_system_reserve + model_read_flexible_metadata_margin)
                fail("Fresh Flexible/kernel reserve cannot admit the next model source window");
        }
        busy_ = true;
        pending_windows_ = 1;
        const auto skip = std::size_t(offset % model_read_alignment);
        copied = std::min(wanted, model_read_window - skip);
        const auto requested = std::size_t(rounded(skip + copied));
        const auto aligned = offset - skip;
        int fd;
        { ProfileScope timing(stats_.handle_ns); fd = handle(file); }
        std::int64_t got;
        { ProfileScope timing(stats_.read_ns); got = ops_.read_at(fd, scratch_, requested, aligned); }
        const auto available = std::min<std::uint64_t>(requested, files_[file].bytes - aligned);
        if (got < 0 || std::uint64_t(got) != available || std::uint64_t(got) < skip + copied)
            fail("Direct model read did not complete its exact admitted window");
        stats_.bytes += copied; ++stats_.chunks; stats_.maximum_chunk = std::max<std::uint64_t>(stats_.maximum_chunk, requested);
        consumer_started_ = ProfileClock::now();
        return static_cast<const unsigned char *>(scratch_) + skip;
    }
};
// The native provider allocates exactly one aligned window. It is explicitly
// shut down only after model destruction and positive native completion.
void start_native_model_sources(std::vector<SourceFile> files);
void start_native_source_parallel_reads();
void enforce_native_model_compute_limits();
SourceReadStats native_model_source_stats();
void stop_native_model_sources();
}
