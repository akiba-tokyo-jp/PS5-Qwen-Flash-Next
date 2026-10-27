#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently check original ranges and the ten-Expert numerical reference."""
import argparse,hashlib,json,os
from pathlib import Path
import numpy as np
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('plan','layout','headers','host-models','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);receipt=a.host_models/'model-receipt.json';source=ROOT/'native/app/ready_expert_fixture.cpp'
    inputs=[record(p)for p in(Path(__file__),a.plan,a.layout,a.headers,receipt,source)]
    plan,layout,headers,original=[json.loads(p.read_bytes())for p in(a.plan,a.layout,a.headers,receipt)]
    assert plan['lineage']['native_layout_seal_sha256']==inputs[2]['sha256']and plan['lineage']['headers_sha256']==inputs[3]['sha256']
    assert original['original_revision']=='de4b8e4d43b917e7706784d8bb445c9af86a3540'and 'x[i]=float(int(i%13)-6)/3.0f;'in source.read_text()
    logical={f['path']:f for f in layout['logical_files']};tensors={t['name']:(h['file'],t)for h in headers for t in h['tensors']}
    x=np.array([(i%13-6)/3 for i in range(2560)],dtype=np.float32);exact=np.zeros(2560,dtype=np.float64);staged=np.zeros(2560,dtype=np.float32)
    for ordinal,expert in enumerate(plan['experts']):
        weights=[]
        for role,name in enumerate(('gate','up','down')):
            logical_name,t=tensors[f'blk.{plan["layer"]}.ffn_{name}_exps.weight'];offset=t['file_offset']+expert*3276800;aligned=offset&~16383;m=plan['matrices'][role*10+ordinal]
            part=next(p for p in logical[logical_name]['parts']if p['offset']<=aligned and aligned+3293184<=p['offset']+p['bytes'])
            assert plan['files'][m['source']]['path'].endswith('/'+part['path'])and m['offset']==aligned-part['offset']and m['residue']==offset-aligned
            with(a.host_models/logical_name).open('rb')as f:
                before=os.fstat(f.fileno());f.seek(aligned);envelope=f.read(3293184);after=os.fstat(f.fileno())
                assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
            payload=envelope[m['residue']:m['residue']+3276800]
            assert hashlib.sha256(envelope).hexdigest()==m['envelope']and hashlib.sha256(payload).hexdigest()==m['raw']
            w=(np.frombuffer(payload,dtype='<u2').astype(np.uint32)<<16).view(np.float32).reshape((2560,640)if role==2 else(640,2560));assert np.all(np.isfinite(w));weights.append(w)
        g=weights[0].astype(np.float64)@x.astype(np.float64);u=weights[1].astype(np.float64)@x.astype(np.float64)
        value=weights[2].astype(np.float64)@((g/(1+np.exp(-g)))*u)
        gf=weights[0]@x;uf=weights[1]@x;valuef=weights[2]@((gf/(np.float32(1)+np.exp(-gf)))*uf)
        scale=np.float32(ordinal+1)/np.float32(256);exact+=value*float(scale);staged+=valuef*scale
    error=np.abs(staged.astype(np.float64)-exact);norm=error/(1e-5+1e-5*np.abs(exact))
    assert np.all(np.isfinite(exact))and np.all(np.isfinite(staged))and np.max(np.abs(exact))>1e-4 and np.max(norm)<=1
    assert inputs==[record(p)for p in(Path(__file__),a.plan,a.layout,a.headers,receipt,source)]
    result=dict(schema='ps5-qwen-ready-original-offline-reference-v1',inputs=inputs,original_BF16_matrices=30,unique_original_Experts=10,
        original_ranges_independently_resolved=True,maximum_absolute_reference_output=float(np.max(np.abs(exact))),
        maximum_staged_F32_absolute_error=float(np.max(error)),maximum_staged_F32_normalized_error=float(np.max(norm)),
        original_reference_limits_unchanged=True,model_loaded=False,tokens_generated=0,PS5_operations=0,CI_runs=0,native_GPU_qualified=False)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='inputs'}),flush=True)
if __name__=='__main__':main()
