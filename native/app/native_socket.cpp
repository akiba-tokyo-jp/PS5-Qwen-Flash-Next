// SPDX-License-Identifier: MIT
// The native SDK has accept/fcntl but no accept4 import. This process never
// forks or execs; descriptor flags are set before exposing an accepted socket.
#include <cerrno>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>

// The native HTTP translation unit explicitly selects this application-only
// accept path. This static title never forks or execs, so close-on-exec flags
// have no effect on its descriptor lifetime. Nonblocking requests are rejected.
// The separate accept4 implementation below retains its full flag contract.
extern "C" int qwen_native_accept_http(int listener, sockaddr * address, socklen_t * length, int flags) {
    if (flags & ~SOCK_CLOEXEC) { errno = EINVAL; return -1; }
    return accept(listener, address, length);
}

extern "C" int accept4(int listener, sockaddr * address, socklen_t * length, int flags) {
    if (flags & ~(SOCK_CLOEXEC | SOCK_NONBLOCK)) { errno = EINVAL; return -1; }
    const int socket = accept(listener, address, length);
    if (socket < 0) return socket;
    const int descriptor_flags = flags & SOCK_CLOEXEC ? fcntl(socket, F_GETFD) : 0;
    const int status_flags = flags & SOCK_NONBLOCK ? fcntl(socket, F_GETFL) : 0;
    if (descriptor_flags < 0 || status_flags < 0 ||
        ((flags & SOCK_CLOEXEC) && fcntl(socket, F_SETFD, descriptor_flags | FD_CLOEXEC) < 0) ||
        ((flags & SOCK_NONBLOCK) && fcntl(socket, F_SETFL, status_flags | O_NONBLOCK) < 0)) {
        const int error = errno;
        close(socket); errno = error; return -1;
    }
    return socket;
}
