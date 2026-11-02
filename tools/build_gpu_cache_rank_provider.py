#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build original-graph shadow qualification and a GPU multiply-ranking candidate."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','prepared','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--backend-qualification',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    prepared=load(args.prepared)
    need(prepared['completed'] and prepared['selected_object_byte_exact'] and not prepared['section_differences'],
         'A byte-exact reconstruction of the actual selected graph is required')
    for key in ('source','artifact','actual_provider'):need(record(prepared[key]['path'])==prepared[key],'Actual reconstructed graph changed')
    source=ROOT/'native/app/gpu_cache_rank_candidate.cpp';test=ROOT/'tests/gpu_cache_rank_state_test.cpp'
    inputs=[record(p) for p in (source,test,ROOT/'native/app/gpu_cache_rank_state.h',ROOT/'native/app/gpu_cache_rank_graph.h')]
    host=args.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe';target=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    env=dict(os.environ,PATH=str(host.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out),TEMP=str(args.out))
    commands=[]
    def run(command,name):
        result=subprocess.run(command,capture_output=True,timeout=180,env=env)
        (args.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:]);commands.append(command)
    executable=args.out/'rank-state-check.exe'
    run([str(host),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(test),'-o',str(executable)],'host-compile')
    run([str(executable)],'host-run')
    artifacts={}
    for name,validation in (('qualification',1),('control',0),('candidate',0)):
        obj=args.out/(name+'-state.o')
        command=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
            '-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),'-std=c++17','-fexceptions','-fcxx-exceptions',
            '-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2','-ffunction-sections','-fdata-sections',
            '-DQWEN_GPU_RANK_VALIDATE_SHADOW='+str(validation),'-I',str(ROOT/'native/app'),
            '-I',str(args.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/ggml/include'),
            '-c',str(source),'-o',str(obj)]
        run(command,name+'-state');artifacts[name]=dict(state=record(obj),shadow_validation=bool(validation))
    folder=args.out/'candidate';folder.mkdir();graph=folder/'graph.private.cpp';obj=folder/'graph.o'
    text=Path(prepared['source']['path']).read_text(encoding='utf-8')
    text='#include "gpu_cache_rank_graph.h"\n'+text
    text=once(text,'selection_probs=ggml_map_custom1(ctx0,selection_probs,qwen_app_route_rank,1,reinterpret_cast<void*>(std::uintptr_t(il)));',
                   'selection_probs=qwen_app::build_gpu_cache_rank(ctx0,res,selection_probs,unsigned(il));')
    graph.write_text(text,encoding='utf-8',newline='\n')
    command=prepared['command'].copy();command[command.index('-c')+1]=str(graph);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-DQWEN_GPU_RANK_VALIDATE_BACKEND='+str(int(args.backend_qualification))]
    command[1:1]=['-I',str(ROOT/'native/app')]
    if '-MF' in command:command[command.index('-MF')+1]=str(folder/'graph.private.d')
    run(command,'candidate-graph');artifacts['candidate']['graph']=record(obj)
    need(all(record(r['path'])==r for r in inputs),'GPU rank source inputs changed during compilation')
    report=dict(completed=True,prepared=record(args.prepared),artifacts=artifacts,commands=commands,inputs=inputs,
        control_graph_is_original_retained_provider=True,latched_state_host_fault_and_arithmetic_controls_passed=True,
        native_shadow_qualification_required=True,original_nonnegative_score_multiplication_preserved=True,
        GPU_coefficients_per_layer_bytes=2048,GPU_coefficients_per_graph_bytes=98304,
        GPU_input_publications_per_graph_evaluation=1,maximum_decode_rows=2,fixed_Top2_scope_only=True,
        GGML_input_lifetime_and_graph_reuse_hooks_used=True,source_weight_or_driver_changes=0,
        link_flags=['--wrap=qwen_app_route_begin','--wrap=qwen_app_route_resident','--wrap=qwen_app_routing_event_begin',
                    '--wrap=qwen_app_route_rank','--wrap=qwen_app_route_stats'],
        GPU_ranking_source_implemented=True,backend_result_buffer_diagnostics=bool(args.backend_qualification),
        all_hit_continuation_implemented=False,PS5_operations=0,
        native_GPU_numerics_or_speed_qualified=False,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('prepared','artifacts','commands','inputs','link_flags')}))


if __name__=='__main__':main()
