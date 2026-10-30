// SPDX-License-Identifier: MIT
#include "expert_routing_policy.h"
#include "ggml.h"
#include "profile_clock.h"
#include <atomic>
namespace {
std::atomic<unsigned>mode{0};std::atomic<bool>decoding{false};
std::array<std::atomic<unsigned char>,49*512>residency{};
std::array<unsigned char,49*512>event_residency{};
std::atomic<std::uint64_t>ranking_calls{0},resident_scores{0},ranking_ns{0};
}
extern "C" unsigned qwen_app_route_mode(){return mode.load();}
extern "C" bool qwen_app_route_is_decode(){return decoding.load();}
extern "C" void qwen_app_route_phase(bool v){decoding=v;}
extern "C" void qwen_app_route_begin(unsigned bits){
    (void)qwen_app::routing_policy(bits);
    for(auto&x:residency)x.store(0,std::memory_order_relaxed);
    event_residency.fill(0);ranking_calls=0;resident_scores=0;ranking_ns=0;decoding=false;mode=bits;
}
extern "C" void qwen_app_route_resident(unsigned layer,unsigned expert,bool present){
    if(layer>=49||expert>=512)throw std::runtime_error("Residency exceeds the admitted model");
    residency[layer*512+expert].store(present,std::memory_order_relaxed);
}
extern "C" void qwen_app_routing_event_begin(){
    if(!qwen_app::routing_policy(mode.load()).cache_rank)return;
    // One preference snapshot for both verification rows and any rejection
    // replay. Physical cache mutations never change this in-flight decision.
    for(std::size_t i=0;i<event_residency.size();++i)event_residency[i]=residency[i].load(std::memory_order_relaxed);
}
extern "C" void qwen_app_route_stats(std::uint64_t*out){
    if(!out)throw std::invalid_argument("Routing counters destination required");
    out[0]=ranking_calls.load();out[1]=resident_scores.load();out[2]=ranking_ns.load();
}
extern "C" void qwen_app_route_rank(ggml_tensor*dst,const ggml_tensor*src,int ith,int nth,void*opaque){
    const auto layer=std::uintptr_t(opaque);const auto started=qwen_app::ProfileClock::now();
    const auto elements=src?ggml_nelements(src):0;
    if(ith||nth!=1||layer>=48||!qwen_app::routing_policy(mode.load()).cache_rank||!dst||!src||
       src->type!=GGML_TYPE_F32||dst->type!=GGML_TYPE_F32||!ggml_is_contiguous(src)||!ggml_is_contiguous(dst)||
       (elements!=512&&elements!=1024)||ggml_nelements(dst)!=elements)
        throw std::runtime_error("Cache ranking requires one or two complete decode rows");
    const auto*cached=event_residency.data()+layer*512;
    const auto*source=static_cast<const float*>(src->data);auto*target=static_cast<float*>(dst->data);
    unsigned resident=0;for(unsigned i=0;i<512;++i)resident+=cached[i]!=0;
    for(unsigned row=0;row<unsigned(elements/512);++row)
        qwen_app::cache_rank_scores(source+row*512,target+row*512,cached,512,1.5f);
    ++ranking_calls;resident_scores+=resident*unsigned(elements/512);ranking_ns+=qwen_app::profile_elapsed_ns(started);
}
