#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a new two-Expert fixture using the qualified native build plumbing."""
from pathlib import Path
import json,re
import build_four_next_gate_up as base
from build_speculative_batch_probe import once
from expert_q4 import record

ROOT=Path(__file__).resolve().parents[1]
SHADER=ROOT/'native/app/gate_up_top2.comp'
OLD_SHADER=ROOT/'native/app/expert_gate_up_q2.comp'
FIXTURE=ROOT/'native/app/expert_gate_up_fixture.h'
BACKEND=ROOT/'native/app/expert_gate_up_backend.inc'
original_read=Path.read_text
original_run=base.subprocess.run
original_link=base.link
original_seal=base.seal
base.SCOPE=dict(base.SCOPE,schema='ps5-qwen-top2-gate-up-fixture-v1',GPU_graphs=180,
               cases=5,selected_Experts=2,distinct_and_duplicate_ids=True,
               vectorized_Q2_bytes=True,local_threads=64)

def fixture(text):
    text=once(text,'for(unsigned tokens:{1u,2u,3u}){',
              'for(unsigned scenario=0;scenario<5;++scenario){\n'
              '        const unsigned tokens=scenario==4?3:scenario/2+1;const bool duplicate=scenario<4&&(scenario%2);')
    text=text.replace('GGML_TYPE_I32,6,tokens','GGML_TYPE_I32,2,tokens')
    text=re.sub(r'\b(tokens|t)\*6(?![0-9])',lambda m:m[1]+'*2',text)
    text=re.sub(r'\be<6(?![0-9])','e<2',text)
    text=once(text,'selected[t*2+e]=slots[(e+t)%3];','selected[t*2+e]=slots[duplicate?t%3:(e+t)%3];')
    text=once(text,'unsigned slot=(e+t)%3;','unsigned slot=duplicate?t%3:(e+t)%3;')
    text=once(text,'graphs<128','graphs<192')
    if 'slot*640+row'not in text or 'slot*240'in text:raise ValueError('Original F64 Expert row stride must remain 640')
    return once(text,'{{"tokens",tokens},{"arms",arms}',
                '{{"tokens",tokens},{"duplicate_ids",duplicate},{"selected_Experts",2},{"arms",arms}')

def backend(text):
    text=once(text,'w->ne[2]>3073','w->ne[2]>3713')
    text=once(text,'ids->ne[0]!=6','ids->ne[0]!=2')
    text=once(text,'y->ne[1]!=6','y->ne[1]!=2')
    text=once(text,'uint32_t(gate->ne[2]),6,','uint32_t(gate->ne[2]),2,')
    return once(text,'pc,{640*128,6,','pc,{640*64,2,')

def read(path,*args,**kwargs):
    text=original_read(path,*args,**kwargs)
    if path==FIXTURE:return fixture(text)
    if path==BACKEND:return backend(text)
    return text

def run(command,*args,**kwargs):
    if isinstance(command,list):command=[str(SHADER)if str(x)==str(OLD_SHADER)else x for x in command]
    return original_run(command,*args,**kwargs)

def link(parent,out,variants,inputs):
    cmd,text=variants['gpu']
    text=once(text,'"main",5,sizeof(QwenGateUpPC),{128,1,1}',
              '"main",5,sizeof(QwenGateUpPC),{64,1,1}')
    variants['gpu']=(cmd,text)
    # Resolve the generated headers ahead of the old immutable source directory.
    # The fixture is a private transformed source, never an edit to its control.
    local=out/'expert_gate_up_fixture.h';local.write_text(fixture(original_read(FIXTURE)),newline='\n')
    local_backend=out/'expert_gate_up_backend.inc';local_backend.write_text(backend(original_read(BACKEND)),newline='\n')
    entry_cmd,entry_text=variants['entry'];entry_text=once(entry_text,'#include "expert_gate_up_fixture.h"',
        '#include '+json.dumps(local.resolve().as_posix()));variants['entry']=(entry_cmd,entry_text)
    gpu_cmd,gpu_text=variants['gpu'];gpu_text=once(gpu_text,'#include "expert_gate_up_backend.inc"',
        '#include '+json.dumps(local_backend.resolve().as_posix()));variants['gpu']=(gpu_cmd,gpu_text)
    return original_link(parent,out,variants,[*inputs,SHADER,local,local_backend,Path(__file__)])

def seal(result,workspace,cache,out):
    row=result['GDN_conv_normalization_fixture'];row['shader_command']=[str(SHADER)if x==str(OLD_SHADER)else x for x in row['shader_command']]
    row['compiled_shader_source']=record(SHADER)
    result['post_top2_gate_up']=dict(scope=base.SCOPE,implementation=record(Path(__file__)),
        complete_fixtures=[record(out/'expert_gate_up_fixture.h'),record(out/'expert_gate_up_backend.inc')])
    return original_seal(result,workspace,cache,out)

if __name__=='__main__':
    Path.read_text=read;base.subprocess.run=run;base.link=link;base.seal=seal
    try:base.main()
    finally:Path.read_text=original_read;base.subprocess.run=original_run
