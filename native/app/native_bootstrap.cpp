// SPDX-License-Identifier: MIT
// Run before C++ constructors. Only fixed metadata reaches the public journal;
// stdout/stderr use a separate owner-only file. No model, display or GPU calls.
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstddef>
#include <cstring>

extern "C" void qwen_native_set_fault_report(const char *);
namespace {
int journal = -1;
[[noreturn]] void stop_bootstrap() {
    static constexpr char message[] = "Native bootstrap failed; no GPU work started; ordinary OS close required\n";
    (void) write(2, message, sizeof(message) - 1);
    for (;;) (void) usleep(1000000);
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
void bootstrap() {
    char path[160]; path_for_pid(path, ".stages");
    journal = above_stdio(open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0644));
    if (journal < 0 || fchmod(journal, 0644)) stop_bootstrap();
    static constexpr char begin[] = "preinit_entered GPU_not_started=1 model_loaded=0\n";
    if (write(journal, begin, sizeof(begin) - 1) != sizeof(begin) - 1 || fsync(journal)) stop_bootstrap();
    path_for_pid(path, ".fatal"); qwen_native_set_fault_report(path);
    path_for_pid(path, ".private.log");
    const int log = above_stdio(open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600));
    if (log < 0 || fchmod(log, 0600)) stop_bootstrap();
    if (dup2(log, 1) < 0 || dup2(log, 2) < 0) stop_bootstrap();
    if (log != 1 && log != 2) (void) close(log);
}
// The pinned CRT explicitly invokes the kept preinit array before init_array.
using Initializer = void (*)();
__attribute__((used, section(".preinit_array"))) Initializer early = bootstrap;
}
extern "C" void qwen_native_stage(const char * stage) {
    if (journal < 0) stop_bootstrap();
    const std::size_t bytes = std::strlen(stage);
    if (write(journal, stage, bytes) != static_cast<ssize_t>(bytes) || write(journal, "\n", 1) != 1 || fsync(journal)) stop_bootstrap();
}
