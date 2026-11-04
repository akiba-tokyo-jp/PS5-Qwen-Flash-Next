// SPDX-License-Identifier: MIT
#include "bounded_part_concat.h"
#include <algorithm>
#include <cassert>
#include <cstring>
#include <vector>
#include <cstdio>
struct Owner{
    std::vector<std::vector<unsigned char>>parts;std::vector<unsigned char>output,digested;
    unsigned closes=0;int fault=0;
};
static unsigned char input_storage[QWEN_CONCAT_WINDOW+16384],output_storage[QWEN_CONCAT_WINDOW+16384];
static unsigned char*input=reinterpret_cast<unsigned char*>((reinterpret_cast<uintptr_t>(input_storage)+16383)&~uintptr_t(16383));
static unsigned char*output=reinterpret_cast<unsigned char*>((reinterpret_cast<uintptr_t>(output_storage)+16383)&~uintptr_t(16383));
static int64_t read_part(void*opaque,unsigned part,uint64_t offset,void*data,size_t count){
    auto&o=*static_cast<Owner*>(opaque);assert(part<o.parts.size()&&offset%16384==0&&count%16384==0&&count<=QWEN_CONCAT_WINDOW);
    const auto n=std::min<uint64_t>(count,o.parts[part].size()-offset);std::memcpy(data,o.parts[part].data()+offset,n);
    if(o.fault==1)return int64_t(n)-1;if(o.fault==2)return int64_t(n)+1;return int64_t(n);
}
static int write_part(void*opaque,uint64_t offset,const void*data,size_t count){
    auto&o=*static_cast<Owner*>(opaque);assert(offset==o.output.size()&&offset%16384==0&&count%16384==0&&count<=QWEN_CONCAT_WINDOW);
    if(o.fault==3)return 0;const auto*p=static_cast<const unsigned char*>(data);o.output.insert(o.output.end(),p,p+count);return 1;
}
static int digest(void*opaque,const void*data,size_t count){auto&o=*static_cast<Owner*>(opaque);
    if(o.fault==4)return 0;const auto*p=static_cast<const unsigned char*>(data);o.digested.insert(o.digested.end(),p,p+count);return 1;}
static int end_part(void*opaque,unsigned part){auto&o=*static_cast<Owner*>(opaque);assert(part==o.closes);++o.closes;return o.fault!=5;}
static void exercise(const std::vector<uint64_t>&sizes,int fault=0){
    Owner o;o.fault=fault;std::vector<unsigned char>expected;
    for(unsigned part=0;part<sizes.size();++part){o.parts.emplace_back(sizes[part]);for(size_t i=0;i<sizes[part];++i)o.parts.back()[i]=(i*37+part*61)%251;
        expected.insert(expected.end(),o.parts.back().begin(),o.parts.back().end());}
    qwen_concat_ops ops{&o,read_part,write_part,digest,end_part};qwen_concat_stats stats{};
    const auto pass=qwen_concat_copy(sizes.data(),unsigned(sizes.size()),input,output,&ops,&stats);
    if(fault){assert(!pass&&o.closes>=1);return;}
    assert(pass&&stats.logical_bytes==expected.size()&&o.closes==sizes.size()&&o.digested==expected);
    assert(std::equal(expected.begin(),expected.end(),o.output.begin())&&o.output.size()==(expected.size()+16383)/16384*16384);
    assert(std::all_of(o.output.begin()+expected.size(),o.output.end(),[](unsigned char x){return x==0;}));
}
int main(){
    for(const auto&s:std::vector<std::vector<uint64_t>>{{1},{16383},{16384},{262144},{262145},{13,17,16389,262143},
                                                      {6758400,6758400,6758400,6758400},{1,262143,1,262144}})exercise(s);
    for(int fault=1;fault<=5;++fault)exercise({262145,17},fault);
    Owner owner;qwen_concat_ops ops{&owner,read_part,write_part,digest,end_part};qwen_concat_stats stats{};
    uint64_t one=1,zero=0,large=(512ULL<<20)+1,overflow[2]={512ULL<<20,1};
    assert(!qwen_concat_copy(&one,0,input,output,&ops,&stats));assert(!qwen_concat_copy(&one,129,input,output,&ops,&stats));
    assert(!qwen_concat_copy(&zero,1,input,output,&ops,&stats));assert(!qwen_concat_copy(&large,1,input,output,&ops,&stats));
    assert(!qwen_concat_copy(overflow,2,input,output,&ops,&stats));assert(!qwen_concat_copy(&one,1,input+1,output,&ops,&stats));
    assert(!qwen_concat_copy(&one,1,input,output+1,&ops,&stats));assert(!qwen_concat_copy(&one,1,input,input,&ops,&stats));
    assert(!qwen_concat_copy(nullptr,1,input,output,&ops,&stats));ops.end_part=nullptr;
    assert(!qwen_concat_copy(&one,1,input,output,&ops,&stats));
    std::puts("{\"completed\":true,\"positive_controls\":8,\"negative_controls\":15,\"PS5_operations\":0}");
}
