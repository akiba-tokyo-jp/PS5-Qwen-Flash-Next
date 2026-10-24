// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
std::int64_t sceKernelGetDirectMemorySize();
int sceKernelAvailableDirectMemorySize(std::int64_t,std::int64_t,std::size_t,std::int64_t *,std::size_t *);
int sceKernelAvailableFlexibleMemorySize(std::size_t *);
int sceKernelReserveVirtualRange(void **,std::size_t,int,std::size_t);
int sceKernelQueryMemoryProtection(void *,void **,void **,std::uint32_t *);
int sceKernelMunmap(void *,std::size_t);
