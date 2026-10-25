// SPDX-License-Identifier: MIT
#include "direct_bmp_native.h"
extern "C" {
#include "hash/sha256/sha256.h"
}
#include "frame_output_context.h"
extern "C" int frame_probe_stage(const char *);
extern "C" int frame_probe_guard();
namespace {
void stage(const char *text){if(!frame_probe_stage(text))throw std::runtime_error("Frame fixture journal refused");}
void guard(){if(!frame_probe_guard())throw std::runtime_error("Frame fixture original memory predicate refused");}
struct Source {
    void copy_row(unsigned y,std::size_t at,unsigned char *out,std::size_t bytes){
        if(y>=qwen_app::frame_height||at+bytes>qwen_app::frame_row_bytes)throw std::runtime_error("Frame fixture row bounds refused");
        for(std::size_t i=0;i<bytes;++i)out[i]=static_cast<unsigned char>(((at+i)/4+13*y+((at+i)%4)*37)%251);
    }
};
bool same(const struct stat &a,const struct stat &b){
    return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid&&
        a.st_gid==b.st_gid&&a.st_size==b.st_size&&a.st_mtim.tv_sec==b.st_mtim.tv_sec&&
        a.st_mtim.tv_nsec==b.st_mtim.tv_nsec&&a.st_ctim.tv_sec==b.st_ctim.tv_sec&&a.st_ctim.tv_nsec==b.st_ctim.tv_nsec;
}
}
extern "C" int frame_probe_write(const char *path,void *window,int direct){
    try {Source source;qwen_app::NativeFrameSink sink(path,direct!=0,stage,guard);
        qwen_app::stream_direct_bmp(source,sink,window);return 1;}
    catch(...){return 0;}
}
extern "C" int frame_probe_verify(const char *path,void *window){
    try {
        guard();stage("frame_verify_open_before_native_call");const int fd=open(path,O_RDONLY|O_DIRECT|O_NOFOLLOW);
        stage("frame_verify_open_native_call_returned");if(fd<0)return 0;
        struct stat before{},named{},after{};if(fstat(fd,&before)||lstat(path,&named)||!same(before,named)||
            !S_ISREG(before.st_mode)||before.st_uid!=geteuid()||before.st_nlink!=1||before.st_size!=qwen_app::frame_bmp_bytes)return 0;
        sha256_t hash;sha256_init(&hash);
        for(std::uint64_t offset=0;offset<qwen_app::frame_bmp_bytes;){
            guard();const auto logical=std::size_t(std::min<std::uint64_t>(qwen_app::frame_write_window,qwen_app::frame_bmp_bytes-offset));
            const auto requested=(logical+16383)&~std::size_t(16383);
            stage("frame_verify_read_before_native_call");const auto got=pread(fd,window,requested,offset);
            stage("frame_verify_read_native_call_returned");if(got!=std::int64_t(logical))return 0;
            sha256_update(&hash,static_cast<const unsigned char*>(window),logical);offset+=logical;
        }
        stage("frame_verify_EOF_before_native_call");const auto eof=pread(fd,window,16384,(qwen_app::frame_bmp_bytes+16383)&~std::uint64_t(16383));
        stage("frame_verify_EOF_native_call_returned");if(eof!=0)return 0;
        unsigned char digest[32];sha256_final(&hash,digest);if(std::memcmp(digest,frame_expected_sha256,32))return 0;
        if(fstat(fd,&after)||!same(before,after)||lstat(path,&named)||!same(after,named))return 0;
        stage("frame_verify_close_before_native_call");const int closed=close(fd);
        stage("frame_verify_close_native_call_returned");return closed==0;
    }catch(...){return 0;}
}
