// SPDX-License-Identifier: MIT
#pragma once
#include "resident_slot_maps.h"
#include "ggml-vulkan.h"
#include <nlohmann/json.hpp>
#include <chrono>
namespace qwen_app {namespace resident_slot_maps_fixture {
inline nlohmann::json run(void(*checkpoint)(),void(*stage)(const char*),void(*admit)()){
 using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
 const auto need=[](bool v,const char*m){if(!v)throw std::runtime_error(m);};
 const auto deadline=Clock::now()+std::chrono::seconds(180);Json cases=Json::array();unsigned graphs=0;
 for(unsigned scenario=0;scenario<3;++scenario){
  admit();auto*backend=ggml_backend_vk_init(0);need(backend,"Slot-map fixture Vulkan unavailable");
  ggml_init_params p{};p.no_alloc=true;p.mem_size=16*ggml_tensor_overhead()+ggml_graph_overhead_custom(32,false)+256;
  auto*ctx=ggml_init(p);need(ctx,"Slot-map graph metadata unavailable");
  ggml_init_params hp{};hp.mem_size=ggml_tensor_overhead()+8192;auto*host=ggml_init(hp);need(host,"Slot-map host table unavailable");
  auto*source=ggml_new_tensor_2d(host,GGML_TYPE_I32,1,512);
  auto*destination=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,1,512);ggml_set_input(destination);
  auto*indices=ggml_new_tensor_1d(ctx,GGML_TYPE_I32,4);ggml_set_input(indices);
  auto*output=ggml_get_rows(ctx,destination,indices);ggml_set_output(output);
  need(ggml_backend_supports_op(backend,output),"Slot-map lookup must execute on GPU");
  auto*graph=ggml_new_graph_custom(ctx,32,false);ggml_build_forward_expand(graph,output);
  auto*buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);need(buffer,"Slot-map graph buffer unavailable");
  const std::int32_t ids[4]={0,7,511,1};ggml_backend_tensor_set(indices,ids,0,sizeof(ids));
  Json arms=Json::array();
  {
   ResidentSlotMaps maps(backend,2,64);
   for(unsigned phase=0;phase<4;++phase){const bool reuse=phase==1||phase==2;reuse_slot_maps=reuse;const auto before=slot_map_counts;Json samples=Json::array();
    for(unsigned sample=0;sample<3;++sample){
     admit();need(Clock::now()<deadline&&graphs<36,"Finite slot-map fixture bound reached");
     const unsigned layer=phase==2&&scenario<2?(sample==1?0:1):0;
     const unsigned version=scenario==1&&phase>=2?1:0;
     auto*values=static_cast<std::int32_t*>(source->data);
     for(unsigned i=0;i<512;++i)values[i]=std::int32_t((i*3+layer*7+scenario+version)%64);
     if(scenario==2&&phase==2)values[511]=std::int32_t((values[511]+sample+1)%64);
     const auto begin=Clock::now();need(maps.publish(backend,layer,source,destination),"Slot-map publication geometry rejected");
     need(ggml_backend_graph_compute(backend,graph)==GGML_STATUS_SUCCESS,"Slot-map GPU graph failed; retain owner");ggml_backend_synchronize(backend);checkpoint();++graphs;
     samples.push_back(std::chrono::duration<double,std::micro>(Clock::now()-begin).count());
     std::int32_t actual[4]{};ggml_backend_tensor_get(output,actual,0,sizeof(actual));
     for(unsigned i=0;i<4;++i)need(actual[i]==values[ids[i]],"GPU slot selection differs from authoritative CPU table");
     maps.verify_completed();checkpoint();
    }
    Json delta=Json::array();for(unsigned i=0;i<8;++i)delta.push_back(slot_map_counts[i]-before[i]);
    need(delta[3]==3&&delta[1].get<unsigned>()+delta[2].get<unsigned>()==3,"All dedicated publications must be accounted");
    need(reuse||delta[2]==0,"Control must retain every original upload");
    arms.push_back({{"reuse_enabled",reuse},{"samples_us",samples},{"slot_map_delta",delta},{"all_I32_bytes_and_canaries_exact",true}});
   }
   ggml_backend_synchronize(backend);checkpoint();
  }
  ggml_backend_buffer_free(buffer);ggml_free(ctx);ggml_free(host);ggml_backend_free(backend);checkpoint();
  cases.push_back({{"scenario",scenario},{"arms",arms},{"same_graph_destination_rebound_across_layers",scenario<2},{"changed_maps_checked",scenario>0},{"positive_retirement",true}});stage("resident_slot_map_fixture_case_completed");
 }
 need(graphs==36,"Every slot-map lookup graph required");reuse_slot_maps=false;
 return{{"completed",true},{"GPU_graphs",graphs},{"cases",cases},{"all_I32_bytes_and_canaries_exact",true},{"synthetic_inputs_only",true},{"model_loaded",false}};
}
}}
