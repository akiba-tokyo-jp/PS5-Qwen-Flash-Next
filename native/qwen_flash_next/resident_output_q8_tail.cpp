// SPDX-License-Identifier: MIT
// Convert only a missing new Q8 tail from sealed, read-only original BF16.
#include "resident_output_Q8_tail_plan.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cpuid.h>
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
int qwen_resident_bf16_to_q8(const std::uint16_t*,unsigned char*,std::size_t);
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();std::uint64_t split_now_ns();
}
namespace {
using Key=std::array<std::uint64_t,10>;constexpr std::size_t window_bytes=8u<<20;
std::uint64_t begun;int input=-1,output=-1;
void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_owners_retained=1 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Q8 tail journal failed");}
Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
Key named(const char*p){struct stat s{};need(!lstat(p,&s)&&S_ISREG(s.st_mode),"Regular Q8 tail source required");return key(s);}
Key descriptor(int fd){struct stat s{};need(fd>=0&&!fstat(fd,&s)&&S_ISREG(s.st_mode),"Q8 tail descriptor failed");return key(s);}
void close_fd(int&fd){if(fd>=0){int old=fd;fd=-1;if(close(old))retain();}}
void boundary(){need(split_headroom()&&split_now_ns()-begun<300000000000ull,"Q8 tail CPU memory or deadline refused");}
void sources(){for(const auto&s:tail_sources)need(named(s.path)==s.identity,"Original BF16 source changed");}
void read_original(std::uint64_t at,std::size_t bytes,unsigned char*scratch,unsigned char*destination){
    std::size_t copied=0;
    for(const auto&s:tail_sources){if(at<s.offset||at>=s.offset+s.identity[5])continue;
        const auto take=std::min<std::uint64_t>(bytes-copied,s.offset+s.identity[5]-at);
        const auto relative=at-s.offset,aligned=relative&~std::uint64_t(16383),skip=relative-aligned;
        const auto count=(skip+take+16383)&~std::uint64_t(16383);need(count<=3u<<20,"Bounded BF16 source window required");
        input=open(s.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input>=0&&(fcntl(input,F_GETFL)&O_DIRECT)&&descriptor(input)==s.identity,"Original BF16 Direct source differs");
        line("BEFORE BF16_tail_read offset="+std::to_string(at)+" bytes="+std::to_string(take));
        const auto got=pread(input,scratch,count,aligned);
        line("RETURN BF16_tail_read bytes="+std::to_string(got));
        const bool valid=got==std::int64_t(std::min<std::uint64_t>(count,s.identity[5]-aligned))&&got>=std::int64_t(skip+take)&&descriptor(input)==s.identity&&named(s.path)==s.identity;
        if(valid)memcpy(destination+copied,scratch+skip,take);close_fd(input);need(valid,"Original BF16 read or identity differs");
        copied+=take;at+=take;if(copied==bytes)break;
    }need(copied==bytes,"Complete original BF16 range required");
}
std::string digest(sha256_t&h){unsigned char raw[32];sha256_final(&h,raw);std::string s;for(auto b:raw){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
}
int main(int argc,char**){if(!split_open_journal())return 2;begun=split_now_ns();bool ok=false,mapped=false;void*owned=nullptr;std::int64_t physical=-1;
 try{
    line("BEGIN nonce=" OUTPUT_Q8_TAIL_NONCE " CPU_only=1 GPU_calls=0 original_source_writes=0");
    unsigned a,b,c,d;need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2)&&__get_cpuid(1,&a,&b,&c,&d)&&(c&bit_F16C),"Current CPU owner or F16C refused");boundary();sources();
    struct stat absent{};errno=0;if(!tail_existing_bytes)need(lstat(tail_target,&absent)&&errno==ENOENT,"Only an absent new Q8 tail may be created");
    struct statfs cap{};need(!statfs("/data/ai",&cap)&&cap.f_bavail>0&&std::uint64_t(cap.f_bavail)*cap.f_bsize>=tail_bytes+(256ull<<20),"Q8 tail cannot retain bounded transfer reserve");
    line("CAPACITY available_bytes="+std::to_string(std::uint64_t(cap.f_bavail)*cap.f_bsize)+" new_tail_bytes="+std::to_string(tail_bytes));
    need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Q8 tail bounded Direct allocation failed");
    if(sceKernelMapDirectMemory(&owned,window_bytes,3,0,physical,16384)||!owned||std::uintptr_t(owned)%16384)retain();mapped=true;
    auto*scratch=static_cast<unsigned char*>(owned);auto*bf16=scratch+(3u<<20);auto*encoded=scratch+(5u<<20);auto*readback=scratch+(13u<<19);
    Key prior{};
    if(tail_existing_bytes){
        input=open(tail_target,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input>=0&&(fcntl(input,F_GETFL)&O_DIRECT),"Owned partial tail readback required");prior=descriptor(input);
        need(prior==named(tail_target)&&prior[2]==0100600&&prior[5]==tail_existing_bytes&&!prior[3]&&!prior[4],"Bound owned partial tail differs");sha256_t prefix;sha256_init(&prefix);
        for(std::uint64_t at=0;at<tail_existing_bytes;){boundary();const auto n=std::size_t(std::min<std::uint64_t>(1u<<20,tail_existing_bytes-at));need(pread(input,readback,n,at)==ssize_t(n),"Owned partial tail readback short");sha256_update(&prefix,readback,n);at+=n;}
        need(digest(prefix)==tail_existing_SHA256&&descriptor(input)==prior&&named(tail_target)==prior,"Owned partial tail must exactly match pinned Q8 bytes");close_fd(input);line("OWNED_PREFIX complete_SHA256_passed=1 bytes="+std::to_string(tail_existing_bytes));
    }
    output=open(tail_target,O_WRONLY|O_NOFOLLOW|O_DIRECT|(tail_existing_bytes?0:O_CREAT|O_EXCL),0600);need(output>=0&&(fcntl(output,F_GETFL)&O_DIRECT),"Exclusive new or verified owned Q8 tail required");
    const auto inode=descriptor(output);need(!inode[3]&&!inode[4]&&inode[5]==tail_existing_bytes&&inode[2]==0100600&&(!tail_existing_bytes||inode==prior),"New Q8 tail ownership differs");
    std::size_t pending=0;std::uint64_t written=tail_existing_bytes,block=tail_first_block;bool first=true;
    while(block<19865600){boundary();need(split_context(3),"Q8 tail CPU owner changed");
        const auto blocks=std::size_t(std::min<std::uint64_t>(32768,19865600-block));
        read_original(160+block*64,blocks*64,scratch,bf16);
        need(qwen_resident_bf16_to_q8(reinterpret_cast<const std::uint16_t*>(bf16),encoded+pending,blocks*32)==1,"Q8 deterministic encoder refused");
        std::size_t produced=blocks*34;if(first){memmove(encoded+pending,encoded+pending+tail_initial_skip,produced-tail_initial_skip);produced-=tail_initial_skip;first=false;}
        pending+=produced;const auto bulk=pending&~std::size_t(16383);
        if(bulk){line("BEFORE own_Q8_tail_write offset="+std::to_string(written)+" bytes="+std::to_string(bulk));errno=0;const auto got=pwrite(output,encoded,bulk,written);const auto error=errno;
            line("RETURN own_Q8_tail_write bytes="+std::to_string(got)+" errno="+std::to_string(error));need(got==ssize_t(bulk),"New Q8 tail write incomplete");
            written+=bulk;pending-=bulk;memmove(encoded,encoded+bulk,pending);}
        block+=blocks;
    }
    need(written+pending==tail_bytes&&pending==160&&!fsync(output),"Exact Q8 tail body or durability differs");close_fd(output);
    output=open(tail_target,O_WRONLY|O_NOFOLLOW);need(output>=0,"New Q8 final-tail reopen failed");auto before=descriptor(output);
    need(std::equal(inode.begin(),inode.begin()+5,before.begin())&&before[5]==written&&before==named(tail_target),"New Q8 final-tail inode changed");
    need(pwrite(output,encoded,pending,written)==ssize_t(pending)&&!fsync(output)&&!fchmod(output,0644)&&!fsync(output),"New Q8 final-tail write or seal failed");close_fd(output);
    input=open(tail_target,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input>=0&&(fcntl(input,F_GETFL)&O_DIRECT),"Q8 tail Direct readback required");before=descriptor(input);
    need(before==named(tail_target)&&before[2]==0100644&&before[5]==tail_bytes&&!before[3]&&!before[4],"New Q8 tail final identity differs");sha256_t hash;sha256_init(&hash);
    for(std::uint64_t at=0;at<tail_bytes;){boundary();const auto count=std::size_t(std::min<std::uint64_t>(1u<<20,tail_bytes-at));
        need(pread(input,readback,(count+16383)&~std::size_t(16383),at)==ssize_t(count),"Q8 tail readback short");sha256_update(&hash,readback,count);at+=count;
        line("Q8_TAIL_READBACK bytes="+std::to_string(at));}
    need(digest(hash)==tail_SHA256&&pread(input,readback,16384,(tail_bytes+16383)&~std::uint64_t(16383))==0&&descriptor(input)==before&&named(tail_target)==before,"Q8 tail complete SHA256/EOF or identity differs");
    line("SEALED_Q8_TAIL bytes="+std::to_string(tail_bytes)+" SHA256="+tail_SHA256+" original_sources_preserved=1");close_fd(input);sources();ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" own_partial_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
 close_fd(input);close_fd(output);if(mapped){if(sceKernelMunmap(owned,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();line("DIRECT known_completion_cleanup_returned=1 fully_released=1");}else if(physical>=0)retain();
 if(!split_context(5)||!split_headroom())ok=false;
 line("END success="+std::to_string(ok)+" nonce=" OUTPUT_Q8_TAIL_NONCE " active_calls=0 original_source_writes=0 GPU_calls=0 retry=0");if(!split_close_journal())return 2;return ok?0:1;
}
