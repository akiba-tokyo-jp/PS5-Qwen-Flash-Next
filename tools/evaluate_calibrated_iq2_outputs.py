#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare isolated quantized matmul outputs on their real calibration operands."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save

ALIGN=16384


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','capture','importance','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--samples',type=Path,action='append',required=True);a=p.parse_args()
    # Bound this quantization-only CPU reference before importing NumPy/BLAS.
    os.environ['OPENBLAS_NUM_THREADS']='6';os.environ['MKL_NUM_THREADS']='6';os.environ['OMP_NUM_THREADS']='6'
    import numpy as np
    package=types.ModuleType('gguf');package.__path__=[str(a.cache/('upstream/llama.cpp-'+REVISION)/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.quants import IQ2_XXS,Q2_K,Q2_0
    capture=load(a.capture);importance=load(a.importance)
    need(capture['completed'] and capture['native_and_host_whole_SHA256_equal'] and importance['completed'] and
        importance['up_and_down_operands_independently_observed'] and not importance['synthetic_uniform_importance_used'] and
        importance['native_capture']==record(a.capture),'The complete actual native calibration and its sparse moments are required')
    need(record(capture['raw']['path'])==capture['raw'],'Complete calibration stream changed')
    samples=[load(path) for path in a.samples];matrices={}
    for sample in samples:
        need(sample['completed'] and sample['all_nine_Experts_actually_visited'] and not sample['synthetic_uniform_importance_used'] and
            sample['real_importance']==record(a.importance) and record(sample['pack']['path'])==sample['pack'],'Calibrated sample provenance changed')
        for row in sample['matrices']:
            key=(row['layer'],int(row['role']=='down'),row['expert']);need(key not in matrices and row['C_and_Python_IQ2_decode_exact'],'Distinct independently decoded samples required')
            matrices[key]=(row,sample)
    need(len(matrices) in (9,18),'One or both nine-matrix roles required')
    actual={key:[] for key in matrices};records=0;evaluations=set()
    with Path(capture['raw']['path']).open('rb') as stream:
        header=stream.read(ALIGN);need(len(header)==ALIGN and header[:8]==b'QWENACT1','Complete native stream header required')
        while True:
            header=stream.read(ALIGN)
            if not header:break
            need(len(header)==ALIGN and header[:8]==b'QACTREC1','Exact bounded record header required')
            evaluation,role,layer,k,tokens,xslots,selected,payload,padded,weight_type=struct.unpack_from('<Q6I2QI',header,8)
            need(role in (0,1) and layer<48 and k==(640 if role else 2560) and 1<=tokens<=32 and 1<=selected<=10 and
                xslots in (1,selected) and (not role or xslots==selected) and payload==tokens*xslots*k*4 and
                padded==(payload+ALIGN-1)//ALIGN*ALIGN,'Actual original operand geometry differs')
            ids=np.frombuffer(header,dtype='<i4',count=tokens*selected,offset=64).reshape(tokens,selected)
            raw=stream.read(padded);need(len(raw)==padded and not any(raw[payload:]),'Complete padded payload required')
            values=np.frombuffer(raw,dtype='<f4',count=payload//4).reshape(tokens,xslots,k)
            need(np.isfinite(values).all(),'Actual operands must remain finite')
            for token in range(tokens):
                for slot in range(selected):
                    key=(layer,role,int(ids[token,slot]))
                    if key in actual:actual[key].append(values[token,0 if xslots==1 else slot].copy())
            records+=1;evaluations.add(evaluation)
    need(records==importance['records']==96*len(evaluations) and len(evaluations)==importance['evaluations'],'All original evaluations required')
    a.out.mkdir(parents=True,exist_ok=False);verified_sources={};results=[];outputs=[]
    for key,(row,sample) in sorted(matrices.items()):
        need(len(actual[key])==row['actual_activation_samples']>0,'Every actually selected Expert operand must be retained')
        inputs=np.stack(actual[key]);moment=row['importance'];need(record(moment['path'])==moment,'Original real moments changed')
        data=np.load(moment['path']);index=list(map(int,data['expert_ids'])).index(row['expert']);sums=np.zeros(row['columns'],np.float64)
        for vector in inputs:sums+=np.square(vector,dtype=np.float64)
        need(int(data['counts'][index])==len(inputs) and np.array_equal(sums,data['sum_squares'][index]),'Actual vectors must reproduce every original F64 moment exactly')
        source=Path(row['original_source']['path']);before=source.stat();stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
        if source not in verified_sources:
            verified_sources[source]=record(source);need(verified_sources[source]==row['original_source'],'Whole original BF16 source changed')
        with source.open('rb') as stream:
            stream.seek(row['original_offset']);raw=stream.read(row['rows']*row['columns']*2)
        need(hashlib.sha256(raw).hexdigest()==row['original_BF16_sha256'],'The original BF16 Expert slice differs')
        original=(np.frombuffer(raw,dtype='<u2').astype(np.uint32)<<16).view(np.float32).reshape(row['rows'],row['columns'])
        reference=inputs.astype(np.float64)@original.astype(np.float64).T;norm=float(np.square(reference).sum());need(norm>0 and np.isfinite(reference).all(),'Nonzero finite original output required')
        formats={};saved={'input':inputs,'original_BF16_output_F64':reference}
        for label,decoder,block_bytes in (('Q2_0' if key[1] else 'Q2_K',Q2_0 if key[1] else Q2_K,18 if key[1] else 84),('IQ2_XXS',IQ2_XXS,66)):
            part=row[label]
            with Path(sample['pack']['path']).open('rb') as stream:stream.seek(part['offset']);encoded=stream.read(part['bytes'])
            need(len(encoded)==part['bytes'] and hashlib.sha256(encoded).hexdigest()==part['sha256'],'An encoded component extent changed')
            weights=decoder.dequantize(np.frombuffer(encoded,dtype=np.uint8).reshape(-1,block_bytes)).reshape(row['rows'],row['columns'])
            need(np.isfinite(weights).all(),'The complete independent decoded matrix must be finite')
            output=inputs.astype(np.float64)@weights.astype(np.float64).T;error=output-reference
            formats[label]=dict(output_NRMSE=float(np.sqrt(np.square(error).sum()/norm)),maximum_absolute_output_error=float(np.max(np.abs(error))),
                all_outputs_finite=bool(np.isfinite(output).all()),output_values=int(output.size))
            saved[label+'_output_F64']=output
        path=a.out/('layer-'+str(key[0]).zfill(2)+'-'+row['role']+'-Expert-'+str(key[2])+'.npz');np.savez_compressed(path,**saved);outputs.append(record(path))
        need(stamp(source.stat())==stamp(before),'Original source metadata changed during component scoring')
        control='Q2_0' if key[1] else 'Q2_K'
        value=dict(layer=key[0],role=row['role'],expert=key[2],real_input_vectors=len(inputs),all_original_F64_moments_exact=True,
            formats=formats,IQ2_output_NRMSE_lower_than_control=formats['IQ2_XXS']['output_NRMSE']<formats[control]['output_NRMSE'])
        results.append(value);print(json.dumps(value),flush=True)
    need(record(capture['raw']['path'])==capture['raw'],'Actual calibration stream changed during scoring')
    save(a.out/'result.private.json',dict(completed=True,capture=record(a.capture),importance=record(a.importance),samples=[record(path) for path in a.samples],
        source=record(__file__),matrices=results,outputs=outputs,whole_original_sources=list(verified_sources.values()),
        all_actual_operand_moments_independently_reproduced=True,original_weight_source='BF16',arithmetic='F64 CPU isolated matrix products after independent format decoding',
        in_sample_calibration_operands=True,held_out_validation=False,prompts=1,full_model_inference=False,broader_answer_quality_qualified=False,
        native_kernel_qualified_by_this_scope=False,whole_speed_qualified=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,matrices=len(results),IQ2_lower_output_error=sum(row['IQ2_output_NRMSE_lower_than_control'] for row in results),in_sample_only=True,PS5_operations=0)))


if __name__=='__main__':main()
