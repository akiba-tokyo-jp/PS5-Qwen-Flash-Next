#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate the existing actual-input shadow graph into a bounded comparison."""
from build_speculative_batch_probe import once


def model_source(text):
    text=once(text,'#include "models.h"','#include "models.h"\n#include "router_shadow_graph.h"\nextern "C" bool qwen_app_router_shadow_graph_enabled();')
    marker='        ggml_build_forward_expand(gf, cur);\n\n        if (hparams.is_recr(il))'
    return once(text,marker,'''        if(il==23&&qwen_app_router_shadow_graph_enabled()){
            auto*shadow=qwen_app::build_router_shadow(ctx0,cur,model.layers[il].ffn_gate_inp);
            cb(shadow,"qwen_router_shadow_topk",il);ggml_build_forward_expand(gf,shadow);
        }
'''+marker)


def engine_source(text):
    text='#include "router_shadow_runtime.h"\n'+text
    text=once(text,'    stage("inference_before_decode_call");','    begin_router_shadow_process(count);\n    stage("inference_before_decode_call");')
    marker='    if(expert_hooks_.completed_ordinary&&count==1)'
    return once(text,marker,'    complete_router_shadow_process();\n'+marker)
