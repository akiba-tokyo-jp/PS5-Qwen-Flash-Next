#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run a finite desktop-only paired Down shader check against independent outputs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import time

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','build','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--first-case-only',action='store_true');p.add_argument('--software-ICD',type=Path)
    p.add_argument('--carrier',action='store_true',help='Exercise the distinct source-bound Q2_0-plane IQ2 carrier shaders')
    a=p.parse_args();built=load(a.build)
    qualified_inputs=(built.get('paired_down_carrier') and built['all_complete_carriers_independently_inverse_verified'] and
        built['original_IQ2_operands_and_F64_references_preserved']) if a.carrier else built['all14745600_decoded_F32_values_byte_exact']
    need(built['completed'] and qualified_inputs and not built['native_GPU_execution'],
        'Exact paired decoder and validated SPIRV component required')
    need(record(built['GPU_cases']['path'])==built['GPU_cases'],'GPU cases changed');cases=load(built['GPU_cases']['path'])
    inputs={}
    for row in cases['cases']:
        for key in ('weights','inputs','ids','expected'):inputs[row[key]['path']]=row[key]
    for row in cases['shader']:inputs[row['artifact']['path']]=row['artifact']
    if cases.get('buffer_tables'):inputs[cases['tables']['path']]=cases['tables']
    inputs[str(a.build.resolve())]=record(a.build);inputs[str(Path(built['GPU_cases']['path']).resolve())]=built['GPU_cases']
    need(all(record(row['path'])==row for row in inputs.values()),'An independently prepared GPU input changed')
    a.out.mkdir(parents=True,exist_ok=False);source=a.out/'desktop.cpp';shutil.copyfile(ROOT/'tools/check_iq2_paired_down_gpu.cpp',source)
    if a.carrier:
        text=source.read_text();old='weights.size()==422400u*planes'
        need(text.count(old)==1 and cases['paired_down_carrier'] and cases['carrier_plane_bytes']==460800 and not cases['buffer_tables'],
             'Only the exact changed carrier storage geometry is admitted')
        source.write_text(text.replace(old,'weights.size()==460800u*planes'),newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    exe=a.out/'paired-down-desktop.exe';command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(a.workspace/'toolchain/Vulkan-Headers/include'),'-I',str(a.cache/('upstream/llama.cpp-'+REVISION)/'vendor'),str(source),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    if a.software_ICD:
        icd=a.software_ICD.resolve();configuration=load(icd);library=(icd.parent/configuration['ICD']['library_path']).resolve()
        need(icd.name=='vk_swiftshader_icd.json' and library.name=='vk_swiftshader.dll' and library.is_relative_to(icd.parent),
            'One exact installed SwiftShader ICD is admitted only as a software SPIRV reference')
        inputs[str(icd)]=record(icd);inputs[str(library)]=record(library);env['VK_DRIVER_FILES']=str(icd)
    run=subprocess.run(command,capture_output=True,timeout=240,env=env);(a.out/'compile.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
    output=a.out/'desktop-GPU.private.json';execute=[str(exe),built['GPU_cases']['path'],str(output)]+(['--first-case-only'] if a.first_case_only else [])+(['--software-reference'] if a.software_ICD else [])
    save(a.out/'intent.private.json',dict(build=record(a.build),source=record(source),inputs=list(inputs.values()),command=command,execute=execute,
        maximum_Vulkan_dispatches=(1 if a.first_case_only else 24)*(40 if a.software_ICD else 1),software_SPIRV_reference=bool(a.software_ICD),physical_GPU_execution=not bool(a.software_ICD),
        scoped_driver_files=env.get('VK_DRIVER_FILES'),PS5_operations=0,automatic_retries=0))
    deadline=time.monotonic()+300;notice=0;positive=0
    with (a.out/'desktop.private.log').open('xb') as log:
        child=subprocess.Popen(execute,stdout=log,stderr=subprocess.STDOUT,env=env)
        while child.poll() is None:
            observed={}
            if output.exists():
                try:observed=load(output)
                except json.JSONDecodeError:pass
            if observed.get('unknown_completion'):
                save(a.out/'retained-owner.private.json',dict(pid=child.pid,unknown_completion=True,process_retained=True,resubmitted=False,PS5_operations=0))
                raise RuntimeError('Desktop GPU completion unknown; child and resources retained, no retry')
            completed=observed.get('positive_reference_dispatches',0)
            if completed>positive:positive=completed;deadline=time.monotonic()+60
            if time.monotonic()>=deadline:
                save(a.out/'retained-owner.private.json',dict(pid=child.pid,unknown_completion=True,process_retained=True,resubmitted=False,PS5_operations=0))
                raise RuntimeError('Desktop observation deadline reached; process retained, no retry')
            if time.monotonic()>=notice:print(json.dumps(dict(phase='desktop-only-paired-Down',process_running=True,PS5_operations=0)),flush=True);notice=time.monotonic()+30
            time.sleep(1)
    need(output.exists(),'Desktop GPU pre-dispatch setup failed; inspect its log')
    result=load(output);need(result['completed'] and not result['unknown_completion'] and result['all_GPU_resources_positively_retired'],
        'Desktop GPU owners must positively retire')
    need(all(record(row['path'])==row for row in inputs.values()),'A checked component input changed during desktop verification')
    save(a.out/'result.private.json',dict(completed=True,all_outputs_passed=result['all_outputs_passed'],desktop_GPU=result['desktop_GPU'],
        native_desktop=record(output),Vulkan_dispatches=result['positive_reference_dispatches'],GPU_dispatches=0 if a.software_ICD else result['positive_reference_dispatches'],
        software_SPIRV_reference=bool(a.software_ICD),physical_GPU_execution=not bool(a.software_ICD),all_GPU_resources_positively_retired=True,
        build=record(a.build),source=record(source),desktop_executable=record(exe),PS5_operations=0,PS5_kernel_qualified=False,
        whole_model_quality_qualified=False,whole_model_speed_qualified=False,production_adopted=False,automatic_retries=0))
    print(json.dumps(dict(completed=True,desktop_backend=result['desktop_GPU'],Vulkan_dispatches=result['positive_reference_dispatches'],software_SPIRV_reference=bool(a.software_ICD),all_outputs_passed=result['all_outputs_passed'],PS5_operations=0)))
    need(child.returncode==0 and result['all_outputs_passed'],'Returned numerical desktop negative; no repeated unchanged dispatch')


if __name__=='__main__':main()
