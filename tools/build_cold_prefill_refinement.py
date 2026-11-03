#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a cold-only P1 refinement without replaying previous graph checks."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','graph-provider','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    graph=load(a.graph_provider);model=graph['artifacts']['candidate']['model']
    need(graph['completed'] and graph['candidate_output_selection_integrated'],'Completed post-trunk graph provenance required')
    graph_rebuilds=0
    if not Path(model['path']).exists():
        original_source=graph['artifacts']['candidate']['source']
        need(record(original_source['path'])==original_source,'Exact preserved original graph source required')
        job=next(c for c in graph['commands'] if '-o' in c and c[c.index('-o')+1]==model['path']).copy()
        rebuilt=a.out/'recreated-post-trunk-model.o';job[job.index('-o')+1]=str(rebuilt)
        run=subprocess.run(job,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/'recreate-retired-model.private.log').write_bytes(run.stdout+run.stderr)
        need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
        actual=record(rebuilt);need(all(actual[k]==model[k] for k in ('bytes','sha256')),'Recreated graph provider must be byte identical')
        model=actual;graph_rebuilds=1
    else:need(record(model['path'])==model,'Exact completed graph provider changed')
    base=load(a.current/'provenance/selected-entry-build.private.json');profile=load(base['application_policy']['path'])
    need(record(profile['source']['path'])==profile['source'],'Exact selected completed-stage R1 entry required')
    source_dir=Path(profile['source']['path']).parent
    for header in source_dir.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    # Compile only the new selector scope. Original graph/math and its earlier
    # host/native numerical comparisons are reused, not rerun here.
    (a.out/'llama.h').write_text('#pragma once\n#include <cstdint>\nusing llama_token=int32_t;struct llama_context;struct llama_sampler;struct llama_token_data_array;\nenum llama_process_type {LLAMA_PROCESS_TYPE_DECODE=1};\n')
    (a.out/'llama-batch.h').write_text('#pragma once\n#include "llama.h"\n#include <array>\n#include <vector>\nstruct llama_batch_ext{struct token{bool output=false;std::array<int32_t,4>pos{};};std::vector<token>tokens;};\ninline bool llama_batch_ext_set_output_logits(llama_batch_ext*b,int32_t i,bool v){b->tokens.at(i).output=v;return true;}\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';test=a.out/'cold-prefill-scope.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),
             str(ROOT/'tests/prefill_cold_candidate_test.cpp'),'-o',str(test)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    run=subprocess.run(command,capture_output=True,timeout=60,env=env);(a.out/'host-build.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
    checks=[]
    for length in (1,2,31,32,33,63,64,65):
        for enabled in (False,True):
            args=[str(test),str(length),str(int(enabled))]
            run=subprocess.run(args,capture_output=True,timeout=10,env=env)
            (a.out/(str(length)+'-'+str(int(enabled))+'.private.log')).write_bytes(run.stdout+run.stderr)
            need(run.returncode==0,'New cold/retained/prefix selector control failed')
            checks.append(dict(tokens=length,candidate=enabled,three_ordered_phases=True,decode_widths=[1,2],
                               rejected_overlap_and_mode_change=True,exception_restores_flags=True))
    original_wrapper=ROOT/'native/app/prefill_process_candidate.cpp'
    wrapper=ROOT/'native/app/prefill_cold_candidate.cpp';target=a.out/'cold-selector.o'
    target_command=next(c for c in graph['commands'] if '-c' in c and 'selector' in c[c.index('-o')+1]).copy()
    target_command=[x for x in target_command if not x.startswith('-DQWEN_PERF_PREFILL_POST_TRUNK=')]
    target_command[target_command.index('-c')+1]=str(wrapper);target_command[target_command.index('-o')+1]=str(target)
    run=subprocess.run(target_command,capture_output=True,timeout=120,env=env);(a.out/'target-selector.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
    # Remove host-only type stubs before compiling either real native entry.
    (a.out/'llama.h').rename(a.out/'host-llama.stub');(a.out/'llama-batch.h').rename(a.out/'host-llama-batch.stub')
    original=Path(profile['source']['path']).read_text()
    marker='            const auto &result=trial.run(request,[&](const auto &bound){'
    need(original.count(marker)==1,'One exact actual ordinary-request invocation required')
    entries={};commands=[command,target_command]
    for arm,enabled in (('control',False),('candidate',True)):
        source=a.out/(arm+'-entry.private.cpp')
        text='extern "C" void qwen_P1_select_request(unsigned,bool);\n'+original.replace(marker,
            '            qwen_P1_select_request(ordinal,'+str(enabled).lower()+');\n'+marker,1)
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                     'model_file_identity','model_directory_identity','bind_resident_main_SELF'):
            need(body(original,name)==body(text,name),'An original memory, identity or integrity guard changed')
        source.write_text(text,encoding='utf-8',newline='\n');obj=a.out/(arm+'-entry.o')
        job=base['commands'][1].copy()
        job=[str(a.out) if x==str(source_dir) else x for x in job]
        overlay=load(job[job.index('-ivfsoverlay')+1])
        for root in overlay['roots']:
            path=Path(root['external-contents'])
            if (a.out/path.name).is_file():root['external-contents']=(a.out/path.name).resolve().as_posix()
        overlay_path=a.out/(arm+'-selected-view.private.json');save(overlay_path,overlay)
        job[job.index('-ivfsoverlay')+1]=str(overlay_path)
        job[job.index('-c')+1]=str(source);job[job.index('-o')+1]=str(obj)
        if '-MF' in job:job[job.index('-MF')+1]=str(a.out/(arm+'.private.d'))
        run=subprocess.run(job,capture_output=True,timeout=120,env=env);(a.out/(arm+'-entry.private.log')).write_bytes(run.stdout+run.stderr)
        need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
        commands.append(job);entries[arm]=dict(source=record(source),entry=record(obj),cold_output_crop=enabled,
            later_two_requests_full_output=True,reader=base['reader'])
    save(a.out/'result.private.json',dict(completed=True,graph_provider=record(a.graph_provider),model_provider_reused=model,
        selector=record(target),entries=entries,new_selector_controls=checks,commands=commands,
        source_inputs=[record(wrapper),record(original_wrapper),record(ROOT/'tests/prefill_cold_candidate_test.cpp')],
        selected_R1_entry=profile['source'],actual_PS5_ABI_compiled=True,earlier_graph_checks_replayed=0,
        retired_graph_artifact_rebuilt_byte_exact=bool(graph_rebuilds),native_model_qualified=False,native_model_rate_measured=False,production_adopted=False,PS5_operations=0))
    print(json.dumps(dict(completed=True,new_scope_controls=16,real_native_entries=2,necessary_retired_graph_rebuilds=graph_rebuilds,PS5_operations=0)))


if __name__=='__main__':main()
