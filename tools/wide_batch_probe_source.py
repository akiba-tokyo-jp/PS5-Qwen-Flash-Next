#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the qualified bounded state writer for four-row diagnostic references."""
from build_speculative_batch_probe import once


def renamed(text):
    return text.replace('speculative_batch_probe.h','wide_batch_probe.h').replace('SpeculativeBatchProbe','WideBatchProbe').replace(
        'ProbeStateDigest','WideProbeStateDigest').replace('speculative_batch_probe_','wide_batch_probe_').replace(
        'logit_difference_report','wide_logit_difference_report')


def header_source(text):
    text=renamed(text)
    text=once(text,'void observe(unsigned kind,llama_context *,const float *,const float *);',
        'void observe(unsigned kind,llama_context *,const std::array<const float *,4>&);')
    text=once(text,'std::array<LogitDifference,4> comparisons_{};','std::array<LogitDifference,8> comparisons_{};')
    return once(text,'void wide_batch_probe_observe(unsigned,llama_context *,const float *,const float *);',
        'void wide_batch_probe_observe(unsigned,llama_context *,const std::array<const float *,4>&);')


def cpp_source(text):
    text=renamed(text).replace('reference_(2*columns)','reference_(4*columns)')
    text=once(text,'void WideBatchProbe::observe(unsigned kind,llama_context *context,const float *first,const float *second){',
        'void WideBatchProbe::observe(unsigned kind,llama_context *context,const std::array<const float *,4>&rows){')
    text=once(text,'||!context||!first||!second)',
        '||!context||!rows[0]||!rows[1]||!rows[2]||!rows[3])')
    begin=text.index('    if(kind==0){std::copy(first,first+columns_,reference_.data());')
    end=text.index('    llama_synchronize(context);',begin)
    text=text[:begin]+'''    if(kind==0){for(unsigned row=0;row<4;++row)std::copy(rows[row],rows[row]+columns_,reference_.data()+row*columns_);}
    else for(unsigned row=0;row<4;++row)
        comparisons_[4*(kind-1)+row]=compare_logits(rows[row],reference_.data()+row*columns_,columns_,scratch_.data());
'''+text[end:]
    text=text.replace('ps5-qwen-same-batch-probe-v1','ps5-qwen-wide-same-batch-probe-v1').replace('Probe two-row/state','Probe four-row/state')
    text=text.replace('{"readback_window_bytes",65536}', '{"verified_target_width",4},{"readback_window_bytes",65536}')
    return once(text,'void wide_batch_probe_observe(unsigned kind,llama_context*c,const float*a,const float*b){if(!active)throw std::runtime_error("Probe owner missing");active->observe(kind,c,a,b);}',
        'void wide_batch_probe_observe(unsigned kind,llama_context*c,const std::array<const float *,4>&rows){if(!active)throw std::runtime_error("Probe owner missing");active->observe(kind,c,rows);}')


def engine_source(text):
    text='#include "wide_batch_probe.h"\n'+text
    marker='            process_batch_once(pair.data(),wide_plan.width,position_);'
    text=once(text,marker,'''            const bool wide_same_batch=wide_plan.width==4&&wide_batch_probe_requested();
            const auto observe_wide_reference=[&](unsigned kind){std::array<const float *,4> values{};
                for(unsigned row=0;row<4;++row)values[row]=llama_get_logits_ith(context_,int(row));
                wide_batch_probe_observe(kind,context_,values);};
            if(wide_same_batch){
                process_batch_once(pair.data(),4,position_);observe_wide_reference(0);restore_checkpoint_in_active_epoch();
                process_batch_once(pair.data(),4,position_);observe_wide_reference(1);restore_checkpoint_in_active_epoch();
            }
'''+marker)
    marker='            unsigned accepted_prefix=0;'
    text=once(text,marker,'            if(wide_same_batch)wide_batch_probe_observe(2,context_,rows);\n'+marker)
    marker='            if(expert_hooks_.verified)expert_hooks_.verified(draft_accepted,capture_seconds,restore_seconds);'
    return once(text,marker,'            if(wide_same_batch)wide_batch_probe_decision(draft_accepted,position_,speculative_bonus_ready_);\n'+marker)
