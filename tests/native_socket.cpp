// SPDX-License-Identifier: MIT
// Execute the real adapter against API stubs, never native sockets.
#include <sys/socket.h>
#include <fcntl.h>
#include <cstdarg>
#include <cerrno>
#include <iostream>
#include <stdexcept>
extern "C" int qwen_native_accept_http(int, sockaddr *, socklen_t *, int);

static int accepted = 9, accepts = 0, closes = 0, calls = 0, fail = 0, descriptor = 32, status = 64;
static void check(bool value) { if (!value) throw std::runtime_error("Socket adapter contract failed"); }
extern "C" int accept(int listener, sockaddr * address, socklen_t * length) {
    check(listener == 7 && !address && !length); ++accepts; return accepted;
}
extern "C" int close(int socket) { check(socket == 9); ++closes; errno = EIO; return 0; }
extern "C" int fcntl(int socket, int operation, ...) {
    check(socket == 9); ++calls;
    if (operation == fail) { errno = EACCES; return -1; }
    if (operation == F_GETFD) return descriptor;
    if (operation == F_GETFL) return status;
    va_list args; va_start(args, operation); int value = va_arg(args, int); va_end(args);
    if (operation == F_SETFD) descriptor = value;
    else if (operation == F_SETFL) status = value;
    else check(false);
    return 0;
}
int main() {
    try {
        check(accept4(7, nullptr, nullptr, 0x400) == -1 && errno == EINVAL && accepts == 0);
        check(accept4(7, nullptr, nullptr, SOCK_CLOEXEC | SOCK_NONBLOCK) == 9);
        check(descriptor == (32 | FD_CLOEXEC) && status == (64 | O_NONBLOCK) && calls == 4 && closes == 0);
        for (int operation : {F_GETFD, F_GETFL, F_SETFD, F_SETFL}) {
            fail = operation;
            check(accept4(7, nullptr, nullptr, SOCK_CLOEXEC | SOCK_NONBLOCK) == -1 && errno == EACCES);
        }
        check(closes == 4); fail = 0;
        calls = 0; check(accept4(7, nullptr, nullptr, 0) == 9 && calls == 0);
        accepted = -1; errno = EAGAIN;
        check(accept4(7, nullptr, nullptr, SOCK_CLOEXEC) == -1 && errno == EAGAIN && closes == 4);
        accepted = 9; calls = 0;
        const auto before = accepts;
        check(qwen_native_accept_http(7, nullptr, nullptr, SOCK_NONBLOCK) == -1 && errno == EINVAL && accepts == before);
        check(qwen_native_accept_http(7, nullptr, nullptr, SOCK_CLOEXEC) == 9 && accepts == before + 1 && calls == 0 && closes == 4);
        accepted = -1; errno = EAGAIN;
        check(qwen_native_accept_http(7, nullptr, nullptr, SOCK_CLOEXEC) == -1 && errno == EAGAIN && calls == 0 && closes == 4);
        std::cout << "Strict accept4 flags/cleanup and plain HTTP acceptance without subprocesses passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
