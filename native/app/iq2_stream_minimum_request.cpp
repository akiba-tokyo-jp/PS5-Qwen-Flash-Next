// SPDX-License-Identifier: MIT
#include <atomic>
#include <cstddef>
#include <cstdint>

#ifndef IQ2_STREAM_KIND
#error Select the complete Up or Gate/Up source layout.
#endif
static_assert(IQ2_STREAM_KIND == 1 || IQ2_STREAM_KIND == 2, "Unsupported stream layout");

extern "C" bool __real_qwen_app_try_Q2_stream(
    const void *const *, const std::size_t *, unsigned, void *, void (*)(void *, unsigned, const void *));

namespace {
std::atomic<std::uint64_t> completed_unused_request_bytes{0};
}

extern "C" std::uint64_t qwen_iq2_stream_unused_request_bytes() {
    return completed_unused_request_bytes.load(std::memory_order_relaxed);
}

extern "C" bool __wrap_qwen_app_try_Q2_stream(
    const void *const *addresses, const std::size_t *sizes, unsigned count,
    void *opaque, void (*consume)(void *, unsigned, const void *)) {
    if (!addresses || !sizes || !opaque || !consume || !count || count > 12 || count % 3) return false;
    std::size_t requested[12]{};
    std::uint64_t unused = 0;
    for (unsigned i = 0; i < count; ++i) {
        const unsigned role = i % 3;
        const std::size_t expected = role == 2 ? 460800 :
            role == 1 || IQ2_STREAM_KIND == 2 ? 422400 : 537600;
        if (!addresses[i] || sizes[i] != expected) return false;
        // The original owner retains every file-range, EOF, overlap, identity,
        // lease and positive-completion guard. Its accepted request sizes stay
        // unchanged. Use the smallest accepted request; its byte count is not
        // tied to a projection role. Upload only the actual shorter prefix.
        // A final Expert without enough suffix returns false before any I/O.
        requested[i] = expected == 422400 ? 460800 : expected;
        unused += requested[i] - expected;
    }
    const bool used = __real_qwen_app_try_Q2_stream(addresses, requested, count, opaque, consume);
    if (used) completed_unused_request_bytes.fetch_add(unused, std::memory_order_relaxed);
    return used;
}
