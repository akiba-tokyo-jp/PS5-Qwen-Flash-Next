#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect original packaged SPIR-V precision without selecting or executing it."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from shader_storage import elf_objects,unpack
from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import current_files


def arithmetic(text):
    types={}
    for line in text.splitlines():
        match=re.match(r'\s*(%\w+) = OpTypeFloat (\d+)\s*$',line)
        if match:types[match[1]]=int(match[2])
        match=re.match(r'\s*(%\w+) = OpTypeVector (%\w+) \d+\s*$',line)
        if match and match[2] in types:types[match[1]]=types[match[2]]
    counts=Counter()
    for line in text.splitlines():
        match=re.match(r'\s*%\w+ = (OpFConvert|OpFAdd|OpFSub|OpFMul|OpFDiv|OpDot|OpExtInst) (%\w+) ',line)
        if match and match[2] in types:
            op=match[1]
            if op=='OpExtInst':
                if not re.search(r'\bFma\b',line):continue
                op='GLSL_Fma'
            counts[str(types[match[2]])+'_'+op]+=1
    return dict(sorted(counts.items()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','workspace','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();inputs=load(a.current/'provenance/retained-relink-inputs.private.json')
    locations=next(r for r in inputs if Path(r['original_path']).name=='shader-locations.o')
    expected={k:locations[k] for k in ('path','bytes','sha256')};need(record(expected['path'])==expected,'Exact currently linked shader locations required')
    storage=current_files(a.current)[-1];need(record(storage['path'])=={k:storage[k] for k in ('path','bytes','sha256')},'Exact selected original shader storage required')
    symbols=elf_objects(Path(expected['path']).read_bytes());blob=Path(storage['path']).read_bytes()
    names=['dequant_q2_k','matmul_id_f16_f32','matmul_id_f16_f32_fp32','matmul_id_iq2_xxs_f32',
           'matmul_id_iq2_xxs_f32_fp32','matmul_id_iq2_xxs_f32_f16acc','matmul_id_q2_k_q8_1','matmul_id_q2_k_q8_1_fp32']
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));rows=[]
    for name in names:
        token=symbols[name+'_data'];magic,offset,size,original=struct.unpack('<8sQII',token)
        need(magic==b'QWSPVX01' and offset+size<=len(blob) and symbols[name+'_len']==struct.pack('<Q',size),'Exact linked external token and bounds required')
        decoded=unpack(blob[offset:offset+size]);need(len(decoded)==original,'Decoded original shader size changed')
        path=a.out/(name+'.spv');path.write_bytes(decoded);assembly=a.out/(name+'.spvasm')
        for command in ([str(host/'spirv-val.exe'),'--target-env','vulkan1.2',str(path)],
                        [str(host/'spirv-dis.exe'),str(path),'-o',str(assembly)]):
            run=subprocess.run(command,capture_output=True,env=env,timeout=30)
            need(run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')[-2000:])
        text=assembly.read_text();rows.append(dict(name=name,original_SPIRV=record(path),disassembly=record(assembly),
            validation_passed=True,float16_type_declared=bool(re.search(r'OpTypeFloat 16\b',text)),
            typed_float_operation_counts=arithmetic(text)))
    result=dict(completed=True,currently_linked_locations=expected,selected_storage={k:storage[k] for k in ('path','bytes','sha256')},
        inputs=[record(Path(__file__)),record(host/'spirv-dis.exe'),record(host/'spirv-val.exe')],shaders=rows,
        original_encoded_and_SPIRV_bytes_unchanged=True,dispatch_selection_observed=False,native_pipeline_selection_not_inferred=True,
        CPU_reference_correction_qualified=False,PS5_operations=0,GPU_dispatches=0,production_adopted=False)
    save(a.out/'result.private.json',result)
    for r in rows:print(json.dumps({k:r[k] for k in ('name','float16_type_declared','typed_float_operation_counts')}))


if __name__=='__main__':main()
