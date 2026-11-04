#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Refine existing IQ2 block scales on fit outputs; score separate decode operands."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save


def refine(np,encoded,decoder,fit,target,columns,rows,sweeps,ridge,cap):
    """Joint residual coordinate updates; each block owns one FP16 scale."""
    blocks=encoded.reshape(-1,66).copy();original=blocks[:,:2].copy().reshape(-1).view('<f2').astype(np.float64)
    unit=blocks.copy();unit[:,0]=0;unit[:,1]=0x3c
    coefficients=decoder.dequantize(unit).reshape(-1,256).astype(np.float64)
    decoded=decoder.dequantize(blocks).reshape(rows,columns).astype(np.float64)
    baseline=fit.astype(np.float64)@decoded.T;residual=target-baseline
    d=original.copy();fit=fit.astype(np.float64)
    pairs=columns%256!=0
    need(not pairs or columns==640 and rows%2==0,'Only the actual paired640 or aligned2560 geometry is admitted')
    per=5 if pairs else columns//256;groups=rows//2 if pairs else rows
    coefficients=coefficients.reshape(groups,per,256);scales=d.reshape(groups,per);anchor=original.reshape(groups,per)
    # Segment definitions are explicit original row/column coordinates. A
    # paired middle block contributes128 columns to each adjacent output row.
    segments=([[(0,0,256,0)],[(0,256,512,0)],[(0,512,640,0),(1,0,128,128)],
               [(1,128,384,0)],[(1,384,640,0)]] if pairs else
              [[(0,256*b,256*(b+1),0)] for b in range(per)])
    contributions=[]
    for b,parts in enumerate(segments):
        contributions.append([(parity,fit[:,first:last]@coefficients[:,b,offset:offset+last-first].T)
                              for parity,first,last,offset in parts])
    step=2 if pairs else 1
    for sweep in range(sweeps):
        for b,parts in enumerate(contributions):
            denominator=sum(np.square(v).sum(axis=0) for _,v in parts)
            numerator=sum((residual[:,parity::step]*v).sum(axis=0) for parity,v in parts)
            old=scales[:,b].copy();base=anchor[:,b]
            desired=old+np.divide(numerator,denominator,out=np.zeros_like(old),where=denominator>0)
            desired=(desired+ridge*base)/(1+ridge)
            if cap is not None:desired=np.clip(desired,base*(1-cap),base*(1+cap))
            desired=np.where(base>0,np.maximum(desired,0),base)
            rounded=desired.astype('<f2').astype(np.float64)
            delta=rounded-old
            improvement=2*delta*numerator-delta*delta*denominator
            penalty=ridge*denominator*((rounded-base)**2-(old-base)**2)
            chosen=np.where(improvement>=penalty,rounded,old);delta=chosen-old;scales[:,b]=chosen
            for parity,v in parts:residual[:,parity::step]-=v*delta
    result=blocks.copy();result[:,:2]=d.astype('<f2').view(np.uint8).reshape(-1,2)
    need(np.array_equal(result[:,2:],blocks[:,2:]) and np.isfinite(d).all() and (d>=0).all(),
         'Only finite nonnegative FP16 scales may change; all64 code bytes stay exact')
    actual=decoder.dequantize(result).reshape(rows,columns).astype(np.float64)
    independently_recomputed=fit@actual.T
    need(np.allclose(independently_recomputed,target-residual,rtol=1e-11,atol=1e-11),
         'The actual encoded/dequantized output must reproduce residual accounting')
    return result.reshape(-1),dict(changed_scales=int(np.count_nonzero(d!=original)),total_scales=len(d),
        unchanged_code_bytes=True,unchanged_encoded_bytes=True,
        fit_squared_error=float(np.square(independently_recomputed-target).sum()),
        original_fit_squared_error=float(np.square(baseline-target).sum()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','heldout','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();os.environ['OPENBLAS_NUM_THREADS']='6';os.environ['OMP_NUM_THREADS']='6'
    import numpy as np
    prior=load(a.heldout)
    need(prior['completed'] and prior['no_heldout_values_used_for_importance'] and prior['same_prompt'] and
         len(prior['matrices'])==18 and all(record(r['path'])==r for r in prior['outputs']) and
         record(prior['pack']['path'])==prior['pack'],'Immutable separate fit/test inputs and encoded IQ2 samples required')
    package=types.ModuleType('gguf');package.__path__=[str(a.cache/('upstream/llama.cpp-'+REVISION)/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.quants import IQ2_XXS
    from gguf.constants import GGMLQuantizationType as Type
    need(record(prior['reference_library']['path'])==prior['reference_library'],'Pinned independent C decoder changed')
    directory=os.add_dll_directory(str(a.workspace/'toolchain/msys-clang64/clang64/bin'))
    library=ctypes.CDLL(prior['reference_library']['path'])
    class Traits(ctypes.Structure):
        _fields_=[('name',ctypes.c_char_p),('block',ctypes.c_int64),('interleave',ctypes.c_int64),('size',ctypes.c_size_t),('quantized',ctypes.c_bool),('to_float',ctypes.c_void_p),('from_float',ctypes.c_void_p)]
    library.ggml_get_type_traits.argtypes=[ctypes.c_int];library.ggml_get_type_traits.restype=ctypes.POINTER(Traits)
    trait=library.ggml_get_type_traits(int(Type.IQ2_XXS)).contents
    decode=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64)(trait.to_float)
    current=load(a.cache/'Post-top2-output-Q4-32100/model-receipt.json')
    a.out.mkdir(parents=True,exist_ok=False)
    variants=[dict(name='residual_one_sweep',sweeps=1,ridge=0.,cap=None),
              dict(name='ridge_half_two_sweeps_cap_one_eighth',sweeps=2,ridge=.5,cap=.125)]
    results=[];outputs=[];inputs=[record(a.heldout),prior['pack'],prior['reference_library']]+prior['outputs']
    with Path(prior['pack']['path']).open('rb') as packed:
        for row in prior['matrices']:
            role=row['role'];columns,rows=(640,2560) if role=='down' else (2560,640)
            path=a.heldout.parent/('layer-'+str(row['layer']).zfill(2)+'-'+role+'-Expert-'+str(row['expert'])+'.npz')
            need(record(path) in prior['outputs'],'Actual saved independent operands required');data=np.load(path)
            fit=data['fit_input'];test=data['heldout_input']
            need(hashlib.sha256(fit.tobytes()).hexdigest()==row['fit_input_SHA256'] and
                 hashlib.sha256(test.tobytes()).hexdigest()==row['heldout_input_SHA256'],'Exact fit and test identities required')
            logical=next(r for r in current['tensors'] if r['name']=='blk.'+str(row['layer'])+'.ffn_'+role+'_exps.weight')
            source=a.cache/'converted-bf16-002'/logical['file']
            with source.open('rb') as stream:stream.seek(row['original_offset']);raw=stream.read(rows*columns*2)
            need(hashlib.sha256(raw).hexdigest()==row['original_BF16_sha256'],'Exact previously authenticated original BF16 slice required')
            weights=(np.frombuffer(raw,dtype='<u2').astype(np.uint32)<<16).view(np.float32).reshape(rows,columns)
            fit_target=fit.astype(np.float64)@weights.astype(np.float64).T
            part=row['formats']['IQ2_XXS']['encoded'];packed.seek(part['offset']);encoded=np.frombuffer(packed.read(part['bytes']),np.uint8).copy()
            need(hashlib.sha256(encoded).hexdigest()==part['sha256'],'Original fit-only encoded matrix changed')
            pending=[]
            for variant in variants:
                altered,details=refine(np,encoded,IQ2_XXS,fit,fit_target,columns,rows,
                    variant['sweeps'],variant['ridge'],variant['cap'])
                pending.append((variant,altered,details))
            # Heldout target values are first used here, after BOTH complete
            # candidate encodings are fixed. They never select scales or caps.
            target=data['original_BF16_output_F64'];norm=float(np.square(target).sum())
            need(norm>0 and np.allclose(test.astype(np.float64)@weights.astype(np.float64).T,target,rtol=1e-14,atol=1e-14),
                 'Independent original heldout outputs must reproduce')
            for variant,altered,details in pending:
                decoded=IQ2_XXS.dequantize(altered.reshape(-1,66)).reshape(rows,columns)
                c=np.empty(rows*columns,np.float32);decode(altered.ctypes.data,c.ctypes.data,c.size)
                need(c.tobytes()==decoded.tobytes(),'Every NEW encoded F32 value must match independent C/Python decoders')
                output=test.astype(np.float64)@decoded.astype(np.float64).T
                error=output-target;nrmse=float(np.sqrt(np.square(error).sum()/norm));need(np.isfinite(output).all(),'Finite independent heldout result required')
                base=a.out/(str(row['layer'])+'-'+role+'-'+str(row['expert'])+'-'+variant['name'])
                binary=base.with_suffix('.bin');binary.write_bytes(altered.tobytes());outputs.append(record(binary))
                control=row['formats']['Q2_0' if role=='down' else 'Q2_K']['output_NRMSE'];old=row['formats']['IQ2_XXS']['output_NRMSE']
                result=dict(layer=row['layer'],role=role,expert=row['expert'],variant=variant,details=details,
                    heldout_output_NRMSE=nrmse,original_IQ2_heldout_NRMSE=old,current_Q2_heldout_NRMSE=control,
                    lower_than_original_IQ2=nrmse<old,lower_than_current_Q2=nrmse<control,
                    maximum_absolute_heldout_error=float(np.abs(error).max()),encoded=record(binary),
                    new_all_C_and_Python_F32_bytes_exact=True,fit_input_SHA256=row['fit_input_SHA256'],
                    heldout_input_SHA256=row['heldout_input_SHA256'],original_BF16_slice_SHA256=row['original_BF16_sha256'])
                results.append(result);print(json.dumps({k:result[k] for k in ('layer','role','expert','heldout_output_NRMSE','lower_than_current_Q2')}|dict(variant=variant['name'])),flush=True)
    summary=[]
    for variant in variants:
        for role in ('up','down'):
            chosen=[r for r in results if r['variant']==variant and r['role']==role]
            summary.append(dict(variant=variant['name'],role=role,matrices=len(chosen),
                better_than_original_IQ2=sum(r['lower_than_original_IQ2'] for r in chosen),
                better_than_current_Q2=sum(r['lower_than_current_Q2'] for r in chosen)))
    save(a.out/'result.private.json',dict(completed=True,source=record(__file__),inputs=inputs,outputs=outputs,
        variants=variants,matrices=results,summary=summary,fit_only_prefill=True,heldout_never_used_for_fit=True,
        same_prompt=True,independent_heldout_prompts=0,original_BF16_not_requantized_from_Q2=True,
        changed_only_existing_FP16_scales=True,encoded_sizes_and_GPU_arithmetic_unchanged=True,
        native_GPU_qualified=False,whole_model_quality_qualified=False,model_speed_qualified=False,production_adopted=False,
        previous_checks_replayed=0,PS5_operations=0))
    print(json.dumps(dict(completed=True,summary=summary,PS5_operations=0)),flush=True)
    directory.close()


if __name__=='__main__':main()
