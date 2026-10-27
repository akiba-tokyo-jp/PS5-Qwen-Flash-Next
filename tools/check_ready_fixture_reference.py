#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the original-byte numerical fixture's signal and fixed error limits.

This is offline matrix-reference verification, with no model loader, tokenizer,
token generation or replacement for native arithmetic qualification.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from build_preservation_integrity import record
from split_bank_result import HASHES,PACK_SHA
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('pack','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'native/app/ready_expert_fixture.cpp'
    assert 'x[i]=float(int(i%13)-6)/3.0f;'in source.read_text()
    inputs=[record(Path(__file__)),record(source),record(a.pack)]
    assert inputs[-1]['sha256']==PACK_SHA and inputs[-1]['bytes']==63488000
    x=np.array([(i%13-6)/3 for i in range(2560)],dtype=np.float32)
    xbits=x.view(np.uint32);nonexact=int(np.count_nonzero(xbits&0xffff));assert nonexact>0
    values=[];float_values=[];offsets=((4210688,7503872,10797056),(14090240,17383424,20676608))
    with a.pack.open('rb')as f:
        for group in range(2):
            weights=[]
            for role in range(3):
                f.seek(offsets[group][role]);envelope=f.read(3293184);residue=1632 if role==2 else 2784
                payload=envelope[residue:residue+3276800];raw,outer=HASHES[role*2+group]
                assert hashlib.sha256(envelope).hexdigest()==outer and hashlib.sha256(payload).hexdigest()==raw
                w=(np.frombuffer(payload,dtype='<u2').astype(np.uint32)<<16).view(np.float32).reshape((2560,640)if role==2 else(640,2560))
                assert np.all(np.isfinite(w));weights.append(w)
            gate,up,down=[v.astype(np.float64)for v in weights];xd=x.astype(np.float64)
            g=gate@xd;u=up@xd;values.append(down@((g/(1+np.exp(-g)))*u))
            g=weights[0]@x;u=weights[1]@x
            float_values.append(weights[2]@((g/(np.float32(1)+np.exp(-g)))*u))
    exact=np.zeros(2560,dtype=np.float64);staged=np.zeros(2560,dtype=np.float32)
    for i in range(10):
        scale=np.float32(i+1)/np.float32(256)
        exact+=values[i%2]*float(scale);staged+=float_values[i%2]*scale
    error=np.abs(staged.astype(np.float64)-exact);normalized=error/(1e-5+1e-5*np.abs(exact))
    assert np.all(np.isfinite(exact))and np.all(np.isfinite(staged))and np.max(np.abs(exact))>1e-4 and np.max(normalized)<=1
    assert inputs==[record(Path(__file__)),record(source),record(a.pack)]
    result=dict(schema='ps5-qwen-ready-offline-reference-v1',inputs=inputs,original_BF16_matrices=6,
        original_contributions=10,non_BF16_exact_F32_inputs=nonexact,F64_maximum_absolute_output=float(np.max(np.abs(exact))),
        staged_F32_maximum_absolute_error=float(np.max(error)),staged_F32_maximum_normalized_error=float(np.max(normalized)),
        reference_absolute_tolerance=1e-5,reference_relative_tolerance=1e-5,numpy_version=np.__version__,
        matrix_reference_only=True,model_loaded=False,tokens_generated=0,native_GPU_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='inputs'}),flush=True)
if __name__=='__main__':main()
