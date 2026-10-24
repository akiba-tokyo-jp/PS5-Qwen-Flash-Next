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
#include <sys/types.h>
#include <sys/sysctl.h>
#include <time.h>
#include "stage_memory_probe.h"

extern "C" void qwen_native_set_fault_report(const char *);
extern "C" void qwen_native_set_fault_journal(int);
extern "C" [[noreturn]] void qwen_native_halt(const char *);
extern "C" void qwen_native_stage(const char *);
namespace {
int journal = -1;
int diagnostic = -1;
std::atomic<std::size_t> diagnostic_bytes{0};
std::atomic<std::size_t> stage_bytes{0};
std::atomic<bool> probe_enabled{false},probe_fault{false};
std::atomic<std::size_t> probe_count{0},probe_active{0};
qwen_app::StageMemorySample probe_samples[qwen_app::stage_memory_probe_capacity]{};
bool probe_observation(std::uint32_t & free_pages,std::uint64_t & ns) {
    struct {std::uint64_t first;std::uint32_t value;std::uint64_t last;} value{0x725b725b725b725bull,0,0x725b725b725b725bull};
    std::size_t bytes=4;struct timespec now{};
    if(sysctlbyname("vm.stats.vm0.v_free_count",&value.value,&bytes,nullptr,0)||bytes!=4||
       value.first!=0x725b725b725b725bull||value.last!=0x725b725b725b725bull||
       clock_gettime(CLOCK_MONOTONIC,&now)||now.tv_sec<0||now.tv_nsec<0||now.tv_nsec>=1000000000)return false;
    free_pages=value.value;ns=std::uint64_t(now.tv_sec)*1000000000ull+std::uint64_t(now.tv_nsec);return ns!=0;
}
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
    // Retain a fixed failure record before the journal can grow without bound.
    // Never start an unrecordable backend operation or delete prior evidence.
    if (bytes > 1024 || stage_bytes.fetch_add(bytes + 1) > (8u << 20) - 1025)
        stop_bootstrap("bootstrap_stage_capacity_exhausted");
    qwen_app::StageMemorySample * sample=nullptr;
    bool before_valid=false,recording=false;
    if(probe_enabled.load(std::memory_order_acquire)) {
        recording=true;
        probe_active.fetch_add(1);
        const auto index=probe_count.fetch_add(1);
        if(index<qwen_app::stage_memory_probe_capacity) {
            sample=&probe_samples[index];
            const auto kept=std::min(bytes,sizeof(sample->phase)-1);
            std::memcpy(sample->phase,stage,kept);sample->phase[kept]=0;
            before_valid=probe_observation(sample->free_before,sample->before_ns);
        } else probe_fault.store(true);
    }
    if (write(journal, stage, bytes) != static_cast<ssize_t>(bytes) || write(journal, "\n", 1) != 1 || fsync(journal)) stop_bootstrap("bootstrap_stage_persist_failed");
    if(sample) {
        sample->valid=probe_observation(sample->free_after,sample->after_ns)&&before_valid&&sample->after_ns>=sample->before_ns;
        if(!sample->valid)probe_fault.store(true);
    }
    if(recording)probe_active.fetch_sub(1);
}
namespace qwen_app {
bool begin_native_stage_memory_probe() {
    if(probe_count.load()||probe_fault.load()||probe_active.load()||probe_enabled.exchange(true))return false;
    return true;
}
bool end_native_stage_memory_probe() {
    return probe_enabled.exchange(false)&&!probe_active.load()&&!probe_fault.load()&&
        probe_count.load()>0&&probe_count.load()<=stage_memory_probe_capacity;
}
std::size_t native_stage_memory_probe_count(){return std::min(probe_count.load(),stage_memory_probe_capacity);}
const StageMemorySample * native_stage_memory_probe_sample(std::size_t index) {
    return !probe_enabled.load()&&!probe_active.load()&&index<native_stage_memory_probe_count()?&probe_samples[index]:nullptr;
}
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
