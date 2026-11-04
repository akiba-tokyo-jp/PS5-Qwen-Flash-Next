#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finish the original Gate/Up proposal without repeating completed Up/Down encodings."""
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
    for name in ('workspace','cache','prior-encoding','Gate-input-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior_intent=load(a.prior_encoding/'intent.private.json')
    need(prior_intent['workers']==2 and os.cpu_count()>=4,'Keep the original two-worker host policy')
    for key in ('importance','reference'):
        need(record(prior_intent[key]['path'])==prior_intent[key],'The pinned original encoding input changed')
    gate=load(a.Gate_input_proof)
    need(gate['completed'] and gate['native_input_identity_qualified'] and gate['all48_layers_per_width'],
         'Actual native Gate/Up input identity is required')
    a.out.mkdir(parents=True,exist_ok=False)
    encoder=a.out/'encoder.private.py';encoder.write_bytes((ROOT/'tools/encode_full_iq2_layer.py').read_bytes())
    model=load(a.cache/'Post-top2-output-Q4-32100/model-receipt.json');pending=[]
    for layer in range(48):
        name='blk.'+str(layer)+'.ffn_gate_exps.weight';t=next(t for t in model['tensors'] if t['name']==name)
        pending.append(dict(layer=layer,role='gate',source=t['file']))
    save(a.out/'intent.private.json',dict(prior_encoding_intent=record(a.prior_encoding/'intent.private.json'),
        Gate_input_identity=record(a.Gate_input_proof),importance=prior_intent['importance'],reference=prior_intent['reference'],
        encoder_snapshot=record(encoder),jobs=pending.copy(),workers=2,original_BF16_direct_quantization=True,
        unchanged_prior_encodings_replayed=0,host_model_inference=False,PS5_operations=0,automatic_retries=0))
    while not(a.prior_encoding/'result.private.json').exists():
        print(json.dumps(dict(phase='waiting_for_original_encoder_positive_completion',new_workers=0,PS5_operations=0)),flush=True)
        time.sleep(30)
    prior=load(a.prior_encoding/'result.private.json')
    need(prior['completed'] and len(prior['layers'])==96 and not prior['failed_layers'],
         'All original children must positively exit before new Gate workers start')
    hashes={r['job']['source']:Path(r['result']['path']) for r in prior['layers']}
    completed=[];failed=[];running=[];notice=0
    while pending or running:
        for row in running[:]:
            status=row['child'].poll()
            if status is None:continue
            row['stream'].close();running.remove(row);path=row['out']/'result.private.json'
            if status or not path.exists():failed.append(dict(job=row['job'],returncode=status,log=record(row['log'])))
            else:
                done=load(path)
                need(done['completed'] and done['complete_layer'] and done['role']=='gate' and done['encoded_Experts']==512,
                     'Only complete Gate encodings may advance')
                hashes[row['job']['source']]=path
                item=dict(job=row['job'],result=record(path),pack=done['pack']);completed.append(item)
                save(a.out/('gate-'+str(row['job']['layer']).zfill(2)+'.complete.private.json'),item)
        while len(running)<2 and pending:
            busy={r['job']['source'] for r in running}
            index=next((i for i,j in enumerate(pending) if j['source'] in hashes or j['source'] not in busy),None)
            if index is None:break
            job=pending.pop(index);out=a.out/('gate-'+str(job['layer']).zfill(2));log=a.out/(out.name+'.private.log')
            command=[sys.executable,'-B',str(encoder),'--workspace',str(a.workspace),'--cache',str(a.cache),
                '--importance',prior_intent['importance']['path'],'--reference',prior_intent['reference']['path'],
                '--Gate-input-proof',str(a.Gate_input_proof),'--role','gate','--layer',str(job['layer']),
                '--Experts','512','--out',str(out)]
            if job['source'] in hashes:command+=['--source-hash-proof',str(hashes[job['source']])]
            stream=log.open('xb');child=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                env=dict(os.environ,PYTHONPATH=str(ROOT/'tools')))
            running.append(dict(child=child,stream=stream,job=job,out=out,log=log))
        if time.monotonic()>=notice:
            progress=dict(completed=completed,failed=failed,
                running=[dict(job=r['job'],pid=r['child'].pid,out=str(r['out']),log=str(r['log'])) for r in running],pending=pending)
            (a.out/'progress.private.json').write_text(json.dumps(progress,indent=2)+'\n')
            print(json.dumps(dict(completed_layers=len(completed),running_layers=len(running),pending_layers=len(pending),
                failed_layers=len(failed),unchanged_prior_encodings_replayed=0,PS5_operations=0)),flush=True)
            notice=time.monotonic()+30
        if pending or running:time.sleep(1)
    save(a.out/'result.private.json',dict(completed=not failed,layers=completed,failed_layers=failed,
        prior_encoding=record(a.prior_encoding/'result.private.json'),Gate_input_identity=record(a.Gate_input_proof),
        workers=2,original_BF16_direct_quantization=True,unchanged_prior_encodings_replayed=0,
        host_model_inference=False,PS5_operations=0,automatic_retries=0,full_model_quality_or_speed_qualified=False))
    need(not failed,'Preserve complete Gate outputs; inspect failed jobs without replaying completed encodings')


if __name__=='__main__':
    main()
