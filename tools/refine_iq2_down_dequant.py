#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Refine only the unqualified wide-path dequant resource; reuse twelve shaders."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','provider','full-view-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    need(not any(a.out.iterdir()),'Only an empty, never-compiled host scope may start')
    provider=load(a.provider);old=load(provider['shaders']['path']);view=load(a.full_view_proof)
    need(record(provider['shaders']['path'])==provider['shaders'] and provider['completed'] and
         view['completed'] and view['all_outputs_and_guards_passed'] and view['full_view_cases']==18,
         'The exact completed original shader and nonzero-view controls are required')
    view_plan=load(view['plan']['path']);view_provider=load(view_plan['provider']['path'])
    need(record(view_plan['provider']['path'])==view_plan['provider'] and
         view_provider['shaders']==provider['shaders'],'The software scope must use the same thirteen immutable shaders')
    previous=load(provider['software_proof']['path']);prior_plan=load(previous['plan']['path'])
    need(previous['completed'] and previous['actual_model_matvec_shaders']==6 and previous['shape_cases']==18 and
         previous['all_outputs_passed'] and record(prior_plan['software_ICD']['path'])==prior_plan['software_ICD'],
         'The exact already qualified six-resource scope and software ICD must be reused')
    def run(command,label,timeout=90,environment=None):
        command=list(map(str,command));r=subprocess.run(command,capture_output=True,timeout=timeout,env=environment or env)
        (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-3000:]);return command
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    source=ROOT/'native/app/iq2_down_dequant_packed_half.comp';shader=a.out/'dequant_q2_0.spv'
    shader_host=a.workspace/'toolchain/shaderc-clang64/clang64/bin'
    shader_env=dict(env,PATH=str(shader_host)+os.pathsep+env['PATH'])
    compile_shader=run([shader_host/'glslc.exe','-fshader-stage=compute','--target-env=vulkan1.2','-O',
        '-I'+str(ROOT/'native/app'),source,'-o',shader],'shader-compile',environment=shader_env)
    run([host/'spirv-val.exe','--target-env','vulkan1.2',shader],'shader-validate')
    raw=shader.read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw);at=5;capabilities=[]
    while at<len(words):
        count,opcode=words[at]>>16,words[at]&65535
        need(count>0 and at+count<=len(words),'Complete actual SPIR-V required')
        if opcode==17:capabilities.append(words[at+1])
        at+=count
    need(capabilities==[1],'The packed-half resource must require only Shader capability')
    api=a.out/'model_shader_desktop_API.private.h';shutil.copyfile(view_plan['API']['path'],api)
    need('#define MODEL_STORAGE16_REQUIRED 0' in api.read_text() and '#define MODEL_STORAGE8_REQUIRED 0' in api.read_text(),
         'The actual new resource requires neither unsupported storage feature')
    component=load(previous['component']['path']);cases=load(component['GPU_cases']['path'])['cases']
    cases=[r for r in cases if r['width']==1]
    need(len(cases)==3 and {r['layer']for r in cases}=={0,23,47},'Three complete original carrier banks required')
    for r in cases:need(record(r['weights']['path'])==r['weights'],'An immutable complete bank changed')
    manifest=a.out/'cases.private.json';save(manifest,dict(shader=record(shader),cases=cases))
    checker=ROOT/'tools/check_iq2_down_dequant_gpu.cpp';exe=a.out/'packed-half-software.exe'
    # The qualified host command compiles one source directly, without -c.
    command=[str(a.out) if v==str(Path(view['plan']['path']).parent) else v for v in view_plan['command']]
    old_source=next(i for i,v in enumerate(command) if str(v).endswith('.cpp'))
    command[old_source]=str(checker);command[command.index('-o')+1]=str(exe)
    run(command,'checker-compile')
    env['VK_DRIVER_FILES']=prior_plan['software_ICD']['path']
    output=a.out/'software.private.json';run([exe,manifest,output],'software',timeout=600)
    result=load(output)
    need(result['completed'] and result['all_GPU_resources_positively_retired'] and len(result['cases'])==3 and
         all(r['passed'] and r['FP16_storage_bits_exact'] and r['values']==16384000 and
             r['canaries_exact'] and r['positive_fence'] for r in result['cases']),
         'All49152000 FP16 outputs and original descriptor guards must pass')
    built=copy.deepcopy(old);changed=next(r for r in built['shaders']if r['name']=='dequant_q2_0')
    changed.update(artifact=record(shader),recipe=dict(name='dequant_q2_0',source=record(source),
        defines={},fp16=False,coopmat=False,coopmat2=False,FP16_output_storage_via_packed_uint32=True))
    built.update(ancestor=provider['shaders'],packed_half_dequant_refinement=True,reused_shader_resources=12,
        all_non_declaration_words_byte_exact=False,only_unused_capability_extension_declarations_changed=False,
        packed_half_software_proof=record(output),complete_FP16_values_verified=49152000,
        original_FP16_output_ABI_preserved=True,original_sources=old['original_sources']+[record(source),
            record(ROOT/'native/app/iq2_down_carrier.glsl'),record(checker),record(Path(__file__))],
        changed_sources=[record(source)],commands=[compile_shader,command],PS5_operations=0)
    build=a.out/'build.private.json';save(build,built)
    proof=copy.deepcopy(previous);proof.update(build=record(build),reused_matvec_proof=provider['software_proof'],
        actual_model_matvec_shaders=6,shape_cases=18,reused_matvec_cases=18,new_matvec_cases=0,
        packed_half_software=record(output),packed_half_complete_values=49152000,
        original_FP16_output_ABI_preserved=True,new_positive_dequant_cases=3,PS5_operations=0)
    save(a.out/'result.private.json',proof)
    print(json.dumps(dict(completed=True,new_dequant_cases=3,complete_FP16_values=49152000,reused_other_shaders=12,PS5_operations=0)))


if __name__=='__main__':main()
