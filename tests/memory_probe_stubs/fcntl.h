// SPDX-License-Identifier: MIT
#pragma once
#define O_RDONLY 0
#define O_DIRECT 0x10000
#define O_NOFOLLOW 0x100
#define open memory_probe_test_open
int memory_probe_test_open(const char *,int);
