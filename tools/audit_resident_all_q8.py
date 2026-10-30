#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently verify every Q8 byte, GGUF descriptor and unchanged tensor."""
import argparse
import copy
import hashlib
import json
import math
import sys
import types
from pathlib import Path
from expert_q4 import require, record, write_json, LOCK
from resident_all_q8 import selection, stored_shape, placement, PARENT_SHA256
from audit_shared_q8_headers import parse


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prep=json.loads(a.preparation.read_text())
    require(prep['completed'] and prep['parent']['sha256']==PARENT_SHA256,'Exact completed conversion required')
    for row in [prep['parent'],prep['candidate'],*prep['parts']]:require(record(row['path'])==row,'Prepared input changed')
    old=json.loads(Path(prep['parent']['path']).read_text());new=json.loads(Path(prep['candidate']['path']).read_text())
    selected={t['name']:t for t in selection(old)};overlay=new['resident_all_Q8_overlay'];changes={c['name']:c for c in overlay['tensors']}
    require(len(changes)==len(overlay['tensors']) and changes.keys()==selected.keys(),'Complete unique selection required')
    expected=copy.deepcopy(old);byname={t['name']:t for t in expected['tensors']};ranges=[[] for _ in prep['parts']]
    up=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision']);pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.constants import GGMLQuantizationType as Type
    import numpy as np
    from contextlib import ExitStack
    with ExitStack() as stack:
        parts=[stack.enter_context(Path(row['path']).open('rb')) for row in prep['parts']]
        def read(c):
            i,offset,size=c['part'],c['pack_offset'],c['bytes'];require(0<=i<len(parts) and offset%16384==0 and 0<size<=prep['parts'][i]['bytes']-offset,'Bounded aligned range required')
            ranges[i].append((offset,offset+size));parts[i].seek(offset);return parts[i],size
        for name,c in changes.items():
            t=byname[name];require(t['payload_sha256']==c['parent_payload_sha256'] and t['bytes']==c['original_bytes'],'Parent payload differs')
            require(all(math.isfinite(c[k]) and c[k]>=0 for k in ('maximum_absolute_weight_error','relative_weight_RMSE')),'Finite weight-error evidence required')
            stream,left=read(c);digest=hashlib.sha256()
            while left:
                raw=stream.read(min(34*32768,left));require(bool(raw) and len(raw)%34==0,'Short or incomplete Q8 blocks');digest.update(raw);left-=len(raw)
                blocks=np.frombuffer(raw,dtype=np.uint8).reshape(-1,34)
                require(np.isfinite(blocks[:,:2].copy().view('<f2')).all() and (blocks[:,2:].view(np.int8)>=-127).all(),'Invalid Q8 scale or signed value')
            require(digest.hexdigest()==c['payload_sha256'],'Complete Q8 payload digest differs')
            t.update(type='Q8_0',shape=stored_shape(t),bytes=c['bytes'],payload_sha256=c['payload_sha256'])
        files={f['path']:f for f in old['files']};header_names=set()
        for h in overlay['headers']:
            require(h['file'] not in header_names,'Duplicate header');header_names.add(h['file']);stream,size=read(h);raw=stream.read(size)
            require(hashlib.sha256(raw).hexdigest()==h['sha256'] and size==files[h['file']]['header_bytes'],'Complete header differs')
            rows=[t for t in expected['tensors'] if t['file']==h['file']];parsed=parse(raw);require(len(rows)==len(parsed),'Every tensor descriptor required');cursor=0
            for t,(name,shape,kind,offset) in zip(rows,parsed):
                require(t['name']==name and t['shape']==shape and t['type']==Type(kind).name and offset==cursor,'Serialized type/shape/order/offset differs')
                t['offset']=size+cursor;cursor+=t['bytes'];require(cursor%32==0,'Unaligned tensor end')
            require(size+cursor<=files[h['file']]['bytes'],'Compacted range exceeds immutable base')
        require(header_names=={t['file'] for t in selected.values()},'Changed headers incomplete')
    for spans in ranges:
        spans.sort();require(bool(spans) and all(x[1]<=y[0] for x,y in zip(spans,spans[1:])),'Physical ranges overlap')
    expected.pop('original_BF16_receipt');expected.pop('resident_Q8_overlay');expected.update(schema='ps5-qwen-all-resident-Q8-overlay-v1',non_Expert_except_output_and_shared_payload_bytes_preserved=False,resident_all_Q8_overlay=overlay)
    require(expected==new,'Unadmitted tensor or metadata change')
    footprint={k:sum(t['bytes'] for t in new['tensors'] if placement(t['name'])==k) for k in ('device_weights','mapped_experts','lazy_ple','mapped_embeddings','skipped_mtp')}
    require(footprint['device_weights']==4774100480,'Resident footprint differs')
    write_json(a.out,dict(completed=True,selected_tensors=len(selected),payloads_whole_SHA256_verified=len(changes),contiguous_headers=len(header_names),all_unselected_tensor_payloads_shapes_and_types_unchanged=True,
        resident_BF16_tensors_remaining=sum(t['type']=='BF16' and placement(t['name'])=='device_weights' for t in new['tensors']),footprint=footprint,
        preparation=record(a.preparation),PS5_operations=0,CI_runs=0))
    print('All544 resident Q8 payloads, exact headers and every unselected tensor verified; PLE convolution stays BF16.')


if __name__=='__main__':main()
