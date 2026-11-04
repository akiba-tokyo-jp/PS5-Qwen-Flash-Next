#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconstruct and compile the actual selected graph before GPU-ranking changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_cache_capacity_1125 import recipes
from build_performance_quantizer import record
from build_routing_winners import graph_source as routing_graph
from build_six_candidate_screen import graph_source as six_graph
from build_speculative_batch_probe import once
from driver_table_storage import sections
from start_success_route import load,need,save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('current','cache','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    native=load(args.current/'provenance/native-link.receipt.private.json')
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    matches=[r for r in retained if Path(r['original_path']).name=='graph.o'];need(len(matches)==1,'One actual graph provider required')
    provider=matches[0];need(record(provider['path'])=={k:provider[k] for k in ('path','bytes','sha256')},'Actual graph provider changed')
    candidates={json.dumps(c):c for c in recipes(native) if '-o' in c and c[c.index('-o')+1]==provider['original_path']}
    need(len(candidates)==1,'One actual selected graph compilation recipe required');command=next(iter(candidates.values())).copy()
    upstream=args.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/llama-graph.cpp'
    text=six_graph(routing_graph(upstream.read_text(encoding='utf-8'))).replace('#include "six_candidate_policy.h"','#include "normal_performance_policy.h"')
    expected=native['normal_performance']['actual_sources']['graph']
    need(len(text.encode())==expected['bytes'] and hashlib.sha256(text.encode()).hexdigest()==expected['sha256'],
         'The complete original normal graph must be reconstructed exactly')
    text='#include "next_five_policy.h"\n'+text
    text=once(text,'n_expert_used=qwen_app::decode_policy_experts(qwen_app_route_mode(),unsigned(n_tokens));',
                   'n_expert_used=qwen_next_experts();')
    source=args.out/'graph.private.cpp';original_source=command[command.index('-c')+1]
    source.write_text('#line 1 '+json.dumps(original_source)+'\n'+text,encoding='utf-8',newline='\n')
    obj=args.out/'graph.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'graph.private.d')
    result=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
    old,new=sections(Path(provider['path']).read_bytes()),sections(obj.read_bytes())
    differences=[]
    if len(old)!=len(new):differences.append('section_count')
    else:
        for left,right in zip(old,new):
            if any(left[k]!=right[k] for k in ('name','type','flags','bytes','info','alignment','data')):
                differences.append(left['name'])
    exact=record(obj)['sha256']==provider['sha256']
    report=dict(completed=True,actual_provider={k:provider[k] for k in ('path','bytes','sha256')},
        source=record(source),artifact=record(obj),upstream=record(upstream),command=command,
        exact_original_normal_graph_source_reconstructed=True,selected_next_five_transformation_applied=True,
        selected_object_byte_exact=exact,section_differences=differences,PS5_operations=0,
        GPU_ranking_implemented=False,native_speed_or_quality_measured=False,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('actual_provider','source','artifact','upstream','command')}))


if __name__=='__main__':main()
