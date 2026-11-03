#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare one required 64-Expert byte range from a completed frozen IQ2 layer."""
import argparse
import hashlib
import json
from pathlib import Path
from build_performance_quantizer import record
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layer',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--first-Expert',type=int,required=True)
    a=p.parse_args();value=load(a.layer)
    need(value['completed'] and value['complete_layer'] and value['encoded_Experts']==512 and
         value['role'] in ('up','down') and value['pack']['bytes']==216268800 and
         0<=a.first_Expert<=448 and a.first_Expert%64==0,'One actual completed uniform IQ2 layer required')
    need(record(value['pack']['path'])==value['pack'],'The immutable full layer changed')
    a.out.mkdir(parents=True,exist_ok=False);source=Path(value['pack']['path']);before=source.stat()
    path=a.out/'fragment.iq2.bin';digest=hashlib.sha256();remaining=27033600
    with source.open('rb') as stream,path.open('xb') as target:
        stream.seek(a.first_Expert*422400)
        while remaining:
            block=stream.read(min(262144,remaining));need(bool(block),'The actual encoded range ended early')
            target.write(block);digest.update(block);remaining-=len(block)
    after=source.stat();need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
        (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'The original encoded source changed during slicing')
    save(a.out/'result.private.json',dict(completed=True,complete_verified_IQ2_fragment=True,
        master_encoding=record(a.layer),master_pack=value['pack'],role=value['role'],layer=value['layer'],
        first_Expert=a.first_Expert,Experts=64,pack=dict(path=str(path.resolve()),bytes=27033600,sha256=digest.hexdigest()),
        lossless_byte_slice_only=True,requantization=False,PS5_operations=0))
    print(json.dumps(dict(completed=True,first_Expert=a.first_Expert,Experts=64,bytes=27033600,PS5_operations=0)))


if __name__=='__main__':main()
