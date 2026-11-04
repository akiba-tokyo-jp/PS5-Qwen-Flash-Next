#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check IQ2 geometry and synthetic codec fixtures, without model inference."""
import argparse
import collections
import ctypes
import json
import os
from pathlib import Path
import sys
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION,load


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','reference','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    up=args.cache/('upstream/llama.cpp-'+REVISION)
    package=types.ModuleType('gguf');package.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import IQ2_XXS
    import numpy as np
    reference=load(args.reference);assert record(reference['library']['path'])==reference['library']
    directory=os.add_dll_directory(str(args.workspace/'toolchain/msys-clang64/clang64/bin'))
    lib=ctypes.CDLL(reference['library']['path'])
    lib.ggml_blck_size.argtypes=[ctypes.c_int];lib.ggml_blck_size.restype=ctypes.c_int64
    lib.ggml_type_size.argtypes=[ctypes.c_int];lib.ggml_type_size.restype=ctypes.c_size_t
    lib.ggml_quantize_requires_imatrix.argtypes=[ctypes.c_int];lib.ggml_quantize_requires_imatrix.restype=ctypes.c_bool
    kind=int(Type.IQ2_XXS);block=lib.ggml_blck_size(kind);size=lib.ggml_type_size(kind)
    assert (block,size)==(256,66) and lib.ggml_quantize_requires_imatrix(kind)
    model=args.cache/'Post-top2-output-Q4-32100/model-receipt.json'
    assert record(model)['sha256']=='46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426'
    groups=collections.defaultdict(list)
    for row in load(model)['tensors']:
        if row['name'].startswith('blk.') and int(row['name'].split('.')[1])<48 and row['name'].endswith('_exps.weight'):
            role=row['name'].split('.')[2];groups[role].append(row)
    geometry=[]
    for role in ('ffn_gate_exps','ffn_up_exps','ffn_down_exps'):
        rows=groups[role];assert len(rows)==48
        widths={r['shape'][0] for r in rows};assert len(widths)==1
        width=next(iter(widths));padded=(width+block-1)//block*block
        current=sum(r['bytes'] for r in rows)
        candidate=sum((padded//block)*size*r['shape'][1]*r['shape'][2] for r in rows)
        geometry.append(dict(role=role,tensors=len(rows),current_type=rows[0]['type'],row_width=width,
                             block=block,directly_representable=width%block==0,current_payload_bytes=current,
                             IQ2_payload_bytes=candidate if width%block==0 else None,
                             padded_width=padded,padded_payload_bytes=candidate,
                             padded_delta_bytes=candidate-current))
    # Exercise only invented vectors. Uniform importance is a codec fixture,
    # never an activation calibration or a converted model candidate.
    class Params(ctypes.Structure):
        _fields_=[('mem_size',ctypes.c_size_t),('mem_buffer',ctypes.c_void_p),('no_alloc',ctypes.c_bool)]
    lib.ggml_init.argtypes=[Params];lib.ggml_init.restype=ctypes.c_void_p
    lib.ggml_free.argtypes=[ctypes.c_void_p]
    context=lib.ggml_init(Params(1<<20,None,True));assert context
    class Traits(ctypes.Structure):
        _fields_=[('name',ctypes.c_char_p),('block',ctypes.c_int64),('interleave',ctypes.c_int64),
                  ('size',ctypes.c_size_t),('quantized',ctypes.c_bool),('to_float',ctypes.c_void_p),
                  ('from_float',ctypes.c_void_p)]
    lib.ggml_get_type_traits.argtypes=[ctypes.c_int];lib.ggml_get_type_traits.restype=ctypes.POINTER(Traits)
    traits=lib.ggml_get_type_traits(kind).contents;assert traits.block==block and traits.size==size
    decode=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64)(traits.to_float)
    quantize=lib.ggml_quantize_chunk
    quantize.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64,ctypes.c_int64,ctypes.c_int64,ctypes.c_void_p]
    quantize.restype=ctypes.c_size_t
    rng=np.random.default_rng(63040);fixtures=[]
    for width in (256,512,2560):
        for name in ('zero','impulse','ramp','normal','skewed'):
            if name=='zero':values=np.zeros((2,width),np.float32)
            elif name=='impulse':
                values=np.zeros((2,width),np.float32);values[0,0]=1;values[1,-1]=-1
            elif name=='ramp':values=np.linspace(-2,2,2*width,dtype=np.float32).reshape(2,width)
            elif name=='normal':values=rng.standard_normal((2,width)).astype(np.float32)
            else:values=(rng.standard_normal((2,width))**3).astype(np.float32)
            importance=np.ones(width,np.float32);encoded=np.empty(2*width//block*size,np.uint8)
            assert quantize(kind,values.ctypes.data,encoded.ctypes.data,0,2,width,importance.ctypes.data)==encoded.nbytes
            repeated=np.empty_like(encoded)
            assert quantize(kind,values.ctypes.data,repeated.ctypes.data,0,2,width,importance.ctypes.data)==encoded.nbytes
            assert np.array_equal(encoded,repeated)
            python=IQ2_XXS.dequantize(encoded.reshape(-1,size)).reshape(-1)
            native=np.empty(values.size,np.float32);decode(encoded.ctypes.data,native.ctypes.data,values.size)
            assert np.isfinite(native).all() and np.array_equal(native,python)
            fixtures.append(dict(name=name,width=width,decoded_F32_equal=True,deterministic=True))
    lib.ggml_quantize_free();lib.ggml_free(context);directory.close()
    result=dict(completed=True,format='IQ2_XXS',block_elements=block,block_bytes=size,
                requires_activation_importance=True,real_importance_supplied=False,
                real_model_candidate_encoded=False,synthetic_uniform_importance_only=True,
                geometry=geometry,fixtures=fixtures,model=record(model),reference=reference['library'],
                inputs=[record(p) for p in (Path(__file__),up/'ggml/src/ggml-quants.c',up/'gguf-py/gguf/quants.py')],
                learned_host_inference=False,native_execution=False,production_adopted=False)
    (args.out/'result.private.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,synthetic_cases=len(fixtures),C_and_Python_decode_equal=True,
                         geometry=geometry,real_model_candidate_encoded=False,production_adopted=False)))


if __name__=='__main__':main()
