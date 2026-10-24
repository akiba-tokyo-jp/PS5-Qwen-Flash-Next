// SPDX-License-Identifier: MIT
// Exercise the actual resolver with the native sockaddr layout, without DNS.
#include <netdb.h>
#include <netinet/in.h>
#include <cstring>
#include <iostream>
#include <stdexcept>
extern "C" int qwen_native_getaddrinfo(const char *, const char *, const addrinfo *, addrinfo **);
extern "C" void qwen_native_freeaddrinfo(addrinfo *);
extern "C" int qwen_native_getnameinfo(const sockaddr *, socklen_t, char *, socklen_t, char *, socklen_t, int);
static void check(bool value) { if (!value) throw std::runtime_error("Numeric address contract failed"); }
int main() {
    try {
        static_assert(sizeof(sockaddr_in) == 16);
        addrinfo hints{}; hints.ai_family = AF_UNSPEC; hints.ai_socktype = SOCK_STREAM;
        hints.ai_flags = AI_NUMERICHOST | AI_NUMERICSERV | AI_CANONNAME;
        addrinfo * result = nullptr;
        check(qwen_native_getaddrinfo("127.0.0.1", "8086", &hints, &result) == 0 && result && !result->ai_next);
        const unsigned char expected[16] = {16, AF_INET, 0x1f, 0x96, 127, 0, 0, 1};
        check(result->ai_family == AF_INET && result->ai_socktype == SOCK_STREAM && result->ai_protocol == IPPROTO_TCP);
        check(result->ai_addrlen == 16 && std::memcmp(result->ai_addr, expected, 16) == 0);
        check(std::strcmp(result->ai_canonname, "127.0.0.1") == 0);
        char host[16] = {}, port[6] = {};
        check(qwen_native_getnameinfo(result->ai_addr, 16, host, sizeof(host), port, sizeof(port), NI_NUMERICHOST | NI_NUMERICSERV) == 0);
        check(std::strcmp(host, "127.0.0.1") == 0 && std::strcmp(port, "8086") == 0);
        check(qwen_native_getnameinfo(result->ai_addr, 15, host, 16, port, 6, 0) == EAI_FAMILY);
        std::strcpy(host, "unchanged");
        check(qwen_native_getnameinfo(result->ai_addr, 16, host, 9, port, 6, 0) == EAI_OVERFLOW && std::strcmp(host, "unchanged") == 0);
        qwen_native_freeaddrinfo(result);
        for (const char * bad : {"localhost", "::1", "127.0.0", "127.0.0.1.", "256.0.0.1", "1..2.3", "", "1.1.1.1234"})
            check(qwen_native_getaddrinfo(bad, "8086", &hints, &result) == EAI_NONAME && !result);
        for (const char * bad : {"http", "65536", "-1", "12x", "", "99999999999999999"})
            check(qwen_native_getaddrinfo("127.0.0.1", bad, &hints, &result) == EAI_SERVICE && !result);
        hints.ai_family = AF_INET6;
        check(qwen_native_getaddrinfo("127.0.0.1", "0", &hints, &result) == EAI_FAMILY && !result);
        hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM;
        check(qwen_native_getaddrinfo("127.0.0.1", "0", &hints, &result) == EAI_SOCKTYPE && !result);
        hints.ai_socktype = SOCK_STREAM; hints.ai_flags = AI_PASSIVE;
        check(qwen_native_getaddrinfo(nullptr, "65535", &hints, &result) == 0);
        const unsigned char passive[8] = {16, AF_INET, 255, 255, 0, 0, 0, 0};
        check(std::memcmp(result->ai_addr, passive, 8) == 0); qwen_native_freeaddrinfo(result);
        check(qwen_native_getaddrinfo(nullptr, nullptr, nullptr, &result) == EAI_NONAME && !result);
        qwen_native_freeaddrinfo(nullptr);
        std::cout << "Native loopback wire layout, numeric roundtrip, bounded errors and DNS rejection passed\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
