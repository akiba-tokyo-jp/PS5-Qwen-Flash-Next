#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Default-off metadata reset on the original live MoE cache and bank owners."""


def generate(source):
    source='#include "resident_cache_reset.h"\n#include <thread>\n'+source
    anchor='static qwen_predictive_cache_stats predictive_stats;'
    addition='''
static bool resident_reuse_enabled=false;
static void *resident_reuse_owner=nullptr;
static void (*resident_reuse_reset)(void *,qwen_resident_cache_reset_stats *)=nullptr;
static std::thread::id resident_reuse_thread;
static std::uint64_t resident_reuse_ordinal=0;
extern "C" unsigned qwen_app_resident_cache_reuse_live_owners(){return resident_reuse_owner?1:0;}
extern "C" void qwen_app_configure_resident_cache_reuse(bool enabled){
    if(resident_reuse_owner)throw std::runtime_error("Configure cache reuse before the original context exists");
    resident_reuse_enabled=enabled;
}
extern "C" void qwen_app_reset_resident_expert_cache(qwen_resident_cache_reset_stats *out){
    if(!out||!resident_reuse_enabled||!resident_reuse_owner||!resident_reuse_reset||resident_reuse_thread!=std::this_thread::get_id())
        throw std::runtime_error("One original producer and registered cache reset owner required");
    qwen_app_complete_predictive_expert();
    resident_reuse_reset(resident_reuse_owner,out);
}
'''
    assert source.count(anchor)==1;source=source.replace(anchor,anchor+addition)
    anchor='    std::unique_ptr<qwen_app::CrossLayerForecast> forecast;'
    assert source.count(anchor)==1;source=source.replace(anchor,'    bool resident_original_geometry=false;\n'+anchor)
    anchor='        if(qwen_app_predictive_cache_enabled()) {'
    assert source.count(anchor)==1
    source=source.replace(anchor,'''        resident_original_geometry=qwen_app::original_predictive_model_geometry(model.hparams.n_layer(),model.layers.size(),model.hparams.n_layer_nextn,model.hparams.n_expert,n_expert_used);
'''+anchor)
    anchor='''    }

    ggml_backend_t backend(int32_t il) const {'''
    addition='''        if(resident_reuse_enabled){
            if(resident_reuse_owner||!resident_original_geometry)throw std::runtime_error("One original cache context required for reuse");
            resident_reuse_owner=this;resident_reuse_thread=std::this_thread::get_id();
            resident_reuse_reset=[](void *value,qwen_resident_cache_reset_stats *out){static_cast<impl *>(value)->reset_resident(out);};
        }
    }

    void reset_resident(qwen_resident_cache_reset_stats *out){
        if(!out||!resident_original_geometry||groups.size()!=1||predicted_layer>=0||
           groups[0].banks.size()!=3||groups[0].n_slots!=int(qwen_app::selected_padded_cache_geometry().active_slots))
            throw std::runtime_error("Complete original cache and drained prediction required for reset");
        const auto hits=app_hits.load(),misses=app_misses.load(),upload=app_upload.load(),advice=app_advice.load();
        const bool predictive=qwen_app_predictive_cache_enabled();
        if(predictive&&groups[0].n_slots!=53)throw std::runtime_error("Original 53-slot predictive geometry required");
        qwen_resident_cache_reset_stats result{};
        for(auto &g:groups){result.occupied_before+=qwen_app::reset_resident_cache_metadata(g.slru,unsigned(g.layers.size()));
            ++result.groups;result.maps+=g.layers.size();result.slots+=g.n_slots;
            for(const auto key:g.slru.key_of)result.occupied_after+=key>=0;}
        forecast.reset();if(predictive)forecast=std::make_unique<qwen_app::CrossLayerForecast>();
        predicted_layer=predicted_expert=-1;ids.clear();fills.clear();stats_small={};stats_large={};stats_copy={};
        if(ctx_views)ggml_reset(ctx_views.get());
        if(hits!=app_hits.load()||misses!=app_misses.load()||upload!=app_upload.load()||advice!=app_advice.load()||result.occupied_after)
            throw std::runtime_error("Cache reset changed cumulative counters or retained occupied slots");
        result.reset_ordinal=resident_reuse_ordinal++;result.original_banks_retained=true;result.cumulative_counters_preserved=true;result.predictive=predictive;*out=result;
    }

    ggml_backend_t backend(int32_t il) const {'''
    assert source.count(anchor)==1;source=source.replace(anchor,addition)
    anchor='    ~impl() {\n        log_stats();'
    assert source.count(anchor)==1;source=source.replace(anchor,'''    ~impl() {
        if(resident_reuse_owner==this){resident_reuse_owner=nullptr;resident_reuse_reset=nullptr;}
        log_stats();''')
    return source
