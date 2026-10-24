// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
extern "C" std::int32_t sceKernelMprotect(const void *, std::size_t, int);
