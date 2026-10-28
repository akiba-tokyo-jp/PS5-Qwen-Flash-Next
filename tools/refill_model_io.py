#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Overlay only original expert delivery; keep routing and arithmetic intact."""


def generate(source):
    anchor='''        size_t bytes = 0;
        for (size_t ip = 0; ip < l.experts.size(); ++ip) {'''
    if source.count(anchor)!=1:raise ValueError('Unique original all-role delivery loop required')
    begin='''        size_t bytes = 0;
        const bool six_refill=qwen_app_six_bank_refill_enabled();
        std::array<bool,40> delivered{};
        if(six_refill) {
            if(!qwen_app_padded_cache_enabled()||fills.size()>delivered.size()||g.banks.size()!=3||l.experts.size()!=3)
                throw std::runtime_error("Six-demand delivery requires the original three-role padded cache");
            for(const auto *w:l.experts)if(w->type!=GGML_TYPE_BF16||w->nb[2]!=qwen_app::bank_expert_bytes||w->ne[2]!=512)
                throw std::runtime_error("Six-demand original BF16 Expert geometry differs");
            const auto joined=[&](size_t a,size_t b){return fills[b].expert==fills[a].expert+1&&fills[b].slot==fills[a].slot+1;};
            for(size_t i=0;i+1<fills.size();i+=2) {
                if((i&&joined(i-1,i))||joined(i,i+1)||(i+2<fills.size()&&joined(i+1,i+2)))continue;
                const void *sources[6];size_t residues[3];const int slots[2]={fills[i].slot,fills[i+1].slot};
                for(unsigned role=0;role<3;++role){const auto *w=l.experts[role];
                    residues[role]=bindings.at(w).cached->view_offs;
                    for(unsigned j=0;j<2;++j)sources[role*2+j]=static_cast<const uint8_t *>(w->data)+fills[i+j].expert*w->nb[2];}
                if(qwen_app_try_six_bank_refill(g.banks.data(),sources,slots,residues)) {
                    delivered[i]=delivered[i+1]=true;bytes+=6*qwen_app::bank_expert_bytes;
                }
            }
        }
        for (size_t ip = 0; ip < l.experts.size(); ++ip) {'''
    text=source.replace(anchor,begin)
    anchor='''            for (size_t i = 0; i < fills.size();) {
                size_t n = 1;'''
    if text.count(anchor)!=1:raise ValueError('Unique original per-role delivery cursor required')
    text=text.replace(anchor,'''            for (size_t i = 0; i < fills.size();) {
                if(six_refill&&delivered[i]){++i;continue;}
                size_t n = 1;''')
    anchor='while (i + n < fills.size() && fills[i + n].expert'
    if text.count(anchor)!=1:raise ValueError('Unique original coalescing predicate required')
    text=text.replace(anchor,'while (i + n < fills.size() && (!six_refill||!delivered[i+n]) && fills[i + n].expert')
    anchor='const unsigned count=i+1<fills.size()?2:1;'
    if text.count(anchor)!=1:raise ValueError('Unique original padded pair selection required')
    text=text.replace(anchor,'const unsigned count=i+1<fills.size()&&(!six_refill||!delivered[i+1])?2:1;')
    return '#include "six_bank_refill.h"\n#include <array>\n'+text
