#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Encode nine original BF16 Up samples using measured per-Expert importance."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','reference','importance','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();importance=load(args.importance)
    need(importance['completed'] and importance['up_and_down_operands_independently_observed'] and
         not importance['synthetic_uniform_importance_used'],'Actual PS5 per-Expert activation moments required')
    for row in importance['outputs']:need(record(row['path'])==row,'Actual activation moments changed')
    args.out.mkdir(parents=True,exist_ok=False)
    up=args.cache/('upstream/llama.cpp-'+REVISION)
    package=types.ModuleType('gguf');package.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import IQ2_XXS
    import numpy as np
    ref=load(args.reference);need(ref['completed'] and not ref['host_model_inference'] and record(ref['library']['path'])==ref['library'],
         'The pinned quantization-only reference library is required')
    directory=os.add_dll_directory(str(args.workspace/'toolchain/msys-clang64/clang64/bin'))
    lib=ctypes.CDLL(ref['library']['path'])
    class Params(ctypes.Structure):_fields_=[('mem_size',ctypes.c_size_t),('mem_buffer',ctypes.c_void_p),('no_alloc',ctypes.c_bool)]
    lib.ggml_init.argtypes=[Params];lib.ggml_init.restype=ctypes.c_void_p;lib.ggml_free.argtypes=[ctypes.c_void_p]
    context=lib.ggml_init(Params(1<<20,None,True));need(context,'Quantization reference metadata unavailable')
    quantize=lib.ggml_quantize_chunk
    quantize.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64,ctypes.c_int64,ctypes.c_int64,ctypes.c_void_p]
    quantize.restype=ctypes.c_size_t
    class Traits(ctypes.Structure):
        _fields_=[('name',ctypes.c_char_p),('block',ctypes.c_int64),('interleave',ctypes.c_int64),
                  ('size',ctypes.c_size_t),('quantized',ctypes.c_bool),('to_float',ctypes.c_void_p),('from_float',ctypes.c_void_p)]
    lib.ggml_get_type_traits.argtypes=[ctypes.c_int];lib.ggml_get_type_traits.restype=ctypes.POINTER(Traits)
    trait=lib.ggml_get_type_traits(int(Type.IQ2_XXS)).contents;need((trait.block,trait.size)==(256,66),'Exact IQ2 block geometry required')
    decode=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64)(trait.to_float)
    host=args.workspace/'toolchain/msys-clang64/clang64/bin';dll=args.out/'q2-control-encode.dll'
    command=[str(host/'clang.exe'),'-std=c11','-O3','-ffp-contract=off','-shared',str(ROOT/'tools/expert_q2k_quantize.c'),'-o',str(dll)]
    result=subprocess.run(command,capture_output=True,timeout=120);(args.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
    control_lib=ctypes.CDLL(str(dll));control=control_lib.qwen_quantize_bf16_q2_K
    control.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];control.restype=ctypes.c_int
    current=load(args.cache/'Post-top2-output-Q4-32100/model-receipt.json')
    original_path=args.cache/'converted-bf16-002/model-receipt.json';original=load(original_path)
    need(original['original_shards_verified'] and not original['learned_inference_performed'] and original['upstream_revision']==REVISION,
         'Authenticated original BF16 conversion required')
    original_files={r['path']:r for r in original['files']};verified={};matrices=[];pack=args.out/'iq2-up-samples.bin'
    with pack.open('xb') as output:
        for layer in (0,23,47):
            moment=next(r for r in importance['outputs'] if Path(r['path']).name=='layer-'+str(layer).zfill(2)+'-up.npz')
            data=np.load(moment['path']);ids=data['expert_ids'];counts=data['counts'];order=sorted(range(len(ids)),key=lambda i:(int(counts[i]),int(ids[i])))
            chosen=[order[-1],order[len(order)//2],order[0]];need(len(set(chosen))==3,'Three distinct actually visited Experts required')
            name='blk.'+str(layer)+'.ffn_up_exps.weight';logical=next(t for t in current['tensors'] if t['name']==name)
            source=args.cache/'converted-bf16-002'/logical['file'];before=source.stat()
            stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            need(before.st_size==original_files[logical['file']]['bytes'],'Original BF16 source length changed')
            if source not in verified:
                print(json.dumps(dict(phase='hash_original_BF16_source',layer=layer,bytes=before.st_size)),flush=True)
                actual=record(source);need(actual['sha256']==original_files[logical['file']]['sha256'],'Complete original BF16 source SHA256 differs')
                verified[source]=actual
            reader=GGUFReader(source,'r');tensor=next(t for t in reader.tensors if t.name==name)
            need(tensor.tensor_type==Type.BF16 and list(tensor.shape)==[2560,640,512] and tensor.n_bytes==2560*640*512*2,
                 'Exact original Up geometry required')
            with source.open('rb') as stream:
                for index in chosen:
                    expert=int(ids[index]);samples=int(counts[index]);imatrix=np.ascontiguousarray(data['sum_squares'][index]/samples,dtype=np.float32)
                    need(samples>0 and np.isfinite(imatrix).all() and (imatrix>=0).all() and np.any(imatrix>0),'Real per-Expert moments are empty or invalid')
                    stream.seek(int(tensor.data_offset)+expert*2560*640*2);raw=stream.read(2560*640*2)
                    need(len(raw)==2560*640*2,'Original BF16 Expert slice is truncated')
                    bits=np.frombuffer(raw,dtype='<u2');values=(bits.astype(np.uint32)<<16).view(np.float32)
                    need(np.isfinite(values).all(),'Original BF16 sample contains nonfinite values')
                    q2=np.empty(537600,np.uint8);need(control(bits.ctypes.data,q2.ctypes.data,bits.size)==0,'Original Q2_K reference encoding failed')
                    iq2=np.empty(422400,np.uint8);started=time.monotonic()
                    need(quantize(int(Type.IQ2_XXS),values.ctypes.data,iq2.ctypes.data,0,640,2560,imatrix.ctypes.data)==iq2.nbytes,
                         'Calibrated IQ2 encoding did not return the exact extent')
                    native=np.empty(values.size,np.float32);decode(iq2.ctypes.data,native.ctypes.data,values.size)
                    python=IQ2_XXS.dequantize(iq2.reshape(-1,66)).reshape(-1)
                    need(np.isfinite(native).all() and np.array_equal(native,python),'Independent C/Python actual IQ2 sample decode differs')
                    q2_values=lib.ggml_get_type_traits(int(Type.Q2_K)).contents
                    q2_decode=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64)(q2_values.to_float)
                    control_values=np.empty_like(values);q2_decode(q2.ctypes.data,control_values.ctypes.data,values.size)
                    reference_values=values.astype(np.float64);norm=float(np.square(reference_values).sum());need(norm>0,'Nonzero original weight norm required')
                    row=dict(layer=layer,role='up',expert=expert,columns=2560,rows=640,actual_activation_samples=samples,
                        original_BF16_sha256=hashlib.sha256(raw).hexdigest(),original_source=verified[source],
                        original_offset=int(tensor.data_offset)+expert*2560*640*2,importance=moment,
                        importance_F32_sha256=hashlib.sha256(imatrix.tobytes()).hexdigest(),importance_zero_columns=int((imatrix==0).sum()),
                        IQ2_weight_NRMSE=float(np.sqrt(np.square(native.astype(np.float64)-reference_values).sum()/norm)),
                        Q2_K_weight_NRMSE=float(np.sqrt(np.square(control_values.astype(np.float64)-reference_values).sum()/norm)),
                        C_and_Python_IQ2_decode_exact=True,encode_seconds=time.monotonic()-started)
                    for label,encoded in (('Q2_K',q2),('IQ2_XXS',iq2)):
                        output.write(bytes((-output.tell())%16384));row[label]=dict(offset=output.tell(),bytes=encoded.nbytes,
                            sha256=hashlib.sha256(encoded.tobytes()).hexdigest());output.write(encoded.tobytes())
                    matrices.append(row);print(json.dumps(dict(phase='calibrated_sample_encoded',layer=layer,expert=expert,
                        real_activation_samples=samples,seconds=row['encode_seconds'])),flush=True)
            need(stamp(before)==stamp(source.stat()),'Original source identity changed during encoding');del reader
        output.write(bytes((-output.tell())%16384));output.flush();os.fsync(output.fileno())
    lib.ggml_quantize_free();lib.ggml_free(context);directory.close()
    save(args.out/'result.private.json',dict(completed=True,pack=record(pack),matrices=matrices,real_importance=record(args.importance),
        original_receipt=record(original_path),whole_original_sources=list(verified.values()),reference=ref['library'],
        source=record(Path(__file__)),control_encoder=record(ROOT/'tools/expert_q2k_quantize.c'),
        formats=['Q2_K','IQ2_XXS'],source_encoding='original BF16 independently encoded into each format',
        all_nine_Experts_actually_visited=True,synthetic_uniform_importance_used=False,unvisited_Expert_fallback_used=False,
        full_model_IQ2_candidate_encoded=False,Up_only_component=True,Gate_input_calibration_qualified=False,
        learned_host_inference=False,native_GPU_operator_qualified=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,real_calibrated_Up_matrices=9,full_model_candidate_encoded=False,production_adopted=False)))


if __name__=='__main__':main()
