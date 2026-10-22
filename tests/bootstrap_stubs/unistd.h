// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
using ssize_t = std::intptr_t;
extern "C" int getpid();
extern "C" ssize_t write(int, const void *, std::size_t);
extern "C" int close(int);
extern "C" int fsync(int);
extern "C" int dup2(int, int);
extern "C" int usleep(unsigned);
