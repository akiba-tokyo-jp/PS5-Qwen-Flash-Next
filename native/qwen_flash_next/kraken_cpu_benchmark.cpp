// SPDX-License-Identifier: GPL-3.0-or-later
// One whole-Expert read for both variants, with reused padded buffers.
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <time.h>
extern "C" {
#include "sha256.h"
}
#include "kraken_probe_inputs.h"
extern "C" int qwen_kraken_log(const char*);
extern "C" int qwen_kraken_entropy(const unsigned char*,size_t,unsigned char*,size_t,unsigned char*,size_t);
namespace {
constexpr size_t raw_size=1536000,stride=1540096,pad=64;
alignas(16384) unsigned char raw[stride+pad],compressed[stride+pad],decoded[stride+pad];
alignas(16) unsigned char scratch[0x6c000+pad];
struct Metric{uint64_t read_ns=0,decode_ns=0,total_ns=0,bytes=0,requests=0;};
bool clock_good=true;
uint64_t now(){timespec t{};if(clock_gettime(CLOCK_MONOTONIC,&t))clock_good=false;return uint64_t(t.tv_sec)*1000000000u+t.tv_nsec;}
bool read_all(int fd,void*target,size_t n,uint64_t offset,Metric&m){
    size_t at=0;while(at<n){ssize_t got=pread(fd,static_cast<unsigned char*>(target)+at,n-at,offset+at);++m.requests;
        if(got<0&&errno==EINTR)continue;if(got<=0)return false;at+=size_t(got);m.bytes+=uint64_t(got);}return true;
}
bool identity(int fd,const uint64_t*k){
    struct stat s{};if(fstat(fd,&s))return false;
    const uint64_t actual[]={uint64_t(s.st_dev),uint64_t(s.st_ino),uint64_t(s.st_mode),uint64_t(s.st_uid),uint64_t(s.st_gid),uint64_t(s.st_size),uint64_t(s.st_mtim.tv_sec),uint64_t(s.st_mtim.tv_nsec),uint64_t(s.st_ctim.tv_sec),uint64_t(s.st_ctim.tv_nsec)};
    return !memcmp(actual,k,sizeof(actual));
}
bool digest_matches(const char*expected){
    struct ai_sha256 h;unsigned char hash[32];char hex[65];ai_sha256_init(&h);ai_sha256_update(&h,raw,raw_size);ai_sha256_final(&h,hash);
    for(unsigned i=0;i<32;++i)snprintf(hex+2*i,3,"%02x",hash[i]);return !strcmp(hex,expected);
}
bool variant(unsigned index,unsigned round,int original,int encoded,int kind,Metric&m){
    const auto&s=kraken_samples[index];uint64_t requests_before=m.requests,start=now(),read_start=start;
    if(!read_all(kind?encoded:original,kind?compressed:raw,kind?s.compressed_padded:stride,kind?s.compressed_offset:s.source_offset,m))return false;
    uint64_t after_read=now();m.read_ns+=after_read-read_start;
    if(kind){
        size_t at=0;memset(compressed+s.compressed_padded,0,pad);
        for(const auto&block:s.chunks){
            if(block.flags||!block.raw||block.raw>131072||block.stored>block.raw||block.offset+block.stored>s.compressed_padded||at+block.raw>raw_size)return false;
            if(qwen_kraken_entropy(compressed+block.offset,block.stored,decoded+at,block.raw,scratch,0x6c000))return false;at+=block.raw;
        }
        if(at!=raw_size)return false;
    }
    uint64_t complete=now();if(kind)m.decode_ns+=complete-after_read;m.total_ns+=complete-start;
    if(!clock_good||(kind&&memcmp(raw,decoded,raw_size)))return false;
    char line[512];snprintf(line,sizeof(line),"KRAKEN_TIMING sample=%u round=%u variant=%s read_ns=%llu decode_ns=%llu total_ns=%llu bytes=%llu requests=%llu exact=1 hardware_decoder=0 cache=direct_retained_device_unspecified",index,round,kind?"CPU_Kraken":"raw",(unsigned long long)(after_read-start),(unsigned long long)(kind?complete-after_read:0),(unsigned long long)(complete-start),(unsigned long long)(kind?s.compressed_padded:stride),(unsigned long long)(m.requests-requests_before));
    return qwen_kraken_log(line);
}
}
extern "C" int qwen_run_kraken_benchmark(){
    int packed=open(KRAKEN_SOURCE,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(packed<0)return 0;
    bool good=true;Metric totals[2];unsigned completed=0;
    for(unsigned i=0;good&&i<16;++i){
        int fd=open(kraken_samples[i].path,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0){good=false;break;}
        Metric verify;
        good=identity(fd,kraken_samples[i].key)&&read_all(fd,raw,stride,kraken_samples[i].source_offset,verify)&&digest_matches(kraken_samples[i].raw_SHA256);
        // Verify exact input before the timed reversal; each raw round resets it.
        const int kinds[]={0,1,1,0};
        for(unsigned round=0;good&&round<4;++round)good=variant(i,round,fd,packed,kinds[round],totals[kinds[round]]);
        good=good&&identity(fd,kraken_samples[i].key);if(close(fd))good=false;if(good)++completed;
    }
    if(close(packed))good=false;
    for(int k=0;k<2;++k){char line[512];const auto&m=totals[k];snprintf(line,sizeof(line),"KRAKEN_SUMMARY variant=%s read_ns=%llu decode_ns=%llu total_ns=%llu bytes=%llu requests=%llu completed_Experts=%u hardware_decoder=0",k?"CPU_Kraken":"raw",(unsigned long long)m.read_ns,(unsigned long long)m.decode_ns,(unsigned long long)m.total_ns,(unsigned long long)m.bytes,(unsigned long long)m.requests,completed);if(!qwen_kraken_log(line))good=false;}
    return good&&completed==16&&clock_good;
}
