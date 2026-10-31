#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently check every changed payload, compact descriptor and unchanged tensor."""
import argparse,copy,hashlib,json,sys,types
from contextlib import ExitStack
from pathlib import Path
from expert_q4 import require,record,write_json,LOCK
from prepare_precision_overlay import selection,CONTROL
from audit_shared_q8_headers import parse

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prep=json.loads(a.preparation.read_text())
    require(prep['completed']and prep['parent']['sha256']==CONTROL,'Exact completed precision preparation required')
    for row in [prep['parent'],prep['candidate'],*prep['parts']]:require(record(row['path'])==row,'Prepared precision input changed')
    old=json.loads(Path(prep['parent']['path']).read_text());new=json.loads(Path(prep['candidate']['path']).read_text())
    selected={t['name']:t for t in selection(old,prep['mode'])};o=new['precision_overlay'];changes={t['name']:t for t in o['tensors']}
    require(len(changes)==len(o['tensors'])and changes.keys()==selected.keys(),'Complete exact precision selection required')
    expected=copy.deepcopy(old);byname={t['name']:t for t in expected['tensors']};ranges=[[]for _ in prep['parts']]
    up=a.cache/('upstream/llama.cpp-'+LOCK['llama_cpp']['revision']);pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.constants import GGMLQuantizationType as Type
    import numpy as np
    with ExitStack()as stack:
        parts=[stack.enter_context(Path(row['path']).open('rb'))for row in prep['parts']]
        def read(c):
            part,at,n=c['part'],c['pack_offset'],c['bytes']
            require(0<=part<len(parts)and at%16384==0 and 0<n<=prep['parts'][part]['bytes']-at,'Bounded precision range required')
            ranges[part].append((at,at+n));parts[part].seek(at);return parts[part],n
        for name,c in changes.items():
            t=byname[name];require(t['bytes']==c['original_bytes']and t['payload_sha256']==c['parent_payload_sha256'],'Parent tensor changed')
            block,stored=(64,18)if c['type']=='Q2_0'else(32,18)if c['type']=='Q4_0'else(32,34)
            require(c['type']in('Q2_0','Q4_0','Q8_0')and c['bytes']==int(np.prod(t['shape']))//block*stored,'Exact quantized extent required')
            stream,left=read(c);digest=hashlib.sha256()
            while left:
                raw=stream.read(min(stored*65536,left));require(raw and len(raw)%stored==0,'Complete quantized blocks required')
                left-=len(raw);digest.update(raw);blocks=np.frombuffer(raw,dtype=np.uint8).reshape(-1,stored)
                require(np.isfinite(blocks[:,:2].copy().view('<f2')).all(),'Nonfinite stored quantized scale')
            require(digest.hexdigest()==c['payload_sha256'],'Whole changed payload hash differs')
            t.update(type=c['type'],bytes=c['bytes'],payload_sha256=c['payload_sha256'])
        names=set();files={f['path']:f for f in old['files']}
        for h in o['headers']:
            require(h['file']not in names,'Duplicate precision header');names.add(h['file'])
            stream,n=read(h);raw=stream.read(n);require(hashlib.sha256(raw).hexdigest()==h['sha256']and n==files[h['file']]['header_bytes'],'Complete precision header differs')
            tensors=[t for t in expected['tensors']if t['file']==h['file']];parsed=parse(raw)
            require(len(parsed)==len(tensors),'Every tensor descriptor required');cursor=0
            for t,(name,shape,kind,at)in zip(tensors,parsed):
                require((t['name'],t['shape'],t['type'],cursor)==(name,shape,Type(kind).name,at),'Serialized precision geometry differs')
                t['offset']=n+cursor;cursor+=t['bytes'];require(cursor%32==0,'Unaligned compact tensor')
            require(n+cursor<=files[h['file']]['bytes'],'Compact tensor set exceeds immutable logical file')
        require(names=={t['file']for t in selected.values()},'Changed prefix set incomplete')
    for spans in ranges:
        spans.sort();require(spans and all(x[1]<=y[0]for x,y in zip(spans,spans[1:])),'Overlapping physical precision spans')
    expected.pop('resident_all_Q8_overlay');expected.update(schema='ps5-qwen-precision-overlay-v1',precision_candidate=prep['mode'],precision_overlay=o)
    require(expected==new,'Unselected payload/type/shape or metadata changed')
    ple=next(t for t in new['tensors']if t['name']=='blk.1.ple_conv1d.weight')
    require(ple['type']=='BF16'and ple['bytes']==81920,'Original narrow PLE convolution changed')
    write_json(a.out,dict(completed=True,preparation=record(a.preparation),selected_tensors=len(selected),
        payloads_whole_SHA256_verified=len(changes),contiguous_headers=len(names),
        all_unselected_tensor_payloads_shapes_and_types_unchanged=True,
        original_PLE_convolution_preserved=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
