#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse completed Q8 payloads while restoring the owner's BF16 PLE exception."""
import argparse
import copy
import hashlib
import json
import struct
import sys
import types
from pathlib import Path
from expert_q4 import LOCK, require, record, write_json
from resident_all_q8 import CONV, EXPECTED_Q8_BYTES, selection


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','cache','original','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prep=json.loads(a.preparation.read_text());require(prep['completed'] and prep['selected_tensors']==545,'Completed initial conversion required for byte reuse')
    for row in [prep['parent'],prep['candidate'],*prep['parts']]:require(record(row['path'])==row,'Completed input changed')
    parent=json.loads(Path(prep['parent']['path']).read_text());candidate=json.loads(Path(prep['candidate']['path']).read_text());o=candidate['resident_all_Q8_overlay']
    allowed={t['name'] for t in selection(parent)};require(len(allowed)==544,'Exact narrowed scope required')
    o['tensors']=[c for c in o['tensors'] if c['name'] in allowed];require(len(o['tensors'])==544,'Complete reused selection required')
    original=next(t for t in parent['tensors'] if t['name']==CONV);index=next(i for i,t in enumerate(candidate['tensors']) if t['name']==CONV);candidate['tensors'][index]=copy.deepcopy(original)
    o.pop('narrow_convolution_Q8_storage_and_F32_compute');o['narrow_convolution_BF16_preserved']=True
    saved=sum(c['original_bytes']-c['bytes'] for c in o['tensors']);require(sum(c['bytes'] for c in o['tensors'])==EXPECTED_Q8_BYTES,'Reused Q8 lengths differ');o['saved_resident_payload_bytes']=saved
    up=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision']);pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    a.out.mkdir(parents=True,exist_ok=False);part=len(o['parts']);path=a.out/f'resident-all-Q8.part{part}.bin';headers=[]
    with path.open('xb') as out:
        for old in o['headers']:
            file=old['file'];reader=GGUFReader(a.original/file,'r');fields={t.name:t for t in reader.tensors}
            with (a.original/file).open('rb') as source:header=bytearray(source.read(reader.data_offset))
            cursor=reader.data_offset
            for t in candidate['tensors']:
                if t['file']!=file:continue
                t['offset']=cursor;field=int(fields[t['name']].field.offset)+8+len(t['name'].encode())+4+8*len(t['shape'])
                require(list(fields[t['name']].shape)==t['shape'],'All effective shapes must retain the original layout')
                struct.pack_into('<IQ',header,field,int(Type[t['type']]),cursor-reader.data_offset);cursor+=t['bytes'];require(cursor%32==0,'Unaligned restored header')
            out.write(bytes((-out.tell())%16384));offset=out.tell();out.write(header)
            headers.append(dict(file=file,part=part,pack_offset=offset,bytes=len(header),sha256=hashlib.sha256(header).hexdigest()))
            del fields,reader
    o['parts'].append(record(path));o['headers']=headers
    target=a.out/'model-receipt.json';target.write_text(json.dumps(candidate,separators=(',',':'))+'\n',encoding='utf-8',newline='\n');require(target.stat().st_size<=1<<20,'Original native metadata limit required')
    result=copy.deepcopy(prep);result.update(candidate=record(target),parts=o['parts'],selected_tensors=544,original_BF16_bytes=sum(c['original_bytes'] for c in o['tensors']),
        Q8_bytes=EXPECTED_Q8_BYTES,saved_resident_payload_bytes=saved,previous_conversion=record(a.preparation),weight_reconversions=0,
        PLE_convolution_BF16_preserved=True,PLE_convolution_payload_bytes=81920,discarded_Q8_convolution_bytes_not_referenced=43520)
    write_json(a.out/'receipt.private.json',result)
    print('Reused544 completed Q8 payloads; original BF16 PLE convolution restored without weight reconversion.')


if __name__=='__main__':main()
