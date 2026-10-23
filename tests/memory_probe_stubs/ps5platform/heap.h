// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
struct ps5_heap_stats {
    std::size_t mapped_bytes,peak_bytes;unsigned segments;
    unsigned long long libc_fallbacks;
};
void ps5_heap_stats(struct ps5_heap_stats *);
void * ps5_heap_memalign(std::size_t,std::size_t);
void ps5_heap_free(void *);
