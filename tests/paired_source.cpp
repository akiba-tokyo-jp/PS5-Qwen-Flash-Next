// SPDX-License-Identifier: MIT
// Actual two-read executor and bounded reader: exact bytes and no GPU work.
#include "paired_source_io.h"
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool ok, const char * message) { if (!ok) throw std::runtime_error(message); }
template<class F> static void rejected(F action) {
    bool failed = false; try { action(); } catch (const std::exception &) { failed = true; }
    check(failed, "An unsafe paired source operation was admitted");
}
struct Ops final : SourceReadOps {
    std::vector<SourceFile> files;
    std::map<int, std::size_t> descriptors;
    std::atomic<unsigned> reads{0}, active{0}, peak{0};
    std::mutex barrier_mutex;
    std::condition_variable barrier;
    unsigned entered = 0, opens = 0, closes = 0;
    int failure = 0;
    bool changed = false;
    std::uint64_t available = 512ull << 20;
    void * half = nullptr;
    PairedSourceIO worker{*this};
    Ops() {
        for (unsigned i = 0; i < 2; ++i) {
            const std::uint64_t bytes = 3 * model_read_window + 1000;
            files.push_back({"sealed-" + std::to_string(i), bytes,
                {1, i+1, 0100644, 0, 0, bytes, 123, 0, 123, 0}});
            descriptors[10 + int(i)] = i;
        }
        worker.start();
    }
    ~Ops() override { worker.stop_completed(); }
    SourceIdentity identity(int fd) override {
        auto result = files.at(descriptors.at(fd)).identity;
        if (changed) ++result[8];
        return result;
    }
    int open_direct(const std::string & path) override {
        for (std::size_t i = 0; i < files.size(); ++i) if (files[i].path == path) {
            const auto fd = 100 + int(++opens); descriptors[fd] = i; return fd;
        }
        return -1;
    }
    bool close_file(int fd) override {
        check(active.load() == 0, "A source descriptor closed during I/O");
        ++closes; return descriptors.erase(fd) == 1;
    }
    std::uint64_t system_headroom() override { return available; }
    std::int64_t read_at(int fd, void * target, std::size_t bytes, std::uint64_t offset) override {
        ++reads;
        const auto current = ++active;
        auto prior = peak.load(); while (current > prior && !peak.compare_exchange_weak(prior, current)) {}
        struct Leave { std::atomic<unsigned> & active; ~Leave() { --active; } } leave{active};
        check(bytes && bytes <= model_read_window / 2 && !(bytes % model_read_alignment) &&
            !(offset % model_read_alignment) && !(reinterpret_cast<std::uintptr_t>(target) % model_read_alignment),
            "An I/O request escaped its aligned half window");
        {
            std::unique_lock<std::mutex> lock(barrier_mutex);
            ++entered; barrier.notify_all();
            check(barrier.wait_for(lock, std::chrono::seconds(5), [&] { return entered >= 2; }),
                "The paired executor serialized both read calls");
        }
        if (failure == 2 && target == half) throw std::runtime_error("Injected helper read failure");
        if (failure == 3 && target != half) return -1;
        if (failure == 4 && target == half) std::this_thread::sleep_for(std::chrono::seconds(12));
        const auto file = descriptors.at(fd);
        const auto count = std::min<std::uint64_t>(bytes, files[file].bytes - offset);
        auto * out = static_cast<unsigned char *>(target);
        for (std::size_t i = 0; i < count; ++i) out[i] = static_cast<unsigned char>((offset + i + 17*file) % 251);
        return static_cast<std::int64_t>(count) - ((failure == 1 && target == half) ? 1 : 0);
    }
    std::array<std::int64_t,2> read_pair(const std::array<SourceReadRequest,2> & requests) override {
        { std::lock_guard<std::mutex> lock(barrier_mutex); entered = 0; }
        half = requests[1].target;
        return worker.read(requests);
    }
};
int main(int argc,char ** argv) {
    try {
        std::vector<unsigned char> storage(model_read_window + 3*model_read_alignment, 0xa5);
        const auto raw = reinterpret_cast<std::uintptr_t>(storage.data());
        auto * scratch = reinterpret_cast<unsigned char *>((raw + 2*model_read_alignment-1) &
            ~(std::uintptr_t(model_read_alignment)-1));
        constexpr std::uintptr_t first = 512ull << 30, second = first + (64ull << 20);
        constexpr std::size_t expert = 3276800;
        if (argc==2 && std::strcmp(argv[1],"uncertain")==0) {
            // Host-only subprocess: retain the actual timed-out worker and its
            // backing, then end the synthetic process without running destructors.
            auto * ops=new Ops;ops->failure=4;
            auto * reader=new MappedSourceReader(ops->files,*ops,scratch);
            reader->register_mapping(first,ops->files[0].bytes,10);
            reader->register_mapping(second,ops->files[1].bytes,11);
            rejected([&] {reader->prepare_pair({first,second},model_read_alignment);});
            check(ops->reads==2 && ops->active==1 && reader->stats().completed_windows==0,
                "A timed-out read was not retained as pending");
            rejected([&] {reader->prepare_pair({first,second},model_read_alignment);});
            rejected([&] {ops->worker.stop_completed();});
            check(ops->reads==2,"An uncertain read was automatically retried");
            std::cout<<"Actual ten-second timeout retained worker, source backing and quarantine; no retry\n"<<std::flush;
            std::_Exit(0);
        }
        {
            Ops ops;
            rejected([&] { ops.worker.read({SourceReadRequest{10,scratch,model_read_alignment,0},
                SourceReadRequest{10,scratch,model_read_alignment,0}}); });
            check(ops.reads==0,"Overlapping destinations entered native I/O");
        }
        {
            Ops ops; MappedSourceReader reader(ops.files,ops,scratch);
            reader.preflight_parallel();
            reader.register_mapping(first,ops.files[0].bytes,10);
            reader.register_mapping(second,ops.files[1].bytes,11);
            const auto windows = reader.prepare_pair({first+123, second+34567},expert);
            for (unsigned j=0;j<2;++j) {
                const auto offset = j ? 34567u : 123u;
                const auto * bytes = static_cast<const unsigned char *>(windows[j]);
                for (std::size_t i=0;i<expert;++i)
                    check(bytes[i] == (offset+i+17*j)%251,"Concurrent original source bytes differ");
            }
            check(reader.stats().completed_windows==2,"A live pair was counted as consumed");
            reader.completed();
            const auto tail = reader.prepare_pair({first+3*model_read_window,second+3*model_read_window},1000);
            check(static_cast<const unsigned char *>(tail[1])[999] ==
                (3*model_read_window+999+17)%251,"An admitted EOF tail differs");
            reader.completed();
            check(ops.peak==2 && ops.reads==6 && reader.stats().chunks==6 &&
                reader.stats().completed_windows==6 && reader.stats().parallel_batches==3,
                "Paired completion accounting or actual overlap differs");
            check(reader.stats().maximum_chunk <= model_read_window/2,"A pair allocated a larger source window");
            for (auto at : {first,second}) { reader.before_unmap(at,ops.files[0].bytes);reader.after_unmap(at,ops.files[0].bytes); }
            reader.close_completed(); check(ops.closes==2,"Completed descriptors were not closed");
        }
        for (unsigned i=0;i<model_read_alignment;++i)
            check(scratch[-int(i)-1]==0xa5 && scratch[model_read_window+i]==0xa5,
                "Paired reads modified bytes outside the original 8 MiB window");
        for (int failure=0;failure<8;++failure) {
            Ops ops; MappedSourceReader reader(ops.files,ops,scratch);
            reader.register_mapping(first,ops.files[0].bytes,10);
            reader.register_mapping(second,ops.files[1].bytes,11);
            if (failure>=3 && failure<=5) ops.failure=failure-2;
            if (failure==6) ops.changed=true;
            if (failure==7) ops.available=model_read_system_reserve;
            rejected([&] {
                if (failure==0) reader.prepare_pair({first-1,second},expert);
                else if (failure==1) reader.prepare_pair({first,second},model_read_window/2);
                else {
                    reader.prepare_pair({first+123,second+34567},expert);
                    if (failure==2) reader.before_unmap(first,ops.files[0].bytes);
                }
            });
            const auto reads=ops.reads.load();
            rejected([&] { reader.prepare_pair({first,second},expert); });
            check(ops.reads==reads && reader.stats().completed_windows==0,
                "A failed pair retried reads or published consumer completion");
        }
        std::cout << "Actual concurrent reads, exact bytes, EOF, fixed 8 MiB canaries, ownership and failure quarantine passed\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
