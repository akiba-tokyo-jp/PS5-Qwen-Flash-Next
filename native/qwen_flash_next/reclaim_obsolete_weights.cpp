// SPDX-License-Identifier: MIT
// Retire only explicitly authorized obsolete Q4 parts outside both live maps.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <stdexcept>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <ps5platform/kernel.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_open_journal();int split_context(unsigned);int split_headroom();
int split_report_line(const char*);int split_close_journal();std::uint64_t split_now_ns();
}
#include "obsolete-weight-plan.private.h"
using Key=std::array<std::uint64_t,10>;
static void*window;static int fd=-1;static std::uint64_t begun;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable journal failure");}
[[noreturn]]static void retain(){split_report_line("UNCERTAIN CPU_resources_retained=1 retry=0");for(;;)sleep(1);}
static Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
    std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),
    std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
static Key named(const char*p){struct stat s{};need(!lstat(p,&s),"Named identity unavailable");return key(s);}
static void boundary(){need(split_headroom()&&split_now_ns()-begun<300000000000ull,"Original CPU reserve or finite deadline refused");}
static void intact(const Key*obsolete=nullptr){
    for(const auto&p:protected_files){const auto actual=named(p.path);need(actual==p.identity,"Current or immediate source identity changed");
        if(obsolete)need(actual[0]!=(*obsolete)[0]||actual[1]!=(*obsolete)[1],"Obsolete target aliases a protected source");}
    boundary();
}
static void close_fd(){if(fd>=0){int old=fd;fd=-1;if(close(old))retain();}}
static Key hash_file(const char*p,std::uint64_t bytes,const char*expected,bool obsolete){
    boundary();fd=open(p,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Owned Direct input required");
    struct stat before{},after{};need(!fstat(fd,&before)&&S_ISREG(before.st_mode)&&std::uint64_t(before.st_size)==bytes&&key(before)==named(p),"Input identity differs");
    if(obsolete)need(before.st_nlink==1&&!before.st_uid&&!before.st_gid,"Unaliased root-owned obsolete output required");
    const auto identity=key(before);sha256_t hash;sha256_init(&hash);
    for(std::uint64_t at=0;at<bytes;){boundary();const auto n=std::size_t(std::min<std::uint64_t>(8u<<20,bytes-at));
        line("READ_BEFORE obsolete="+std::to_string(obsolete)+" offset="+std::to_string(at));
        const auto got=pread(fd,window,(n+16383)&~std::size_t(16383),at);line("READ_RETURN bytes="+std::to_string(got));
        need(got==std::int64_t(n)&&!fstat(fd,&after)&&key(after)==identity,"Complete Direct read failed");
        sha256_update(&hash,static_cast<unsigned char*>(window),n);at+=n;
    }
    unsigned char digest[32];sha256_final(&hash,digest);std::string hex;
    for(auto b:digest){hex+="0123456789abcdef"[b>>4];hex+="0123456789abcdef"[b&15];}
    need(pread(fd,window,16384,(bytes+16383)&~std::uint64_t(16383))==0&&!fstat(fd,&after)&&key(after)==identity&&named(p)==identity&&hex==expected,
         "Whole original SHA256, EOF or stable input differs");
    close_fd();return identity;
}
static std::uint64_t available(){struct statfs s{};need(!statfs("/data/ai",&s)&&s.f_bsize>0&&s.f_bavail>=0,"Filesystem capacity unavailable");return std::uint64_t(s.f_bavail)*s.f_bsize;}
static void vm(const char*phase){
    std::string text=std::string("VM phase=")+phase;
    for(const char*field:{"free","inactive","active","wire"}){
        const auto name=std::string("vm.stats.vm0.v_")+field+"_count";
        std::uint64_t value=0;std::size_t size=sizeof(value);
        need(!sysctlbyname(name.c_str(),&value,&size,nullptr,0)&&(size==4||size==8),"Fresh existing VM counter unavailable");
        text+=" "+std::string(field)+"="+std::to_string(value);
    }
    line(text);
}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;unsigned retired=0;std::int64_t physical=-1;begun=split_now_ns();
    try{
        need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2),"Current CPU owner refused");intact();
        const auto directory=named(obsolete_directory);need((directory[2]&0170000)==0040000,"Exact obsolete directory required");
        need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),8u<<20,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU Direct allocation failed");
        if(sceKernelMapDirectMemory(&window,8u<<20,3,0,physical,16384)||!window)retain();mapped=true;
        hash_file(control_path,control_bytes,control_hash,false);
        std::array<Key,obsolete_count>verified{};
        // Complete every original hash before retiring any obsolete payload.
        for(unsigned i=0;i<obsolete_count;++i){const auto&t=obsolete_files[i];
            verified[i]=hash_file(t.path,t.bytes,t.sha256,true);need(verified[i]==t.identity,"Original obsolete-part identity changed");intact(&verified[i]);
            line("OBSOLETE_VERIFIED index="+std::to_string(i)+" bytes="+std::to_string(t.bytes));}
        const auto before=available();vm("before_retirement");
        for(unsigned i=0;i<obsolete_count;++i){boundary();const auto&t=obsolete_files[i];intact(&verified[i]);
            fd=open(t.path,O_WRONLY|O_NOFOLLOW);need(fd>=0,"Owned obsolete output cannot be opened");struct stat s{};
            need(!fstat(fd,&s)&&key(s)==verified[i]&&s.st_nlink==1&&named(t.path)==verified[i],"Obsolete target changed before retirement");
            line("BEFORE_TRUNCATE index="+std::to_string(i)+" exact_original_SHA256_passed=1 outside_current_and_immediate_maps=1 original_BF16_and_recipe_retained=1");
            const int rc=ftruncate(fd,0);line("RETURN_TRUNCATE index="+std::to_string(i)+" rc="+std::to_string(rc));
            need(!rc&&!fsync(fd)&&!fstat(fd,&s)&&s.st_size==0&&s.st_dev==dev_t(verified[i][0])&&s.st_ino==ino_t(verified[i][1]),"Obsolete retirement did not complete");
            close_fd();++retired;
        }
        intact();need(named(obsolete_directory)==directory,"Model-directory identity changed");
        hash_file(control_path,control_bytes,control_hash,false);const auto after=available();need(after>before,"Available capacity did not increase");
        line("CAPACITY before="+std::to_string(before)+" after="+std::to_string(after));vm("after_retirement");
        need(split_context(5),"Final CPU owner changed");ok=true;
    }catch(const std::exception&e){line(std::string("REFUSED reason=")+e.what()+" retired="+std::to_string(retired));}
    close_fd();if(mapped){if(sceKernelMunmap(window,8u<<20)||sceKernelReleaseDirectMemory(physical,8u<<20))retain();line("DIRECT positively_released=1");}
    else if(physical>=0)retain();
    line("END success="+std::to_string(ok)+" obsolete_Q4_parts_retired="+std::to_string(retired)+" active_or_immediate_source_writes=0 GPU_calls=0 title_launches=0 retry=0");
    return split_close_journal()?(ok?0:1):2;
}
