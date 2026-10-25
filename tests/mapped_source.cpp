// SPDX-License-Identifier: MIT
// Synthetic address/descriptor tests; no mapped pointer is dereferenced.
#include "mapped_source.h"
#include "device_buffer_budget.h"
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool value, const char * message) { if (!value) throw std::runtime_error(message); }
template<class F> static void rejected(F action) {
    bool failed = false; try { action(); } catch (const std::exception &) { failed = true; }
    check(failed, "An unsafe model source operation was admitted");
}
struct Ops final : SourceReadOps {
    std::vector<SourceFile> files;
    std::map<int, std::size_t> descriptors;
    unsigned opens = 0, closes = 0, reads = 0, live = 0, peak = 0;
    bool short_read = false, changed = false, bad_close = false, bad_open = false;
    std::uint64_t free = 512ull << 20;
    SourceIdentity identity(int fd) override {
        auto result = files.at(descriptors.at(fd)).identity;
        if (changed) ++result[8]; return result;
    }
    int open_direct(const std::string & path) override {
        if (bad_open) return -1;
        for (std::size_t i = 0; i < files.size(); ++i) if (files[i].path == path) {
            const int fd = 100 + int(++opens); descriptors[fd] = i;
            peak = std::max(peak, ++live); return fd;
        }
        return -1;
    }
    bool close_file(int fd) override { ++closes; if (bad_close) return false; descriptors.erase(fd); --live; return true; }
    std::int64_t read_at(int fd, void * target, std::size_t bytes, std::uint64_t offset) override {
        ++reads; check(bytes <= model_read_window && !(bytes % model_read_alignment) && !(offset % model_read_alignment),
            "Direct I/O exceeded its aligned bound");
        const auto index = descriptors.at(fd);
        const auto count = std::min<std::uint64_t>(bytes, files[index].bytes - offset);
        auto * output = static_cast<unsigned char *>(target);
        for (std::size_t i = 0; i < count; ++i) output[i] = static_cast<unsigned char>((offset + i + index * 17) % 251);
        return static_cast<std::int64_t>(count) - (short_read ? 1 : 0);
    }
    std::uint64_t system_headroom() override { return free; }
    void setup(unsigned count = 1, std::uint64_t bytes = model_read_window * 3 + 1000) {
        for (unsigned i = 0; i < count; ++i) {
            SourceIdentity key{1, i + 1, 0100644, 0, 0, bytes, 123, 0, 123, 0};
            files.push_back({"original-" + std::to_string(i), bytes, key}); descriptors[10 + int(i)] = i;
        }
    }
};
static constexpr std::uintptr_t base = 1ull << 40;
int main() {
    try {
        std::vector<unsigned char> storage(model_read_window + model_read_alignment);
        const auto raw = reinterpret_cast<std::uintptr_t>(storage.data());
        void * scratch = reinterpret_cast<void *>((raw + model_read_alignment - 1) & ~(std::uintptr_t(model_read_alignment) - 1));
        {
            Ops ops;ops.setup(16);MappedSourceReader reader(ops.files,ops,scratch);
            for(const auto &file:ops.files) {
                const auto lease=reader.begin_metadata_window(file.path);
                check(lease.target==scratch&&lease.bytes==model_read_window&&ops.identity(lease.fd)==file.identity,
                    "Metadata did not reuse the existing original window and descriptor");
                check(!reader.borrowed_window_contains(lease.target,100),"A metadata-only lease authorized a payload copy");
                reader.end_metadata_window();reader.require_completed_window();
            }
            check(ops.peak==8&&ops.reads==0,"Metadata lease added buffers, payload reads or descriptors");
            reader.close_completed();check(ops.live==0,"Positive metadata descriptors did not retire");
        }
        for(unsigned failure=0;failure<4;++failure) {
            Ops ops;ops.setup();MappedSourceReader reader(ops.files,ops,scratch);
            if(failure==3)rejected([&]{reader.begin_metadata_window("unowned");});
            else {
                reader.begin_metadata_window(ops.files[0].path);
                rejected([&]{if(failure==0)reader.completed();else if(failure==1)reader.close_completed();else reader.begin_metadata_window(ops.files[0].path);});
            }
            rejected([&]{reader.end_metadata_window();});check(ops.closes==0,"Failed metadata lease was speculatively released");
        }
        {
            Ops ops; ops.setup(); MappedSourceReader reader(ops.files, ops, scratch);
            reader.preflight(); reader.register_mapping(base, ops.files[0].bytes, 10);
            bool metadata_owned = false;
            std::thread metadata_worker([&] { metadata_owned = reader.contains_metadata(base + 123, 100); });
            metadata_worker.join();
            check(metadata_owned && ops.reads == 2, "Graph-worker range lookup read payload or lost immutable ownership");
            check(!reader.contains(base - model_read_alignment, 10), "An unowned pointer was treated as model data");
            std::size_t left = model_read_window + 100000, done = 0;
            check(!reader.borrowed_window_contains(scratch,100),"An idle source window authorized a copy");
            while (left) {
                std::size_t copied = 0;
                const auto * data = static_cast<const unsigned char *>(reader.prepare(base + 123 + done, left, copied));
                check(copied && copied <= model_read_window, "Invalid source window length");
                check(reader.borrowed_window_contains(data,copied),"The completed payload consumer lost window authority");
                check(!reader.borrowed_window_contains(data,0)&&
                    !reader.borrowed_window_contains(reinterpret_cast<void *>(reinterpret_cast<std::uintptr_t>(scratch)-1),1)&&
                    !reader.borrowed_window_contains(static_cast<unsigned char *>(scratch)+model_read_window,1)&&
                    !reader.borrowed_window_contains(scratch,model_read_window+1),"A source copy escaped its window");
                for (std::size_t i = 0; i < copied; ++i)
                    check(data[i] == (123 + done + i) % 251, "An original source byte changed");
                done += copied; left -= copied; reader.completed();
                check(!reader.borrowed_window_contains(data,copied),"A retired payload lease still authorized a copy");
            }
            const auto bytes = ops.files[0].bytes;
            reader.before_unmap(base, bytes); reader.after_unmap(base, bytes); reader.close_completed();
            check(reader.stats().maximum_chunk == model_read_window && ops.live == 0, "Fixed window or descriptor retirement failed");
            check(reader.stats().chunks == reader.stats().completed_windows,
                "Profiling counted an uncompleted source window as completed");
            check(reader.stats().read_ns > 0 && reader.stats().consumer_ns > 0,
                "Completed source read and consumer intervals were not measured");
        }
        {
            Ops ops; ops.setup(16, model_read_alignment * 2); MappedSourceReader reader(ops.files, ops, scratch);
            for (unsigned i = 0; i < 16; ++i) reader.register_mapping(base + i * model_read_alignment * 4, ops.files[i].bytes, 10 + int(i));
            for (unsigned i = 0; i < 16; ++i) {
                std::size_t copied = 0; reader.prepare(base + i * model_read_alignment * 4, 100, copied); reader.completed();
            }
            check(ops.peak == 8 && ops.closes == 8, "Descriptor cache did not stay within eight handles");
            for (unsigned i = 0; i < 16; ++i) {
                const auto at = base + i * model_read_alignment * 4;
                reader.before_unmap(at, ops.files[i].bytes); reader.after_unmap(at, ops.files[i].bytes);
            }
            reader.close_completed(); check(ops.live == 0 && ops.closes == 16, "Completed source descriptors leaked");
        }
        {
            Ops ops; ops.setup(1, model_read_alignment * 4); MappedSourceReader reader(ops.files, ops, scratch);
            reader.register_mapping(base, ops.files[0].bytes, 10);
            reader.before_unmap(base + model_read_alignment, model_read_alignment);
            reader.after_unmap(base + model_read_alignment, model_read_alignment);
            check(!reader.contains(base + model_read_alignment, 1), "A retired VA hole aliases a new CPU allocation");
            std::size_t copied = 0;
            const auto * data = static_cast<const unsigned char *>(reader.prepare(base + model_read_alignment * 2 + 7, 50, copied));
            check(data[0] == (model_read_alignment * 2 + 7) % 251, "A split mapping lost its file offset"); reader.completed();
        }
        for (int failure = 0; failure < 11; ++failure) {
            Ops ops; ops.setup(); MappedSourceReader reader(ops.files, ops, scratch);
            reader.register_mapping(base, ops.files[0].bytes, 10); std::size_t copied = 0;
            if (failure == 0) ops.short_read = true;
            if (failure == 1) ops.changed = true;
            if (failure == 2) ops.free = model_read_system_reserve;
            if (failure == 3) ops.bad_open = true;
            rejected([&] {
                if (failure < 4) reader.prepare(base, 100, copied);
                else if (failure == 4) { reader.prepare(base, 100, copied); reader.prepare(base, 100, copied); }
                else if (failure == 5) { reader.prepare(base, 100, copied); reader.before_unmap(base, model_read_alignment); }
                else if (failure == 6) reader.contains(base + ops.files[0].bytes - 1, 2);
                else if (failure == 7) reader.contains(std::numeric_limits<std::uintptr_t>::max() - 1, 10);
                else if (failure == 8) reader.register_mapping(base + model_read_alignment, ops.files[0].bytes, 10);
                else if (failure == 9) reader.close_completed();
                else reader.before_unmap(base - model_read_alignment, model_read_alignment * 2);
            });
            const auto before = ops.reads;
            rejected([&] { reader.prepare(base, 100, copied); });
            check(before == ops.reads, "A failed source operation retried I/O");
        }
        {
            Ops ops; ops.setup(); MappedSourceReader reader(ops.files, ops, scratch);
            reader.register_mapping(base, ops.files[0].bytes, 10);
            reader.before_unmap(base, ops.files[0].bytes); reader.after_unmap(base, ops.files[0].bytes);
            reader.preflight(); ops.bad_close = true;
            rejected([&] { reader.close_completed(); }); const auto before = ops.closes;
            rejected([&] { reader.close_completed(); }); check(ops.closes == before, "An uncertain descriptor close was repeated");
        }
        {
            DeviceBufferBudget budget; budget.enable();
            for (std::uintptr_t key = 1; key <= 3; ++key) {
                check(budget.reserve((512u << 20) - 1) == (512u << 20), "Conservative device alignment changed");
                budget.commit(reinterpret_cast<void *>(key));
            }
            budget.reserve(256u << 20); budget.commit(reinterpret_cast<void *>(4));
            check(budget.stats().peak == model_postload_device_budget, "Aggregate device accounting differs");
            budget.released(reinterpret_cast<void *>(2));
            budget.reserve(400u << 20); budget.commit(reinterpret_cast<void *>(5));
            for (std::uintptr_t key : {1, 3, 4, 5}) budget.released(reinterpret_cast<void *>(key));
            budget.released(reinterpret_cast<void *>(100)); // Separately admitted resident model buffer.
            check(budget.stats().live == 0 && budget.stats().allocations == 5, "Device lifecycle accounting differs");
            budget.close_completed();
        }
        for (unsigned failure = 0; failure < 5; ++failure) {
            DeviceBufferBudget budget; budget.enable();
            rejected([&] {
                if (failure == 0) budget.reserve((512u << 20) + 1);
                if (failure == 1) { budget.reserve(1); budget.reserve(1); }
                if (failure == 2) { budget.reserve(1); budget.close_completed(); }
                if (failure == 3) { budget.reserve(1); budget.commit(reinterpret_cast<void *>(1)); budget.close_completed(); }
                if (failure == 4) {
                    for (std::uintptr_t key = 1; key <= 3; ++key) { budget.reserve(512u << 20); budget.commit(reinterpret_cast<void *>(key)); }
                    budget.reserve((256u << 20) + 1);
                }
            });
            rejected([&] { budget.reserve(1); });
        }
        {
            DeviceBufferBudget budget; budget.enable();
            budget.workspace(reinterpret_cast<void *>(10), {0, 1, 64u << 20, 64u << 20});
            check(budget.stats().live == model_internal_workspace_budget, "The internal workspace was omitted from the aggregate pool");
            budget.workspace(reinterpret_cast<void *>(10), {64u << 20, 64u << 20, 64u << 20, 64u << 20});
            check(budget.stats().allocations == 1, "A retained workspace was charged twice");
            for (std::uintptr_t key = 1; key <= 3; ++key) { budget.reserve(512u << 20); budget.commit(reinterpret_cast<void *>(key)); }
            check(budget.stats().live == model_postload_device_budget, "GGML buffers and internal workspace do not share one pool");
            for (std::uintptr_t key : {1, 2, 3, 10}) budget.released(reinterpret_cast<void *>(key));
            budget.close_completed();
        }
        for (unsigned failure = 0; failure < 3; ++failure) {
            DeviceBufferBudget budget; budget.enable();
            rejected([&] {
                if (failure == 0) budget.workspace(reinterpret_cast<void *>(10), {(256u << 20) + 1, 0, 0, 0});
                if (failure == 1) budget.workspace(reinterpret_cast<void *>(10), {128u << 20, 128u << 20, 1, 0});
                if (failure == 2) {
                    budget.reserve(256u << 20); budget.commit(reinterpret_cast<void *>(10));
                    budget.workspace(reinterpret_cast<void *>(10), {0, 0, 0, 0});
                }
            });
            rejected([&] { budget.reserve(1); });
        }
        std::cout << "Bounded source windows, exact bytes, VA retirement, device/workspace limits and failure quarantine passed\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
