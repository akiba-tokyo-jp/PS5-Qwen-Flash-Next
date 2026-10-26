// SPDX-License-Identifier: MIT
#include "batch_metadata_reuse.h"
#include <chrono>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <new>

#ifndef QWEN_BATCH_PROBE_BOUNDARY
#define QWEN_BATCH_PROBE_BOUNDARY() ((void)0)
#endif

static std::uint64_t allocations = 0;
static std::size_t live_bytes = 0, peak_bytes = 0;
struct alignas(std::max_align_t) AllocationHeader { std::size_t bytes; };
void * operator new(std::size_t size) {
    if (size > (1u << 20) - live_bytes) throw std::bad_alloc();
    auto * header = static_cast<AllocationHeader *>(std::malloc(sizeof(AllocationHeader)+(size ? size : 1)));
    if (!header) throw std::bad_alloc();
    ++allocations; header->bytes=size; live_bytes+=size;
    if (live_bytes>peak_bytes) peak_bytes=live_bytes;
    return header+1;
}
void operator delete(void * p) noexcept {
    if (!p) return;
    auto * header=static_cast<AllocationHeader *>(p)-1;
    live_bytes-=header->bytes; std::free(header);
}
void operator delete(void * p, std::size_t) noexcept { ::operator delete(p); }

static void require(bool value) {
    if (!value) throw std::runtime_error("Batch metadata equivalence or allocation check failed");
}
template<class F> static void refuses(F fn) {
    bool caught = false;
    try { fn(); } catch (const std::exception &) { caught = true; }
    require(caught);
}
static void original(llama_batch_ext & batch, const llama_token * ids, unsigned count, llama_pos pos) {
    batch.clear();
    for (unsigned i = 0; i < count; ++i) {
        require(batch.add_token(0) == static_cast<int>(i));
        require(batch.set_token_id(i, ids[i]));
        const llama_pos current = pos + static_cast<int>(i);
        require(batch.set_token_pos(i, &current) && batch.set_output(i, true));
    }
}
static void equal(const llama_batch_ext & a, const llama_batch_ext & b) {
    require(a.n_embd == b.n_embd && a.embd == b.embd && a.state == b.state);
    require(a.tokens.size() == b.tokens.size());
    for (unsigned i = 0; i < a.tokens.size(); ++i) {
        const auto & x = a.tokens[i]; const auto & y = b.tokens[i];
        require(x.id == y.id && x.seq_ids == y.seq_ids && x.pos == y.pos && x.output == y.output);
        require(x.has_embd == y.has_embd && x.has_state == y.has_state && x.embd_off == y.embd_off &&
                x.state_off == y.state_off && x.decision_order == y.decision_order);
    }
}
int main() {
    QWEN_BATCH_PROBE_BOUNDARY();
    qwen_app::BatchMetadataReuse candidate(7, 1000);
    llama_batch_ext control(4, 2560, 2560, 1, nullptr, 1000, 1);
    llama_token ids[4] = {0, 999, 17, 8};
    unsigned comparisons = 0;
    for (unsigned reset = 0; reset < 3; ++reset)
        for (unsigned pos = 0; pos < 253; ++pos)
            for (auto width : {1u, 2u, 4u}) {
                auto & batch = candidate.prepare(7, ids, width, pos, 256);
                original(control, ids, width, pos); equal(control, batch); ++comparisons;
                refuses([&] { candidate.prepare(7, ids, width, pos, 256); });
                refuses([&] { candidate.completed(8); });
                candidate.completed(7);
            }
    refuses([&] { candidate.prepare(8, ids, 1, 0, 256); });
    refuses([&] { candidate.prepare(7, ids, 3, 0, 256); });
    refuses([&] { candidate.prepare(7, ids, 4, 254, 256); });
    refuses([&] { candidate.prepare(7, nullptr, 1, 0, 256); });
    refuses([&] { candidate.prepare(7, ids, 1, -1, 256); });
    refuses([&] { candidate.prepare(7, ids, 1, 0, 257); });
    ids[3] = 1000;
    refuses([&] { candidate.prepare(7, ids, 4, 0, 256); });
    ids[3] = 8;
    volatile std::uint64_t checksum = 0;
    std::printf("{\"metadata_comparisons\":%u,\"rounds\":[", comparisons);
    for (unsigned round = 0; round < 12; ++round) {
        const auto width = std::array<unsigned,3>{1,2,4}[round % 3];
        std::uint64_t ns[2]{}, calls[2]{};
        for (unsigned arm = 0; arm < 2; ++arm) {
            QWEN_BATCH_PROBE_BOUNDARY();
            const unsigned mode = arm ^ (round & 1);
            const auto before = allocations;
            const auto start = std::chrono::steady_clock::now();
            for (unsigned i = 0; i < 100000; ++i) {
                ids[0] = i % 1000;
                const llama_pos pos = i % 250;
                if (mode) {
                    auto & batch = candidate.prepare(7, ids, width, pos, 256);
                    checksum += batch.tokens[0].id + batch.tokens.back().pos[0];
                    candidate.completed(7);
                } else {
                    original(control, ids, width, pos);
                    checksum += control.tokens[0].id + control.tokens.back().pos[0];
                }
            }
            ns[mode] = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
            calls[mode] = allocations-before;
        }
        require(calls[1] == 0 && calls[0] > 0);
        std::printf("%s{\"width\":%u,\"iterations\":100000,\"control_ns\":%llu,\"reuse_ns\":%llu,\"control_allocations\":%llu,\"reuse_allocations\":%llu}",
                    round ? "," : "", width, (unsigned long long)ns[0], (unsigned long long)ns[1],
                    (unsigned long long)calls[0], (unsigned long long)calls[1]);
    }
    candidate.quarantine();
    refuses([&] { candidate.prepare(7, ids, 1, 0, 256); });
    std::printf("],\"checksum\":%llu,\"CPP_live_peak_bytes\":%zu,\"learned_inference\":false,\"PS5_execution\":false}\n", (unsigned long long)checksum,peak_bytes);
    return 0;
}
