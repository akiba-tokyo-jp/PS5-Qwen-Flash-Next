// SPDX-License-Identifier: MIT
// This local service uses numeric IPv4 TCP endpoints only. The SDK's resolver
// placeholder returns EAI_FAIL even for loopback; do not depend on DNS or a
// separately initialized network module to bind the passive native monitor.
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <cstdlib>
#include <cstring>
#include <cstdio>

namespace {
struct Result { addrinfo info; sockaddr_in address; char canonical[16]; };
bool parse_ipv4(const char * text, unsigned char bytes[4]) {
    if (!text || !*text) return false;
    for (int index = 0; index < 4; ++index) {
        unsigned value = 0, digits = 0;
        while (*text >= '0' && *text <= '9') {
            value = value * 10 + unsigned(*text++ - '0');
            if (++digits > 3 || value > 255) return false;
        }
        if (!digits) return false;
        bytes[index] = static_cast<unsigned char>(value);
        if (index < 3) { if (*text++ != '.') return false; }
        else if (*text) return false;
    }
    return true;
}
bool parse_port(const char * text, unsigned & port) {
    port = 0;
    if (!text) return true;
    if (!*text) return false;
    unsigned digits = 0;
    while (*text) {
        if (*text < '0' || *text > '9' || ++digits > 5) return false;
        port = port * 10 + unsigned(*text++ - '0');
        if (port > 65535) return false;
    }
    return true;
}
}

extern "C" int qwen_native_getaddrinfo(const char * node, const char * service,
                                       const addrinfo * hints, addrinfo ** output) {
    if (!output) return EAI_FAIL;
    *output = nullptr;
    if (!node && !service) return EAI_NONAME;
    const int flags = hints ? hints->ai_flags : 0;
    if (flags & ~(AI_PASSIVE | AI_CANONNAME | AI_NUMERICHOST | AI_NUMERICSERV | AI_ADDRCONFIG)) return EAI_BADFLAGS;
    if (hints && hints->ai_family != AF_UNSPEC && hints->ai_family != AF_INET) return EAI_FAMILY;
    if (hints && hints->ai_socktype && hints->ai_socktype != SOCK_STREAM) return EAI_SOCKTYPE;
    if (hints && hints->ai_protocol && hints->ai_protocol != IPPROTO_TCP) return EAI_SERVICE;
    unsigned char address[4] = {127, 0, 0, 1};
    if (node) { if (!parse_ipv4(node, address)) return EAI_NONAME; }
    else if (flags & AI_PASSIVE) std::memset(address, 0, sizeof(address));
    unsigned port = 0;
    if (!parse_port(service, port)) return EAI_SERVICE;
    auto * result = static_cast<Result *>(std::calloc(1, sizeof(Result)));
    if (!result) return EAI_MEMORY;
    auto & info = result->info;
    auto & socket = result->address;
    socket.sin_len = sizeof(socket); socket.sin_family = AF_INET;
    std::memcpy(&socket.sin_addr, address, 4);
    auto * port_bytes = reinterpret_cast<unsigned char *>(&socket.sin_port);
    port_bytes[0] = static_cast<unsigned char>(port >> 8); port_bytes[1] = static_cast<unsigned char>(port);
    info.ai_flags = flags; info.ai_family = AF_INET; info.ai_socktype = SOCK_STREAM; info.ai_protocol = IPPROTO_TCP;
    info.ai_addrlen = sizeof(socket); info.ai_addr = reinterpret_cast<sockaddr *>(&socket);
    if (flags & AI_CANONNAME) {
        std::snprintf(result->canonical, sizeof(result->canonical), "%u.%u.%u.%u", address[0], address[1], address[2], address[3]);
        info.ai_canonname = result->canonical;
    }
    *output = &info;
    return 0;
}

extern "C" void qwen_native_freeaddrinfo(addrinfo * info) { std::free(info); }

extern "C" int qwen_native_getnameinfo(const sockaddr * address, socklen_t length,
                                       char * host, socklen_t host_size, char * service, socklen_t service_size, int flags) {
    if (flags & ~(NI_NUMERICHOST | NI_NUMERICSERV)) return EAI_BADFLAGS;
    if (!address || length < sizeof(sockaddr_in) || address->sa_family != AF_INET) return EAI_FAMILY;
    const auto * socket = reinterpret_cast<const sockaddr_in *>(address);
    const auto * bytes = reinterpret_cast<const unsigned char *>(&socket->sin_addr);
    const auto * port_bytes = reinterpret_cast<const unsigned char *>(&socket->sin_port);
    char host_text[16], service_text[6];
    const int host_length = std::snprintf(host_text, sizeof(host_text), "%u.%u.%u.%u", bytes[0], bytes[1], bytes[2], bytes[3]);
    const int service_length = std::snprintf(service_text, sizeof(service_text), "%u", (unsigned(port_bytes[0]) << 8) | port_bytes[1]);
    if ((host && host_size <= static_cast<unsigned>(host_length)) ||
        (service && service_size <= static_cast<unsigned>(service_length))) return EAI_OVERFLOW;
    if (host) std::memcpy(host, host_text, host_length + 1);
    if (service) std::memcpy(service, service_text, service_length + 1);
    return 0;
}
