#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile IQ2 carrier float shaders for an exclusively converted Down model."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','recipes','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();plan=load(a.recipes)
    need(plan['completed'] and plan['all_required_recipes_present'] and
         record(plan['source']['path'])==plan['source'],'Exact pinned generator recipes required')
    a.out.mkdir(parents=True,exist_ok=False);overlay=a.out/'shaders';overlay.mkdir()
    directory=Path(plan['source']['path']).parent
    inputs=[record(a.recipes)]
    for source in directory.glob('*.glsl'):
        inputs.append(record(source));shutil.copyfile(source,overlay/source.name)
    decoder=ROOT/'native/app/iq2_down_carrier.glsl';inputs.append(record(decoder));shutil.copyfile(decoder,overlay/decoder.name)
    funcs=overlay/'dequant_funcs.glsl';text=funcs.read_text()
    start=text.index('#if defined(DATA_A_Q2_0)\n');end=text.index('#if defined(DATA_A_IQ1_S)',start)
    text=text[:start]+'''#if defined(DATA_A_Q2_0)
// This resource is admitted only when every Q2_0 tensor is a sealed IQ2 Down
// carrier. The original control keeps its original resources and payloads.
#include "iq2_down_carrier.glsl"
vec2 dequantize(uint ib,uint iqs,uint a_offset){
    const uint value=(a_offset+ib)*64u+iqs;
    return vec2(iq2_down_decode(value),iq2_down_decode(value+1u));
}
vec4 dequantize4(uint ib,uint iqs,uint a_offset){
    const uint value=(a_offset+ib)*64u+iqs;
    return vec4(iq2_down_decode(value),iq2_down_decode(value+1u),iq2_down_decode(value+2u),iq2_down_decode(value+3u));
}
vec2 get_dm(uint ib,uint a_offset){return vec2(1.0,0.0);}
#endif

''' + text[end:]
    text=once(text,'#if defined(DATA_A_Q2_0) || defined(DATA_A_Q4_0) ||',
                   '#if defined(DATA_A_Q4_0) ||')
    funcs.write_text(text,encoding='utf-8',newline='\n')
    records=[];commands=[];host=a.workspace/'toolchain/shaderc-clang64/clang64/bin'
    validator=a.workspace/'toolchain/msys-clang64/clang64/bin/spirv-val.exe'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    wanted=set(plan['required_float_resources'])
    for recipe in plan['recipes']:
        if recipe['name'] not in wanted:continue
        need(record(recipe['source']['path'])==recipe['source'] and not recipe['coopmat'] and not recipe['coopmat2'],
             'Only exact selected noncooperative float source recipes are admitted')
        source=overlay/Path(recipe['source']['path']).name
        if not source.exists():
            inputs.append(recipe['source']);shutil.copyfile(recipe['source']['path'],source)
            if source.name=='dequant_q2_0.comp':
                text=source.read_text();text=once(text,'layout (binding = 1) writeonly buffer D {D_TYPE data_b[];};',
                    'layout (binding = 1) writeonly buffer D {D_TYPE data_b[];};\n#include "iq2_down_carrier.glsl"')
                begin=text.index('    const uint bits = uint(data_a[ib].qs[il]);')
                text=text[:begin]+'''    data_b[b_idx    ]=D_TYPE(iq2_down_decode(b_idx));
    data_b[b_idx + 1]=D_TYPE(iq2_down_decode(b_idx+1u));
    data_b[b_idx + 2]=D_TYPE(iq2_down_decode(b_idx+2u));
    data_b[b_idx + 3]=D_TYPE(iq2_down_decode(b_idx+3u));
}
'''
                source.write_text(text,encoding='utf-8',newline='\n')
        output=a.out/(recipe['name']+'.spv')
        compile=[str(host/'glslc.exe'),'-fshader-stage=compute','--target-env=vulkan1.2','-O',str(source),'-o',str(output)]
        compile+=['-D'+k+'='+v for k,v in sorted(recipe['defines'].items())]
        for label,job in (('compile',compile),('validate',[str(validator),'--target-env','vulkan1.2',str(output)])):
            commands.append(job);r=subprocess.run(job,capture_output=True,timeout=90,env=env)
            (a.out/(recipe['name']+'-'+label+'.private.log')).write_bytes(r.stdout+r.stderr)
            need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-3500:])
        records.append(dict(name=recipe['name'],artifact=record(output),recipe=recipe))
    need({x['name'] for x in records}==wanted,'Every required float resource must compile and validate')
    save(a.out/'result.private.json',dict(completed=True,recipes=record(a.recipes),shaders=records,commands=commands,
        original_sources=inputs,changed_sources=[record(x) for x in overlay.iterdir()],
        required_converted_Down_layers=list(range(48)),all_Q2_0_tensors_must_be_IQ2_carriers=True,
        original_Q2_0_payloads_allowed=False,hybrid_header_detection_used=False,
        original_control_resources_unchanged=True,MMVQ_and_F16_must_be_disabled=True,
        descriptor_plane_origin_and_cache_view_qualified=False,software_model_shader_qualified=False,
        native_model_shader_qualified=False,PS5_operations=0,production_adopted=False))
    print(dict(completed=True,model_float_shaders=len(records),requires_uniform_all48_Down=True,PS5_operations=0))


if __name__=='__main__':main()
