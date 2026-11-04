#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare target Up/paired-Down IQ2 layers with bounded independent CPU workers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from build_performance_quantizer import record
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','importance','reference','Up-prefix','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--workers',type=int,default=0);a=p.parse_args()
    if a.workers==0:a.workers=min(8,max(1,(os.cpu_count() or 1)//2))
    need(1<=a.workers<=8 and a.workers<=max(1,(os.cpu_count() or 1)//2),'At most8 workers and half of host logical CPUs required')
    prefix=load(a.Up_prefix);need(prefix['completed'] and prefix['role']=='up' and prefix['layer']==0 and prefix['encoded_Experts']==4 and
        prefix['importance']==record(a.importance),'Reuse the completed original four-Expert prefix')
    a.out.mkdir(parents=True,exist_ok=False);model=load(a.cache/'Post-top2-output-Q4-32100/model-receipt.json')
    encoder=a.out/'encoder.private.py';encoder.write_bytes((ROOT/'tools/encode_full_iq2_layer.py').read_bytes())
    pending=[]
    for layer in range(48):
        for role in ('up','down'):
            name='blk.'+str(layer)+'.ffn_'+role+'_exps.weight';tensor=next(t for t in model['tensors'] if t['name']==name)
            pending.append(dict(layer=layer,role=role,source=tensor['file']))
    hashes={Path(prefix['original_BF16_source']['path']).name:a.Up_prefix};running=[];completed=[];failed=[];notice=0
    save(a.out/'intent.private.json',dict(importance=record(a.importance),reference=record(a.reference),Up_prefix=record(a.Up_prefix),
        jobs=pending.copy(),workers=a.workers,encoder_snapshot=record(encoder),original_BF16_direct_quantization=True,host_model_inference=False,
        automatic_retries=0,PS5_operations=0))
    while pending or running:
        for row in running[:]:
            child=row['child'];status=child.poll()
            if status is None:continue
            row['stream'].close();path=row['out']/'result.private.json';running.remove(row)
            if status or not path.exists():failed.append(dict(job=row['job'],returncode=status,log=record(row['log'])))
            else:
                done=load(path);need(done['completed'] and done['complete_layer'] and done['encoded_Experts']==512,'Only fully encoded positive layers may advance')
                hashes[row['job']['source']]=path;completed.append(dict(job=row['job'],result=record(path),pack=done['pack']))
                save(a.out/(row['job']['role']+'-'+str(row['job']['layer']).zfill(2)+'.complete.private.json'),completed[-1])
        while len(running)<a.workers and pending:
            busy={r['job']['source'] for r in running}
            index=next((i for i,j in enumerate(pending) if j['source'] in hashes or j['source'] not in busy),None)
            if index is None:break
            job=pending.pop(index);out=a.out/(job['role']+'-'+str(job['layer']).zfill(2));log=a.out/(out.name+'.private.log')
            command=[sys.executable,'-B',str(encoder)]
            for name in ('workspace','cache','importance','reference'):command+=['--'+name,str(getattr(a,name))]
            command+=['--role',job['role'],'--layer',str(job['layer']),'--Experts','512','--out',str(out)]
            if job['source'] in hashes:command+=['--source-hash-proof',str(hashes[job['source']])]
            if job['role']=='up' and job['layer']==0:command+=['--reuse-prefix',str(a.Up_prefix)]
            stream=log.open('xb');child=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                env=dict(os.environ,PYTHONPATH=str(ROOT/'tools')))
            running.append(dict(child=child,stream=stream,job=job,out=out,log=log))
        if time.monotonic()>=notice:
            print(json.dumps(dict(completed_layers=len(completed),running_layers=len(running),pending_layers=len(pending),failed_layers=len(failed),PS5_operations=0)),flush=True)
            (a.out/'progress.private.json').write_text(json.dumps(dict(completed=completed,failed=failed,
                running=[dict(job=r['job'],pid=r['child'].pid,out=str(r['out']),log=str(r['log'])) for r in running],pending=pending),indent=2)+'\n')
            notice=time.monotonic()+30
        if pending or running:time.sleep(1)
    save(a.out/'result.private.json',dict(completed=not failed,layers=completed,failed_layers=failed,automatic_retries=0,
        original_BF16_direct_quantization=True,host_model_inference=False,PS5_operations=0,
        model_GPU_integration_quality_and_speed_qualified=False))
    need(not failed,'Independent completed layers are retained; inspect failed host layers without replaying completed encodings')


if __name__=='__main__':main()
