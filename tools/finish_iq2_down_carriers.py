#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Consume each newly completed Down encoding once, preserving the completed prefix."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','encoded-root','prior-prefix','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=load(a.prior_prefix);intent=load(a.prior_prefix.parent/'intent.private.json')
    builder=ROOT/'tools/build_iq2_down_carrier.py';bound=record(builder)
    need(prior['completed'] and not prior['requantization'] and prior['PS5_operations']==0 and
         intent['builder']==bound and record(a.encoded_root/'intent.private.json')==intent['encoder_intent'],
         'Reuse only the exact completed carrier prefix and unchanged encoder/builder')
    parts=prior['parts'].copy();need([r['layer'] for r in parts]==list(range(len(parts))),
        'The positive prefix must be contiguous')
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'intent.private.json',dict(prior_prefix=record(a.prior_prefix),builder=bound,
        encoder_intent=intent['encoder_intent'],poll_seconds=60,PS5_operations=0,requantization=False,
        prior_pack_payloads_rehashed=False,complete_input_SHA256_verified_by_each_new_builder=True))
    for layer in range(len(parts),48):
        marker=a.encoded_root/('down-'+str(layer).zfill(2)+'.complete.private.json')
        while not marker.exists():
            progress=load(a.encoded_root/'progress.private.json')
            need(not progress['failed'],'The original encoder failed; never restart or repeat a job')
            print(json.dumps(dict(waiting_for_original_encoder_Down_layer=layer,PS5_operations=0)),flush=True)
            time.sleep(60)
        need(record(builder)==bound,'The frozen carrier builder changed')
        encoded=a.encoded_root/('down-'+str(layer).zfill(2))/'result.private.json'
        out=a.out/('down-'+str(layer).zfill(2))
        with (a.out/('down-'+str(layer).zfill(2)+'.private.log')).open('xb') as log:
            r=subprocess.run([sys.executable,'-B',str(builder),'--cache',str(a.cache),
                '--encoded-layer',str(encoded),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=180)
        need(r.returncode==0,'One changed layer failed; preserve the completed prefix without retry')
        result=load(out/'result.private.json');need(result['completed'],'A complete inverse-qualified carrier is required')
        parts.append(dict(layer=layer,result=record(out/'result.private.json'),pack=result['pack'],reused_without_rebuilding=False))
        (a.out/'progress.private.json').write_text(json.dumps(dict(parts=parts,currently_prepared_layers=len(parts),PS5_operations=0),indent=2)+'\n')
        print(json.dumps(dict(complete_Down_carrier_layers=len(parts),PS5_operations=0)),flush=True)
    save(a.out/'result.private.json',dict(completed=True,parts=parts,pending_layers=[],full48_ready=True,
        prior_prefix=record(a.prior_prefix),requantization=False,model_inference=False,PS5_operations=0,automatic_retries=0))


if __name__=='__main__':main()
