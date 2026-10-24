// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
struct probe_timestamp {std::int64_t tv_sec;long tv_nsec;};
struct stat {
    std::uint64_t st_dev,st_ino;std::int64_t st_size;
    unsigned st_mode,st_uid,st_gid;
    probe_timestamp st_mtim,st_ctim;
};
#define S_ISREG(mode) (((mode)&0170000)==0100000)
#define fstat memory_probe_test_fstat
int memory_probe_test_fstat(int,struct stat *);
