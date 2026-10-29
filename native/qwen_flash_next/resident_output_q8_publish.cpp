// SPDX-License-Identifier: MIT
// CPU-only publication of three new, exact owned files. No original is moved.
#include "resident_output_Q8_publish_plan.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <sys/mount.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();std::uint64_t split_now_ns();
}
namespace {
using Key=std::array<std::uint64_t,10>;constexpr std::size_t window_bytes=8u<<20;
void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN owned_CPU_resources_retained=1 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Q8 publication journal failed");}
Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
Key named(const char*p,bool directory=false){struct stat s{};need(!lstat(p,&s)&&(directory?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Q8 owned path identity failed");return key(s);}
Key descriptor(int fd){struct stat s{};need(fd>=0&&!fstat(fd,&s)&&S_ISREG(s.st_mode),"Q8 owned descriptor identity failed");return key(s);}
void close_fd(int&fd){if(fd>=0){const int old=fd;fd=-1;if(close(old))retain();}}
std::string digest(sha256_t&h){unsigned char raw[32];sha256_final(&h,raw);std::string s;for(auto b:raw){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
void emit(const std::string&label,const Key&k){std::string s=label;for(auto v:k)s+=" "+std::to_string(v);line(s);}
}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;void*window=nullptr;std::int64_t physical=-1;int fd=-1;const auto begun=split_now_ns();
 try{
    line("BEGIN nonce=" OUTPUT_Q8_PUBLISH_NONCE " CPU_only=1 GPU_calls=0 title_launches=0 original_source_writes=0");
    need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2)&&split_headroom(),"Current idle owner or CPU memory refused");
    struct statfs capacity{};
    need(!statfs(output_Q8_files[0].source,&capacity)&&capacity.f_bavail>0&&
        std::uint64_t(capacity.f_bavail)*capacity.f_bsize>=(256ull<<20),"New output assets cannot retain four bounded application-file transfers");
    struct stat absent{};errno=0;need(lstat(output_Q8_directory,&absent)&&errno==ENOENT,"Fresh Q8 directory required");
    for(const auto&v:output_Q8_files){const auto s=named(v.source);need(!s[3]&&!s[4]&&s[5]==v.bytes,"Owned uploaded Q8 file differs");}
    need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Q8 bounded CPU Direct allocation failed");
    if(sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384)||!window||std::uintptr_t(window)%16384)retain();mapped=true;
    need(!mkdir(output_Q8_directory,0755),"Exclusive new Q8 directory creation failed");const auto root=named(output_Q8_directory,true);
    need(root[2]==0040755&&!root[3]&&!root[4],"New Q8 directory owner or mode differs");sha256_t whole;sha256_init(&whole);
    for(unsigned i=0;i<3;++i){const auto&v=output_Q8_files[i];need(split_context(3)&&split_headroom(),"Q8 current CPU owner changed");
        errno=0;need(lstat(v.destination,&absent)&&errno==ENOENT,"Q8 publication may not overwrite an existing file");
        fd=open(v.source,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Q8 uploaded Direct descriptor failed");
        need(!fchmod(fd,0644)&&!fsync(fd),"Own Q8 file mode/durability finalization failed");const auto before=descriptor(fd);
        need(before==named(v.source)&&before[2]==0100644&&!before[3]&&!before[4]&&before[5]==v.bytes,"Q8 uploaded stable source differs");
        sha256_t hash;sha256_init(&hash);
        for(std::uint64_t at=0;at<v.bytes;){need(split_headroom()&&split_now_ns()-begun<300000000000ull,"Q8 CPU deadline or memory refused");
            const auto n=std::size_t(std::min<std::uint64_t>(window_bytes,v.bytes-at));const auto count=(n+16383)&~std::size_t(16383);
            line("BEFORE Q8_Direct_read file="+std::to_string(i)+" offset="+std::to_string(at));const auto got=pread(fd,window,count,at);
            line("RETURN Q8_Direct_read file="+std::to_string(i)+" bytes="+std::to_string(got));
            need(got==std::int64_t(n)&&descriptor(fd)==before,"Q8 Direct bytes or identity incomplete");
            sha256_update(&hash,static_cast<unsigned char*>(window),n);if(i<2)sha256_update(&whole,static_cast<unsigned char*>(window),n);at+=n;
        }
        need(pread(fd,window,16384,(v.bytes+16383)&~std::uint64_t(16383))==0&&digest(hash)==v.sha256&&descriptor(fd)==before&&named(v.source)==before,"Q8 complete SHA256/EOF or stable identity differs");
        close_fd(fd);line("BEFORE own_Q8_rename file="+std::to_string(i));
        need(!rename(v.source,v.destination),"Own Q8 publication rename failed");const auto final=named(v.destination);
        need(std::equal(before.begin(),before.begin()+8,final.begin()),"Q8 published inode, mode, owner or payload changed");
        emit("SEALED_FILE index="+std::to_string(i),final);
    }
    need(digest(whole)==output_Q8_GGUF_SHA256,"Q8 complete concatenated GGUF SHA256 differs");
    line("WHOLE_Q8_GGUF SHA256="+std::string(output_Q8_GGUF_SHA256)+" bytes=675430560");
    const auto final_root=named(output_Q8_directory,true);need(std::equal(root.begin(),root.begin()+5,final_root.begin()),"New Q8 directory ownership changed");emit("SEALED_DIRECTORY",final_root);
    need(split_context(5)&&split_headroom(),"Final Q8 owner or memory refused");ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" own_partial_files_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
 close_fd(fd);if(mapped){if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();line("DIRECT known_completion_cleanup_returned=1 fully_released=1");}else if(physical>=0)retain();
 line("END success="+std::to_string(ok)+" nonce=" OUTPUT_Q8_PUBLISH_NONCE " active_calls=0 original_source_writes=0 GPU_calls=0 title_launches=0 retry=0");if(!split_close_journal())return 2;return ok?0:1;
}
