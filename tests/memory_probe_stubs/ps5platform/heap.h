// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
struct ps5_heap_stats {
    std::size_t mapped_bytes,peak_bytes;unsigned segments;
    unsigned long long libc_fallbacks;
    std::uintptr_t range_base;std::size_t range_bytes;
};
void ps5_heap_stats(struct ps5_heap_stats *);
void * ps5_heap_memalign(std::size_t,std::size_t);
void ps5_heap_free(void *);
