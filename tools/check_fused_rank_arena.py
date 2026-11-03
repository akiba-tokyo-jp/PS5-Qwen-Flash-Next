#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the revised fused output views with real GGML; reuse completed component checks."""
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
    for name in ('workspace','cache','provider','reference-build','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.provider)
    need(old['completed'] and old['new_shader_lease_controls']==10 and old['shader_SPIRV_validated'] and
         old['GPU_executable_sections_byte_exact'],'Completed distinct shader/lease checks required')
    for key in ('GPU','shader','shader_data','shader_wrapper','state','graph_source'):
        need(record(old[key]['path'])==old[key],'A reused compiled component changed')
    for r in old['inputs']:
        if Path(r['path']).name!='gpu_cache_rank_fused_graph.h':need(record(r['path'])==r,'A reused shader/lease source changed')
    a.out.mkdir(parents=True,exist_ok=False)
    header=a.out/'gpu_cache_rank_fused_graph.h';shutil.copyfile(ROOT/'native/app/gpu_cache_rank_fused_graph.h',header)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    library=a.reference_build/'ggml/src/libggml-base.dll.a';runtime=a.reference_build/'bin/ggml-base.dll'
    need(library.is_file() and runtime.is_file(),'The existing pinned GGML host reference must be present')
    executable=a.out/'arena-check.exe';env=dict(os.environ,PATH=str(runtime.parent)+os.pathsep+str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    compile=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),
        '-I',str(up/'src'),'-I',str(up/'include'),'-I',str(up/'ggml/include'),'-I',str(up/'ggml/src'),'-I',str(up/'vendor'),
        str(ROOT/'tests/gpu_cache_rank_fused_arena_test.cpp'),str(library),'-o',str(executable)]
    commands=[]
    def run(command,label):
        commands.append(command);done=subprocess.run(command,capture_output=True,timeout=180,env=env)
        (a.out/(label+'.private.log')).write_bytes(done.stdout+done.stderr)
        need(done.returncode==0,(done.stdout+done.stderr).decode(errors='replace')[-4000:])
    run(compile,'host-arena-compile');run([str(executable)],'host-arena-execute')
    target=a.out/'graph.o';job=next(c for c in old['commands'] if '-c' in c and c[c.index('-c')+1]==old['graph_source']['path']).copy()
    job[1:1]=['-I',str(a.out)];job[job.index('-o')+1]=str(target)
    if '-MF' in job:job[job.index('-MF')+1]=str(a.out/'graph.private.d')
    run(job,'native-revised-graph')
    result=copy.deepcopy(old);result.update(graph=record(target),source=record(__file__),
        previous_provider=record(a.provider),new_arena_controls=104,actual_GGML_F32_I32_view_aliases_checked=True,
        disjoint_all48_layer_ranges_for_both_decode_widths_checked=True,
        prior_shader_and_lease_checks_replayed=0,arena_test=record(ROOT/'tests/gpu_cache_rank_fused_arena_test.cpp'),
        graph_header=record(header),commands=old['commands']+commands,
        inputs=[record(r['path']) for r in old['inputs']]+[record(header),record(ROOT/'tests/gpu_cache_rank_fused_arena_test.cpp'),record(runtime),record(library)])
    save(a.out/'result.private.json',result);print(dict(completed=True,new_arena_controls=104,old_checks_replayed=0,PS5_operations=0))


if __name__=='__main__':main()
