// SPDX-License-Identifier: MIT
#include "shader_file_native.h"
#include "profile_clock.h"
#include "system_memory.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdexcept>
extern "C" void qwen_native_stage(const char*);
namespace qwen_app {
namespace {
class NativeShaderFileOps final:public ShaderFileOps {
    int descriptor_=-1;
    bool attempted_=false;
public:
    void open(const std::string &path) {
        if(attempted_)throw std::runtime_error("External shader descriptor cannot reopen or retry");
        attempted_=true;
        descriptor_=::open(path.c_str(),O_RDONLY|O_DIRECT|O_NOFOLLOW);
        if(descriptor_<0)throw std::runtime_error("The exact external shader resource is unavailable");
    }
    std::array<std::uint64_t,10> identity()override {
        struct stat s{};
        if(fstat(descriptor_,&s)||!S_ISREG(s.st_mode)||s.st_size<=0)
            throw std::runtime_error("External shader storage requires stable regular-file metadata");
        return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),
            std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
            std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
    }
    void system_headroom(bool startup)override {
        if(startup)(void)admit_native_system_memory();
        else(void)qualified_system_headroom(observe_native_system_memory());
    }
    std::uint64_t now_ns()override{return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();}
    void before_read()override{qwen_native_stage("shader_asset_read_before_native_call");}
    std::int64_t read_at(void*at,std::size_t bytes,std::uint64_t offset)override {
        static_assert(sizeof(off_t)==8,"External shader storage requires native 64-bit offsets");
        return pread(descriptor_,at,bytes,static_cast<off_t>(offset));
    }
    void read_returned()override{qwen_native_stage("shader_asset_read_native_call_returned");}
};
}
ShaderFileOps &open_native_shader_file(const std::string &path) {
    // Neither the descriptor nor its backing is released after uncertainty.
    // Ordinary OS close owns final retirement of these static input resources.
    static NativeShaderFileOps ops;ops.open(path);return ops;
}
}
