#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce the selected pooled-checkpoint context before adding the qualified MTP capacity."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_cache_capacity_1125 import recipes
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from checkpoint_trial_source import transform
from driver_table_storage import sections
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();native=load(a.current/'provenance/native-link.receipt.private.json')
    retained=load(a.current/'provenance/retained-relink-inputs.private.json')
    providers=[r for r in retained if Path(r['original_path']).name=='context.o'];need(len(providers)==1,'One selected context required')
    provider=providers[0];need(record(provider['path'])=={k:provider[k] for k in ('path','bytes','sha256')},'Selected context changed')
    jobs={json.dumps(c):c for c in recipes(native) if '-o'in c and c[c.index('-o')+1]==provider['original_path']}
    need(len(jobs)==1,'One actual selected context recipe required');command=next(iter(jobs.values())).copy()
    upstream=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/llama-context.cpp'
    text=transform(upstream.read_text(encoding='utf-8'),True).replace('#include "checkpoint_device_trial.h"','#include "checkpoint_device_pool_trial.h"')
    text=once(text,'ggml_backend_alloc_ctx_tensors_from_buft(mbuf_cur.ctx.get(), buft)','qwen_checkpoint_trial::allocate(mbuf_cur,buft)')
    text=once(text,'void llama_context::sched_new(size_t max_nodes, bool parallel) {','void llama_context::sched_new(size_t max_nodes, bool parallel) {\n    sched.reset();')
    text=once(text,'    gf_res_reserve.reset(new llm_graph_result(max_nodes));\n    gf_res_prev_active = nullptr;',
        '    gf_res_prev_active=nullptr;gf_res_reserve.reset();\n    gf_res_reserve.reset(new llm_graph_result(max_nodes));')
    a.out.mkdir(parents=True,exist_ok=False);source=a.out/'context.private.cpp';obj=a.out/'context.o'
    original=command[command.index('-c')+1];source.write_text('#line 1 '+json.dumps(original)+'\n'+text,encoding='utf-8',newline='\n')
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'context.private.d')
    result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    old,new=sections(Path(provider['path']).read_bytes()),sections(obj.read_bytes())
    differences=['section_count'] if len(old)!=len(new) else [l['name'] for l,r in zip(old,new)
        if any(l[k]!=r[k] for k in ('name','type','flags','bytes','info','alignment','data'))]
    exact=record(obj)['sha256']==provider['sha256']
    save(a.out/'result.private.json',dict(completed=True,selected_object_byte_exact=exact,source=record(source),artifact=record(obj),
        actual_provider={k:provider[k] for k in ('path','bytes','sha256')},command=command,upstream=record(upstream),
        inputs=[record(ROOT/'tools/checkpoint_trial_source.py'),record(ROOT/'tools/build_checkpoint_pool_fixture.py'),
            record(ROOT/'tools/build_post_top2_normal.py'),record(ROOT/'native/app/checkpoint_device_pool_trial.h')],
        section_differences=differences,PS5_operations=0,native_MTP_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,selected_object_byte_exact=exact,section_differences=differences,PS5_operations=0)))


if __name__=='__main__':main()
