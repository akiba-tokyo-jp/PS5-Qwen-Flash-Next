// SPDX-License-Identifier: MIT
// Host test declarations only; no target implementation or GPU access.
#pragma once
#include <cstddef>
#include <cstdint>
extern "C" {
std::int64_t sceKernelGetDirectMemorySize();
int sceKernelAllocateDirectMemory(std::int64_t, std::int64_t, std::size_t, std::size_t, int, std::int64_t *);
int sceKernelMapDirectMemory(void **, std::size_t, int, int, std::int64_t, std::size_t);
}
