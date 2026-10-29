// SPDX-License-Identifier: MIT
#include "expert_q2_metadata_window.h"
#include <cassert>
#include <vector>
using namespace qwen_app;
struct Input final:MetadataReadOps{
    std::vector<unsigned char> data;bool short_read=false;unsigned calls=0;
    explicit Input(std::size_t n):data(n){for(std::size_t i=0;i<n;++i)data[i]=static_cast<unsigned char>(i%251);}
    std::int64_t read_at(void*out,std::size_t bytes,std::uint64_t at)override{
        assert(at%metadata_direct_alignment==0&&bytes%metadata_direct_alignment==0);++calls;
        const auto n=std::min<std::size_t>(bytes,data.size()-at);std::memcpy(out,data.data()+at,n);
        return n-(short_read?1:0);
    }
    std::uint64_t now_ns()override{return 1000000;}
};
static std::vector<unsigned char> storage(metadata_direct_window+metadata_direct_alignment);
static auto*scratch=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(storage.data())+
    metadata_direct_alignment-1)&~std::uintptr_t(metadata_direct_alignment-1));
template<class F>void refuses(F f){bool denied=false;try{f();}catch(const std::exception&){denied=true;}assert(denied);}
int main(){
    for(auto n:{std::size_t(832),metadata_direct_window+832,std::size_t(3*metadata_direct_window+12345)}){
        Input in(n);ExpertQ2MetadataWindow w(in,scratch,3ull<<30,n,n);
        std::vector<unsigned char> result(n);for(std::size_t at=0;at<n;){const auto bytes=std::min<std::size_t>(417,n-at);
            assert(w.read(result.data()+at,at,bytes)==bytes);at+=bytes;}
        w.completed();assert(result==in.data&&w.logical_end==n&&w.physical_bytes==n&&in.calls==(n+metadata_direct_window-1)/metadata_direct_window);
        unsigned char extra=0;refuses([&]{w.read(&extra,n,1);});refuses([&]{w.completed();});
    }
    Input ordinary(832);ExpertQ2MetadataWindow a(ordinary,scratch,832,832,0);
    unsigned char value=0;assert(a.read(&value,831,1)==1&&value==831%251);a.completed();
    Input bad(832);bad.short_read=true;ExpertQ2MetadataWindow b(bad,scratch,1ull<<30,832,832);
    refuses([&]{b.read(&value,0,1);});assert(bad.calls==1);refuses([&]{b.read(&value,0,1);});assert(bad.calls==1);
    refuses([&]{ExpertQ2MetadataWindow x(bad,scratch,1ull<<30,832,833);});
    refuses([&]{ExpertQ2MetadataWindow x(bad,scratch,832,832,832);});
    refuses([&]{ExpertQ2MetadataWindow x(bad,scratch,1ull<<30,0,1);});
    return 0;
}
