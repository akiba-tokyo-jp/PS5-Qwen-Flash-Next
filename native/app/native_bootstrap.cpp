// SPDX-License-Identifier: MIT
// Run before C++ constructors. Only fixed metadata reaches the public journal;
// library callbacks use an owner-only raw-fd file. No model, display or GPU calls.
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstddef>
#include <cstdint>
#include <atomic>
#include <algorithm>
#include <cstring>

extern "C" void qwen_native_set_fault_report(const char *);
extern "C" void qwen_native_set_fault_journal(int);
extern "C" [[noreturn]] void qwen_native_halt(const char *);
extern "C" void qwen_native_stage(const char *);
namespace {
int journal = -1;
int diagnostic = -1;
std::atomic<std::size_t> diagnostic_bytes{0};
[[noreturn]] void stop_bootstrap(const char * reason) {
    if (journal >= 0) {
        (void) write(journal, reason, std::strlen(reason));
        (void) write(journal, "\n", 1); (void) fsync(journal);
    }
    qwen_native_halt(reason);
}
void path_for_pid(char (&path)[160], const char * suffix) {
    static constexpr char prefix[] = "/app0/qwen-runtime/entry-";
    std::memcpy(path, prefix, sizeof(prefix) - 1);
    std::size_t used = sizeof(prefix) - 1;
    unsigned pid = static_cast<unsigned>(getpid());
    char reverse[16]; unsigned count = 0;
    do { reverse[count++] = char('0' + pid % 10); pid /= 10; } while (pid);
    while (count) path[used++] = reverse[--count];
    std::memcpy(path + used, suffix, std::strlen(suffix) + 1);
}
int above_stdio(int descriptor) {
    if (descriptor < 0 || descriptor >= 3) return descriptor;
    const int replacement = fcntl(descriptor, F_DUPFD, 3);
    (void) close(descriptor);
    return replacement;
}
}
extern "C" void qwen_native_bootstrap() {
    if (journal >= 0) stop_bootstrap("bootstrap_reentered");
    char path[160]; path_for_pid(path, ".stages");
    journal = above_stdio(open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0644));
    if (journal < 0) stop_bootstrap("bootstrap_journal_open_failed");
    if (fchmod(journal, 0644)) stop_bootstrap("bootstrap_journal_mode_failed");
    qwen_native_set_fault_journal(journal);
    static constexpr char begin[] = "preinit_entered GPU_not_started=1 model_loaded=0\n";
    if (write(journal, begin, sizeof(begin) - 1) != sizeof(begin) - 1 || fsync(journal)) stop_bootstrap("bootstrap_journal_persist_failed");
    path_for_pid(path, ".fatal"); qwen_native_set_fault_report(path);
    path_for_pid(path, ".private.log");
    qwen_native_stage("before_private_log_open");
    const int log = above_stdio(open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600));
    if (log < 0) stop_bootstrap("bootstrap_private_log_open_failed");
    qwen_native_stage("before_private_log_mode");
    if (fchmod(log, 0600)) stop_bootstrap("bootstrap_private_log_mode_failed");
    // Native dup2 failed during bounded startup qualification. Keep inherited
    // standard descriptors unchanged and give application log callbacks this
    // independently owned descriptor instead.
    diagnostic = log;
    qwen_native_stage("raw_diagnostic_descriptor_ready stdio_unchanged=1");
    qwen_native_stage("bootstrap_completed before_CXX_initializers");
}
extern "C" void qwen_native_log_bytes(const char * text, std::size_t bytes) {
    if (diagnostic < 0 || !text || !bytes) return;
    constexpr std::size_t limit = 8u << 20, chunk = 16u << 10;
    bytes = std::min(bytes, chunk);
    const auto offset = diagnostic_bytes.fetch_add(bytes);
    if (offset >= limit) return;
    bytes = std::min(bytes, limit - offset);
    if (write(diagnostic, text, bytes) != static_cast<ssize_t>(bytes)) stop_bootstrap("private_diagnostic_write_failed");
}
namespace {
// The pinned CRT explicitly invokes the kept preinit array before init_array.
using Initializer = void (*)();
__attribute__((used, section(".preinit_array"))) Initializer early = qwen_native_bootstrap;
}
extern "C" void qwen_native_stage(const char * stage) {
    if (journal < 0) stop_bootstrap("bootstrap_stage_without_journal");
    const std::size_t bytes = std::strlen(stage);
    if (write(journal, stage, bytes) != static_cast<ssize_t>(bytes) || write(journal, "\n", 1) != 1 || fsync(journal)) stop_bootstrap("bootstrap_stage_persist_failed");
}
extern "C" void qwen_native_trace_initializer(std::size_t index, std::uintptr_t address, bool completed) {
    char line[96];
    const char * prefix = completed ? "initializer_return index=0x" : "initializer_enter index=0x";
    std::size_t used = std::strlen(prefix); std::memcpy(line, prefix, used);
    auto hex = [&](std::uintptr_t value) {
        for (unsigned shift = sizeof(value) * 8; shift;) {
            shift -= 4; line[used++] = "0123456789abcdef"[(value >> shift) & 15];
        }
    };
    hex(index); static constexpr char middle[] = " address=0x";
    std::memcpy(line + used, middle, sizeof(middle) - 1); used += sizeof(middle) - 1;
    hex(address); line[used] = 0; qwen_native_stage(line);
}
