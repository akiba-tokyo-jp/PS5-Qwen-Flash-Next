#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fit isolated IQ2 weights on real prefill inputs and score unseen decode inputs."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]
ALIGN=16384


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','capture','prior-samples','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();os.environ['OPENBLAS_NUM_THREADS']='6';os.environ['OMP_NUM_THREADS']='6'
    import numpy as np
    run=load(a.capture);prior=load(a.prior_samples)
    need(run['completed'] and run['native_and_host_whole_SHA256_equal'] and prior['completed'] and
        record(run['raw']['path'])==run['raw'] and record(prior['reference']['path'])==prior['reference'],'Whole real stream and pinned quantization library required')
    for key in ('case','closure','capture'):need(record(run[key]['path'])==run[key],'Original positively closed native evidence changed')
    closed=load(run['closure']['path']);need(closed['completed'] and closed['ordinary_exit_observed'] and not closed['unknown_completion'],
        'The real calibration owner must already be positively closed')
    a.out.mkdir(parents=True,exist_ok=False);vectors={};seen=set();evaluations=set()
    with Path(run['raw']['path']).open('rb') as stream:
        header=stream.read(ALIGN);need(len(header)==ALIGN and header[:8]==b'QWENACT1','Exact original stream required')
        while True:
            header=stream.read(ALIGN)
            if not header:break
            need(len(header)==ALIGN and header[:8]==b'QACTREC1','Exact original record required')
            evaluation,role,layer,k,tokens,xslots,selected,payload,padded,weight_type=struct.unpack_from('<Q6I2QI',header,8)
            need(role in (0,1) and layer<48 and k==(640 if role else 2560) and 1<=tokens<=32 and 1<=selected<=10 and
                xslots in (1,selected) and (not role or xslots==selected) and payload==tokens*xslots*k*4 and
                padded==(payload+ALIGN-1)//ALIGN*ALIGN and (evaluation,role,layer) not in seen,'Complete original geometry and unique records required')
            raw=stream.read(padded);need(len(raw)==padded and not any(raw[payload:]),'Full original payload required')
            values=np.frombuffer(raw,dtype='<f4',count=payload//4).reshape(tokens,xslots,k);need(np.isfinite(values).all(),'Finite real inputs required')
            ids=np.frombuffer(header,dtype='<i4',count=tokens*selected,offset=64).reshape(tokens,selected)
            if layer in (0,23,47):
                phase=0 if evaluation==1 else 1
                need((evaluation==1 and tokens==30) or (evaluation>1 and tokens==1),'One30-token prefill and subsequent width-one decode required')
                for token in range(tokens):
                    for slot in range(selected):
                        key=(layer,role,int(ids[token,slot]));entry=vectors.setdefault(key,[[],[]]);entry[phase].append(values[token,0 if xslots==1 else slot].copy())
            seen.add((evaluation,role,layer));evaluations.add(evaluation)
    capture=load(run['capture']['path']);need(len(seen)==capture['records']==96*len(evaluations) and evaluations==set(range(1,24)),
        'All23 actual evaluations and2208 operand records required')
    up=a.cache/('upstream/llama.cpp-'+REVISION);package=types.ModuleType('gguf');package.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import IQ2_XXS,Q2_K,Q2_0
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';dll=a.out/'current-Q2-control.dll';control_sources=[ROOT/'tools/expert_q2k_quantize.c',ROOT/'tools/expert_q2_mse_quantize.c']
    command=[str(host/'clang.exe'),'-std=c11','-O3','-ffp-contract=off','-shared',*map(str,control_sources),'-o',str(dll)]
    compile_run=subprocess.run(command,capture_output=True,timeout=180);(a.out/'compile.private.log').write_bytes(compile_run.stdout+compile_run.stderr)
    need(compile_run.returncode==0,compile_run.stderr.decode(errors='replace')[-3000:]);directory=os.add_dll_directory(str(host))
    controls=ctypes.CDLL(str(dll));library=ctypes.CDLL(prior['reference']['path'])
    class Params(ctypes.Structure):_fields_=[('mem_size',ctypes.c_size_t),('mem_buffer',ctypes.c_void_p),('no_alloc',ctypes.c_bool)]
    library.ggml_init.argtypes=[Params];library.ggml_init.restype=ctypes.c_void_p;library.ggml_free.argtypes=[ctypes.c_void_p]
    context=library.ggml_init(Params(1<<20,None,True));need(context,'Quantization-only metadata context required')
    quantize=library.ggml_quantize_chunk;quantize.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64,ctypes.c_int64,ctypes.c_int64,ctypes.c_void_p];quantize.restype=ctypes.c_size_t
    class Traits(ctypes.Structure):_fields_=[('name',ctypes.c_char_p),('block',ctypes.c_int64),('interleave',ctypes.c_int64),('size',ctypes.c_size_t),('quantized',ctypes.c_bool),('to_float',ctypes.c_void_p),('from_float',ctypes.c_void_p)]
    library.ggml_get_type_traits.argtypes=[ctypes.c_int];library.ggml_get_type_traits.restype=ctypes.POINTER(Traits)
    current=load(a.cache/'Post-top2-output-Q4-32100/model-receipt.json');original_path=a.cache/'converted-bf16-002/model-receipt.json';original=load(original_path)
    need(original['original_shards_verified'] and not original['learned_inference_performed'] and original['upstream_revision']==REVISION,'Authenticated original BF16 source required')
    files={row['path']:row for row in original['files']};verified={};rows=[];outputs=[];pack=a.out/'prefill-fit-IQ2-components.bin';coverage=[]
    with pack.open('xb') as packed:
        for layer in (0,23,47):
            for role,label in ((0,'up'),(1,'down')):
                eligible=[key for key,value in vectors.items() if key[:2]==(layer,role) and value[0] and value[1]]
                ordered=sorted(eligible,key=lambda key:(len(vectors[key][1]),key[2]));need(len(ordered)>=3,'At least three Experts with both independent phases required')
                chosen=[ordered[-1],ordered[len(ordered)//2],ordered[0]];need(len(set(chosen))==3,'Distinct most/middle/least held-out coverage required')
                coverage.append(dict(layer=layer,role=label,Experts_with_both_phases=len(eligible)))
                columns,count=(640,2560) if role else (2560,640);control_label='Q2_0' if role else 'Q2_K';control_type=Type.Q2_0 if role else Type.Q2_K
                encoder=getattr(controls,'qwen_quantize_bf16_q2_0' if role else 'qwen_quantize_bf16_q2_K');encoder.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];encoder.restype=ctypes.c_int
                name='blk.'+str(layer)+'.ffn_'+label+'_exps.weight';logical=next(row for row in current['tensors'] if row['name']==name)
                source=a.cache/'converted-bf16-002'/logical['file'];before=source.stat();stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
                if source not in verified:
                    print(json.dumps(dict(phase='verify_original_BF16',file=source.name,bytes=before.st_size)),flush=True)
                    verified[source]=record(source);need(verified[source]['sha256']==files[logical['file']]['sha256'],'Whole original BF16 source differs')
                reader=GGUFReader(source,'r');tensor=next(row for row in reader.tensors if row.name==name)
                need(tensor.tensor_type==Type.BF16 and list(tensor.shape)==[columns,count,512],'Original isolated Expert geometry differs')
                with source.open('rb') as stream:
                    for key in chosen:
                        fit=np.stack(vectors[key][0]);test=np.stack(vectors[key][1]);need(fit.shape[1]==test.shape[1]==columns,'Actual phase widths differ')
                        importance=np.mean(np.square(fit,dtype=np.float64),axis=0).astype(np.float32);need(np.isfinite(importance).all() and np.any(importance>0),'Measured fit importance must be nonzero')
                        if role:importance=np.tile(importance,2)
                        offset=int(tensor.data_offset)+key[2]*columns*count*2;stream.seek(offset);raw=stream.read(columns*count*2);need(len(raw)==columns*count*2,'Complete original Expert required')
                        bits=np.frombuffer(raw,dtype='<u2');weights=(bits.astype(np.uint32)<<16).view(np.float32);need(np.isfinite(weights).all(),'Finite original weights required')
                        q2=np.empty(460800 if role else 537600,np.uint8);need(encoder(bits.ctypes.data,q2.ctypes.data,bits.size)==0,'Independent current Q2 encoding failed')
                        iq2=np.empty(422400,np.uint8);need(quantize(int(Type.IQ2_XXS),weights.ctypes.data,iq2.ctypes.data,0,1280 if role else 640,1280 if role else 2560,importance.ctypes.data)==iq2.nbytes,'Prefill-only IQ2 encoding failed')
                        expected=test.astype(np.float64)@weights.reshape(count,columns).astype(np.float64).T;norm=float(np.square(expected).sum());need(norm>0,'Nonzero independent held-out output norm required')
                        entry=dict(layer=layer,role=label,expert=key[2],fit_input_vectors=len(fit),heldout_input_vectors=len(test),fit_evaluations=[1],heldout_evaluations=list(range(2,24)),
                            fit_input_SHA256=hashlib.sha256(fit.tobytes()).hexdigest(),heldout_input_SHA256=hashlib.sha256(test.tobytes()).hexdigest(),original_BF16_sha256=hashlib.sha256(raw).hexdigest(),original_offset=offset,formats={})
                        saved={'fit_input':fit,'heldout_input':test,'importance_from_fit_only':importance,'original_BF16_output_F64':expected}
                        for format,kind,decoder,block_size,encoded in ((control_label,control_type,Q2_0 if role else Q2_K,18 if role else 84,q2),('IQ2_XXS',Type.IQ2_XXS,IQ2_XXS,66,iq2)):
                            trait=library.ggml_get_type_traits(int(kind)).contents;decode=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64)(trait.to_float)
                            decoded=np.empty(weights.size,np.float32);decode(encoded.ctypes.data,decoded.ctypes.data,decoded.size);python=decoder.dequantize(encoded.reshape(-1,block_size)).reshape(-1)
                            need(decoded.tobytes()==python.tobytes() and np.isfinite(decoded).all(),'Full independent C/Python format decoding must match byte-for-byte')
                            output=test.astype(np.float64)@decoded.reshape(count,columns).astype(np.float64).T;error=output-expected;need(np.isfinite(output).all(),'Finite held-out component outputs required')
                            packed.write(bytes((-packed.tell())%ALIGN));extent=dict(offset=packed.tell(),bytes=encoded.nbytes,sha256=hashlib.sha256(encoded.tobytes()).hexdigest());packed.write(encoded.tobytes())
                            entry['formats'][format]=dict(output_NRMSE=float(np.sqrt(np.square(error).sum()/norm)),maximum_absolute_output_error=float(np.max(np.abs(error))),all_C_and_Python_F32_bytes_exact=True,encoded=extent)
                            saved[format+'_heldout_output_F64']=output
                        entry['IQ2_heldout_output_NRMSE_lower']=entry['formats']['IQ2_XXS']['output_NRMSE']<entry['formats'][control_label]['output_NRMSE']
                        path=a.out/('layer-'+str(layer).zfill(2)+'-'+label+'-Expert-'+str(key[2])+'.npz');np.savez_compressed(path,**saved);outputs.append(record(path));rows.append(entry)
                        print(json.dumps(entry),flush=True)
                need(stamp(before)==stamp(source.stat()),'Original source changed during separate-phase encoding');del reader
        packed.write(bytes((-packed.tell())%ALIGN));packed.flush();os.fsync(packed.fileno())
    library.ggml_quantize_free();library.ggml_free(context);directory.close();need(record(run['raw']['path'])==run['raw'],'Actual captured data changed')
    save(a.out/'result.private.json',dict(completed=True,source=record(__file__),capture=record(a.capture),reference_library=prior['reference'],original_receipt=record(original_path),
        whole_original_sources=list(verified.values()),control_sources=[record(path) for path in control_sources],control_library=record(dll),command=command,
        matrices=rows,outputs=outputs,pack=record(pack),eligible_coverage=coverage,fit='Actual evaluation1 prefill operands only',heldout='Actual evaluations2 through23 decode operands; never used for fitting',
        no_heldout_values_used_for_importance=True,no_synthetic_uniform_importance=True,same_prompt=True,independent_heldout_prompts=0,
        full_model_inference=False,broader_answer_quality_qualified=False,native_GPU_qualified=False,whole_speed_qualified=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,matrices=len(rows),Up_IQ2_lower=sum(row['IQ2_heldout_output_NRMSE_lower'] for row in rows if row['role']=='up'),
        Down_IQ2_lower=sum(row['IQ2_heldout_output_NRMSE_lower'] for row in rows if row['role']=='down'),separate_actual_fit_and_test_inputs=True,same_prompt=True,PS5_operations=0)))


if __name__=='__main__':main()
