#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rebuild only the changed sort shader and its immutable data/checksum providers."""
import argparse
import copy
import hashlib
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('provider','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.provider)
    need(old['completed'] and old['new_arena_controls']==104 and old['new_shader_lease_controls']==10,'Existing distinct lease and real GGML checks required')
    changed=ROOT/'native/app/gpu_cache_rank_fused_argsort.comp'
    for row in old['inputs']:
        if Path(row['path']).resolve()!=changed.resolve():need(record(row['path'])==row,'An unchanged qualified source changed')
    for key in ('graph','GPU','state'):need(record(old[key]['path'])==old[key],'A reused exact native provider changed')
    a.out.mkdir(parents=True,exist_ok=False);shader=a.out/'fused-argsort.spv';commands=[]
    def run(command,label):
        commands.append(command);host=Path(command[0]).parent
        support=Path(old['commands'][3][0]).parent
        env=dict(os.environ,PATH=str(support)+os.pathsep+str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
        done=subprocess.run(command,capture_output=True,env=env,timeout=180)
        (a.out/(label+'.private.log')).write_bytes(done.stdout+done.stderr);need(done.returncode==0,(done.stdout+done.stderr).decode(errors='replace')[-4000:]+' exit='+str(done.returncode))
    command=old['commands'][2].copy();command[command.index('-o')+1]=str(shader);run(command,'shader')
    command=old['commands'][3].copy();command[-1]=str(shader);run(command,'SPIRV-validate')
    raw=shader.read_bytes();need(len(raw)%4==0 and 20<=len(raw)<=1<<20,'Bounded new SPIRV required')
    data=a.out/'fused-argsort-data.c';data.write_text('#include <stdint.h>\n__attribute__((aligned(4),visibility("hidden"))) const unsigned char qwen_fused_argsort_f32_data[]={'+
        ','.join(map(str,raw))+'};\nconst uint64_t qwen_fused_argsort_f32_len='+str(len(raw))+'ULL;\n',encoding='utf-8',newline='\n')
    header=a.out/'fused_argsort_assets.h';header.write_text('#pragma once\n#include <cstddef>\n#include <cstdint>\nextern "C" {extern const unsigned char qwen_fused_argsort_f32_data[];extern const std::uint64_t qwen_fused_argsort_f32_len;}\n'+
        'inline constexpr std::size_t fused_argsort_original_decoded_bytes='+str(old['original_shader_decoded_bytes'])+';\n'+
        'inline constexpr unsigned char fused_argsort_SHA256[]={'+','.join(map(str,hashlib.sha256(raw).digest()))+'};\n',encoding='utf-8',newline='\n')
    products={}
    for key,source in (('shader_data',data),('shader_wrapper',ROOT/'native/app/gpu_cache_rank_fused_shader.cpp')):
        command=next(c for c in old['commands'] if '-o' in c and c[c.index('-o')+1]==old[key]['path']).copy()
        command[command.index('-c')+1]=str(source);target=a.out/Path(old[key]['path']).name;command[command.index('-o')+1]=str(target)
        if key=='shader_wrapper':command[1:1]=['-I',str(a.out)]
        run(command,key);products[key]=record(target)
    result=copy.deepcopy(old);result.update(products);result.update(shader=record(shader),previous_provider=record(a.provider),
        inputs=[record(r['path']) for r in old['inputs']],source=record(__file__),commands=old['commands']+commands,
        physical_sort_lanes=128,logical_sort_width_up_to=1024,original_bitonic_comparison_and_barrier_order_preserved=True,
        unchanged_lease_and_arena_tests_replayed=0,software_GPU_qualified=False,native_GPU_qualified=False)
    save(a.out/'result.private.json',result);print(dict(completed=True,physical_lanes=128,old_checks_replayed=0,PS5_operations=0))


if __name__=='__main__':main()
