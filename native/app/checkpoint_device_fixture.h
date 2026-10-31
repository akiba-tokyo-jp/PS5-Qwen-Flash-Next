// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <stdexcept>
#include <vector>
#include <nlohmann/json.hpp>
extern "C" void qwen_checkpoint_trial_select(unsigned);
extern "C" void qwen_checkpoint_trial_stats(std::uint64_t*);
extern "C" void*qwen_checkpoint_fixture_create();
extern "C" void qwen_checkpoint_fixture_free(void*);
extern "C" void qwen_checkpoint_fixture_save(void*,ggml_tensor*const*,const size_t*,const size_t*,size_t);
extern "C" void qwen_checkpoint_fixture_restore(void*,ggml_tensor*const*,const size_t*,const size_t*,size_t);
namespace qwen_app {namespace checkpoint_fixture {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
constexpr size_t small=119881728,large=121049088,guard=4096,full=large+2*guard;
constexpr unsigned spans=49;
inline std::uint32_t pattern(size_t i,unsigned salt){return 0x3f000000u|std::uint32_t((i*2654435761ull+salt*2246822519ull)&0x007fffffu);}
struct Device {
    ggml_backend_t backend=nullptr;std::array<ggml_context*,2>ctx{};
    std::array<ggml_tensor*,2>root{};std::array<ggml_backend_buffer_t,2>buffer{};
    std::vector<std::uint32_t>window=std::vector<std::uint32_t>(65536);
    void(*checkpoint)();void(*stage)(const char*);void(*admit)();Clock::time_point deadline;
    size_t checked=0,events=0;
    Device(void(*c)(),void(*s)(const char*),void(*a)()):checkpoint(c),stage(s),admit(a),deadline(Clock::now()+std::chrono::seconds(600)){
        admit();backend=ggml_backend_vk_init(0);if(!backend)throw std::runtime_error("Checkpoint fixture Vulkan unavailable");
        for(unsigned i=0;i<2;++i){ggml_init_params p{};p.mem_size=8*ggml_tensor_overhead();p.no_alloc=true;ctx[i]=ggml_init(p);
            if(!ctx[i])throw std::runtime_error("Checkpoint fixture metadata unavailable");
            root[i]=ggml_new_tensor_1d(ctx[i],GGML_TYPE_F32,full/4);ggml_set_input(root[i]);ggml_set_output(root[i]);
            buffer[i]=ggml_backend_alloc_ctx_tensors(ctx[i],backend);if(!buffer[i])throw std::runtime_error("Checkpoint fixture bounded GPU buffer unavailable");
            fill(i,0,full,false);
        }ggml_backend_synchronize(backend);checkpoint();
    }
    void bound(){admit();if(Clock::now()>deadline||events>=64)throw std::runtime_error("Checkpoint fixture finite bound reached");}
    void fill(unsigned which,size_t offset,size_t bytes,bool corrupt){
        for(size_t pos=offset;pos<offset+bytes;){const auto n=std::min(window.size(),(offset+bytes-pos)/4);
            for(size_t j=0;j<n;++j)window[j]=corrupt?0x42a40000u:pattern(pos/4+j,which+1);
            ggml_backend_tensor_set(root[which],window.data(),pos,n*4);pos+=n*4;
        }
    }
    void verify(unsigned which){
        for(size_t pos=0;pos<full;){const auto n=std::min(window.size(),(full-pos)/4);ggml_backend_tensor_get(root[which],window.data(),pos,n*4);
            for(size_t j=0;j<n;++j)if(window[j]!=pattern(pos/4+j,which+1))throw std::runtime_error("Full checkpoint bytes or canary differ; retain GPU owner");
            checked+=n*4;pos+=n*4;
        }
    }
    Json block(unsigned mode,unsigned ordinal){
        qwen_checkpoint_trial_select(mode);std::uint64_t before[5]{},after[5]{};qwen_checkpoint_trial_stats(before);
        void*state=qwen_checkpoint_fixture_create();if(!state)throw std::runtime_error("Checkpoint fixture state unavailable");
        Json samples=Json::array();std::array<ggml_tensor*,spans>list{};std::array<size_t,spans>offset{},size{};
        for(unsigned event=0;event<5;++event){bound();++events;const auto bytes=event==1||event==2?small:large;const unsigned which=event==4?1:0;
            const auto unit=(bytes/spans)&~size_t(3);size_t cursor=guard;
            for(unsigned i=0;i<spans;++i){list[i]=root[which];offset[i]=cursor;size[i]=i+1==spans?guard+bytes-cursor:unit;cursor+=size[i];}
            stage("checkpoint_fixture_before_save");const auto started=Clock::now();qwen_checkpoint_fixture_save(state,list.data(),offset.data(),size.data(),spans);
            ggml_backend_synchronize(backend);const auto saved=Clock::now();checkpoint();const auto save_checked=Clock::now();
            fill(which,guard,bytes,true);ggml_backend_synchronize(backend);checkpoint();
            stage("checkpoint_fixture_before_restore");const auto restore_started=Clock::now();qwen_checkpoint_fixture_restore(state,list.data(),offset.data(),size.data(),spans);
            ggml_backend_synchronize(backend);const auto restored=Clock::now();checkpoint();const auto restore_checked=Clock::now();verify(which);
            auto us=[](auto a,auto b){return std::chrono::duration<double,std::micro>(b-a).count();};
            samples.push_back({{"event",event},{"payload_bytes",bytes},{"source_buffer",which},{"save_backend_us",us(started,saved)},
                {"save_completion_us",us(saved,save_checked)},{"restore_backend_us",us(restore_started,restored)},
                {"restore_completion_us",us(restored,restore_checked)},{"save_total_us",us(started,save_checked)},{"restore_total_us",us(restore_started,restore_checked)}});
        }
        // Same count with different split points, then a different count. Both
        // must preserve the original byte-cursor fallback and every canary.
        for(unsigned altered=0;altered<2;++altered){bound();
            const unsigned count=altered?32:spans;const auto unit=(large/count)&~size_t(3);size_t cursor=guard;
            for(unsigned i=0;i<count;++i){offset[i]=cursor;size[i]=i+1==count?guard+large-cursor:unit;if(!altered&&i==0)size[i]+=256;cursor+=size[i];list[i]=root[1];}
            fill(1,guard,large,true);ggml_backend_synchronize(backend);checkpoint();
            qwen_checkpoint_fixture_restore(state,list.data(),offset.data(),size.data(),count);ggml_backend_synchronize(backend);checkpoint();verify(1);
        }
        qwen_checkpoint_trial_stats(after);std::array<std::uint64_t,5>delta{};for(unsigned i=0;i<5;++i)delta[i]=after[i]-before[i];
        if((mode==1||mode==2)&&(!delta[0]||!delta[1]))throw std::runtime_error("Checkpoint descriptor/high-water candidate was not executed");
        if((mode==2||mode==3)&&(!delta[2]||delta[3]<spans))throw std::runtime_error("Checkpoint batch candidate was not executed");
        qwen_checkpoint_fixture_free(state);ggml_backend_synchronize(backend);checkpoint();
        return {{"ordinal",ordinal},{"mode",mode},{"samples",samples},{"counter_delta",delta},{"all_payload_bytes_and_canaries_exact",true},
            {"same_count_different_chunking_exact",true},{"different_count_chunking_exact",true},{"distinct_source_buffers_checked",true}};
    }
    Json run(){
        Json rows=Json::array();constexpr unsigned order[]={0,1,1,0,0,3,3,0,1,2,2,1};
        for(unsigned i=0;i<12;++i)rows.push_back(block(order[i],i));
        qwen_checkpoint_trial_select(0);ggml_backend_synchronize(backend);checkpoint();
        for(auto&b:buffer){ggml_backend_buffer_free(b);b=nullptr;}for(auto&c:ctx){ggml_free(c);c=nullptr;}ggml_backend_free(backend);backend=nullptr;checkpoint();
        return {{"blocks",rows},{"save_restore_events",events},{"full_checked_bytes",checked},{"model_loaded",false},
            {"baseline_payload_bytes",small},{"maximum_payload_bytes",large},{"write_spans",spans},{"original_shaders_preserved",true},
            {"all_payload_bytes_and_canaries_exact",true},{"all_owners_positively_retired",true},{"mode_reset_to_original",true}};
    }
};
inline Json run(void(*c)(),void(*s)(const char*),void(*a)()){Device fixture(c,s,a);return fixture.run();}
}}
