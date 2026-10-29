// SPDX-License-Identifier: MIT
#include "expert_routing_experiment.h"
#include "ggml.h"
#include "profile_clock.h"
#include <atomic>
#include <cstring>
namespace {
std::atomic<unsigned>mode{0};
std::atomic<bool>decoding{false};
std::array<std::atomic<unsigned char>,49*512> residency{};
std::atomic<std::uint64_t>ranking_calls{0},resident_scores{0},ranking_ns{0};
}
extern "C" unsigned qwen_app_route_mode(){return mode.load();}
extern "C" bool qwen_app_route_is_decode(){return decoding.load();}
extern "C" void qwen_app_route_phase(bool selected){decoding.store(selected);}
extern "C" void qwen_app_route_begin(unsigned selected){
    if(selected>4)throw std::invalid_argument("Unknown experimental routing selection");
    for(auto&x:residency)x.store(0,std::memory_order_relaxed);
    ranking_calls=0;resident_scores=0;ranking_ns=0;decoding=false;mode.store(selected);
}
extern "C" void qwen_app_route_resident(unsigned layer,unsigned expert,bool present){
    if(layer>=49||expert>=512)throw std::runtime_error("Logical residency exceeds the original model");
    residency[layer*512+expert].store(present,std::memory_order_relaxed);
}
extern "C" void qwen_app_route_stats(std::uint64_t*out){
    if(!out)throw std::invalid_argument("Routing statistics destination required");
    out[0]=ranking_calls.load();out[1]=resident_scores.load();out[2]=ranking_ns.load();
}
extern "C" void qwen_app_route_rank(ggml_tensor*dst,const ggml_tensor*src,int ith,int nth,void*opaque){
    const auto layer=std::uintptr_t(opaque);
    const auto started=qwen_app::ProfileClock::now();
    if(ith||nth!=1||layer>=48||mode.load()!=1||!dst||!src||src->type!=GGML_TYPE_F32||dst->type!=GGML_TYPE_F32||
       !ggml_is_contiguous(src)||!ggml_is_contiguous(dst)||ggml_nelements(src)!=512||ggml_nelements(dst)!=512)
        throw std::runtime_error("Cache ranking requires one completed 512-score decode row");
    std::array<unsigned char,512>cached{};unsigned resident=0;
    for(unsigned i=0;i<512;++i){cached[i]=residency[layer*512+i].load(std::memory_order_relaxed);resident+=cached[i]!=0;}
    qwen_app::cache_rank_scores(static_cast<const float*>(src->data),static_cast<float*>(dst->data),cached.data(),512,1.5f);
    ++ranking_calls;resident_scores+=resident;ranking_ns+=qwen_app::profile_elapsed_ns(started);
}
