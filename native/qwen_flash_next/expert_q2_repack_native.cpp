// SPDX-License-Identifier: MIT
// CPU-only conversion of current immutable Gate/Up Q2_K payloads to Q2_0.
#include <algorithm>
#include <array>
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
int split_open_journal();int split_context(unsigned);int split_headroom();
int split_report_line(const char*);int split_close_journal();std::uint64_t split_now_ns();
int qwen_repack_q2k_q20(const std::uint8_t*,std::uint8_t*,std::size_t);
}
#include "expert-repack-plan.private.h"
using Key=std::array<std::uint64_t,10>;
static unsigned char*window;static int input_fd=-1,output_fd=-1;static std::uint64_t begun;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable CPU journal failed");}
[[noreturn]]static void retain(){split_report_line("UNCERTAIN CPU_resources_retained=1 retry=0");for(;;)sleep(1);}
static Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
    std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),
    std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
static Key named(const char*p){struct stat s{};need(!lstat(p,&s),"Named identity unavailable");return key(s);}
static void boundary(){need(split_headroom()&&split_now_ns()-begun<3600000000000ull,"Original CPU reserve or finite conversion deadline refused");}
static void intact(){for(const auto&p:protected_files)need(named(p.path)==p.identity,"Current or immediate source identity changed");boundary();}
static void close_owned(int&fd){if(fd>=0){int old=fd;fd=-1;if(close(old))retain();}}
static std::string digest(sha256_t&hash){unsigned char bytes[32];sha256_final(&hash,bytes);std::string s;
    for(auto b:bytes){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
static void sealed(const std::string&tag,const Key&k){std::string s=tag;for(auto v:k)s+=" "+std::to_string(v);line(s);}
static Key hash_file(const char*path,std::uint64_t bytes,const std::string&expected){
    boundary();input_fd=open(path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input_fd>=0&&(fcntl(input_fd,F_GETFL)&O_DIRECT),"Owned Direct hash input required");
    struct stat st{},after{};need(!fstat(input_fd,&st)&&S_ISREG(st.st_mode)&&std::uint64_t(st.st_size)==bytes&&key(st)==named(path),"Hash source identity differs");
    const auto original=key(st);sha256_t hash;sha256_init(&hash);
    for(std::uint64_t at=0;at<bytes;){boundary();const auto n=std::size_t(std::min<std::uint64_t>(8u<<20,bytes-at));
        const auto got=pread(input_fd,window,(n+16383)&~std::size_t(16383),at);
        need(got==std::int64_t(n)&&!fstat(input_fd,&after)&&key(after)==original,"Complete Direct hash read failed");
        sha256_update(&hash,window,n);at+=n;
    }
    need(pread(input_fd,window,16384,(bytes+16383)&~std::uint64_t(16383))==0&&!fstat(input_fd,&after)&&key(after)==original&&named(path)==original,
         "Hash source EOF or identity changed");
    need(digest(hash)==expected,"Complete stored payload SHA256 differs");close_owned(input_fd);return original;
}
static void read_expert(const RepackTensor&t,std::uint64_t offset,sha256_t&hash){
    constexpr std::size_t bytes=537600;std::size_t copied=0;
    for(unsigned s=0;s<t.slices;++s){const auto&r=t.source[s];
        const auto lo=std::max(offset,r.logical),hi=std::min(offset+bytes,r.logical+r.bytes);if(lo>=hi)continue;
        need(lo==offset+copied,"Current tensor source has a gap");boundary();
        input_fd=open(r.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input_fd>=0&&(fcntl(input_fd,F_GETFL)&O_DIRECT),"Current Q2_K Direct input unavailable");
        struct stat st{};need(!fstat(input_fd,&st)&&key(st)==r.identity&&named(r.path)==r.identity,"Current Q2_K source changed");
        const auto physical=r.offset+lo-r.logical,skip=physical%16384,aligned=physical-skip;
        const auto n=hi-lo,request=(skip+n+16383)&~std::uint64_t(16383);
        need(request<=2u<<20&&aligned<r.identity[5],"Current Q2_K read exceeds its bounded arena");
        const auto expected=std::min(request,r.identity[5]-aligned);
        const auto got=pread(input_fd,window,std::size_t(request),aligned);
        need(got==std::int64_t(expected)&&expected>=skip+n&&!fstat(input_fd,&st)&&key(st)==r.identity&&named(r.path)==r.identity,
             "Current Q2_K read was incomplete or changed");
        std::memcpy(window+(2u<<20)+copied,window+skip,std::size_t(n));copied+=n;close_owned(input_fd);
    }
    need(copied==bytes,"Complete current Q2_K Expert input required");sha256_update(&hash,window+(2u<<20),bytes);
}
struct Output {
    std::uint64_t written=0;std::size_t used=0;sha256_t hash{};
    Output(){sha256_init(&hash);}
    void flush(){if(!used)return;boundary();need(used%16384==0,"Output write lost Direct alignment");
        const auto got=pwrite(output_fd,window+(4u<<20),used,written);need(got==std::int64_t(used),"New Q2_0 output write failed; no retry");
        written+=used;used=0;
    }
    void put(const unsigned char*p,std::size_t n){sha256_update(&hash,p,n);
        while(n){const auto take=std::min<std::size_t>((2u<<20)-used,n);std::memcpy(window+(4u<<20)+used,p,take);
            used+=take;p+=take;n-=take;if(used==(2u<<20))flush();}
    }
};
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;unsigned converted=0;std::int64_t physical=-1;begun=split_now_ns();
    try{
        need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2),"Current CPU owner refused");intact();
        struct statfs capacity{};need(!statfs("/data/ai",&capacity)&&capacity.f_bsize>0&&capacity.f_bavail>=0&&
            std::uint64_t(capacity.f_bavail)*capacity.f_bsize>=96ull*235929600+(256u<<20),"New Q2_0 payloads cannot preserve transfer storage");
        struct stat absent{};errno=0;need(lstat(repack_root,&absent)&&errno==ENOENT,"Fresh isolated output directory required");
        need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),8u<<20,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU Direct allocation failed");
        if(sceKernelMapDirectMemory(reinterpret_cast<void**>(&window),8u<<20,3,0,physical,16384)||!window)retain();mapped=true;
        hash_file(control_path,control_bytes,control_hash);need(!mkdir(repack_root,0755),"Exclusive isolated output directory creation failed");
        for(unsigned i=0;i<96;++i){const auto&t=repack_tensors[i];boundary();line("TENSOR_BEGIN index="+std::to_string(i)+" name="+t.name);
            output_fd=open(t.output,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);need(output_fd>=0,"Exclusive new Q2_0 output required");
            sha256_t input;sha256_init(&input);Output output;
            for(unsigned expert=0;expert<512;++expert){
                if(expert%16==0)line("EXPERT_GROUP_BEGIN tensor="+std::to_string(i)+" expert="+std::to_string(expert));
                read_expert(t,std::uint64_t(expert)*537600,input);
                need(qwen_repack_q2k_q20(window+(2u<<20),window+(3u<<20),6400)==0,"Finite pinned Q2_K to Q2_0 conversion refused");
                output.put(window+(3u<<20),460800);
                if(expert%16==15)line("EXPERT_GROUP_COMPLETE tensor="+std::to_string(i)+" expert="+std::to_string(expert));
            }
            output.flush();need(output.written==235929600&&digest(input)==t.input_sha256,"Complete current Q2_K tensor SHA256 differs");
            need(!fsync(output_fd)&&!fchmod(output_fd,0644),"New output finalization failed");close_owned(output_fd);
            const auto sha=digest(output.hash);const auto identity=hash_file(t.output,235929600,sha);++converted;
            line("TENSOR_COMPLETE index="+std::to_string(i)+" input_SHA256="+t.input_sha256+" output_SHA256="+sha+" bytes=235929600");
            sealed("SEALED_PART index="+std::to_string(i),identity);
        }
        intact();hash_file(control_path,control_bytes,control_hash);sealed("SEALED_DIRECTORY",named(repack_root));
        need(split_context(5),"Final CPU owner changed");ok=true;
    }catch(const std::exception&e){line(std::string("REFUSED reason=")+e.what()+" converted="+std::to_string(converted));}
    close_owned(input_fd);close_owned(output_fd);
    if(mapped){if(sceKernelMunmap(window,8u<<20)||sceKernelReleaseDirectMemory(physical,8u<<20))retain();line("DIRECT positively_released=1");}
    else if(physical>=0)retain();
    line("END success="+std::to_string(ok)+" Gate_Up_tensors="+std::to_string(converted)+" current_sources_unchanged=1 GPU_calls=0 title_launches=0 retry=0");
    return split_close_journal()?(ok?0:1):2;
}
