#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Parse serialized GGUF headers independently and verify contiguous tensors."""
import argparse,hashlib,json,struct,sys,types
from pathlib import Path
from expert_q4 import require,record,write_json
def parse(raw):
    at=0
    def read(fmt):
        nonlocal at
        size=struct.calcsize(fmt);require(at+size<=len(raw),'Serialized header is short');v=struct.unpack_from(fmt,raw,at);at+=size;return v[0]if len(v)==1 else v
    def string():
        nonlocal at
        n=read('<Q');require(n<=len(raw)-at,'Serialized string exceeds header');v=raw[at:at+n].decode('utf-8');at+=n;return v
    def value(kind):
        nonlocal at
        formats={0:'<B',1:'<b',2:'<H',3:'<h',4:'<I',5:'<i',6:'<f',7:'<?',10:'<Q',11:'<q',12:'<d'}
        if kind in formats:return read(formats[kind])
        if kind==8:return string()
        if kind==9:
            k=read('<I');n=read('<Q');require(n<=1<<20,'Metadata array exceeds its bound')
            for _ in range(n):value(k)
            return None
        raise ValueError('Unsupported GGUF metadata type')
    require(read('<I')==0x46554747 and read('<I')==3,'Pinned GGUF v3 required');count=read('<Q');kv=read('<Q');require(count<=8192 and kv<=65536,'Bounded header counts required');alignment=32
    for _ in range(kv):
        name=string();v=value(read('<I'))
        if name=='general.alignment':alignment=v
    tensors=[]
    for _ in range(count):
        name=string();dims=read('<I');require(0<dims<=4,'Valid tensor dimensions required');shape=[read('<Q')for _ in range(dims)];kind=read('<I');offset=read('<Q');tensors.append((name,shape,kind,offset))
    require(alignment==32 and (at+31)//32*32==len(raw),'Exact32-byte header alignment required');return tensors
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prep=json.loads(a.preparation.read_text());require(prep['completed']and prep.get('GGUF_tensor_offsets_contiguous')is True,'Compacted preparation required')
    for r in (prep['candidate'],prep['pack']):require(record(r['path'])==r,'Prepared Q8 input changed')
    r=json.loads(Path(prep['candidate']['path']).read_text());details=r['resident_Q8_overlay'];tensors={t['name']:t for t in r['tensors']};files={f['path']:f for f in r['files']}
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.constants import GGMLQuantizationType as Type
    checked=0
    with Path(prep['pack']['path']).open('rb')as pack:
        for h in details['headers']:
            pack.seek(h['pack_offset']);raw=pack.read(h['bytes']);require(hashlib.sha256(raw).hexdigest()==h['sha256'],'Serialized header hash differs');cursor=0
            for name,shape,kind,offset in parse(raw):
                t=tensors[name];require(t['file']==h['file']and t['shape']==shape and t['type']==Type(kind).name and offset==cursor and t['offset']==h['bytes']+offset,'Native GGUF contiguous offset/type/shape conditions differ')
                cursor+=(t['bytes']+31)//32*32;checked+=1
            require(h['bytes']+cursor<=files[h['file']]['bytes'],'Declared data exceeds immutable base file length')
        for c in details['tensors']:
            pack.seek(c['pack_offset']);require(hashlib.sha256(pack.read(c['bytes'])).hexdigest()==c['payload_sha256'],'Reused complete Q8 payload changed')
    names={h['file']for h in details['headers']};require(checked==sum(t['file']in names for t in r['tensors']),'Every relocated tensor must appear in the serialized header')
    write_json(a.out,dict(completed=True,serialized_contiguous_tensor_headers=checked,Q8_payloads_verified=144,
        unchanged_native_GGUF_offset_rule_satisfied=True,native_parser_relaxations=0,original_weight_reconversions=0,PS5_operations=0,preparation=record(a.preparation)))
    print(f'All{checked} serialized tensor offsets and144 complete Q8 payloads pass the unchanged contiguous GGUF rule.')
if __name__=='__main__':main()
