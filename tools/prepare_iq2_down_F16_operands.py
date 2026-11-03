#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare six changed FP16-domain wide references without repeating decode cases."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import types
from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','component','native-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
    import numpy as np
    component,native=load(a.component),load(a.native_proof)
    need(component['completed'] and component['paired_down_carrier'] and native['completed'] and
         native['native_passed'] and native['ordinary_exit_observed'] and native['current_seven_restored_and_native_hashed'],
         'The original component and completed native F32 arithmetic are required')
    need(record(component['GPU_cases']['path'])==component['GPU_cases'],'The actual operand collection changed')
    cases=copy.deepcopy(load(component['GPU_cases']['path']))
    need(len(cases['cases'])==12,'The twelve original layer/width records are required')
    package=types.ModuleType('gguf');package.__path__=[str(a.cache/('upstream/llama.cpp-'+REVISION)/'gguf-py/gguf')]
    sys.modules['gguf']=package
    from gguf.quants import IQ2_XXS
    a.out.mkdir(parents=True,exist_ok=False)
    layer=None;decoded={};checks=[];source_inputs=[record(a.component),record(a.native_proof),component['GPU_cases']]
    for row in cases['cases']:
        if row['width']<=2:continue
        if row['layer']!=layer:
            layer=row['layer'];decoded={}
        need(row['width'] in (30,32) and row['selected']==10 and row['planes']==10,
             'Only the six changed wide arithmetic cases are admitted')
        for key in ('weights','inputs','ids'):
            need(record(row[key]['path'])==row[key],'An actual operand blob changed')
            source_inputs.append(copy.deepcopy(row[key]))
        weights=Path(row['weights']['path']).read_bytes();need(len(weights)==4608000,'Ten complete carrier planes required')
        x=np.fromfile(row['inputs']['path'],dtype='<f4').reshape(row['width'],10,640)
        x=x.astype(np.float16).astype(np.float32)
        need(np.isfinite(x).all(),'Rounded actual inputs must remain finite')
        ids=np.fromfile(row['ids']['path'],dtype='<u4').reshape(row['width'],10)
        need(int(ids.max())<10,'Only the original ten planes may be indexed')
        y=np.empty((row['width'],10,2560),dtype='<f8')
        grouped={}
        for plane in range(10):
            base=plane*460800;payload=weights[base+64:base+64+422400]
            digest=hashlib.sha256(payload).hexdigest()
            need(weights[base:base+2]==b'\x00\x7e','The sealed carrier header must remain present')
            if digest not in decoded:
                w=IQ2_XXS.dequantize(np.frombuffer(payload,np.uint8).reshape(-1,66)).reshape(2560,640)
                w=w.astype(np.float16).astype(np.float64)
                need(np.isfinite(w).all(),'Rounded decoded weights must remain finite')
                decoded[digest]=w
            grouped.setdefault(digest,[]).append(plane)
        for digest,planes in grouped.items():
            tokens,slots=np.where(np.isin(ids,planes))
            y[tokens,slots]=(decoded[digest]@x[tokens,slots].astype(np.float64).T).T
        need(np.isfinite(y).all(),'The complete new F64 output must be finite')
        tag='layer-'+str(layer)+'-width-'+str(row['width'])
        inputs,expected=a.out/(tag+'-FP16-exact-inputs.bin'),a.out/(tag+'-FP16-weights-F64-reference.bin')
        inputs.write_bytes(x.astype('<f4').tobytes());expected.write_bytes(y.tobytes())
        row['inputs'],row['expected']=record(inputs),record(expected)
        row['reference_domain']='F64 of FP16-rounded decoded weights and FP16-exact F32 inputs'
        checks.append(dict(layer=layer,width=row['width'],values=y.size,finite=True,unique_encoded_matrices=len(grouped),
            weights_unchanged=True,ids_unchanged=True,inputs_exactly_FP16=True))
    need(len(checks)==6,'Exactly six changed references must complete')
    cases['F16_storage_FP32_accumulation']=True
    case_path=a.out/'GPU-cases.private.json';save(case_path,cases)
    packed=copy.deepcopy(cases);blobs={}
    for row in packed['cases']:
        for key in ('weights','inputs','ids','expected'):blobs[row[key]['sha256']]=row[key]
    for row in packed['shader']:blobs[row['artifact']['sha256']]=row['artifact']
    blobs[packed['tables']['sha256']]=packed['tables'];parts=[];pack=a.out/'paired-Down-F16.pack'
    with pack.open('xb') as stream:
        for index,blob in enumerate(blobs.values()):
            raw=Path(blob['path']).read_bytes()
            need(len(raw)==blob['bytes'] and hashlib.sha256(raw).hexdigest()==blob['sha256'],'A packed operand differs')
            stream.write(bytes((-stream.tell())%16384))
            parts.append(dict(key='BLOB_'+str(index),offset=stream.tell(),bytes=len(raw),sha256=blob['sha256']))
            stream.write(raw)
        stream.write(bytes((-stream.tell())%16384))
    pack_record=record(pack);need(pack_record['bytes']<=128<<20,'The original bounded component-pack limit remains')
    keys={r['sha256']:r['key'] for r in parts}
    for row in packed['cases']:
        for key in ('weights','inputs','ids','expected'):row[key]['path']=keys[row[key]['sha256']]
    for row in packed['shader']:row['artifact']['path']=keys[row['artifact']['sha256']]
    packed['tables']['path']=keys[packed['tables']['sha256']]
    remote='/app0/qwen-runtime/paired-Down-'+pack_record['sha256'][:24]+'.bin'
    header='#pragma once\n#include <cstdint>\nstruct NativePart{const char*key;std::uint64_t offset,bytes;const char*sha256;};\n'
    header+='inline constexpr NativePart paired_parts[]={\n'+''.join('{'+json.dumps(r['key'])+','+str(r['offset'])+'ULL,'+str(r['bytes'])+'ULL,'+json.dumps(r['sha256'])+'},\n' for r in parts)+'};\n'
    header+='inline constexpr const char*paired_pack_path='+json.dumps(remote)+';\n'
    header+='inline constexpr std::uint64_t paired_pack_bytes='+str(pack_record['bytes'])+'ULL;\n'
    header+='inline constexpr const char*paired_pack_sha256='+json.dumps(pack_record['sha256'])+';\n'
    header+='inline constexpr char paired_cases_json[]='+json.dumps(json.dumps(packed,separators=(',',':')))+';\n'
    assets=a.out/'paired_down_assets.h';assets.write_text(header,newline='\n')
    save(a.out/'result.private.json',dict(completed=True,component=record(a.component),native_F32_proof=record(a.native_proof),
        GPU_cases=record(case_path),assets=record(assets),component_pack=dict(local=pack_record,application_path=remote),parts=parts,
        F16_storage_FP32_accumulation=True,wide_cases=checks,reused_decode_cases=6,new_native_graphs=6,
        original_tolerance_unchanged=True,original_weights_and_ids_unchanged=True,CPU_math_threads=1,
        source_inputs=source_inputs,PS5_operations=0,native_F16_or_model_speed_qualified=False))
    print(dict(completed=True,new_wide_references=6,reference_values=sum(r['values'] for r in checks),
        pack_bytes=pack_record['bytes'],CPU_math_threads=1,PS5_operations=0))


if __name__=='__main__':
    main()
