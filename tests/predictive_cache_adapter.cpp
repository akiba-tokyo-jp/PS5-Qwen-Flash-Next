// SPDX-License-Identifier: MIT
// Executes the extracted production cache planner and prefetch hook, with
// metadata-only bank/API substitutes. No model or GPU arithmetic is performed.
#include "expert_policy.h"
#include "cross_layer_forecast.h"
#include "predictive_cache_bridge.h"
#include "padded_bank.h"
#include <atomic>
#include <cstring>
#include <iostream>
#include <memory>
#include <unordered_map>
#define GGML_ASSERT(x) do{if(!(x))throw std::runtime_error("Cache assertion failed");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Cache abort")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
static qwen_predictive_cache_stats predictive_stats;
static std::atomic<std::uint64_t> app_upload{0};
static bool admitted=true;
static int *pinned=nullptr;
static int submitted=0;
enum {GGML_TYPE_BF16=30};
struct ggml_tensor {int type=GGML_TYPE_BF16;std::size_t nb[4]{},view_offs=256;std::int64_t ne[4]{};void *data=nullptr;};
extern "C" bool qwen_app_begin_predictive_expert(ggml_tensor *const *banks,const void *const *sources,int slot,const std::size_t *residues) {
    GGML_ASSERT(banks&&sources&&slot>=0&&slot<53&&pinned);
    for(unsigned i=0;i<10;++i)GGML_ASSERT(slot!=pinned[i]);
    for(unsigned role=0;role<3;++role)GGML_ASSERT(banks[role]&&sources[role]&&residues[role]==256);
    ++submitted;return admitted;
}
#include "actual_predictive_cache.inc"
int main(int argc,char **argv){try {
    admitted=argc!=2||std::strcmp(argv[1],"ineligible");
    Harness h;Harness::group g;g.slru.init(48,512,53,48);
    std::array<std::array<int,512>,48> maps;
    std::array<ggml_tensor,3> banks{};std::array<std::array<ggml_tensor,3>,48> weights{},cached{};
    h.layers.resize(48);
    for(unsigned role=0;role<3;++role)g.banks.push_back(&banks[role]);
    for(unsigned layer=0;layer<48;++layer) {
        maps[layer].fill(-1);g.slru.slot_map[layer]=maps[layer].data();h.layers[layer].ig=0;
        for(unsigned role=0;role<3;++role) {
            auto &w=weights[layer][role];w.nb[2]=qwen_app::bank_expert_bytes;w.ne[2]=512;
            w.data=reinterpret_cast<void *>((1ull<<40)+(layer*3ull+role)*(2ull<<30)+256);
            h.layers[layer].experts.push_back(&w);h.bindings[&w]={&cached[layer][role]};
        }
    }
    std::vector<moe_cache_slru::fill> fills;std::size_t hits=0;std::array<int,10> pins{};
    for(unsigned token=0;token<4;++token)for(unsigned layer=0;layer<48;++layer) {
        h.ids.clear();for(unsigned i=0;i<10;++i)h.ids.push_back(int((layer*11+i)%512));
        GGML_ASSERT(g.slru.plan(int(layer),h.ids.data(),10,fills,hits));
        for(unsigned i=0;i<10;++i)pins[i]=maps[layer][h.ids[i]];
        pinned=pins.data();const auto before=g.slru.key_of;
        h.predict_next_expert(int(layer),g);
        for(unsigned i=0;i<10;++i)GGML_ASSERT(maps[layer][h.ids[i]]==pins[i]);
        if(!admitted)GGML_ASSERT(before==g.slru.key_of);
    }
    GGML_ASSERT(submitted>0);
    if(admitted)GGML_ASSERT(predictive_stats.loads==predictive_stats.useful&&predictive_stats.unused==0&&
        app_upload==predictive_stats.loads*3*qwen_app::bank_expert_bytes);
    else GGML_ASSERT(predictive_stats.loads==0&&predictive_stats.ineligible>0);
    std::cout<<"{\"actual_cache_planner_and_prediction_hook\":true,\"loads\":"<<predictive_stats.loads
        <<",\"pinned_experts_preserved\":true,\"PS5_operations\":0}\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
