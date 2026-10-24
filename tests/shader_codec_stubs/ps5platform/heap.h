// SPDX-License-Identifier: MIT
// Host-only ABI surface. The actual PS5 provider is compiled separately.
#pragma once
#include <cstddef>
#include <cstdint>
extern "C" {
struct ps5_heap_stats {
    std::uintptr_t range_base;std::size_t range_bytes,mapped_bytes,peak_bytes;
    unsigned segments;unsigned long long libc_fallbacks;unsigned arenas;
};
void ps5_heap_stats(struct ps5_heap_stats *);
void *ps5_heap_memalign(std::size_t,std::size_t);
void *ps5_heap_calloc(std::size_t,std::size_t);
void ps5_heap_free(void *);
bool ps5_heap_owns(const void *);
}
