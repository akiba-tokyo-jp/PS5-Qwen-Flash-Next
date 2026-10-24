// SPDX-License-Identifier: MIT
// Minimal host-test declarations; not a target SDK header.
#pragma once
using socklen_t = unsigned;
struct sockaddr {};
#define SOCK_CLOEXEC 0x100
#define SOCK_NONBLOCK 0x200
extern "C" int accept(int, sockaddr *, socklen_t *);
extern "C" int accept4(int, sockaddr *, socklen_t *, int);
