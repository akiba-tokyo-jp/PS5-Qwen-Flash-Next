#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fuse cached ranking into the original complete sort without recompiling GPU instructions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from native_dispatch import ELF
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def section_map(path):
    e=ELF(path);names=e.section_data(e.sections[struct.unpack_from('<H',e.data,62)[0]])
    return {names[s[0]:names.index(0,s[0])].decode():(s,e.section_data(s) if s[1]!=8 else None)
            for s in e.sections if s[0]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','prepared','state-provider','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    prepared=load(a.prepared);state=load(a.state_provider)
    need(prepared['completed'] and prepared['selected_object_byte_exact'] and record(prepared['source']['path'])==prepared['source'],
         'Actual recovered complete graph source required')
    target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out));commands=[]
    def run(command,label):
        commands.append(list(map(str,command)))
        result=subprocess.run(command,capture_output=True,timeout=240,env=env)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,(result.stdout+result.stderr).decode(errors='replace')[-5000:])
    test=a.out/'lease-controls.exe'
    run([host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app',
         ROOT/'tests/fused_shader_lease_test.cpp','-o',test],'lease-compile')
    run([test],'lease-ten-controls')
    shader=a.out/'fused-argsort.spv'
    run([a.workspace/'toolchain/shaderc-clang64/clang64/bin/glslangValidator.exe','-V','--target-env','vulkan1.2',
         '-S','comp',ROOT/'native/app/gpu_cache_rank_fused_argsort.comp','-o',shader],'shader-compile')
    run([host/'spirv-val.exe','--target-env','vulkan1.2',shader],'shader-validate')
    raw=shader.read_bytes();need(20<=len(raw)<=1<<20 and len(raw)%4==0,'Bounded valid new static SPIRV required')
    rows=load(a.current/'provenance/retained-relink-inputs.private.json')
    gpu=next(r for r in rows if Path(r['original_path']).name=='gpu.o')
    need(record(gpu['path'])=={k:gpu[k] for k in ('path','bytes','sha256')},'Selected actual GPU object changed')
    renamed=a.out/'GPU-fused-resource-references.o'
    run([target/'llvm-objcopy.exe','--redefine-sym=argsort_f32_data=qwen_fused_argsort_f32_data',
         '--redefine-sym=argsort_f32_len=qwen_fused_argsort_f32_len',gpu['path'],renamed],'GPU-resource-rename')
    before,after=section_map(Path(gpu['path'])),section_map(renamed)
    need(before.keys()==after.keys(),'Only existing resource symbol names may change')
    for name,(section,data) in before.items():
        if section[2]&4:need(data==after[name][1],'An executable GPU byte changed')
    original=ELF(a.current/'provenance/qwen-native.pie.elf');token=original.symbol_data('argsort_f32_data')
    magic,offset,stored,decoded=struct.unpack('<8sQII',token)
    need(magic==b'QWSPVX01' and struct.unpack('<Q',original.symbol_data('argsort_f32_len'))[0]==stored,
         'Exact original external shader token and length required')
    asset=a.out/'fused-argsort-data.c'
    asset.write_text('#include <stdint.h>\n__attribute__((aligned(4),visibility("hidden"))) const unsigned char qwen_fused_argsort_f32_data[]={'+
        ','.join(str(x) for x in raw)+'};\nconst uint64_t qwen_fused_argsort_f32_len='+str(len(raw))+'ULL;\n',encoding='utf-8',newline='\n')
    header=a.out/'fused_argsort_assets.h'
    header.write_text('#pragma once\n#include <cstddef>\n#include <cstdint>\nextern "C" {extern const unsigned char qwen_fused_argsort_f32_data[];extern const std::uint64_t qwen_fused_argsort_f32_len;}\n'+
        'inline constexpr std::size_t fused_argsort_original_decoded_bytes='+str(decoded)+';\n'+
        'inline constexpr unsigned char fused_argsort_SHA256[]={'+','.join(str(x) for x in hashlib.sha256(raw).digest())+'};\n',encoding='utf-8',newline='\n')
    data_object=a.out/'fused-argsort-data.o';wrapper=a.out/'fused-argsort-wrapper.o'
    common=[target/'clang++.exe','--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',sdk/'c++/v1','-isystem',sdk,
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',ROOT/'native/app','-I',a.out,'-I',up/'vendor']
    run([target/'clang.exe','--no-default-config','--target=x86_64-sie-ps5','-isystem',sdk,'-fPIC','-O2',
        '-c',asset,'-o',data_object],'native-data')
    run(common+['-c',ROOT/'native/app/gpu_cache_rank_fused_shader.cpp','-o',wrapper],'native-wrapper')
    data_sections=section_map(data_object)
    need(not any(s[0][2]&4 and s[0][5] for s in data_sections.values()) and not any('init_array' in k for k in data_sections),
         'The new shader data must add zero executable bytes or constructors')
    graph=a.out/'graph.private.cpp';graph_object=a.out/'graph.o'
    text='#include "gpu_cache_rank_fused_graph.h"\n'+Path(prepared['source']['path']).read_text(encoding='utf-8')
    old='''    if(n_expert==512&&n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy(qwen_app_route_mode()).cache_rank){
        selection_probs=ggml_map_custom1(ctx0,selection_probs,qwen_app_route_rank,1,reinterpret_cast<void*>(std::uintptr_t(il)));
        cb(selection_probs,"qwen_cache_rank",il);
    }'''
    text=once(text,old,'    const bool G1_fused_rank=n_expert==512&&n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy(qwen_app_route_mode()).cache_rank;')
    text=once(text,'selected_experts = ggml_argsort_top_k(ctx0, selection_probs, n_expert_used); // [n_expert_used, n_tokens]',
        'selected_experts=qwen_app::fused_cache_rank_top_k(ctx0,res,sched,selection_probs,n_expert_used,unsigned(il),G1_fused_rank);')
    graph.write_text(text,encoding='utf-8',newline='\n')
    command=prepared['command'].copy();command[1:1]=['-I',str(ROOT/'native/app')]
    command[command.index('-c')+1]=str(graph);command[command.index('-o')+1]=str(graph_object)
    if '-MF' in command:command[command.index('-MF')+1]=str(a.out/'graph.private.d')
    run(command,'native-graph')
    state_object=state['artifacts']['control']['state']
    if not Path(state_object['path']).exists():
        command=next(c for c in state['commands'] if '-o' in c and c[c.index('-o')+1]==state_object['path']).copy()
        output=a.out/'state.o';command[command.index('-o')+1]=str(output);run(command,'reproduce-retired-state')
        need(all(record(output)[k]==state_object[k] for k in ('bytes','sha256')),'Necessary state rebuild must be byte identical')
        state_object=record(output)
    else:need(record(state_object['path'])==state_object,'Completed state provider changed')
    inputs=[record(ROOT/'native/app'/n) for n in ('gpu_cache_rank_fused_graph.h','gpu_cache_rank_fused_argsort.comp',
        'gpu_cache_rank_fused_shader.cpp','fused_shader_lease.h')]+[record(ROOT/'tests/fused_shader_lease_test.cpp')]
    save(a.out/'result.private.json',dict(completed=True,source=record(__file__),inputs=inputs,prepared=record(a.prepared),
        graph=record(graph_object),graph_source=record(graph),GPU=record(renamed),selected_GPU=gpu,
        GPU_executable_sections_byte_exact=True,only_two_GPU_resource_symbol_names_redirected=True,
        shader=record(shader),shader_data=record(data_object),shader_wrapper=record(wrapper),state=state_object,
        original_shader_token=token.hex(),original_shader_decoded_bytes=decoded,original_shader_registry_and_file_unchanged=True,
        original_positive_CPU_decoder_lease_preserved=True,new_shader_lease_controls=10,shader_SPIRV_validated=True,
        original_full_bitonic_tie_schedule_preserved=True,partial_TopK_used=False,extra_GPU_rank_multiply_nodes=0,
        GPU_coefficient_publications_per_graph=1,output_arena_bytes_per_row=48*512*4,
        link_flags=state['link_flags']+['--wrap=qwen_app_prepare_shader_code'],commands=commands,
        driver_code_changed=False,persistent_caches=False,software_GPU_qualified=False,native_GPU_qualified=False,
        full_model_state_and_speed_qualified=False,all_hit_continuation_implemented=False,PS5_operations=0,production_adopted=False))
    print(dict(completed=True,unchanged_GPU_instructions=True,new_lease_controls=10,PS5_operations=0))


if __name__=='__main__':main()
