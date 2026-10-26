// SPDX-License-Identifier: MIT
#include "completion_probe_io.h"
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <sys/types.h>
#include <vector>

namespace {
constexpr unsigned stride=3293184, matrix=3276800, start=(4u<<20)+16384;
std::vector<unsigned char> source;
std::atomic<unsigned> reads{0},before{0},returned{0};
std::atomic<bool> permitted{true},short_read{false};
void check(bool value) {if(!value)throw std::runtime_error("Vector delivery control failed");}
}
extern "C" ssize_t qwen_vector_test_pread(int fd,void *destination,size_t bytes,off_t offset) {
    ++reads;
    check(fd==17 && offset>=0 && std::uint64_t(offset)+bytes<=source.size());
    const auto count=short_read ? bytes-16384 : bytes;
    std::memcpy(destination,source.data()+offset,count);
    return static_cast<ssize_t>(count);
}
extern "C" uint64_t completion_probe_now() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
extern "C" int completion_probe_permit(){return permitted;}
extern "C" int completion_probe_event(unsigned done,unsigned,uint64_t,uint64_t,uint64_t,int64_t,uint64_t,uint64_t) {
    if(done)++returned;else ++before;return 1;
}
int main() {
    source.resize(start+3u*stride);
    for(std::size_t i=0;i<source.size();++i)source[i]=static_cast<unsigned char>(i*37+(i>>7)*13+17);
    std::vector<unsigned char> backing(4u*stride+16383);
    auto *destination=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(backing.data())+16383)&~std::uintptr_t(16383));
    std::array<completion_extent,3> extents{};
    for(unsigned i=0;i<3;++i)extents[i]={start+std::uint64_t(i)*stride,matrix,stride};
    completion_times time{};
    check(completion_probe_start()==1);
    for(unsigned repeat=0;repeat<4;++repeat) {
        std::memset(destination,0xa7,4u*stride);
        check(completion_probe_batch(17,0,extents.data(),3,destination,destination,&time)==1);
        check(time.physical_bytes==3u*stride && time.wall_ns>0);
        check(std::memcmp(destination,source.data()+start,3u*stride)==0);
        for(unsigned i=3u*stride;i<4u*stride;++i)check(destination[i]==0xa7);
    }
    check(reads==12 && before==reads && returned==reads);
    auto changed=extents;changed[1].requested=matrix;
    check(completion_probe_batch(17,0,changed.data(),3,destination,destination,&time)==0 && reads==12);
    changed=extents;changed[0].offset=0;
    check(completion_probe_batch(17,0,changed.data(),3,destination,destination,&time)==0 && reads==12);
    check(completion_probe_batch(17,1,extents.data(),3,destination,destination,&time)==0 && reads==12);
    check(completion_probe_batch(17,0,extents.data(),2,destination,destination,&time)==0 && reads==12);
    check(completion_probe_batch(17,0,nullptr,3,destination,destination,&time)==0 && reads==12);
    check(completion_probe_stop()==1);
    check(completion_probe_start()==1);short_read=true;
    check(completion_probe_batch(17,0,extents.data(),3,destination,destination,&time)==0);
    check(completion_probe_stop()==1);short_read=false;
    check(completion_probe_start()==1);permitted=false;
    const auto old=reads.load();
    check(completion_probe_batch(17,0,extents.data(),3,destination,destination,&time)==0 && reads==old);
    check(completion_probe_stop()==1);
    std::printf("{\"exact_padded_matrix_deliveries\":12,\"invalid_geometry_refusals\":5,\"short_read_joined\":true,\"pre_read_refusal_joined\":true,\"tail_canaries\":true,\"learned_inference\":false,\"PS5_operations\":0}\n");
}
