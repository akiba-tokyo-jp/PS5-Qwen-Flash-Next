#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Encode original BF16 Experts with the pinned IQ2 codec and actual layer importance."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import types
from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save


def stamp(path):
    s=path.stat();return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','importance','reference','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--role',choices=('gate','up','down'),required=True);p.add_argument('--layer',type=int,required=True)
    p.add_argument('--Gate-input-proof',type=Path)
    p.add_argument('--Experts',type=int,default=512)
    p.add_argument('--reuse-prefix',type=Path,help='Reuse exact already encoded Experts without encoding them again')
    p.add_argument('--source-hash-proof',type=Path,help='Reuse a complete BF16 shard hash only with unchanged full host identity')
    a=p.parse_args()
    need(0<=a.layer<48 and 1<=a.Experts<=512,'Only target trunk layers and a bounded Expert prefix are permitted')
    os.environ['OPENBLAS_NUM_THREADS']='4';import numpy as np
    importance=load(a.importance);reference=load(a.reference)
    if a.role=='gate':
        need(a.Gate_input_proof is not None,'Actual Gate/Up input identity is required before reusing Up importance')
        gate=load(a.Gate_input_proof)
        need(gate['completed'] and gate['native_input_identity_qualified'] and gate['all48_layers_per_width'] and
             gate['calls']==1200 and set(gate['graph_construction_widths'])=={1,2,30,32} and
             gate['original_GGML_operations_preserved'] and record(gate['audit']['path'])==gate['audit'] and
             record(gate['closure']['path'])==gate['closure'] and load(gate['closure']['path'])['ordinary_exit_observed'],
             'The complete native1200-pair input/ID identity audit and ordinary retirement are required')
    need(importance['completed'] and importance['no_heldout_decode_values_used'] and importance['no_synthetic_uniform_importance'] and
        record(importance['output']['path'])==importance['output'],'Completed actual prefill-only layer importance required')
    library=reference['reference_library'];need(record(library['path'])==library,'The pinned already qualified quantization-only library changed')
    up=a.cache/('upstream/llama.cpp-'+REVISION);package=types.ModuleType('gguf');package.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import IQ2_XXS
    original_path=a.cache/'converted-bf16-002/model-receipt.json';original=load(original_path)
    current=load(a.cache/'Post-top2-output-Q4-32100/model-receipt.json')
    name='blk.'+str(a.layer)+'.ffn_'+a.role+'_exps.weight';logical=next(t for t in current['tensors'] if t['name']==name)
    source=a.cache/'converted-bf16-002'/logical['file'];expected=next(r for r in original['files'] if r['path']==logical['file'])
    need(original['original_shards_verified'] and not original['learned_inference_performed'] and original['upstream_revision']==REVISION,
        'Authenticated original BF16 conversion is required, never current Q2 requantization')
    a.out.mkdir(parents=True,exist_ok=False);identity=stamp(source)
    hash_proof=a.source_hash_proof or a.reuse_prefix
    if hash_proof:
        old_hash=load(hash_proof);checked=old_hash['original_BF16_source']
        need(old_hash['completed'] and old_hash['original_source_stamp']==identity and checked['path']==str(source.resolve()) and
             old_hash['original_receipt']==record(original_path),'Only the same original BF16 shard and unchanged full host identity may reuse its SHA')
        print(json.dumps(dict(phase='reuse_original_BF16_SHA',file=source.name,proof=str(hash_proof))),flush=True)
    else:
        print(json.dumps(dict(phase='verify_original_BF16',file=source.name,bytes=identity[2])),flush=True);checked=record(source)
    need(checked['bytes']==expected['bytes'] and checked['sha256']==expected['sha256'] and stamp(source)==identity,
        'The complete original BF16 shard SHA and identity must agree')
    reader=GGUFReader(source,'r');tensor=next(t for t in reader.tensors if t.name==name)
    down=a.role=='down';columns,rows=(640,2560) if down else (2560,640)
    need(tensor.tensor_type==Type.BF16 and list(tensor.shape)==[columns,rows,512] and tensor.n_bytes==columns*rows*512*2,
         'Exact original target Expert geometry required')
    moments=np.load(importance['output']['path'])['up' if a.role=='gate' else a.role][a.layer]
    moments=np.ascontiguousarray(np.tile(moments,2) if down else moments,dtype=np.float32)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';directory=os.add_dll_directory(str(host));lib=ctypes.CDLL(library['path'])
    class Params(ctypes.Structure):_fields_=[('mem_size',ctypes.c_size_t),('mem_buffer',ctypes.c_void_p),('no_alloc',ctypes.c_bool)]
    lib.ggml_init.argtypes=[Params];lib.ggml_init.restype=ctypes.c_void_p;lib.ggml_free.argtypes=[ctypes.c_void_p]
    context=lib.ggml_init(Params(1<<20,None,True));need(context,'Quantization-only codec metadata unavailable')
    quantize=lib.ggml_quantize_chunk;quantize.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64,ctypes.c_int64,ctypes.c_int64,ctypes.c_void_p];quantize.restype=ctypes.c_size_t
    class Traits(ctypes.Structure):_fields_=[('name',ctypes.c_char_p),('block',ctypes.c_int64),('interleave',ctypes.c_int64),('size',ctypes.c_size_t),('quantized',ctypes.c_bool),('to_float',ctypes.c_void_p),('from_float',ctypes.c_void_p)]
    lib.ggml_get_type_traits.argtypes=[ctypes.c_int];lib.ggml_get_type_traits.restype=ctypes.POINTER(Traits)
    trait=lib.ggml_get_type_traits(int(Type.IQ2_XXS)).contents;need((trait.block,trait.size)==(256,66),'Exact pinned IQ2 block format required')
    decode=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64)(trait.to_float)
    pack=a.out/'weights.iq2.bin';results=[];prefix=b''
    if a.reuse_prefix:
        old=load(a.reuse_prefix)
        need(old['completed'] and old['role']==a.role and old['layer']==a.layer and old['importance']==record(a.importance) and
            old['reference_library']==library and old['original_BF16_source']==checked and old['original_source_stamp']==identity and
            0<old['encoded_Experts']<a.Experts and record(old['pack']['path'])==old['pack'],
            'Only an identical complete previously encoded Expert prefix may be reused')
        prefix=Path(old['pack']['path']).read_bytes();results=old['Experts'].copy()
        need(len(prefix)==len(results)*422400 and all(r['expert']==i and
            hashlib.sha256(prefix[i*422400:(i+1)*422400]).hexdigest()==r['encoded_SHA256'] for i,r in enumerate(results)),
            'Every reused encoded Expert must retain its complete exact bytes')
    start=len(results);journal=a.out/'encoded-Experts.private.jsonl'
    with source.open('rb') as src,pack.open('xb') as output,journal.open('x',encoding='utf-8',newline='\n') as log:
        if prefix:need(output.write(prefix)==len(prefix),'One exact original encoded-prefix copy required')
        for row in results:log.write(json.dumps(row,separators=(',',':'))+'\n')
        for expert in range(start,a.Experts):
            offset=int(tensor.data_offset)+expert*columns*rows*2;src.seek(offset);raw=src.read(columns*rows*2)
            need(len(raw)==columns*rows*2,'Original BF16 Expert slice is truncated')
            values=(np.frombuffer(raw,dtype='<u2').astype(np.uint32)<<16).view(np.float32)
            need(np.isfinite(values).all(),'Original BF16 weights must remain finite')
            encoded=np.empty(422400,np.uint8);begun=time.perf_counter()
            count=quantize(int(Type.IQ2_XXS),values.ctypes.data,encoded.ctypes.data,0,1280 if down else 640,1280 if down else 2560,moments.ctypes.data)
            elapsed=time.perf_counter()-begun;need(count==encoded.nbytes,'The exact full encoded Expert extent must return')
            decoded=np.empty(values.size,np.float32);decode(encoded.ctypes.data,decoded.ctypes.data,values.size)
            need(np.isfinite(decoded).all(),'All newly encoded/dequantized weights must be finite')
            independent=expert in (start,a.Experts-1)
            if independent:need(decoded.tobytes()==IQ2_XXS.dequantize(encoded.reshape(-1,66)).reshape(-1).tobytes(),
                'Complete new first/last-Expert C/Python F32 decoding must agree')
            encoded_bytes=encoded.tobytes();written=output.write(encoded_bytes);need(written==len(encoded_bytes),'One complete encoded write required')
            row=dict(expert=expert,source_offset=offset,original_BF16_SHA256=hashlib.sha256(raw).hexdigest(),
                encoded_offset=expert*422400,encoded_bytes=422400,encoded_SHA256=hashlib.sha256(encoded_bytes).hexdigest(),
                quantization_seconds=elapsed,all_decoded_F32_finite=True,independent_full_C_Python_F32_decode=independent)
            results.append(row);log.write(json.dumps(row,separators=(',',':'))+'\n')
            if expert==start or (expert+1)%16==0 or expert==a.Experts-1:
                log.flush();output.flush();print(json.dumps(dict(layer=a.layer,role=a.role,Expert=expert,quantization_seconds=elapsed)),flush=True)
        output.flush();os.fsync(output.fileno())
        log.flush();os.fsync(log.fileno())
    lib.ggml_quantize_free();lib.ggml_free(context);directory.close();need(stamp(source)==identity,'Original source identity changed during encoding')
    del tensor,reader
    save(a.out/'result.private.json',dict(completed=True,role=a.role,layer=a.layer,encoded_Experts=a.Experts,complete_layer=a.Experts==512,
        original_BF16_source=checked,original_source_stamp=identity,original_receipt=record(original_path),importance=record(a.importance),
        reference_library=library,source_tensor=name,logical_shape=[columns,rows,512],encoded_row_shape=[1280,1280] if down else [2560,640],
        codec='IQ2_XXS',paired_original_rows=down,pack=record(pack),Experts=results,host_model_inference=False,
        encoder_source=record(__file__),completed_Expert_prefix_reused=record(a.reuse_prefix) if a.reuse_prefix else None,
        original_BF16_SHA_reused=record(hash_proof) if hash_proof else None,encoded_Expert_journal=record(journal),
        Gate_input_identity=record(a.Gate_input_proof) if a.role=='gate' else None,
        importance_input_role='up' if a.role=='gate' else a.role,
        target_GPU_format_and_model_integration_qualified=False,full_model_quality_or_speed_qualified=False,PS5_operations=0))


if __name__=='__main__':main()
