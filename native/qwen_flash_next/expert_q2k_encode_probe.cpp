// SPDX-License-Identifier: MIT
// Read-only CPU conformance and throughput probe; no GPU or source writes.
#include "expert_q2k_encode_context.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <cpuid.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char *);
int split_open_journal(void);
int split_context(unsigned);
int split_headroom(void);
std::uint64_t split_now_ns(void);
int split_close_journal(void);
int qwen_quantize_bf16_q2_K(const std::uint16_t*,std::uint8_t*,std::size_t);
}
namespace {
constexpr std::size_t window_bytes=8u<<20;
using Key=std::array<std::uint64_t,10>;
bool line(const char*value){return split_report_line(value)!=0;}
Key identity(int fd) {
    struct stat s{};
    // This is the newly published component pack, bound by complete SHA256 and
    // the exclusive console writer lease. Original model sealing is separate.
    if(fstat(fd,&s)||!S_ISREG(s.st_mode)||s.st_size!=q2k_pack_bytes)return{};
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
bool digest_equal(sha256_t*h,const char*expected) {
    unsigned char raw[32];sha256_final(h,raw);char text[65]{};
    for(unsigned i=0;i<32;++i){text[2*i]="0123456789abcdef"[raw[i]>>4];text[2*i+1]="0123456789abcdef"[raw[i]&15];}
    return !std::strcmp(text,expected);
}
[[noreturn]] void retain(){(void)line("UNCERTAIN owners_retained=1 automatic_retry=0");for(;;)sleep(1);}
}
int main(int argc,char**) {
    if(!split_open_journal())return 2;
    bool ok=false,mapped=false;void*window=nullptr;std::int64_t physical=-1;int fd=-1;
    const auto started=split_now_ns();std::uint64_t encode_ns=0;
    do {
        if(!line("BEGIN nonce=" Q2K_ENCODER_NONCE " CPU_only=1 model_loaded=0 GPU_calls=0 title_launches=0")||
           (argc!=0&&argc!=1)||!started||!split_context(1)||!split_context(2)||!split_headroom())break;
        unsigned a=0,b=0,c=0,d=0;
        if(!__get_cpuid(1,&a,&b,&c,&d)||!(c&bit_F16C)||!line("CPU F16C_verified=1 encoder_not_yet_called=1"))break;
        const int allocated=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
        if(allocated||physical<0){physical=-1;break;}
        const int map=sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384);
        if(map||!window||reinterpret_cast<std::uintptr_t>(window)%16384)retain();mapped=true;
        fd=open(Q2K_PACK_PATH,O_RDONLY|O_NOFOLLOW|O_DIRECT);
        if(fd<0||!(fcntl(fd,F_GETFL)&O_DIRECT)){(void)line("REFUSED pack_Direct_open");break;}
        const auto original=identity(fd);if(!original[0]||!original[1]){(void)line("REFUSED pack_identity");break;}
        sha256_t whole;sha256_init(&whole);bool valid=true;
        for(std::uint64_t at=0;at<q2k_pack_bytes;) {
            const auto logical=std::size_t(std::min<std::uint64_t>(window_bytes,q2k_pack_bytes-at));
            const auto count=(logical+16383)&~std::size_t(16383);
            if(!split_headroom()||!line("BEFORE pack_Direct_read")){valid=false;break;}
            const auto got=pread(fd,window,count,static_cast<off_t>(at));
            if(!line("RETURN pack_Direct_read")||got!=static_cast<ssize_t>(logical)){valid=false;break;}
            sha256_update(&whole,static_cast<const unsigned char*>(window),logical);at+=logical;
        }
        if(!valid||!digest_equal(&whole,Q2K_PACK_SHA256)||identity(fd)!=original)break;
        for(unsigned i=0;i<27;++i) {
            if(!split_headroom()||!split_context(3)||split_now_ns()-started>UINT64_C(60000000000)){valid=false;break;}
            const auto &sample=q2k_encode_samples[i];
            if(sample.offset%16384||sample.offset+3276800>q2k_pack_bytes||!line("BEFORE original_Expert_Direct_read")){valid=false;break;}
            const auto got=pread(fd,window,3276800,static_cast<off_t>(sample.offset));
            if(!line("RETURN original_Expert_Direct_read")||got!=3276800||identity(fd)!=original){valid=false;break;}
            sha256_t original_hash;sha256_init(&original_hash);sha256_update(&original_hash,static_cast<unsigned char*>(window),3276800);
            if(!digest_equal(&original_hash,sample.original_sha256)){valid=false;break;}
            auto*out=static_cast<std::uint8_t*>(window)+(4u<<20);
            std::memset(out,0xa5,1u<<20);const auto begin=split_now_ns();
            const int converted=qwen_quantize_bf16_q2_K(static_cast<const std::uint16_t*>(window),out,1638400);
            const auto elapsed=split_now_ns()-begin;encode_ns+=elapsed;
            sha256_t hash;sha256_init(&hash);sha256_update(&hash,out,537600);
            if(converted||!elapsed||!digest_equal(&hash,sample.q2k_sha256)){valid=false;break;}
            for(std::size_t j=537600;j<(1u<<20);++j)if(out[j]!=0xa5){valid=false;break;}
            char message[256];std::snprintf(message,sizeof(message),"Q2K_MATRIX index=%u encoded_bytes=537600 exact_pinned_SHA256=1 encode_ns=%llu",i,static_cast<unsigned long long>(elapsed));
            if(!valid||!line(message)){valid=false;break;}
        }
        if(!valid||identity(fd)!=original)break;
        ok=true;
    }while(false);
    if(fd>=0&&close(fd))retain();
    if(mapped) {
        if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();
        if(!line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();
    }else if(physical>=0)retain();
    if(!split_context(5)||!split_headroom())ok=false;
    char end[256];std::snprintf(end,sizeof(end),"END success=%u matrices=%u encode_ns=%llu active_calls=0 GPU_calls=0 title_launches=0 retry=0",unsigned(ok),ok?27:0,static_cast<unsigned long long>(encode_ns));
    if(!line(end)||!split_close_journal())return 2;return ok?0:1;
}
