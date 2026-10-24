// SPDX-License-Identifier: MIT
#include "direct_integrity.h"
#include "profile_clock.h"
#include "system_memory.h"
#include <array>
#include <cerrno>
#include <cstdlib>
#include <fcntl.h>
#include <ps5platform/heap.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
}
namespace qwen_app {
namespace {
std::array<std::uint64_t,10> identity(int fd) {
    struct stat s{};
    if(fstat(fd,&s))
        throw std::runtime_error("Direct startup integrity fstat failed: errno="+std::to_string(errno));
    // The reviewed FTP publication preserves executable mode 0777. Startup
    // integrity uses the exclusive writer lease, exact full SHA256 and stable
    // descriptor identity; model-source permission admission stays separate.
    if(!S_ISREG(s.st_mode)||s.st_size<=0)
        throw std::runtime_error("Direct startup integrity requires a nonempty regular file: mode="+
            std::to_string(s.st_mode)+" bytes="+std::to_string(s.st_size));
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
        std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
struct NativeDirect final:DirectIntegrityOps {
    int fd;bool control;
    NativeDirect(int value,bool sampled):fd(value),control(sampled){}
    std::int64_t read_at(void * at,std::size_t bytes,std::uint64_t offset)override{
        static_assert(sizeof(off_t)==8,"Direct startup integrity requires native 64-bit offsets");
        (void)qualified_system_headroom(admit_native_system_memory());
        if(control)qwen_native_stage("startup_SELF_read_before_native_call");
        const auto result=pread(fd,at,bytes,static_cast<off_t>(offset));
        if(control)qwen_native_stage("startup_SELF_read_native_call_returned");
        return result;
    }
    std::uint64_t now_ns()override{return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();}
};
}
static void verify_startup_file(const std::string & path,std::uint64_t bytes,const std::string & expected,unsigned seconds,
                               bool direct,bool control) {
    if(expected.size()!=64||expected.find_first_not_of("0123456789abcdef")!=std::string::npos)
        throw std::invalid_argument("A complete original startup SHA256 is required");
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|(direct?O_DIRECT:0));
    if(fd<0)throw std::runtime_error("Direct startup integrity source is unavailable");
    const auto before=identity(fd);
    if(before[5]!=bytes)throw std::runtime_error("Direct startup integrity file size differs");
    void * buffer=nullptr;
    if(posix_memalign(&buffer,direct_integrity_alignment,direct_integrity_window)||!buffer||!ps5_heap_owns(buffer))
        throw std::runtime_error("Direct startup integrity requires its bounded tracked Direct buffer");
    // Keep fd/buffer on failed or unknown work. Only positive full completion,
    // stable identity, exact SHA256 and a returned close permit explicit release.
    NativeDirect ops(fd,control);sha256_t hash;sha256_init(&hash);
    stream_direct_integrity(ops,buffer,bytes,seconds,[&](const unsigned char * at,std::size_t count){sha256_update(&hash,at,count);});
    if(identity(fd)!=before)throw std::runtime_error("Direct startup integrity source changed");
    unsigned char digest[32];sha256_final(&hash,digest);std::string actual;
    for(auto value:digest){actual.push_back("0123456789abcdef"[value>>4]);actual.push_back("0123456789abcdef"[value&15]);}
    if(actual!=expected)throw std::runtime_error("Direct startup integrity SHA256 does not match");
    if(close(fd))throw std::runtime_error("Direct startup integrity close was uncertain");
    free(buffer);
}
void verify_native_startup_file_direct(const std::string & path,std::uint64_t bytes,const std::string & expected,unsigned seconds) {
    verify_startup_file(path,bytes,expected,seconds,true,false);
}
void verify_native_startup_file_control(const std::string & path,std::uint64_t bytes,const std::string & expected,unsigned seconds,bool direct) {
    verify_startup_file(path,bytes,expected,seconds,direct,true);
}
}
