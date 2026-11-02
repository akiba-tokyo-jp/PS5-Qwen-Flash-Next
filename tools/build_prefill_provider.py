#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile paired full unity providers and output selectors for prefill testing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION,load

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','prepared','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    prior=load(args.cache/'current/provenance/native-link.receipt.private.json')
    prepared=load(args.prepared)
    for key in ('control_source','candidate_source'):
        if record(prepared[key]['path'])!=prepared[key]:raise ValueError('Prepared model source differs')
    if prepared['control_source']['sha256']!=prior['frontier_HC']['model_part']['sha256']:
        raise ValueError('Exact current GDN/HC model source required')
    up=args.cache/('upstream/llama.cpp-'+REVISION)
    models=sorted((up/'src/models').glob('*.cpp'));index=models.index(up/'src/models/qwen4exp.cpp')
    group=models[index//16*16:index//16*16+16]
    expected={'plamo3','plm','pockettts','qwen','qwen2','qwen2moe','qwen2vl','qwen3','qwen35',
              'qwen35moe','qwen3moe','qwen3next','qwen3tts','qwen3vl','qwen3vlmoe','qwen4exp'}
    if {p.stem for p in group}!=expected:raise ValueError('Pinned unity source group changed')
    original=prior['frontier_HC']['commands']['model_graph']
    commands=[];artifacts={};inputs=[record(p) for p in group]
    env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out))
    for arm,key in (('control','control_source'),('candidate','candidate_source')):
        source=args.out/(arm+'-model.cpp');selected=Path(prepared[key]['path'])
        source.write_text('/* generated from the pinned 16-model unity group */\n'+
                          ''.join('#include '+json.dumps((selected if p.name=='qwen4exp.cpp' else p).as_posix())+'\n' for p in group),
                          encoding='utf-8',newline='\n')
        obj=args.out/(arm+'-model.o');command=original.copy()
        command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        command += ['-I',str(ROOT/'native/app'),'-I',str(up/'src/models')]
        jobs=[('model',command)]
        wrapper=ROOT/'native/app/prefill_process_candidate.cpp';wrapper_object=args.out/(arm+'-selector.o')
        selector=command.copy();selector[selector.index('-c')+1]=str(wrapper);selector[selector.index('-o')+1]=str(wrapper_object)
        selector += ['-DQWEN_PERF_PREFILL_POST_TRUNK='+str(int(arm=='candidate'))]
        jobs.append(('selector',selector))
        for name,job in jobs:
            result=subprocess.run(job,capture_output=True,timeout=180,env=env)
            (args.out/(arm+'-'+name+'.private.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-3500:])
            commands.append(job)
        artifacts[arm]=dict(model=record(obj),selector=record(wrapper_object),source=record(source))
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-nm.exe'
    def defined(path):
        raw=subprocess.check_output([str(llvm),'--defined-only','--extern-only',str(path)],text=True)
        return {line.split()[-1] for line in raw.splitlines() if line.split()}
    retained=load(args.cache/'current/provenance/retained-relink-inputs.private.json')
    actual=[r for r in retained if r['original_path']==original[original.index('-o')+1]]
    if len(actual)!=1:raise ValueError('One actual current model graph provider required')
    old=defined(actual[0]['path']);control=defined(artifacts['control']['model']['path'])
    if not old<=control:raise ValueError('Reconstructed unity is missing current model symbols')
    report=dict(completed=True,prepared=record(args.prepared),unchanged_model_group_inputs=inputs,
                all_original_external_model_definitions_preserved=True,artifacts=artifacts,commands=commands,
                link_replacement_basename='model_graph.o',extra_link_flag='--wrap=llama_process',
                candidate_output_selection_integrated=True,default_compile_selection=False,
                PS5_operations=0,native_app_relinked=False,native_state_quality_or_speed_validated=False,
                production_adopted=False)
    (args.out/'result.private.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('prepared','unchanged_model_group_inputs','artifacts','commands')}))


if __name__=='__main__':main()
