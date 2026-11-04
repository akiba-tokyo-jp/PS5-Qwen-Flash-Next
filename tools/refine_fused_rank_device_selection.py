#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Correct integrated-GPU admission without replaying unchanged sort/arena checks."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','provider','software-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.provider);software=load(a.software_proof)
    need(old['completed'] and software['completed'] and software['build']==record(a.provider) and software['positive_fences']==64,
         'Completed actual software proof and unchanged128-lane provider required')
    for key in ('GPU','shader','shader_data','shader_wrapper','state','graph_source','graph_header'):
        need(record(old[key]['path'])==old[key],'An unchanged qualified native provider changed')
    live=ROOT/'native/app/gpu_cache_rank_fused_graph.h';previous=Path(old['graph_header']['path']).read_text(encoding='utf-8');changed=live.read_text(encoding='utf-8')
    begin='inline ggml_tensor*fused_rank_output';end='class FusedCacheRankInput'
    need(previous[previous.index(begin):previous.index(end)]==changed[changed.index(begin):changed.index(end)],
         'All104 completed alias/view checks must cover the exact unchanged helper')
    expected=previous.replace('namespace qwen_app {','namespace qwen_app {\ninline bool fused_rank_device_type(enum ggml_backend_dev_type type){\n    return type==GGML_BACKEND_DEVICE_TYPE_GPU||type==GGML_BACKEND_DEVICE_TYPE_IGPU;\n}',1).replace(
        'if(ggml_backend_dev_type(ggml_backend_get_device(b))==GGML_BACKEND_DEVICE_TYPE_GPU){',
        'if(fused_rank_device_type(ggml_backend_dev_type(ggml_backend_get_device(b)))){',1)
    need(changed==expected,'Only the GPU/IGPU predicate may change')
    a.out.mkdir(parents=True,exist_ok=False);header=a.out/live.name;shutil.copyfile(live,header)
    test=a.out/'device-check.cpp';test.write_text('#include "gpu_cache_rank_fused_graph.h"\n#include <cassert>\nint main(){using namespace qwen_app;'+
        'assert(fused_rank_device_type(GGML_BACKEND_DEVICE_TYPE_GPU));assert(fused_rank_device_type(GGML_BACKEND_DEVICE_TYPE_IGPU));'+
        'assert(!fused_rank_device_type(GGML_BACKEND_DEVICE_TYPE_CPU));assert(!fused_rank_device_type(GGML_BACKEND_DEVICE_TYPE_ACCEL));'+
        'assert(!fused_rank_device_type(GGML_BACKEND_DEVICE_TYPE_META));}\n',encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';exe=a.out/'device-check.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app')]
    for folder in ('src','include','ggml/include','ggml/src','vendor'):command+=['-I',str(up/folder)]
    command += [str(test),'-o',str(exe)];jobs=[]
    def run(job,label):
        jobs.append(job);done=subprocess.run(job,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
        (a.out/(label+'.private.log')).write_bytes(done.stdout+done.stderr)
        need(done.returncode==0,(done.stdout+done.stderr).decode(errors='replace')[-3000:])
    run(command,'host-compile');run([str(exe)],'host-five-device-types')
    job=next(c for c in reversed(old['commands']) if '-c' in c and c[c.index('-c')+1]==old['graph_source']['path']).copy()
    job[1:1]=['-I',str(a.out)];target=a.out/'graph.o';job[job.index('-o')+1]=str(target)
    if '-MF' in job:job[job.index('-MF')+1]=str(a.out/'graph.private.d')
    run(job,'native-graph')
    result=copy.deepcopy(old);result.update(graph=record(target),graph_header=record(header),source=record(__file__),
        previous_provider=record(a.provider),inputs=[record(r['path']) for r in old['inputs']]+[record(header),record(test)],
        discrete_and_integrated_GPU_device_controls=5,CPU_ACCEL_META_refused=True,unchanged_sort_and_arena_checks_replayed=0,
        actual_arena_helper_byte_exact=True,commands=old['commands']+jobs,native_GPU_qualified=False)
    save(a.out/'result.private.json',result)
    reused=copy.deepcopy(software);reused.update(build=record(a.out/'result.private.json'),original_software_proof=record(a.software_proof),
        metadata_only_provider_supplement=True,shader_and_software_inputs_byte_exact=True,prior_software_cases_replayed=0)
    save(a.out/'software-reuse.private.json',reused)
    print(dict(completed=True,new_device_controls=5,old_checks_replayed=0,PS5_operations=0))


if __name__=='__main__':main()
