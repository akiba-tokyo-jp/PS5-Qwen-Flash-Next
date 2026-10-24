// SPDX-License-Identifier: MIT
#pragma once
#include <sys/socket.h>
struct in_addr { std::uint32_t s_addr; };
struct sockaddr_in { std::uint8_t sin_len, sin_family; std::uint16_t sin_port; in_addr sin_addr; char sin_zero[8]; };
#define IPPROTO_TCP 6
#define IPPROTO_UDP 17
