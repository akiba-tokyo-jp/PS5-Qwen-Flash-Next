#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare the uniform Gate/Up metadata once when the original Gate worker finishes."""
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
    for name in ('current','cache','Up-preparation','Gate-encoding-root','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();up=load(a.Up_preparation)
    need(up['completed'] and up['IQ2_Up_layers']==list(range(48)) and not up.get('IQ2_Gate_layers') and
         len(up['encoded_layers'])==48 and len(up['completed_encoding_receipts'])==48,
         'The completed uniform Up metadata and immutable original encoding receipts are required')
    encoded_roots={Path(row['path']).parent for row in up['completed_encoding_receipts']}
    need(len(encoded_roots)==1,'One completed original Up coordinator is required')
    encoder_root=encoded_roots.pop();preparer=ROOT/'tools/prepare_iq2_up_model_overlay.py'
    frozen=record(preparer);gate_intent=record(a.Gate_encoding_root/'intent.private.json')
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'intent.private.json',dict(Up_preparation=record(a.Up_preparation),Gate_encoder_intent=gate_intent,
        preparer=frozen,encoding_replays=0,payload_rehashes=0,PS5_operations=0,automatic_retries=0))
    final=a.Gate_encoding_root/'result.private.json'
    while not final.exists():time.sleep(30)
    gate=None
    for attempt in range(3):
        try:gate=load(final);break
        except json.JSONDecodeError:
            need(attempt<2,'The original Gate terminal receipt remains incomplete; never restart encoding')
            time.sleep(1)
    need(gate['completed'] and len(gate['layers'])==48 and not gate['failed_layers'] and
         record(a.Gate_encoding_root/'intent.private.json')==gate_intent and record(preparer)==frozen,
         'Only complete original Gate work and the unchanged metadata preparer may advance')
    command=[sys.executable,'-B',str(preparer),'--current',str(a.current),'--cache',str(a.cache),
        '--completed-encoding-root',str(encoder_root),'--Gate-encoding-root',str(a.Gate_encoding_root),
        '--out',str(a.out/'preparation')]
    for row in up['encoded_layers']:
        need(record(row['path'])==row,'A completed Up encoding receipt changed')
        command+=['--encoded-layer',row['path']]
    with (a.out/'preparation.private.log').open('xb') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180,
            env=dict(os.environ,PYTHONPATH=str(ROOT/'tools')))
    need(result.returncode==0,'Preserve the completed encodings; inspect this distinct metadata preparation failure')
    path=a.out/'preparation/result.private.json';done=load(path)
    need(done['completed'] and done['IQ2_Gate_layers']==done['IQ2_Up_layers']==list(range(48)) and
         done['selected_model_sha256']==up['selected_model_sha256'] and
         done['parent_model_sha256']==up['parent_model_sha256'], 'The same selected P1 ancestry must remain exact')
    done.update(metadata_preparation=record(path),Gate_encoder_completion=record(final),
        Up_preparation_reused=record(a.Up_preparation),encoding_replays=0,automatic_retries=0)
    save(a.out/'result.private.json',done)
    print(json.dumps(dict(completed=True,Gate_layers=48,Up_layers=48,encoding_replays=0,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
