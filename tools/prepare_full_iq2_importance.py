#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare all48 target-layer importance vectors using only actual prefill inputs."""
import argparse
import hashlib
from pathlib import Path
import struct
from build_performance_quantizer import record
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();import numpy as np
    original=load(a.capture);need(original['completed'] and original['native_and_host_whole_SHA256_equal'] and
        record(original['raw']['path'])==original['raw'],'The exact positively completed native activation stream is required')
    closed=load(original['closure']['path']);need(closed['ordinary_exit_observed'] and
        closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'],'Original model source/GPU owners must already be positively closed')
    need(not a.out.exists() or (a.out.is_dir() and not any(a.out.iterdir())),
         'A new or empty incomplete host output is required; never replace completed importance')
    a.out.mkdir(parents=True,exist_ok=True);sums={};counts={};seen=set();training=0;heldout=0
    with Path(original['raw']['path']).open('rb') as stream:
        need(stream.read(16384)[:8]==b'QWENACT1','Original native capture header required')
        while True:
            h=stream.read(16384)
            if not h:break
            need(len(h)==16384 and h[:8]==b'QACTREC1','Complete original activation header required')
            evaluation,role,layer,k,tokens,xslots,selected,payload,padded,weight_type=struct.unpack_from('<Q6I2QI',h,8)
            need(role in (0,1) and layer<48 and k==(2560 if role==0 else 640) and 1<=tokens<=32 and
                xslots in (1,selected) and 1<=selected<=10 and (not role or xslots==selected) and
                payload==tokens*xslots*k*4 and padded==(payload+16383)//16384*16384 and
                (evaluation,role,layer) not in seen,'Exact original layer/role/input geometry required')
            raw=stream.read(padded);need(len(raw)==padded and not any(raw[payload:]),'Original complete zero-padded activation payload required')
            values=np.frombuffer(raw,dtype='<f4',count=payload//4).reshape(-1,k)
            need(np.isfinite(values).all(),'All original inputs must remain finite')
            if evaluation==1:
                need(tokens==30,'The actual first30-token prefill is the only fitting phase')
                key=(role,layer);need(key not in sums,'One prefill record per layer and role required')
                sums[key]=np.square(values.astype(np.float64)).sum(axis=0);counts[key]=len(values);training+=1
            else:need(2<=evaluation<=23 and tokens==1,'Only the original22 decode evaluations may be held out');heldout+=1
            seen.add((evaluation,role,layer))
    need(len(seen)==2208 and training==96 and heldout==2112 and len(sums)==96,'All original records must be preserved; no decode input may enter fitting')
    matrices={}
    for role,label,k in ((0,'up',2560),(1,'down',640)):
        values=np.stack([sums[(role,layer)]/counts[(role,layer)] for layer in range(48)]).astype('<f4')
        need(values.shape==(48,k) and np.isfinite(values).all() and (values>=0).all() and np.all(np.any(values>0,axis=1)),
             'Every target layer requires actual nonnegative nonempty importance')
        matrices[label]=values
    output=a.out/'prefill-only-target-importance.npz';np.savez_compressed(output,**matrices)
    save(a.out/'result.private.json',dict(completed=True,capture=record(a.capture),raw=original['raw'],closure=original['closure'],
        output=record(output),target_layers=48,training_evaluations=[1],heldout_evaluations=list(range(2,24)),
        actual_vectors_per_layer=dict(up=[counts[(0,l)] for l in range(48)],down=[counts[(1,l)] for l in range(48)]),
        importance_F32_SHA256={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in matrices.items()},
        every_Expert_uses_its_actual_layer_global_prefill_moments=True,no_synthetic_uniform_importance=True,
        no_heldout_decode_values_used=True,independent_prompt_quality_qualified=False,host_model_inference=False,PS5_operations=0))
    print(dict(completed=True,target_layers=48,training_records=training,heldout_records_excluded=heldout,PS5_operations=0))


if __name__=='__main__':main()
