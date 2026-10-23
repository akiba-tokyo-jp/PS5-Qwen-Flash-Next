// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#define RLIMIT_DATA 2
#define RLIMIT_AS 10
using rlim_t=std::uint64_t;
struct rlimit {rlim_t rlim_cur,rlim_max;};
extern "C" int getrlimit(int,struct rlimit *);
