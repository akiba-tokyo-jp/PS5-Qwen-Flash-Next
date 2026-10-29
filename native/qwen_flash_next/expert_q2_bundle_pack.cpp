// SPDX-License-Identifier: MIT
// CPU-only immutable partial bundle pack; original payloads remain unchanged.
#include "expert_q2_bundle_probe_plan.h"
#include "expert_q2_bundle_layout.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();uint64_t split_now_ns();
}
namespace {
using L=qwen_app::ExpertQ2BundleLayout;using Key=std::array<uint64_t,10>;
constexpr size_t owned_bytes=8u<<20;uint64_t begun=0;unsigned char *scratch,*bundle,*readback;
void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_owners_retained=1 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable CPU journal failed");}
Key key(const struct stat&s){return{uint64_t(s.st_dev),uint64_t(s.st_ino),uint64_t(s.st_mode),uint64_t(s.st_uid),uint64_t(s.st_gid),uint64_t(s.st_size),uint64_t(s.st_mtim.tv_sec),uint64_t(s.st_mtim.tv_nsec),uint64_t(s.st_ctim.tv_sec),uint64_t(s.st_ctim.tv_nsec)};}
Key path_key(const char*p){struct stat s{};need(!lstat(p,&s)&&S_ISREG(s.st_mode),"Sealed regular source missing");return key(s);}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode),"Regular descriptor required");return key(s);}
void close_fd(int&fd){if(fd>=0){const int old=fd;fd=-1;if(close(old))retain();}}
void boundary(){const auto now=split_now_ns();need(now>=begun&&now-begun<300000000000ull&&split_headroom(),"CPU deadline or memory boundary refused");}
std::string hex(sha256_t&h){unsigned char d[32];sha256_final(&h,d);std::string s;for(auto v:d){s+="0123456789abcdef"[v>>4];s+="0123456789abcdef"[v&15];}return s;}
std::string digest(const void*p,size_t n){sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char*>(p),n);return hex(h);}
void sources(){for(const auto&p:bundle_probe_sources)need(path_key(p.path)==p.identity,"Immutable Q2 physical source changed");}
void read_source(const BundleProbeSpan&s,unsigned char*destination){
    const auto&p=bundle_probe_sources[s.source];int fd=open(p.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);
    need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&fd_key(fd)==p.identity,"Exact Direct Q2 source required");
    const auto aligned=s.offset&~uint64_t(16383);const auto skip=size_t(s.offset-aligned);
    const auto count=size_t((skip+s.bytes+16383)&~uint64_t(16383));
    need(count<=(2u<<20)&&aligned<p.identity[5]&&s.offset<=p.identity[5]&&s.bytes<=p.identity[5]-s.offset,"Q2 source span exceeds its bound");
    const auto got=pread(fd,scratch,count,aligned);const auto expected=std::min<uint64_t>(count,p.identity[5]-aligned);
    const bool valid=got==ssize_t(expected)&&expected>=skip+s.bytes&&fd_key(fd)==p.identity&&path_key(p.path)==p.identity;
    if(valid)memcpy(destination,scratch+skip,s.bytes);close_fd(fd);need(valid,"Q2 source read/identity differs");
}
}
int main(int argc,char**){if(!split_open_journal())return 2;begun=split_now_ns();bool ok=false,mapped=false;void*owned=nullptr;int64_t physical=-1;int output=-1,input=-1;
 try{
    line("BEGIN nonce=" BUNDLE_PROBE_NONCE " CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0 window_bytes=8388608");
    need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2),"Fresh idle CPU bundle comparison required");boundary();sources();
    struct statfs capacity{};need(!statfs(bundle_probe_parent,&capacity)&&capacity.f_bavail>0&&uint64_t(capacity.f_bavail)*capacity.f_bsize>=bundle_probe_file_bytes+65536,"New bounded bundle output exceeds available disk");
    line("CAPACITY available_bytes="+std::to_string(uint64_t(capacity.f_bavail)*capacity.f_bsize)+" output_bytes="+std::to_string(bundle_probe_file_bytes));
    need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),owned_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU Direct allocation failed");
    if(sceKernelMapDirectMemory(&owned,owned_bytes,3,0,physical,16384)||!owned||uintptr_t(owned)%16384)retain();mapped=true;
    scratch=static_cast<unsigned char*>(owned);bundle=scratch+(2u<<20);readback=scratch+(4u<<20);
    output=open(bundle_probe_path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);need(output>=0&&(fcntl(output,F_GETFL)&O_DIRECT),"Fresh exclusive bundle output required");
    std::array<std::string,BUNDLE_PROBE_COUNT> expected{};
    for(unsigned i=0;i<BUNDLE_PROBE_COUNT;++i){boundary();need(split_context(3),"Idle CPU owner changed");memset(bundle,0,L::stride);
        const auto&v=bundle_probe_experts[i];for(unsigned j=0;j<v.spans;++j){const auto&s=bundle_probe_spans[v.first_span+j];read_source(s,bundle+s.destination);}
        expected[i]=digest(bundle,L::stride);need(pwrite(output,bundle,L::stride,uint64_t(i)*L::stride)==ssize_t(L::stride),"Dense bundle write was short");
        line("BUNDLE index="+std::to_string(i)+" layer="+std::to_string(v.layer)+" Expert="+std::to_string(v.expert)+" SHA256="+expected[i]);
    }
    const auto payload=BUNDLE_PROBE_COUNT*L::stride;const auto tail=size_t(bundle_probe_file_bytes-payload);memset(bundle,0,65536);
    if(tail)need(pwrite(output,bundle,tail,payload)==ssize_t(tail),"Dense final padding write failed");
    need(!fsync(output)&&!fchmod(output,0444)&&!fsync(output),"Owned bundle fsync/seal failed");close_fd(output);
    input=open(bundle_probe_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input>=0&&(fcntl(input,F_GETFL)&O_DIRECT),"Sealed bundle Direct readback required");
    const auto sealed=fd_key(input);need(sealed==path_key(bundle_probe_path)&&sealed[5]==bundle_probe_file_bytes,"Bundle published identity differs");
    sha256_t whole;sha256_init(&whole);
    for(unsigned i=0;i<BUNDLE_PROBE_COUNT;++i){boundary();need(pread(input,readback,L::stride,uint64_t(i)*L::stride)==ssize_t(L::stride)&&digest(readback,L::stride)==expected[i],"Complete bundle SHA256 readback differs");sha256_update(&whole,readback,L::stride);}
    need(pread(input,readback,16384,bundle_probe_file_bytes)==0,"Bundle EOF differs");
    if(tail){need(pread(input,readback,16384,payload)==ssize_t(tail),"Whole bundle tail read was short");sha256_update(&whole,readback,tail);}
    need(fd_key(input)==sealed&&path_key(bundle_probe_path)==sealed,"Bundle seal identity changed");
    std::string identity;for(auto v:sealed){if(!identity.empty())identity+=",";identity+=std::to_string(v);}
    line("SEALED bytes="+std::to_string(bundle_probe_file_bytes)+" SHA256="+hex(whole)+" identity="+identity+" mode=0444 original_sources_preserved=1");
    sources();close_fd(input);ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" new_output_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
 close_fd(output);close_fd(input);
 if(mapped){if(sceKernelMunmap(owned,owned_bytes)||sceKernelReleaseDirectMemory(physical,owned_bytes))retain();if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();
 if(!split_context(5)||!split_headroom())ok=false;
 try{line("END success="+std::to_string(ok)+" nonce=" BUNDLE_PROBE_NONCE " active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0");}catch(...){retain();}
 if(!split_close_journal())return 2;return ok?0:1;
}
