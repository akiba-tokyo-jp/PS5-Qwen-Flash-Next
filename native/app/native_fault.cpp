// SPDX-License-Identifier: MIT
// A fatal backend abort retains the process/resource graph for ordinary OS
// title close. This is not recovery, a retry, or a resource release.
#include <atomic>
#include <fcntl.h>
#include <cstring>
#include <unistd.h>
namespace { std::atomic<bool> fatal{false}; char report_path[1100] = {}; }
extern "C" bool qwen_native_faulted() { return fatal.load(); }
extern "C" void qwen_native_mark_fault() { fatal = true; }
// Set once on the startup thread, before display/backend workers exist.
extern "C" void qwen_native_set_fault_report(const char * path) {
    if (path && std::strlen(path) < sizeof(report_path)) std::strcpy(report_path, path);
}
extern "C" [[noreturn]] void qwen_native_halt(const char * operation) {
    fatal = true;
    static constexpr char message[] = "Native operation failed; resources retained for ordinary OS close\n";
    (void) write(2, message, sizeof(message) - 1);
    if (report_path[0]) {
        const int fd = open(report_path, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd >= 0) {
            static constexpr char prefix[] = "{\"schema\":\"ps5-qwen-native-fatal-v1\",\"backing_retained\":true,\"operation\":\"";
            (void) write(fd, prefix, sizeof(prefix) - 1);
            // Operation names are fixed application literals, never user data.
            (void) write(fd, operation, std::strlen(operation));
            (void) write(fd, "\"}\n", 3); (void) fsync(fd); (void) close(fd);
        }
    }
    for (;;) (void) usleep(1000000);
}
extern "C" [[noreturn]] void __wrap_abort() { qwen_native_halt("backend_abort"); }
// The pinned demo documents that exit is unsafe in this title launch context.
// Override the CRT's weak hook so every main return is retained for OS close.
extern "C" [[noreturn]] void catchReturnFromMain(int) { qwen_native_halt("native_main_returned"); }
