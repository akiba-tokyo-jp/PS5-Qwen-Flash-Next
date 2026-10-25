// SPDX-License-Identifier: MIT
#pragma once
#include "profile_clock.h"
#include "source_read_schedule.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <functional>
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
struct LogicalSourceFile {
    std::string path;
    std::uint64_t bytes;
    std::vector<std::size_t> parts;
};
inline constexpr std::uint64_t model_source_part_bytes = 512ull << 20;
struct SourceReadStats {
    std::uint64_t bytes = 0, chunks = 0, maximum_chunk = 0, mappings = 0, retired_ranges = 0;
    std::uint64_t headroom_ns = 0, handle_ns = 0, read_ns = 0, consumer_ns = 0, completed_windows = 0;
    std::uint64_t parallel_batches = 0;
    std::uint64_t pipeline_batches = 0, worker_read_ns = 0, worker_dispatch_ns = 0;
    std::uint64_t physical_read_bytes = 0, physical_read_calls = 0;
    std::uint64_t coalesced_batches = 0, selected_serial_batches = 0;
    bool schedule_enabled = false;
};
struct SourceReadRequest { int fd = -1; void * target = nullptr; std::size_t bytes = 0; std::uint64_t offset = 0; };
struct SourcePipelineTimes { std::uint64_t producer_wait_ns = 0, worker_read_ns = 0, worker_dispatch_ns = 0; };
struct CompletedSourcePair {
    std::array<std::size_t, 2> files{};
    std::array<std::uint64_t, 2> offsets{};
    std::size_t bytes = 0;
    std::uint64_t completed_ordinal = 0;
};
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
    virtual SourcePipelineTimes pipeline_pair(const std::array<SourceReadRequest, 2> &,
            const std::array<std::uint64_t, 2> &, const std::function<void(unsigned)> &,
            const std::function<void(unsigned, const void *)> &) {
        throw std::runtime_error("Source read/consumer pipelining is not admitted by this provider");
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
    MappedSourceReader(std::vector<SourceFile> files, SourceReadOps & ops, void * scratch,
            std::vector<LogicalSourceFile> logical = {})
        : files_(std::move(files)), ops_(ops), scratch_(scratch), owner_(std::this_thread::get_id()) {
        const bool split = !logical.empty();
        if (files_.empty() || files_.size() > (split ? 1024u : 256u) || !scratch_ ||
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
        if (!split) {
            for (std::size_t i = 0; i < files_.size(); ++i)
                logical.push_back({files_[i].path, files_[i].bytes, {i}});
        }
        if (logical.empty() || logical.size() > 256)
            throw std::invalid_argument("A bounded complete logical model is required");
        std::vector<bool> used(files_.size(), false);
        for (const auto & file : logical) {
            if (file.parts.empty() || file.parts.size() > 1024 || !file.bytes ||
                file.parts.front() >= files_.size() || file.path != files_[file.parts.front()].path)
                throw std::invalid_argument("Invalid logical model source head");
            std::uint64_t bytes = 0;
            for (std::size_t i = 0; i < file.parts.size(); ++i) {
                const auto part = file.parts[i];
                if (part >= files_.size() || used[part] ||
                    (split && (files_[part].bytes > model_source_part_bytes ||
                     (i + 1 < file.parts.size() && files_[part].bytes != model_source_part_bytes))))
                    throw std::invalid_argument("Split sources must cover unique complete 512 MiB parts");
                used[part] = true; bytes += files_[part].bytes;
            }
            if (bytes != file.bytes) throw std::invalid_argument("Split sources do not preserve the original logical size");
        }
        if (std::find(used.begin(), used.end(), false) != used.end())
            throw std::invalid_argument("A physical model source is outside its logical layout");
        logical_ = std::move(logical);
    }
    MappedSourceReader(const MappedSourceReader &) = delete;
    MappedSourceReader & operator=(const MappedSourceReader &) = delete;
    const SourceReadStats & stats() const { return stats_; }
    std::uint64_t logical_file_bytes(int fd) {
        healthy(); const auto identity = ops_.identity(fd);
        for (const auto & file : logical_)
            if (files_[file.parts.front()].identity == identity) return file.bytes;
        fail("Logical model size requires an admitted physical head descriptor");
    }
    void require_completed_window() { healthy(); if (busy_) fail("The model source window has not completed"); }
    SourceReadRequest begin_metadata_window(const std::string & path) {
        require_completed_window();
        const auto file=std::find_if(files_.begin(),files_.end(),[&](const auto & item){return item.path==path;});
        if(file==files_.end())fail("Metadata requires an admitted original source path");
        const int fd=handle(std::size_t(file-files_.begin()));
        busy_=metadata_lease_=true;
        return {fd,scratch_,model_read_window,0};
    }
    void end_metadata_window() {
        healthy();
        if(!busy_||!metadata_lease_||pending_windows_)fail("Metadata window completion has no matching exclusive lease");
        metadata_lease_=busy_=false;
    }
    void enable_source_schedule() {
        require_completed_window();
        if (schedule_enabled_ || trace_enabled_) fail("The source schedule requires a fresh exclusive admission");
        schedule_enabled_ = true; stats_.schedule_enabled = true;
    }
    void qualify_source_schedule() {
        require_completed_window();
        if (schedule_enabled_ || files_.front().bytes < (16ull << 20))
            fail("The selected schedule requires a fresh sufficiently large sealed source");
        const auto digest = [](const void * at, std::size_t count) {
            auto * bytes = static_cast<const unsigned char *>(at);
            std::uint64_t hash = 1469598103934665603ull;
            for (std::size_t i = 0; i < count; ++i) hash = (hash ^ bytes[i]) * 1099511628211ull;
            return hash;
        };
        std::size_t copied = 0;
        const auto * parallel_source = read_window(0, 4ull << 20, model_read_alignment, copied);
        if (copied != model_read_alignment) fail("The selected parallel reference is incomplete");
        const auto parallel_digest = digest(parallel_source, copied); completed();
        const auto * merged_source = static_cast<const unsigned char *>(read_window(0, 8ull << 20, 2 * model_read_alignment, copied));
        if (copied != 2 * model_read_alignment) fail("The coalesced source reference is incomplete");
        const std::array<std::uint64_t, 2> merged_digests{
            digest(merged_source, model_read_alignment), digest(merged_source + model_read_alignment, model_read_alignment)};
        completed();
        const auto before_parallel = stats_.parallel_batches, before_merged = stats_.coalesced_batches;
        enable_source_schedule();
        pipeline_windows({0, 0}, {4ull << 20, 4ull << 20}, model_read_alignment,
            [&](unsigned, const void * at) {
                if (digest(at, model_read_alignment) != parallel_digest) fail("The selected parallel original bytes differ");
            });
        pipeline_windows({0, 0}, {8ull << 20, (8ull << 20) + model_read_alignment}, model_read_alignment,
            [&](unsigned i, const void * at) {
                if (digest(at, model_read_alignment) != merged_digests[i]) fail("The coalesced original bytes differ");
            });
        if (stats_.parallel_batches != before_parallel + 1 || stats_.coalesced_batches != before_merged + 1)
            fail("The selected source CPU preflight did not exercise both candidate paths");
    }
    void enable_completed_pair_trace() {
        require_completed_window();
        if (schedule_enabled_ || trace_enabled_ || trace_count_ || trace_replayed_) fail("The completed source trace may only start once");
        trace_enabled_ = true;
    }
    void replay_completed_pair_trace(const std::function<void(unsigned, unsigned, unsigned,
            const std::array<SourceReadRequest, 2> &, const std::array<std::uint64_t, 2> &,
            const CompletedSourcePair &)> & replay) {
        require_completed_window();
        if (!trace_enabled_ || trace_count_ != trace_.size() || trace_replayed_ || !replay)
            fail("An exact bounded completed source trace is required");
        trace_enabled_ = false; trace_replayed_ = true;
        const auto started = ProfileClock::now();
        for (unsigned round = 0; round < 3; ++round) for (unsigned order = 0; order < 4; ++order) {
            const unsigned mode = round % 2 ? 3 - order : order;
            for (unsigned index = 0; index < trace_.size(); ++index) {
                if (profile_elapsed_ns(started) > 30000000000ull) fail("The source trace diagnostic reached its completed boundary deadline");
                const auto & key = trace_[index];
                std::array<SourceReadRequest, 2> requests{};
                std::array<std::uint64_t, 2> expected{};
                for (unsigned i = 0; i < 2; ++i) {
                    if (ops_.system_headroom() < model_read_system_reserve + model_read_flexible_metadata_margin)
                        fail("The source trace diagnostic cannot retain the original OS reserve");
                    const auto skip = key.offsets[i] % model_read_alignment;
                    const auto bytes = std::size_t(rounded(skip + key.bytes));
                    requests[i] = {handle(key.files[i]), static_cast<unsigned char *>(scratch_) + i * (model_read_window / 2),
                        bytes, key.offsets[i] - skip};
                    expected[i] = std::min<std::uint64_t>(bytes, files_[key.files[i]].bytes - requests[i].offset);
                }
                busy_ = true; pending_windows_ = 2;
                try { replay(round, mode, index, requests, expected, key); }
                catch (...) { failed_ = true; throw; }
                pending_windows_ = 0; busy_ = false;
            }
        }
    }

    void register_mapping(std::uintptr_t at, std::uint64_t bytes, int fd) {
        healthy();
        const auto identity = ops_.identity(fd);
        const auto match = std::find_if(logical_.begin(), logical_.end(), [&](const auto & file) {
            return files_[file.parts.front()].identity == identity && file.bytes == bytes;
        });
        if (match == logical_.end()) fail("An engine mapping is not a verified original-model file");
        const auto span = rounded(bytes);
        if (!at || at % model_read_alignment || at >= (1ull << 47) || span > (1ull << 47) - at)
            fail("An engine mapping has an invalid native range");
        for (const auto & range : ranges_)
            if (at < range.at + range.bytes && range.at < at + span) fail("Engine model mappings overlap");
        if (match->parts.size() > 8192 - ranges_.size()) fail("Engine mapping metadata exceeds its bound");
        const auto owner = std::size_t(stats_.mappings);
        std::uint64_t offset = 0;
        for (const auto part : match->parts) {
            ranges_.push_back({at + offset, rounded(files_[part].bytes), 0, part, owner});
            offset += files_[part].bytes;
        }
        ++stats_.mappings;
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
        const auto first = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & range) {
            return at >= range.at && at < range.at + range.bytes;
        });
        if (first == ranges_.end()) {
            for (const auto & range : ranges_)
                if (at < range.at + range.bytes && range.at < at + bytes)
                    throw std::runtime_error("A model upload starts outside its owned mapping");
            return false;
        }
        const auto owner = first->owner;
        std::uint64_t done = 0;
        while (done < bytes) {
            const auto cursor = at + done;
            const auto range = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & item) {
                return item.owner == owner && cursor >= item.at && cursor < item.at + item.bytes;
            });
            if (range == ranges_.end()) throw std::runtime_error("A model upload crosses an unowned or retired mapping range");
            const auto offset = range->offset + cursor - range->at;
            if (offset >= files_[range->file].bytes)
                throw std::runtime_error("A model upload exceeds its original file payload");
            done += std::min({bytes - done, files_[range->file].bytes - offset,
                range->bytes - (cursor - range->at)});
        }
        return true;
    }

    const void * prepare(std::uintptr_t at, std::size_t wanted, std::size_t & copied) {
        healthy();
        if (busy_ || !contains(at, wanted)) fail("A source window is busy or unowned");
        const auto range = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & candidate) {
            return at >= candidate.at && at < candidate.at + candidate.bytes;
        });
        const auto offset = range->offset + at - range->at;
        return read_window(range->file, offset, std::size_t(std::min<std::uint64_t>(wanted,
            files_[range->file].bytes - offset)), copied);
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
        if (pair_crosses_part(files, offsets, bytes)) return crossing_pair(addresses, bytes);
        return read_pair_windows(files, offsets, bytes);
    }

    void preflight_parallel() {
        healthy();
        const auto bytes = std::size_t(std::min<std::uint64_t>(files_.front().bytes, model_read_alignment));
        const auto windows = read_pair_windows({0, 0}, {0, 0}, bytes);
        if (std::memcmp(windows[0], windows[1], bytes)) fail("Concurrent source preflight bytes differ");
        completed();
    }

    void upload_pair(const std::array<std::uintptr_t, 2> & addresses, std::size_t bytes,
            const std::function<void(unsigned, const void *)> & consume) {
        healthy();
        if (busy_ || !bytes || bytes > model_read_window / 2 - model_read_alignment || !consume)
            fail("A pipelined source pair exceeds its owned half windows");
        std::array<std::size_t, 2> files{};
        std::array<std::uint64_t, 2> offsets{};
        for (unsigned i = 0; i < 2; ++i) {
            if (!contains(addresses[i], bytes)) fail("A pipelined source range is unowned");
            const auto range = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & candidate) {
                return addresses[i] >= candidate.at && addresses[i] < candidate.at + candidate.bytes;
            });
            files[i] = range->file; offsets[i] = range->offset + addresses[i] - range->at;
        }
        if (pair_crosses_part(files, offsets, bytes)) {
            const auto windows = crossing_pair(addresses, bytes);
            try {
                for (unsigned i = 0; i < 2; ++i) consume(i, windows[i]);
                completed(); return;
            } catch (...) { failed_ = true; throw; }
        }
        pipeline_windows(files, offsets, bytes, consume);
    }
    void preflight_pipeline() {
        healthy();
        const auto bytes = std::size_t(std::min<std::uint64_t>(files_.front().bytes, model_read_alignment));
        const void * first = nullptr;
        pipeline_windows({0, 0}, {0, 0}, bytes, [&](unsigned i, const void * at) {
            if (i == 0) first = at;
            else if (!first || std::memcmp(first, at, bytes)) fail("Pipelined source preflight bytes differ");
        });
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
        if(metadata_lease_)fail("A consumer cannot retire an active metadata lease");
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
            if (range.at < at) kept.push_back({range.at, at - range.at, range.offset, range.file, range.owner});
            if (range_end > end) kept.push_back({end, range_end - end, range.offset + end - range.at, range.file, range.owner});
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
    struct Range { std::uintptr_t at; std::uint64_t bytes, offset; std::size_t file, owner; };
    struct Handle { int fd = -1; std::size_t file = 0; std::uint64_t age = 0; };
    std::vector<SourceFile> files_;
    std::vector<LogicalSourceFile> logical_;
    SourceReadOps & ops_;
    void * scratch_;
    std::thread::id owner_;
    std::vector<Range> ranges_;
    std::array<Handle, 8> handles_{};
    std::uint64_t age_ = 0;
    bool busy_ = false, failed_ = false, metadata_lease_ = false;
    ProfileClock::time_point consumer_started_{};
    unsigned pending_windows_ = 0;
    SourceReadStats stats_;
    std::array<CompletedSourcePair, 32> trace_{};
    unsigned trace_count_ = 0;
    std::uint64_t trace_seen_ = 0;
    bool trace_enabled_ = false, trace_replayed_ = false;
    bool schedule_enabled_ = false;
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
    bool pair_crosses_part(const std::array<std::size_t, 2> & files,
            const std::array<std::uint64_t, 2> & offsets, std::size_t bytes) const {
        for (unsigned i = 0; i < 2; ++i)
            if (offsets[i] >= files_[files[i]].bytes || bytes > files_[files[i]].bytes - offsets[i]) return true;
        return false;
    }
    std::array<const void *, 2> crossing_pair(const std::array<std::uintptr_t, 2> & addresses,
            std::size_t bytes) {
        if (busy_) fail("A crossing source pair overlaps an active lease");
        std::array<const void *, 2> windows{};
        busy_ = true; pending_windows_ = 2;
        try {
            for (unsigned i = 0; i < 2; ++i) {
                auto * target = static_cast<unsigned char *>(scratch_) + i * (model_read_window / 2);
                const auto leading = std::size_t(addresses[i] % model_read_alignment);
                const auto first = addresses[i] - leading;
                std::size_t done = 0;
                while (done < leading + bytes) {
                    const auto at = first + done;
                    const auto range = std::find_if(ranges_.begin(), ranges_.end(), [&](const auto & item) {
                        return at >= item.at && at < item.at + item.bytes;
                    });
                    if (range == ranges_.end()) fail("A crossing read lost its admitted source part");
                    const auto offset = range->offset + at - range->at;
                    const auto logical = std::size_t(std::min<std::uint64_t>(leading + bytes - done,
                        files_[range->file].bytes - offset));
                    const auto requested = std::size_t(rounded(logical));
                    if (!logical || done + requested > model_read_window / 2 || offset % model_read_alignment ||
                        ops_.system_headroom() < model_read_system_reserve + model_read_flexible_metadata_margin)
                        fail("A crossing read escaped its fixed half window or reserves");
                    const int fd = handle(range->file);
                    std::int64_t got;
                    { ProfileScope timing(stats_.read_ns); got = ops_.read_at(fd, target + done, requested, offset); }
                    const auto expected = std::min<std::uint64_t>(requested, files_[range->file].bytes - offset);
                    if (got != std::int64_t(expected) || expected < logical)
                        fail("A crossing source read did not return exact admitted bytes");
                    ++stats_.physical_read_calls; stats_.physical_read_bytes += expected;
                    stats_.maximum_chunk = std::max<std::uint64_t>(stats_.maximum_chunk, requested);
                    done += logical;
                }
                windows[i] = target + leading;
            }
        } catch (...) { failed_ = true; throw; }
        stats_.bytes += bytes * 2; stats_.chunks += 2; ++stats_.selected_serial_batches;
        consumer_started_ = ProfileClock::now(); return windows;
    }
    void pipeline_windows(const std::array<std::size_t, 2> & files,
            const std::array<std::uint64_t, 2> & offsets, std::size_t bytes,
            const std::function<void(unsigned, const void *)> & consume) {
        if (busy_ || !bytes || bytes > model_read_window / 2 - model_read_alignment)
            fail("Invalid pipelined source windows");
        std::array<SourceReadRequest, 2> requests{};
        std::array<std::uint64_t, 2> expected{};
        std::array<std::size_t, 2> skips{};
        for (unsigned i = 0; i < 2; ++i) {
            if (files[i] >= files_.size() || offsets[i] >= files_[files[i]].bytes ||
                bytes > files_[files[i]].bytes - offsets[i]) fail("A pipelined read exceeds its sealed file");
            skips[i] = std::size_t(offsets[i] % model_read_alignment);
            const auto requested = std::size_t(rounded(skips[i] + bytes));
            if (requested > model_read_window / 2) fail("An aligned pipeline window exceeds its half buffer");
            int fd;
            { ProfileScope timing(stats_.handle_ns); fd = handle(files[i]); }
            auto * target = static_cast<unsigned char *>(scratch_) + i * (model_read_window / 2);
            requests[i] = {fd, target, requested, offsets[i] - skips[i]};
            expected[i] = std::min<std::uint64_t>(requested, files_[files[i]].bytes - requests[i].offset);
        }
        busy_ = true; pending_windows_ = 2;
        std::size_t merged_bytes = 0;
        if (schedule_enabled_ && files[0] == files[1] && offsets[1] >= offsets[0] &&
            offsets[1] - offsets[0] == bytes) {
            const auto span = skips[0] + std::uint64_t(bytes) * 2;
            if (span <= model_read_window) {
                const auto aligned_span = rounded(span);
                if (aligned_span <= model_read_window && source_schedule_extent(requests[0].offset,
                        aligned_span, files_[files[0]].identity)) merged_bytes = std::size_t(aligned_span);
            }
        }
        try {
            const auto before_read = [&](unsigned) {
                ProfileScope timing(stats_.headroom_ns);
                if (ops_.system_headroom() < model_read_system_reserve + model_read_flexible_metadata_margin)
                    fail("Fresh Flexible/kernel reserve cannot admit a pipelined read");
            };
            const auto consume_window = [&](unsigned i, const void * target) {
                ProfileScope timing(stats_.consumer_ns);
                consume(i, static_cast<const unsigned char *>(target) + skips[i]);
            };
            if (merged_bytes) {
                before_read(0);
                std::int64_t got;
                { ProfileScope timing(stats_.read_ns);
                  got = ops_.read_at(requests[0].fd, scratch_, merged_bytes, requests[0].offset); }
                if (got != std::int64_t(merged_bytes)) fail("A coalesced source read did not complete exactly");
                consume_window(0, scratch_);
                // Each logical expert keeps its original cache destination.
                // Source adjacency does not require adjacent destination slots.
                consume_window(1, static_cast<const unsigned char *>(scratch_) +
                    offsets[1] - requests[0].offset - skips[1]);
            } else if (schedule_enabled_ && source_schedule_parallel(files_[files[0]].identity,
                    requests[0].offset, requests[0].bytes, files_[files[1]].identity,
                    requests[1].offset, requests[1].bytes)) {
                before_read(0); before_read(1);
                std::array<std::int64_t, 2> got;
                { ProfileScope timing(stats_.read_ns); got = ops_.read_pair(requests); }
                for (unsigned i = 0; i < 2; ++i)
                    if (got[i] != std::int64_t(expected[i])) fail("A selected parallel source read did not complete exactly");
                consume_window(0, requests[0].target); consume_window(1, requests[1].target);
                ++stats_.parallel_batches;
            } else {
                const auto timing = ops_.pipeline_pair(requests, expected, before_read, consume_window);
                stats_.read_ns += timing.producer_wait_ns;
                stats_.worker_read_ns += timing.worker_read_ns;
                stats_.worker_dispatch_ns += timing.worker_dispatch_ns;
                ++stats_.pipeline_batches;
                if (schedule_enabled_) ++stats_.selected_serial_batches;
            }
        } catch (...) { failed_ = true; throw; }
        if (merged_bytes) {
            ++stats_.coalesced_batches; ++stats_.physical_read_calls; stats_.physical_read_bytes += merged_bytes;
            stats_.maximum_chunk = std::max<std::uint64_t>(stats_.maximum_chunk, merged_bytes);
        } else for (unsigned i = 0; i < 2; ++i) {
            stats_.maximum_chunk = std::max<std::uint64_t>(stats_.maximum_chunk, requests[i].bytes);
            ++stats_.physical_read_calls; stats_.physical_read_bytes += expected[i];
        }
        stats_.bytes += 2 * bytes; stats_.chunks += 2;
        stats_.completed_windows += 2; pending_windows_ = 0; busy_ = false;
        if (trace_enabled_) {
            const auto ordinal = trace_seen_++;
            // Spread fixed metadata across the actual request's file/layer
            // stream, rather than retaining only its first few cached layers.
            if (trace_count_ < trace_.size() && ordinal % 512 == 0)
                trace_[trace_count_++] = {files, offsets, bytes, ordinal};
        }
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
        stats_.physical_read_calls += 2; stats_.physical_read_bytes += got[0] + got[1];
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
        ++stats_.physical_read_calls; stats_.physical_read_bytes += std::uint64_t(got);
        consumer_started_ = ProfileClock::now();
        return static_cast<const unsigned char *>(scratch_) + skip;
    }
};
// The native provider allocates exactly one aligned window. It is explicitly
// shut down only after model destruction and positive native completion.
void start_native_model_sources(std::vector<SourceFile> files, std::vector<LogicalSourceFile> logical = {});
SourceReadRequest begin_native_metadata_window(const std::string & path);
void end_native_metadata_window();
void start_native_source_parallel_reads();
void enable_native_source_schedule();
void enforce_native_model_compute_limits();
SourceReadStats native_model_source_stats();
void stop_native_model_sources();
void enable_native_completed_source_trace();
}
