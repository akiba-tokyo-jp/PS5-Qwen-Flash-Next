// SPDX-License-Identifier: MIT
#pragma once
#define F_GETFD 1
#define F_SETFD 2
#define F_GETFL 3
#define F_SETFL 4
#define FD_CLOEXEC 8
#define O_NONBLOCK 16
extern "C" int fcntl(int, int, ...);
