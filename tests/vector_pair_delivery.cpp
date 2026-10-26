// SPDX-License-Identifier: MIT
#include "completion_probe_io.h"
#include <sys/uio.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace {
constexpr unsigned stride=3293184,matrix=3276800,start=(4u<<20)+16384;
std::vector<unsigned char> source;
std::atomic<unsigned> scalar_calls{0},vector_calls{0},before{0},returned{0};
std::atomic<bool> short_read{false};
void check(bool value){if(!value)throw std::runtime_error("Two-expert delivery control failed");}
}
extern "C" ssize_t qwen_vector_test_pread(int fd,void *dest,size_t n,off_t offset) {
    check(fd==17&&offset>=0&&std::uint64_t(offset)+n<=source.size());++scalar_calls;
    const auto actual=n-(short_read?16384:0);std::memcpy(dest,source.data()+offset,actual);return actual;
}
extern "C" ssize_t qwen_vector_test_preadv(int fd,const iovec *vectors,int count,off_t offset) {
    check(fd==17&&count==3&&offset>=0);++vector_calls;std::uint64_t total=0;
    for(int i=0;i<count;++i){check(std::uint64_t(offset)+total+vectors[i].iov_len<=source.size());
        std::memcpy(vectors[i].iov_base,source.data()+offset+total,vectors[i].iov_len);total+=vectors[i].iov_len;}
    return total-(short_read?16384:0);
}
extern "C" int completion_probe_source_identity(int fd,std::uint64_t *device,std::uint64_t *inode,std::uint64_t *bytes) {
    if(fd!=17)return 0;*device=7;*inode=31;*bytes=source.size();return 1;
}
extern "C" uint64_t completion_probe_now() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
extern "C" int completion_probe_permit(){return 1;}
extern "C" int completion_probe_event(unsigned done,unsigned,uint64_t,uint64_t,uint64_t,int64_t,uint64_t,uint64_t) {
    if(done)++returned;else ++before;return 1;
}
int main() {
    source.resize(start+6u*stride);
    for(std::size_t i=0;i<source.size();++i)source[i]=static_cast<unsigned char>(i*37+(i>>7)*13+17);
    std::vector<unsigned char> backing(7u*stride+16383);
    auto *destination=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(backing.data())+16383)&~std::uintptr_t(16383));
    completion_extent extents[6];
    for(unsigned role=0;role<3;++role)for(unsigned expert=0;expert<2;++expert)
        extents[2*role+expert]={start+std::uint64_t(expert*3+role)*stride,matrix,stride};
    check(completion_probe_start()==1);completion_times times{};
    for(unsigned round=0;round<4;++round) {
        const unsigned mode=(round^(round>>1))&1;
        std::memset(destination,0xa7,7u*stride);
        check(completion_probe_batch(17,mode,extents,6,destination,destination,&times)==1);
        check(times.physical_bytes==6u*stride&&times.wall_ns>0);
        for(unsigned i=0;i<6;++i)check(std::memcmp(destination+i*stride,source.data()+extents[i].offset,stride)==0);
        for(unsigned i=6u*stride;i<7u*stride;++i)check(destination[i]==0xa7);
    }
    check(scalar_calls==12&&vector_calls==4&&before==16&&returned==16);
    auto calls=before.load();
    check(completion_probe_batch(17,2,extents,6,destination,destination,&times)==0);
    check(completion_probe_batch(17,1,extents,5,destination,destination,&times)==0);
    auto bad=extents[2].offset;extents[2].offset+=16384;
    check(completion_probe_batch(17,1,extents,6,destination,destination,&times)==0);extents[2].offset=bad;
    check(before==calls);check(completion_probe_stop()==1);
    for(unsigned mode=0;mode<2;++mode) {
        check(completion_probe_start()==1);short_read=true;
        check(completion_probe_batch(17,mode,extents,6,destination,destination,&times)==0);
        check(completion_probe_stop()==1);short_read=false;
    }
    std::printf("{\"exact_envelope_deliveries\":24,\"expert_major_to_role_major_destinations\":true,\"control_scalar_calls\":12,\"candidate_vector_calls\":4,\"invalid_shapes_refused_before_IO\":3,\"returned_failures_joined\":2,\"tail_canaries\":true,\"learned_inference\":false,\"PS5_operations\":0}\n");
}
