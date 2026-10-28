#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add one early-hidden Expert proposal to the actual owned-cache implementation."""
from build_speculative_batch_probe import once


def moe_source(text):
    text='#include "hidden_expert_prefetch.h"\n'+text
    marker='    void reset_resident(qwen_resident_cache_reset_stats *out){'
    # Registration is after every bank binding and successful real allocation.
    end='''        }
    }

'''+marker
    text=once(text,end,'''        }
        if(!model.hparams.no_alloc)
            qwen_app::hidden_expert_prefetch.bind(this,[this](unsigned layer,int id){predict_hidden_expert(int32_t(layer),id);});
    }

'''+marker)
    text=once(text,'    ~impl() {','''    ~impl() {
        if(qwen_app::hidden_expert_prefetch.owns(this)){
            qwen_app_complete_predictive_expert();
            qwen_app::hidden_expert_prefetch.unbind(this);
        }
''')
    marker='    void predict_next_expert(int32_t il,group &g) {'
    method='''    void predict_hidden_expert(int32_t il,int32_t expert) {
        if(!qwen_app::hidden_expert_prefetch.enabled()||!qwen_app_predictive_cache_enabled()||il!=23||
           expert<0||expert>=512||predicted_layer>=0)
            throw std::runtime_error("One fresh owned hidden-state Expert proposal is required");
        auto &l=layers.at(il);auto &g=groups.at(l.ig);
        ++predictive_stats.proposals;
        if(!g.slru.adaptive||g.banks.size()!=3||l.experts.size()!=3||layers[il-1].ig!=l.ig)
            throw std::runtime_error("Hidden-state prefetch requires the original three BF16 banks and previous-route protection");
        if(g.slru.slot_map[il][expert]>=0){++predictive_stats.ineligible;return;}
        const auto slot=g.slru.policy.victim(g.slru.key_of,il-1,g.slru.uniq);
        if(slot<0){++predictive_stats.ineligible;return;}
        const void*sources[3];std::size_t residues[3];
        for(unsigned role=0;role<3;++role){const auto*w=l.experts[role];
            if(w->type!=GGML_TYPE_BF16||w->nb[2]!=qwen_app::bank_expert_bytes||w->ne[2]!=512)
                throw std::runtime_error("Hidden-state prefetch cannot change original Expert precision or geometry");
            sources[role]=static_cast<const uint8_t*>(w->data)+expert*w->nb[2];
            residues[role]=bindings.at(w).cached->view_offs;
        }
        if(!qwen_app_begin_predictive_expert(g.banks.data(),sources,slot,residues)){
            ++predictive_stats.ineligible;return;
        }
        const auto old=g.slru.key_of[slot];
        if(old>=0)g.slru.slot_map[old/512][old%512]=-1;
        g.slru.key_of[slot]=il*512+expert;g.slru.slot_map[il][expert]=slot;g.slru.move(slot,false);
        predicted_layer=il;predicted_expert=expert;
        ++predictive_stats.loads;predictive_stats.logical_bytes+=3*qwen_app::bank_expert_bytes;
        app_upload.fetch_add(3*qwen_app::bank_expert_bytes,std::memory_order_relaxed);
    }

'''
    text=once(text,marker,method+marker+'\n        if(qwen_app::hidden_expert_prefetch.owns(this))return;')
    text=once(text,'        if(forecast)qwen_app_complete_predictive_expert();',
        '        if(forecast||predicted_layer>=0)qwen_app_complete_predictive_expert();')
    marker='''        ggml_backend_synchronize(backend);

        size_t n_hit = 0;'''
    text=once(text,marker,'''        ggml_backend_synchronize(backend);
        if(qwen_app::hidden_expert_prefetch.owns(this)&&predicted_layer>=0){
            if(predicted_layer!=il)throw std::runtime_error("Predicted Expert was not consumed at the exact next demand boundary");
            if(std::find(ids.begin(),ids.end(),predicted_expert)!=ids.end())++predictive_stats.useful;
            else ++predictive_stats.unused;
            predicted_layer=predicted_expert=-1;
        }

        size_t n_hit = 0;''')
    return text


def callback_header(text):
    text='#include "hidden_expert_prefetch.h"\n'+text
    return once(text,'            else self.observer_.demand(self.layer_,ids.data(),unsigned(tensor->ne[1]),now);',
        '''            else self.observer_.demand(self.layer_,ids.data(),unsigned(tensor->ne[1]),now);
            if(early)qwen_app::hidden_expert_prefetch.propose(self.layer_,ids[0],unsigned(tensor->ne[1]));''')


def entry_source(text):
    text='#include "hidden_expert_prefetch.h"\n'+text
    text=once(text,'kind=="shadow",ggml_backend_dev_buffer_type(shadow_device)',
        'true,ggml_backend_dev_buffer_type(shadow_device)')
    text=once(text,'            qwen_app::start_router_shadow_request(context,ordinal+1,',
        '''            qwen_app_configure_predictive_cache(kind=="hidden");
            qwen_app::hidden_expert_prefetch.select(kind=="hidden");
            qwen_app::start_router_shadow_request(context,ordinal+1,''')
    text=text.replace('run_arm(0,"shadow",0)','run_arm(0,"hidden",0)')
    return text
