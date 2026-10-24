// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
using socklen_t = std::uint32_t;
struct sockaddr { std::uint8_t sa_len, sa_family; char sa_data[14]; };
#define AF_UNSPEC 0
#define AF_INET 2
#define AF_INET6 28
#define SOCK_STREAM 1
#define SOCK_DGRAM 2
