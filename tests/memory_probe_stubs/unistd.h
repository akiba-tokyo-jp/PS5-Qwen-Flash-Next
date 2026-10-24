// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
using ssize_t=std::ptrdiff_t;
#define close memory_probe_test_close
#define pread memory_probe_test_pread
int memory_probe_test_close(int);
ssize_t memory_probe_test_pread(int,void *,std::size_t,std::int64_t);
