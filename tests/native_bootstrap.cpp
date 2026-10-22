// SPDX-License-Identifier: MIT
// Run the actual early bootstrap against native-fd API stubs. In particular,
// absent standard descriptors must never make redirection overwrite the journal.
#include <unistd.h>
#include <fcntl.h>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
extern "C" void qwen_native_bootstrap();
extern "C" void qwen_native_stage(const char *);
extern "C" void qwen_native_trace_initializer(std::size_t, std::uintptr_t, bool);
extern "C" void qwen_native_log_bytes(const char *, std::size_t);
namespace {
int opens = 0, mode_calls = 0, duplication_calls = 0, failure = 0;
std::string journal, diagnostic, reason, fatal_path;
std::vector<int> closed;
struct Halt {};
void check(bool value) { if (!value) throw std::runtime_error("Native bootstrap contract failed"); }
}
extern "C" int getpid() { return 901; }
extern "C" int open(const char * path, int flags, ...) {
    va_list args; va_start(args, flags); auto mode = va_arg(args, int); va_end(args);
    check(flags == (O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW));
    check(std::string(path) == std::string("/app0/qwen-runtime/entry-901") + (opens ? ".private.log" : ".stages"));
    check(mode == (opens ? 0600 : 0644));
    if (opens++ && failure == 2) return -1;
    return opens - 1;
}
extern "C" int fcntl(int descriptor, int operation, ...) {
    va_list args; va_start(args, operation); int minimum = va_arg(args, int); va_end(args);
    check(operation == F_DUPFD && minimum == 3 && (descriptor == 0 || descriptor == 1));
    return descriptor == 0 ? 3 : 4;
}
extern "C" int close(int descriptor) { check(descriptor != 3); closed.push_back(descriptor); return 0; }
extern "C" int fchmod(int descriptor, unsigned mode) {
    check((descriptor == 3 && mode == 0644) || (descriptor == 4 && mode == 0600));
    ++mode_calls; return failure == 1 && mode_calls == 2 ? -1 : 0;
}
extern "C" ssize_t write(int descriptor, const void * data, std::size_t bytes) {
    check(descriptor == 3 || descriptor == 4);
    if (descriptor == 4 && failure == 3) return -1;
    (descriptor == 3 ? journal : diagnostic).append(static_cast<const char *>(data), bytes); return static_cast<ssize_t>(bytes);
}
extern "C" int fsync(int descriptor) { check(descriptor == 3); return 0; }
extern "C" int dup2(int descriptor, int target) {
    (void) descriptor; (void) target; ++duplication_calls;
    throw std::runtime_error("Native bootstrap must never replace a standard descriptor");
}
extern "C" void qwen_native_set_fault_report(const char * path) { fatal_path = path; }
extern "C" void qwen_native_set_fault_journal(int descriptor) { check(descriptor == 3); }
extern "C" [[noreturn]] void qwen_native_halt(const char * operation) { reason = operation; throw Halt{}; }
int main(int argc, char ** argv) {
    try {
        check(argc == 2); failure = std::atoi(argv[1]); check(failure >= 0 && failure <= 3);
        try { qwen_native_bootstrap(); } catch (const Halt &) {}
        check(fatal_path == "/app0/qwen-runtime/entry-901.fatal");
        if (failure == 1 || failure == 2) {
            const char * expected[] = {"", "bootstrap_private_log_mode_failed", "bootstrap_private_log_open_failed"};
            check(reason == expected[failure] && journal.find(reason) != std::string::npos);
            check(journal.find("bootstrap_completed") == std::string::npos);
        } else if (failure == 3) {
            try { qwen_native_log_bytes("abc", 3); } catch (const Halt &) {}
            check(reason == "private_diagnostic_write_failed" && diagnostic.empty());
        } else {
            check(reason.empty() && opens == 2 && closed == std::vector<int>({0,1}));
            check(journal.find("bootstrap_completed before_CXX_initializers") != std::string::npos);
            qwen_native_log_bytes("abc", 3); check(diagnostic == "abc");
            const std::string large(32768, 'x'); qwen_native_log_bytes(large.data(), large.size());
            check(diagnostic.size() == 3 + 16384);
            qwen_native_stage("main_fixture");
            qwen_native_trace_initializer(2, 0x1234, false); qwen_native_trace_initializer(2, 0x1234, true);
            check(journal.find("initializer_enter index=0x0000000000000002 address=0x0000000000001234\n") != std::string::npos);
            check(journal.find("initializer_return index=0x0000000000000002 address=0x0000000000001234\n") != std::string::npos);
            try { qwen_native_bootstrap(); } catch (const Halt &) {}
            check(opens == 2 && reason == "bootstrap_reentered");
        }
        check(duplication_calls == 0);
        std::cout << "Early journal isolation, bounded raw diagnostics, unchanged stdio and fixed failure classification passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
