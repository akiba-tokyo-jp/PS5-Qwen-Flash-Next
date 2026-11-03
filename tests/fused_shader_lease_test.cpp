// SPDX-License-Identifier: MIT
#include "fused_shader_lease.h"
#include <cassert>
#include <cstdint>
namespace {
alignas(4) unsigned char old_code[24]{},new_code[24]{},hash[32]{};
unsigned prepares,completes,hashes;bool valid,prepare_throws,digest_throws;std::size_t returned;
void*owner=reinterpret_cast<void*>(std::uintptr_t(0x1234));
const void*prepare(const void*p,std::size_t,std::size_t*n,void**lease){
    ++prepares;*n=returned;*lease=owner;if(prepare_throws)throw std::runtime_error("unknown");return p;
}
void complete(void*p){assert(p==owner);++completes;}
bool digest(const void*,std::size_t,const unsigned char*){++hashes;if(digest_throws)throw std::runtime_error("unknown");return valid;}
void reset(){prepares=completes=hashes=0;valid=true;prepare_throws=digest_throws=false;returned=100;}
template<class F>void refuses(F f){bool failed=false;try{f();}catch(const std::runtime_error&){failed=true;}assert(failed);}
}
int main(){
    qwen_app::FusedShaderSource s{old_code,sizeof(old_code),100,new_code,sizeof(new_code),hash};
    qwen_app::FusedShaderOps ops{prepare,complete,digest};std::size_t n=0;void*lease=nullptr;
    auto run=[&]{return qwen_app::prepare_fused_shader(new_code,sizeof(new_code),&n,&lease,s,ops);};
    reset();assert(run()==new_code&&n==24&&lease==owner&&prepares==1&&hashes==1&&!completes);complete(lease);
    reset();assert(qwen_app::prepare_fused_shader(old_code,24,&n,&lease,s,ops)==old_code&&prepares==1&&!hashes&&!completes);
    reset();refuses([&]{qwen_app::prepare_fused_shader(new_code,20,&n,&lease,s,ops);});assert(!prepares);
    reset();returned=99;refuses(run);assert(prepares==1&&completes==1&&!lease&&!hashes);
    reset();valid=false;refuses(run);assert(prepares==1&&completes==1&&!lease&&hashes==1);
    reset();refuses([&]{qwen_app::prepare_fused_shader(new_code,24,nullptr,&lease,s,ops);});assert(!prepares);
    reset();prepare_throws=true;refuses(run);assert(prepares==1&&!completes&&lease==owner);
    reset();digest_throws=true;refuses(run);assert(prepares==1&&!completes&&lease==owner);
    reset();auto missing=ops;missing.prepare=nullptr;refuses([&]{qwen_app::prepare_fused_shader(old_code,24,&n,&lease,s,missing);});assert(!prepares);
    reset();auto unaligned=s;unaligned.replacement=new_code+1;
    refuses([&]{qwen_app::prepare_fused_shader(new_code+1,24,&n,&lease,unaligned,ops);});assert(!prepares);
}
