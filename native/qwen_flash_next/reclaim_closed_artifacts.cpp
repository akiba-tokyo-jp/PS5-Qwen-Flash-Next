// SPDX-License-Identifier: MIT
// Remove only fully archived diagnostic outputs and a proven unused bundle.
#include <array>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <cerrno>
#include <string>
#include <stdexcept>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <unistd.h>
#include <ps5platform/kernel.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_open_journal();int split_context(unsigned);int split_headroom();int split_report_line(const char*);int split_close_journal();std::uint64_t split_now_ns();
}
#include "closed-artifact-plan.private.h"
using Key=std::array<std::uint64_t,10>;
static void*window;static int fd=-1;static std::uint64_t begun;
static void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
static void line(const std::string&s){need(split_report_line(s.c_str()),"Durable archive-retirement journal failed");}
[[noreturn]]static void retain(){split_report_line("UNCERTAIN CPU_owners_retained=1 retry=0");for(;;)sleep(1);}
static Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
static Key named(const char*p){struct stat s{};need(!lstat(p,&s),"Named original unavailable");return key(s);}
static void boundary(){need(split_headroom()&&split_now_ns()-begun<300000000000ull,"Original CPU reserve or finite deadline refused");}
static void intact(){for(const auto&p:protected_files)need(named(p.path)==p.identity,"Current or immediate model source changed");boundary();}
static void close_fd(){if(fd>=0){int old=fd;fd=-1;if(close(old))retain();}}
static Key hash_file(const char*path,std::uint64_t bytes,const char*expected,bool target,const Closed*seal=nullptr){
    boundary();fd=open(path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Immutable Direct archive source unavailable");struct stat st{};need(!fstat(fd,&st)&&S_ISREG(st.st_mode)&&std::uint64_t(st.st_size)==bytes&&named(path)==key(st),"Exact regular original size/identity required");
    const auto before=key(st);if(target){need(seal&&st.st_nlink==1&&unsigned(st.st_uid)==seal->uid&&unsigned(st.st_gid)==seal->gid&&unsigned(st.st_mode)==seal->mode&&unsigned(st.st_flags)==seal->flags,"Exact observed unaliased diagnostic owner required");for(const auto&p:protected_files)need(before[0]!=p.identity[0]||before[1]!=p.identity[1],"Target aliases a protected model source");}
    sha256_t h;sha256_init(&h);for(std::uint64_t at=0;at<bytes;){boundary();const auto n=std::min<std::uint64_t>(8u<<20,bytes-at);need(pread(fd,window,(n+16383)&~std::uint64_t(16383),at)==std::int64_t(n),"Whole archived original read failed");sha256_update(&h,static_cast<unsigned char*>(window),n);at+=n;}
    unsigned char digest[32];sha256_final(&h,digest);std::string hex;for(auto b:digest){hex+="0123456789abcdef"[b>>4];hex+="0123456789abcdef"[b&15];}
    need(hex==expected&&!fstat(fd,&st)&&key(st)==before&&named(path)==before&&pread(fd,window,16384,(bytes+16383)&~std::uint64_t(16383))==0,"Complete archive SHA256, stable identity or EOF differs");close_fd();return before;
}
static std::uint64_t available(){struct statfs s{};need(!statfs("/data/ai",&s)&&s.f_bavail>=0,"Fresh filesystem capacity unavailable");return std::uint64_t(s.f_bavail)*s.f_bsize;}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;unsigned retired=0;std::int64_t physical=-1;begun=split_now_ns();
    try{
        need((argc==0||argc==1)&&split_context(1)&&split_context(2),"Exact inactive CPU context required");intact();
        need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),8u<<20,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU window unavailable");
        need(!sceKernelMapDirectMemory(&window,8u<<20,3,0,physical,16384)&&window&&window!=reinterpret_cast<void*>(~std::uintptr_t(0)),"CPU mapping uncertain");mapped=true;
        hash_file(control_path,control_bytes,control_hash,false);const auto before=available();std::array<Key,closed_count>admitted{};
        for(unsigned i=0;i<closed_count;++i){const auto&t=closed_files[i];admitted[i]=hash_file(t.path,t.bytes,t.sha256,true,&t);line("ARCHIVE_VERIFIED index="+std::to_string(i)+" bytes="+std::to_string(t.bytes));}
        intact();
        for(unsigned i=0;i<closed_count;++i){boundary();const auto&t=closed_files[i];need(named(t.path)==admitted[i],"Archived target changed before removal");line("BEFORE_UNLINK index="+std::to_string(i)+" complete_host_archive_and_native_SHA256_passed=1");const int rc=unlink(t.path),error=errno;line("RETURN_UNLINK index="+std::to_string(i)+" rc="+std::to_string(rc)+" errno="+std::to_string(error));if(!rc)++retired;}
        intact();hash_file(control_path,control_bytes,control_hash,false);const auto after=available();line("CAPACITY before="+std::to_string(before)+" after="+std::to_string(after));need(split_context(5),"Final CPU context changed");ok=retired==closed_count;
    }catch(const std::exception&e){line(std::string("REFUSED reason=")+e.what()+" retired="+std::to_string(retired));}
    close_fd();if(mapped){if(sceKernelMunmap(window,8u<<20)||sceKernelReleaseDirectMemory(physical,8u<<20))retain();line("DIRECT positively_released=1");}else if(physical>=0)retain();
    line("END success="+std::to_string(ok)+" closed_artifacts_retired="+std::to_string(retired)+" model_source_writes=0 GPU_calls=0 title_launches=0 automatic_retries=0");return split_close_journal()?(ok?0:1):2;
}
