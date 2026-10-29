// SPDX-License-Identifier: MIT
// CPU-only equal-byte depth comparison from actual simultaneous Expert misses.
#include "depth_probe_plan.h"
#include "bounded_read_pool.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();uint64_t split_now_ns();
}
namespace {
using Key=std::array<uint64_t,10>;constexpr size_t owned_bytes=8u<<20;
void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_read_owners_retained=1 GPU_calls=0 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable depth journal failed");}
Key key(const struct stat&s){return{uint64_t(s.st_dev),uint64_t(s.st_ino),uint64_t(s.st_mode),uint64_t(s.st_uid),uint64_t(s.st_gid),uint64_t(s.st_size),uint64_t(s.st_mtim.tv_sec),uint64_t(s.st_mtim.tv_nsec),uint64_t(s.st_ctim.tv_sec),uint64_t(s.st_ctim.tv_nsec)};}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode),"Regular descriptor required");return key(s);}
Key path_key(const char*p){struct stat s{};need(!lstat(p,&s)&&S_ISREG(s.st_mode),"Immutable source path missing");return key(s);}
std::string digest(const void*p,size_t n){sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char*>(p),n);unsigned char d[32];sha256_final(&h,d);std::string s;for(auto v:d){s+="0123456789abcdef"[v>>4];s+="0123456789abcdef"[v&15];}return s;}
}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;void*owned=nullptr;int64_t physical=-1;qwen_app::BoundedReadPool*pool=nullptr;
 std::array<int,depth_source_count>fds{};fds.fill(-1);const auto begun=split_now_ns();
 try{
    line("BEGIN nonce=" DEPTH_PROBE_NONCE " CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0 maximum_depth=4 owned_bytes=8388608");
    need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2)&&split_headroom(),"Fresh idle CPU depth scope required");
    for(unsigned i=0;i<depth_source_count;++i){const auto&s=depth_sources[i];need(path_key(s.path)==s.identity,"Source identity changed");fds[i]=open(s.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fds[i]>=0&&(fcntl(fds[i],F_GETFL)&O_DIRECT)&&fd_key(fds[i])==s.identity,"Exact Direct source descriptor required");}
    need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),owned_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU Direct allocation failed");
    if(sceKernelMapDirectMemory(&owned,owned_bytes,3,0,physical,16384)||!owned||uintptr_t(owned)%16384)retain();mapped=true;
    pool=new qwen_app::BoundedReadPool([](const qwen_app::BoundedReadRequest&r){return pread(r.fd,r.target,r.bytes,r.offset);});pool->start();
    std::array<std::array<std::string,4>,depth_group_count> hashes{};
    constexpr unsigned modes[]={1,2,4,1,2,4,4,2,1};
    for(unsigned round=0;round<9;++round){const auto depth=modes[round];uint64_t elapsed=0,bytes=0,calls=0;unsigned maximum=0;
        for(unsigned repeat=0;repeat<(round<3?1:4);++repeat)for(unsigned group=0;group<depth_group_count;++group){
            need(split_now_ns()>=begun&&split_now_ns()-begun<120000000000ull&&split_context(3)&&split_headroom(),"CPU depth owner, memory or deadline refused");
            std::array<qwen_app::BoundedReadRequest,4>requests{};
            for(unsigned item=0;item<4;++item){const auto&r=depth_groups[group].reads[item];const auto&s=depth_sources[r.source];need(fd_key(fds[r.source])==s.identity&&path_key(s.path)==s.identity,"Active source identity changed");
                requests[item]={fds[r.source],static_cast<unsigned char*>(owned)+(2u<<20)*item,r.bytes,r.offset};}
            const auto start=split_now_ns();pool->read(requests,depth);const auto end=split_now_ns();need(end>=start,"CPU timer reversed");elapsed+=end-start;maximum=std::max(maximum,pool->maximum_inflight());
            for(unsigned item=0;item<4;++item){const auto&r=depth_groups[group].reads[item];const auto value=digest(requests[item].target,r.bytes);
                if(round==0)hashes[group][item]=value;else need(hashes[group][item]==value,"Equal-byte depth read SHA256 differs");++calls;bytes+=r.bytes;}
        }
        line("MEASURE round="+std::to_string(round)+" warmup="+std::to_string(round<3)+" depth="+std::to_string(depth)+" calls="+std::to_string(calls)+" bytes="+std::to_string(bytes)+" elapsed_ns="+std::to_string(elapsed)+" maximum_inflight="+std::to_string(maximum)+" all_SHA256_equal=1");
    }
    pool->stop_completed();delete pool;pool=nullptr;
    for(unsigned i=0;i<depth_source_count;++i)need(fd_key(fds[i])==depth_sources[i].identity&&path_key(depth_sources[i].path)==depth_sources[i].identity,"Final immutable identity changed");ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" source_writes=0");}catch(...){retain();}if(pool){try{pool->stop_completed();delete pool;pool=nullptr;}catch(...){retain();}}}
 for(auto&fd:fds)if(fd>=0){if(close(fd))retain();fd=-1;}
 if(mapped){if(sceKernelMunmap(owned,owned_bytes)||sceKernelReleaseDirectMemory(physical,owned_bytes))retain();need(split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"),"Cleanup log failed");}else if(physical>=0)retain();
 if(!split_context(5)||!split_headroom())ok=false;
 try{line("END success="+std::to_string(ok)+" nonce=" DEPTH_PROBE_NONCE " active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0");}catch(...){retain();}
 if(!split_close_journal())return 2;return ok?0:1;
}
