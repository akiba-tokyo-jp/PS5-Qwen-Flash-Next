// SPDX-License-Identifier: MIT
#pragma once
#define O_WRONLY 1
#define O_CREAT 0x200
#define O_EXCL 0x800
#define O_NOFOLLOW 0x100
#define F_DUPFD 0
extern "C" int open(const char *, int, ...);
extern "C" int fcntl(int, int, ...);
