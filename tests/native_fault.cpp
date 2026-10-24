// SPDX-License-Identifier: MIT
// A native fault must persist its fixed metadata without inherited stdio and
// retain control rather than unwinding or releasing uncertain resources.
#include <unistd.h>
#include <fcntl.h>
#include <cstdarg>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
extern "C" bool qwen_native_faulted();
extern "C" void qwen_native_set_fault_journal(int);
extern "C" void qwen_native_set_fault_report(const char *);
extern "C" [[noreturn]] void qwen_native_halt(const char *);
namespace {
std::string journal, report; bool synced_journal = false, synced_report = false, closed_report = false;
struct Retained {};
void check(bool condition) { if (!condition) throw std::runtime_error("Native fault metadata contract failed"); }
}
extern "C" int open(const char * path, int flags, ...) {
    va_list args; va_start(args, flags); int mode = va_arg(args, int); va_end(args);
    check(synced_journal && std::strcmp(path, "/fixture.fatal") == 0 && mode == 0644);
    check(flags == (O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW)); return 4;
}
extern "C" int fchmod(int descriptor, unsigned mode) { check(descriptor == 4 && mode == 0644); return 0; }
extern "C" ssize_t write(int descriptor, const void * data, std::size_t bytes) {
    check(descriptor == 3 || descriptor == 4);
    (descriptor == 3 ? journal : report).append(static_cast<const char *>(data), bytes); return bytes;
}
extern "C" int fsync(int descriptor) {
    check(descriptor == 3 || descriptor == 4); (descriptor == 3 ? synced_journal : synced_report) = true; return 0;
}
extern "C" int close(int descriptor) { check(descriptor == 4 && synced_report); closed_report = true; return 0; }
extern "C" int usleep(unsigned duration) { check(duration == 1000000 && closed_report); throw Retained{}; }
int main() {
    try {
        check(!qwen_native_faulted()); qwen_native_set_fault_journal(3); qwen_native_set_fault_report("/fixture.fatal");
        try { qwen_native_halt("fixture_failed_wait"); } catch (const Retained &) {}
        check(qwen_native_faulted() && journal == "fatal_operation=fixture_failed_wait\n");
        check(report == "{\"schema\":\"ps5-qwen-native-fatal-v1\",\"backing_retained\":true,\"operation\":\"fixture_failed_wait\"}\n");
        std::cout << "Fault latched, journal persisted before report, stdio unused and resources retained; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
