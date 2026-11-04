#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recover exact Q2 shader recipes from the pinned upstream generator on PC."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from start_success_route import load, need, save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    upstream=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    directory=upstream/'ggml/src/ggml-vulkan/vulkan-shaders'
    original=directory/'vulkan-shaders-gen.cpp';text=original.read_text()
    start=text.index('    std::string out_path = join_paths(output_dir, name + ".spv");',text.index('void string_to_spv(std::string name'))
    end=text.index('\nvoid matmul_shaders(',start)
    # Keep every actual variant/define decision. Replace only the emitter;
    # no shader compile, native runtime or generated header is run here.
    text=text[:start]+'''    if(name.find("q2_0")==std::string::npos||name.find("tq2_0")!=std::string::npos)return;
    std::cout<<name<<'\\t'<<source<<'\\t'<<fp16<<'\\t'<<coopmat<<'\\t'<<coopmat2;
    for(const auto&d:defines)std::cout<<'\\t'<<d.first<<'='<<d.second;
    std::cout<<'\\n';
}
''' + text[end:]
    need(text.count('    write_output_files();')==1,'One output-only generator boundary required')
    text=text.replace('    write_output_files();','    // The manifest emitter performs no shader/header writes.',1)
    source=a.out/'generator-manifest.private.cpp';source.write_text(text,encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'shader-recipes.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2',str(source),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    jobs=[command,[str(exe),'--output-dir',str(a.out)]]
    for index,job in enumerate(jobs):
        result=subprocess.run(job,capture_output=True,timeout=90,env=env)
        (a.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,(result.stdout+result.stderr).decode(errors='replace')[-3000:])
    recipes=[]
    for line in result.stdout.decode().splitlines():
        columns=line.split('\t');need(len(columns)>=5,'Complete emitted shader recipe required')
        name,filename,fp16,coop,coop2,*defines=columns
        recipes.append(dict(name=name,source=record(directory/filename),fp16=fp16=='1',coopmat=coop=='1',
            coopmat2=coop2=='1',defines=dict(x.split('=',1) for x in defines)))
    selected=load(a.current/'provenance/native-link.receipt.private.json')['lossless_shader_storage']['shaders']
    shaders={x['name']:x for x in selected if 'q2_0' in x['name'] and 'tq2_0' not in x['name']}
    found={x['name'] for x in recipes}
    needed={k for k in shaders if 'q8_1' not in k and not any(s in k for s in ('_cm1','_cm2','_int8','_dot2')) and
            (k.startswith(('mul_mat_','dequant_','get_rows_')) or k in ('cpy_q2_0_f32','cpy_q2_0_f16'))}
    missing=sorted(needed-found)
    need(not missing,'Every eligible selected float shader needs an actual generator recipe: '+str(missing))
    save(a.out/'result.private.json',dict(completed=True,source=record(original),emitter=record(source),commands=jobs,
        recipes=recipes,selected_Q2_resources=list(shaders.values()),required_float_resources=sorted(needed),
        all_required_recipes_present=True,unselected_generated_variants=sorted(found-set(shaders)),
        model_profile_requires_MMVQ_and_F16_disabled=True,shader_binaries_reconstructed=False,
        model_layout_qualified=False,PS5_operations=0))
    print(dict(completed=True,generated_recipes=len(recipes),required_float_resources=len(needed),PS5_operations=0))


if __name__=='__main__':main()
