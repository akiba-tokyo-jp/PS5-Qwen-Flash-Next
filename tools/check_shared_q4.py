#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently parse candidate GGUF prefixes and verify all shared-Q4 extents."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from build_performance_quantizer import record
from prepare_shared_q4 import load


class Prefix:
    def __init__(self,raw):self.raw=raw;self.at=0
    def take(self,count):
        if count<0 or count>len(self.raw)-self.at:raise ValueError('GGUF prefix exceeds its authenticated extent')
        value=self.raw[self.at:self.at+count];self.at+=count;return value
    def number(self,fmt):return struct.unpack('<'+fmt,self.take(struct.calcsize('<'+fmt)))[0]
    def string(self):return self.take(self.number('Q')).decode('utf-8')
    def value(self,kind):
        if kind==8:return self.string()
        if kind==9:
            element=self.number('I');count=self.number('Q')
            if count>len(self.raw):raise ValueError('Invalid bounded GGUF array')
            return [self.value(element) for _ in range(count)]
        return self.number({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[kind])
    def parse(self):
        if self.take(4)!=b'GGUF' or self.number('I')!=3:raise ValueError('GGUF v3 required')
        tensors=self.number('Q');fields=self.number('Q');metadata={}
        for _ in range(fields):
            key=self.string();metadata[key]=self.value(self.number('I'))
        result={}
        for _ in range(tensors):
            name=self.string();rank=self.number('I')
            if not 1<=rank<=4 or name in result:raise ValueError('Unique bounded tensor required')
            result[name]=dict(shape=[self.number('Q') for _ in range(rank)],type=self.number('I'),offset=self.number('Q'))
        alignment=metadata.get('general.alignment',32)
        if alignment!=32 or (self.at+31)//32*32!=len(self.raw) or any(self.raw[self.at:]):
            raise ValueError('Complete unchanged zero-padded GGUF prefix required')
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delta',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    delta=load(args.delta);assert delta['schema']=='ps5-qwen-shared-Q4-source-delta-v1'
    control=load(delta['control']['path']);assert record(delta['control']['path'])==delta['control']
    candidate=load(args.delta.parent/'candidate-model.private.json')
    assert record(delta['pack']['path'])==delta['pack']
    before={r['name']:r for r in control['tensors']};after={r['name']:r for r in candidate['tensors']}
    assert before.keys()==after.keys() and len(before)==1256
    changed={r['name']:r for r in delta['tensors']};assert len(changed)==144
    headers={r['file']:r for r in delta['headers']};assert len(headers)==48
    with Path(delta['pack']['path']).open('rb') as pack:
        cursor=0
        for row in delta['tensors']:
            offset=row['pack_offset'];length=row['bytes']
            assert offset%16384==0 and cursor<=offset and offset+length<=delta['pack']['bytes']
            pack.seek(cursor);assert not any(pack.read(offset-cursor))
            payload=pack.read(length);assert len(payload)==length
            assert hashlib.sha256(payload).hexdigest()==row['payload_sha256']
            assert row['type']=='Q4_0' and row['control_type']=='Q8_0'
            assert length==row['shape'][0]*row['shape'][1]//32*18
            cursor=offset+length
        assert cursor==delta['pack']['bytes']
    # Type IDs come from the unchanged model's selected GGUF enum contract.
    # A changed tensor must be Q4_0 (ID2); every other dtype is unchanged.
    types=dict(F32=0,F16=1,Q4_0=2,Q8_0=8,Q2_K=10,BF16=30,Q2_0=42)
    covered=0
    for filename,header in headers.items():
        assert record(header['path'])=={k:header[k] for k in ('path','bytes','sha256')}
        descriptors=Prefix(Path(header['path']).read_bytes()).parse()
        rows=[r for r in candidate['tensors'] if r['file']==filename]
        assert descriptors.keys()=={r['name'] for r in rows}
        cursor=header['bytes']
        for row in rows:
            descriptor=descriptors[row['name']]
            assert descriptor['shape']==row['shape'] and descriptor['offset']==cursor-header['bytes']
            assert row['offset']==cursor and cursor%32==0
            assert descriptor['type']==types[row['type']]
            cursor+=row['bytes'];covered+=1
    for name,row in after.items():
        expected=dict(before[name])
        if name in changed:
            expected.update(type='Q4_0',bytes=changed[name]['bytes'],payload_sha256=changed[name]['payload_sha256'])
        if row['file'] in headers:expected['offset']=row['offset']
        assert row==expected,'Unexpected nonselected tensor mutation: '+name
    assert sum(before[n]['bytes']-after[n]['bytes'] for n in changed)==117964800
    # candidate-model is deliberately not a deployable source recipe: its
    # parent precision overlay must be composed by a native source integration.
    assert not delta['native_source_integration_complete'] and not delta['production_adopted']
    result=dict(completed=True,model_tensor_count=len(after),selected_tensors=len(changed),
                independently_parsed_headers=len(headers),tensors_covered_by_headers=covered,
                all_pack_extents_hashes_and_padding_pass=True,unselected_tensor_metadata_unchanged=True,
                saved_payload_bytes=117964800,native_source_integration_complete=False,
                native_speed_measured=False,production_adopted=False,PS5_operations=0,
                input=record(args.delta),checker=record(Path(__file__)))
    (args.out/'result.private.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input','checker')}))


if __name__=='__main__':main()
