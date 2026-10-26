// SPDX-License-Identifier: MIT
#include "vector_layout_delivery.h"
#include <sys/uio.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
constexpr unsigned stride=3293184,matrix=3276800,start=(4u<<20)+16384;
std::vector<unsigned char> originals[6],pack;
std::vector<std::string> records;
std::atomic<unsigned> calls{0},scalar{0},vectors{0};std::atomic<bool> shortened{false};
void check(bool v){if(!v)throw std::runtime_error("Actual-source layout control failed");}
const std::vector<unsigned char> &source(int fd){if(fd==31)return pack;check(fd>=17&&fd<23);return originals[fd-17];}
}
extern "C" ssize_t qwen_vector_test_pread(int fd,void *dest,size_t bytes,off_t offset) {
    const auto &s=source(fd);check(offset>=0&&std::uint64_t(offset)+bytes<=s.size());++calls;++scalar;
    const auto got=bytes-(shortened?16384:0);std::memcpy(dest,s.data()+offset,got);return got;
}
extern "C" ssize_t qwen_vector_test_preadv(int fd,const iovec *v,int count,off_t offset) {
    const auto &s=source(fd);check(count==3&&offset>=0);++calls;++vectors;std::uint64_t bytes=0;
    for(int i=0;i<count;++i){check(std::uint64_t(offset)+bytes+v[i].iov_len<=s.size());std::memcpy(v[i].iov_base,s.data()+offset+bytes,v[i].iov_len);bytes+=v[i].iov_len;}
    return bytes-(shortened?16384:0);
}
extern "C" int vector_layout_identity(int fd,std::uint64_t *device,std::uint64_t *inode,std::uint64_t *bytes) {
    if(fd!=31&&(fd<17||fd>=23))return 0;*device=7;*inode=100+fd;*bytes=source(fd).size();return 1;
}
extern "C" int vector_layout_permit(){return 1;}
extern "C" int vector_layout_record(const char *text){check(std::strlen(text)<=1000);records.emplace_back(text);return 1;}
extern "C" uint64_t vector_layout_now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
int main() {
    pack.resize(start+6u*stride);vector_layout_source control[6],candidate[6];
    for(unsigned role=0;role<3;++role)for(unsigned expert=0;expert<2;++expert) {
        const unsigned i=role*2+expert,residue=(role+1)*64;originals[i].resize(stride+16384,0x5b);
        control[i]={17+int(i),16384};candidate[i]={31,start+std::uint64_t(expert*3+role)*stride};
        for(unsigned j=0;j<matrix;++j){const auto value=static_cast<unsigned char>(j*37+(j>>7)*13+i*5);
            originals[i][16384+residue+j]=value;pack[candidate[i].offset+residue+j]=value;}
    }
    std::vector<unsigned char> backing(7u*stride+16383);auto *destination=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(backing.data())+16383)&~std::uintptr_t(16383));
    check(vector_layout_start()==1);vector_layout_times times{};
    for(unsigned round=0;round<4;++round) {
        const unsigned mode=(round^(round>>1))&1;std::memset(destination,0xa7,7u*stride);
        check(vector_layout_batch(mode,mode?candidate:control,destination,&times)==1);
        check(times.physical_bytes==6u*stride&&times.source_ns>0&&times.source_ns<=times.wall_ns);
        for(unsigned i=0;i<6;++i){const auto &s=mode?pack:originals[i];const auto offset=mode?candidate[i].offset:control[i].offset;
            check(!std::memcmp(destination+i*stride,s.data()+offset,stride));}
        for(unsigned i=6u*stride;i<7u*stride;++i)check(destination[i]==0xa7);
    }
    check(calls==16&&scalar==12&&vectors==4&&records.size()==8);
    const auto before=calls.load();check(vector_layout_batch(2,control,destination,&times)==0);
    auto fd=control[0].fd;control[0].fd=-1;check(vector_layout_batch(0,control,destination,&times)==0);control[0].fd=fd;
    auto off=candidate[2].offset;candidate[2].offset+=16384;check(vector_layout_batch(1,candidate,destination,&times)==0);candidate[2].offset=off;
    check(calls==before&&vector_layout_stop()==1);
    for(unsigned mode=0;mode<2;++mode){check(vector_layout_start()==1);shortened=true;
        check(vector_layout_batch(mode,mode?candidate:control,destination,&times)==0);check(vector_layout_stop()==1);shortened=false;}
    std::puts("{\"exact_envelope_deliveries\":24,\"separate_original_descriptors\":6,\"same_worker_both_arms\":true,\"durable_records_per_complete_batch\":2,\"invalid_requests_before_IO\":3,\"known_short_reads_joined\":2,\"canaries_intact\":true,\"PS5_operations\":0}");
}
