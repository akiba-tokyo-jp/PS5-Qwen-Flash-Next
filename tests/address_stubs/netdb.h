// SPDX-License-Identifier: MIT
#pragma once
#include <sys/socket.h>
struct addrinfo { int ai_flags, ai_family, ai_socktype, ai_protocol; socklen_t ai_addrlen;
                  char * ai_canonname; sockaddr * ai_addr; addrinfo * ai_next; };
#define AI_PASSIVE 1
#define AI_CANONNAME 2
#define AI_NUMERICHOST 4
#define AI_NUMERICSERV 8
#define AI_ADDRCONFIG 0x400
#define NI_NUMERICHOST 2
#define NI_NUMERICSERV 8
#define EAI_BADFLAGS 3
#define EAI_FAIL 4
#define EAI_FAMILY 5
#define EAI_MEMORY 6
#define EAI_NONAME 8
#define EAI_SERVICE 9
#define EAI_SOCKTYPE 10
#define EAI_OVERFLOW 14
