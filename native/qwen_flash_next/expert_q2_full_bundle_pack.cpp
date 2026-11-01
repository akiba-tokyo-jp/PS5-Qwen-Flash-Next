// SPDX-License-Identifier: MIT
// CPU-only repack of all active Experts. No quantization, model or GPU execution.
#include "full_bundle_plan.private.h"
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
constexpr size_t owned_bytes=8u<<20;
unsigned char *scratch,*bundle,*readback;uint64_t part_began=0;
struct Open {int fd=-1;unsigned source=UINT32_MAX;uint64_t used=0;};
std::array<Open,4> inputs{};uint64_t age=0;
void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_owners_retained=1 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable CPU journal failed");}
Key key(const struct stat&s){return{uint64_t(s.st_dev),uint64_t(s.st_ino),uint64_t(s.st_mode),uint64_t(s.st_uid),uint64_t(s.st_gid),uint64_t(s.st_size),uint64_t(s.st_mtim.tv_sec),uint64_t(s.st_mtim.tv_nsec),uint64_t(s.st_ctim.tv_sec),uint64_t(s.st_ctim.tv_nsec)};}
Key path_key(const char*p){struct stat s{};need(!lstat(p,&s)&&S_ISREG(s.st_mode),"Sealed regular source missing");return key(s);}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode),"Regular descriptor required");return key(s);}
void close_fd(int&fd){if(fd>=0){const int old=fd;fd=-1;if(close(old))retain();}}
void boundary(){const auto now=split_now_ns();need(now>=part_began&&now-part_began<300000000000ull&&split_headroom(),"CPU per-part deadline or memory boundary refused");}
std::string hex(sha256_t&h){unsigned char d[32];sha256_final(&h,d);std::string s;for(auto v:d){s+="0123456789abcdef"[v>>4];s+="0123456789abcdef"[v&15];}return s;}
std::string digest(const void*p,size_t n){sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char*>(p),n);return hex(h);}
void sources(){for(const auto&p:full_bundle_sources)need(path_key(p.path)==p.identity,"Immutable Q2 physical source changed");}
int input(unsigned index){
    for(auto &v:inputs)if(v.fd>=0&&v.source==index){v.used=++age;return v.fd;}
    auto &v=*std::min_element(inputs.begin(),inputs.end(),[](const Open&a,const Open&b){return a.used<b.used;});close_fd(v.fd);
    const auto&p=full_bundle_sources[index];v.fd=open(p.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);
    need(v.fd>=0&&(fcntl(v.fd,F_GETFL)&O_DIRECT)&&fd_key(v.fd)==p.identity&&path_key(p.path)==p.identity,"Exact Direct Q2 source required");v.source=index;v.used=++age;return v.fd;
}
void role(unsigned layer,unsigned role_index,unsigned expert,unsigned char*destination){
    const auto&r=full_bundle_roles[layer*3+role_index];uint64_t position=uint64_t(expert)*r.expert_bytes,left=r.expert_bytes;
    for(unsigned i=0;i<r.spans&&left;++i){const auto&s=full_bundle_spans[r.first_span+i];
        if(position<s.role_offset||position>=s.role_offset+s.bytes)continue;
        const auto take=std::min<uint64_t>(left,s.role_offset+s.bytes-position);
        const auto offset=s.file_offset+position-s.role_offset;const auto&p=full_bundle_sources[s.source];
        const auto aligned=offset&~uint64_t(16383);const auto skip=size_t(offset-aligned),count=size_t((skip+take+16383)&~uint64_t(16383));
        need(count<=(2u<<20)&&offset<=p.identity[5]&&take<=p.identity[5]-offset,"Q2 role span exceeds its bound");const int fd=input(s.source);
        const auto got=pread(fd,scratch,count,aligned),expected=ssize_t(std::min<uint64_t>(count,p.identity[5]-aligned));
        need(got==expected&&expected>=ssize_t(skip+take)&&fd_key(fd)==p.identity&&path_key(p.path)==p.identity,"Q2 source read/identity differs");
        memcpy(destination,scratch+skip,take);destination+=take;position+=take;left-=take;
    }
    need(!left,"Complete original quantized role coverage required");
}
std::string identity(const Key&k){std::string s;for(auto v:k){if(!s.empty())s+=",";s+=std::to_string(v);}return s;}
}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;void*owned=nullptr;int64_t physical=-1;int output=-1,read=-1;
 try{
    line("BEGIN nonce=" FULL_BUNDLE_NONCE " CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0 window_bytes=8388608 all_active_Experts=24576");
    need((argc==0||argc==1)&&split_context(1)&&split_context(2),"Fresh idle CPU bundle context required");part_began=split_now_ns();boundary();sources();
    struct statfs capacity{};need(!statfs(full_bundle_parent,&capacity)&&capacity.f_bavail>0&&uint64_t(capacity.f_bavail)*capacity.f_bsize>=full_bundle_total_bytes+(256ull<<20),"Complete bundle output exceeds available disk");
    line("CAPACITY available_bytes="+std::to_string(uint64_t(capacity.f_bavail)*capacity.f_bsize)+" output_bytes="+std::to_string(full_bundle_total_bytes));
    need(!mkdir(full_bundle_directory,0755),"Exclusive bundle directory required");
    need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),owned_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU Direct allocation failed");
    if(sceKernelMapDirectMemory(&owned,owned_bytes,3,0,physical,16384)||!owned||uintptr_t(owned)%16384)retain();mapped=true;
    scratch=static_cast<unsigned char*>(owned);bundle=scratch+(2u<<20);readback=scratch+(4u<<20);
    for(unsigned part=0;part<full_bundle_parts;++part){
        part_began=split_now_ns();boundary();need(split_context(3),"Idle CPU owner changed");
        const unsigned first=part*full_bundle_per_part,count=std::min(full_bundle_per_part,24576-first);const uint64_t bytes=uint64_t(count)*L::stride;
        need(bytes<=(512ull<<20)&&bytes%65536==0,"Bounded aligned output part required");char path[512];need(snprintf(path,sizeof(path),"%s/part-%03u.bin",full_bundle_directory,part)>0,"Bundle output path invalid");
        output=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);need(output>=0&&(fcntl(output,F_GETFL)&O_DIRECT),"Fresh exclusive bundle output required");
        std::array<std::string,348> expected{};
        for(unsigned i=0;i<count;++i){boundary();need(split_context(3),"Idle CPU source owner changed");const auto ordinal=first+i;memset(bundle,0,L::stride);
            role(ordinal/512,0,ordinal%512,bundle);role(ordinal/512,1,ordinal%512,bundle+537600);role(ordinal/512,2,ordinal%512,bundle+1075200);
            expected[i]=digest(bundle,L::stride);need(pwrite(output,bundle,L::stride,uint64_t(i)*L::stride)==ssize_t(L::stride),"Bundle part write was short");
            if(i%32==31)line("PROGRESS part="+std::to_string(part)+" completed_Experts="+std::to_string(first+i+1)+" source_writes=0 GPU_calls=0");
        }
        need(!fsync(output)&&!fchmod(output,0444)&&!fsync(output),"Owned bundle fsync/seal failed");close_fd(output);
        read=open(path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(read>=0&&(fcntl(read,F_GETFL)&O_DIRECT),"Sealed Direct readback required");const auto sealed=fd_key(read);need(sealed==path_key(path)&&sealed[5]==bytes,"Published bundle identity differs");
        sha256_t whole;sha256_init(&whole);
        for(unsigned i=0;i<count;++i){boundary();need(pread(read,readback,L::stride,uint64_t(i)*L::stride)==ssize_t(L::stride)&&digest(readback,L::stride)==expected[i],"Complete bundle SHA256 readback differs");sha256_update(&whole,readback,L::stride);}
        need(pread(read,readback,16384,bytes)==0&&fd_key(read)==sealed&&path_key(path)==sealed,"Whole bundle identity/EOF differs");
        line("SEALED part="+std::to_string(part)+" first_Expert="+std::to_string(first)+" Experts="+std::to_string(count)+" bytes="+std::to_string(bytes)+" SHA256="+hex(whole)+" identity="+identity(sealed));close_fd(read);sources();
    }
    ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" new_output_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
 close_fd(output);close_fd(read);for(auto &v:inputs)close_fd(v.fd);
 if(mapped){if(sceKernelMunmap(owned,owned_bytes)||sceKernelReleaseDirectMemory(physical,owned_bytes))retain();if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();
 if(!split_context(5)||!split_headroom())ok=false;
 try{line("END success="+std::to_string(ok)+" nonce=" FULL_BUNDLE_NONCE " parts="+std::to_string(full_bundle_parts)+" active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0");}catch(...){retain();}
 if(!split_close_journal())return 2;return ok?0:1;
}
