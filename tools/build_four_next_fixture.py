#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extend the qualified convolution fusion to two tokens; retain F64 oracles."""
from pathlib import Path
import build_gdn_conv_norm_fixture as base
from build_speculative_batch_probe import once
from expert_q4 import record

ROOT=Path(__file__).resolve().parents[1]
original_link=base.link
original_seal=base.seal
base.SCOPE=dict(base.SCOPE,schema='ps5-qwen-GDN-two-token-fixture-v1',cases=6,GPU_graphs=216,
               prefill_two_token_original_fallback=False,unsupported_three_token_original_fallback=True,
               original_single_token_control_preserved=True)

def fixture(text):
    from gdn_conv_norm_fixture_source import transform
    text=transform(text)
    text=once(text,'f.eligible=tokens==1&&sequences==1&&heads==48&&qheads==16;',
              'f.eligible=(tokens==1||tokens==2)&&sequences==1&&heads==48&&qheads==16;')
    text=once(text,'for(unsigned salt=0;salt<4;++salt)cases.push_back(one(48,16,salt==3?2:1,1,salt==3?3:2,false,salt,checkpoint,stage,admit,deadline,graphs));',
              'for(unsigned salt=0;salt<6;++salt)cases.push_back(one(48,16,salt==5?3:salt>=3?2:1,1,salt>=3?4:2,false,salt,checkpoint,stage,admit,deadline,graphs));')
    return once(text,'if(graphs!=144)','if(graphs!=216)')

def gpu(text):
    text=once(text,'#include "gdn_conv_norm_state.inc"','#include "gdn_conv_norm_two_state.private.inc"')
    return once(text,'#include "gdn_conv_norm_planner_backend.private.inc"','#include "gdn_conv_norm_two_backend.private.inc"')

def link(parent,out,variants,inputs):
    import json
    prior=json.loads(Path(parent).read_text())
    command=prior['io_gpu_comparison']['GPU_command']
    directories=[Path(prior['io_gpu_comparison']['GPU_source']['path']).parent]+[Path(command[i+1])for i,v in enumerate(command[:-1])if v=='-I']
    source=next(d/'gdn_conv_norm_planner_backend.private.inc'for d in directories if(d/'gdn_conv_norm_planner_backend.private.inc').is_file())
    body=source.read_text()
    body=once(body,'t->ne[2]!=1||t->ne[3]!=1','(t->ne[2]!=1&&t->ne[2]!=2)||t->ne[3]!=1')
    body=once(body,'    size_t accumulated=0;',
              '    if(t->nb[2]!=40960||t->ne[2]!=root->ne[1])return false;\n    size_t accumulated=0;')
    body=once(body,'x->ne[0]!=4||x->ne[1]!=10240','(x->ne[0]!=4&&x->ne[0]!=5)||x->ne[1]!=10240')
    body=once(body,'ggml_nelements(y)!=10240','ggml_nelements(y)!=10240*(x->ne[0]-3)')
    body=once(body,'auto*program=qwen_conv_norm_find(ctx->device);const auto&limits=',
              'if(x->ne[0]==5&&!qwen_conv_norm_two_enabled.load(std::memory_order_relaxed))return out;\n    auto*program=qwen_conv_norm_find(ctx->device);const auto&limits=')
    body=once(body,'m.epsilon,m.scale};','m.epsilon,m.scale,uint32_t(x->ne[0]-3),10240,2048,2048};')
    body=once(body,'pc,{10240,1,1});++qwen_conv_norm_executions;',
              'pc,{10240,uint32_t(x->ne[0]-3),1});++qwen_conv_norm_executions;if(x->ne[0]==5)++qwen_conv_norm_two_executions;')
    state=(ROOT/'native/app/gdn_conv_norm_state.inc').read_text()
    state=once(state,'float epsilon,scale;};','float epsilon,scale;uint32_t tokens,ystep,qstep,kstep;};')
    state=once(state,'sizeof(QwenConvNormPC)==36','sizeof(QwenConvNormPC)==52')
    state=once(state,'std::atomic<std::uint64_t>qwen_conv_norm_executions{0};',
               'std::atomic<std::uint64_t>qwen_conv_norm_executions{0},qwen_conv_norm_two_executions{0};std::atomic<bool>qwen_conv_norm_two_enabled{true};')
    state+='\nextern "C" void qwen_app_conv_norm_two_select(bool v){qwen_conv_norm_two_enabled.store(v);}\nextern "C" std::uint64_t qwen_app_conv_norm_two_selections(){return qwen_conv_norm_two_executions.load();}\n'
    headers=[]
    for name,code in [('gdn_conv_norm_two_backend.private.inc',body),('gdn_conv_norm_two_state.private.inc',state)]:
        path=out/name;path.write_text(code,newline='\n');headers.append(path)
    # The base builder reads the shader at this exact repository-relative name.
    # Redirect its Path.read_text/read_bytes input through a verified local view.
    return original_link(parent,out,variants,[*inputs,*headers,source,Path(__file__),ROOT/'native/app/gdn_conv_norm_two.comp'])

def seal(result,workspace,cache,out):
    result['four_next_fixture']=dict(scope=base.SCOPE,headers=[record(out/n)for n in ['gdn_conv_norm_two_backend.private.inc','gdn_conv_norm_two_state.private.inc']])
    original_seal(result,workspace,cache,out)

base.fixture_transform=fixture
base.gpu_transform=gpu
base.assets_transform=lambda text:text
base.link=link
base.seal=seal

if __name__=='__main__':
    # Use the base builder's audited compile/package plumbing while selecting
    # the new shader without modifying the qualified single-token source.
    original_run=base.subprocess.run
    def run(command,*args,**kwargs):
        if isinstance(command,list)and any(str(x).endswith('/gdn_conv_norm.comp')or str(x).endswith('\\gdn_conv_norm.comp')for x in command):
            command=[str(ROOT/'native/app/gdn_conv_norm_two.comp')if str(x).endswith('/gdn_conv_norm.comp')or str(x).endswith('\\gdn_conv_norm.comp')else x for x in command]
        return original_run(command,*args,**kwargs)
    base.subprocess.run=run
    base.main()
