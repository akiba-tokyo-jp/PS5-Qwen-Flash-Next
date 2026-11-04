// SPDX-License-Identifier: MIT
#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

extern "C" bool __wrap_qwen_app_try_Q2_stream(const void *const *, const std::size_t *, unsigned,
                                             void *, void (*)(void *, unsigned, const void *));
extern "C" std::uint64_t qwen_iq2_stream_unused_request_bytes();

namespace {
std::array<std::vector<unsigned char>, 12> sources, destinations;
std::array<std::size_t, 12> actual{}, available{};
unsigned real_calls = 0, callbacks = 0;

void consume(void *owner, unsigned index, const void *bytes) {
    assert(owner == &callbacks && index < 12 && bytes == sources[index].data());
    auto &destination = destinations[index];
    std::memcpy(destination.data() + 16, bytes, actual[index]);
    assert(std::equal(destination.begin(), destination.begin() + 16, destination.end() - 16));
    assert(std::all_of(destination.begin(), destination.begin() + 16, [](unsigned char x) { return x == 0xa7; }));
    assert(std::all_of(destination.end() - 16, destination.end(), [](unsigned char x) { return x == 0xa7; }));
    assert(std::memcmp(destination.data() + 16, sources[index].data(), actual[index]) == 0);
    ++callbacks;
}
}

extern "C" bool __real_qwen_app_try_Q2_stream(const void *const *addresses, const std::size_t *sizes,
                                              unsigned count, void *owner,
                                              void (*callback)(void *, unsigned, const void *)) {
    ++real_calls;
    // Model the unchanged owner's complete pre-I/O range validation. In
    // particular, a final Expert cannot borrow bytes beyond its source file.
    for (unsigned i = 0; i < count; ++i) {
        assert(sizes[i] == 537600 || sizes[i] == 460800);
        if (addresses[i] != sources[i].data() || sizes[i] > available[i]) return false;
    }
    for (unsigned i = 0; i < count; ++i) callback(owner, i, addresses[i]);
    return true;
}

int main() {
    std::array<const void *, 12> addresses{};
    for (unsigned i = 0; i < 12; ++i) {
        const unsigned role = i % 3;
        actual[i] = role == 2 ? 460800 : role == 1 || IQ2_STREAM_KIND == 2 ? 422400 : 537600;
        sources[i].resize(537600);
        for (std::size_t byte = 0; byte < sources[i].size(); ++byte) sources[i][byte] = (byte * 17 + i * 31) % 251;
        destinations[i].assign(actual[i] + 32, 0xa7);
        addresses[i] = sources[i].data();
        available[i] = sources[i].size();
    }
    unsigned positives = 0, negatives = 0;
    for (unsigned count : {3u, 6u, 9u, 12u}) {
        callbacks = 0;
        const auto before = qwen_iq2_stream_unused_request_bytes();
        assert(__wrap_qwen_app_try_Q2_stream(addresses.data(), actual.data(), count, &callbacks, consume));
        assert(callbacks == count);
        assert(qwen_iq2_stream_unused_request_bytes() - before ==
               std::uint64_t(count / 3) * 115200 * (IQ2_STREAM_KIND == 2 ? 2 : 1));
        ++positives;
    }
    const auto completed = qwen_iq2_stream_unused_request_bytes();
    for (unsigned count : {0u, 1u, 2u, 13u}) {
        const auto calls = real_calls;
        assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(), actual.data(), count, &callbacks, consume));
        assert(real_calls == calls);
        ++negatives;
    }
    for (unsigned index = 0; index < 12; ++index) {
        auto wrong = actual;
        ++wrong[index];
        const auto calls = real_calls;
        assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(), wrong.data(), 12, &callbacks, consume));
        assert(real_calls == calls);
        ++negatives;
    }
    for (unsigned index = 0; index < 12; ++index) {
        if (actual[index] != 422400) continue;
        available[index] = actual[index];
        callbacks = 0;
        assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(), actual.data(), 12, &callbacks, consume));
        assert(callbacks == 0 && qwen_iq2_stream_unused_request_bytes() == completed);
        available[index] = sources[index].size();
        ++negatives;
    }
    assert(!__wrap_qwen_app_try_Q2_stream(nullptr, actual.data(), 12, &callbacks, consume));
    assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(), nullptr, 12, &callbacks, consume));
    assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(), actual.data(), 12, nullptr, consume));
    assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(), actual.data(), 12, &callbacks, nullptr));
    negatives += 4;
    assert(qwen_iq2_stream_unused_request_bytes() == completed);
    std::printf("{\"completed\":true,\"layout\":%d,\"positives\":%u,\"negatives\":%u,\"destination_canaries_exact\":true,\"PS5_operations\":0}\n",
                IQ2_STREAM_KIND, positives, negatives);
}
