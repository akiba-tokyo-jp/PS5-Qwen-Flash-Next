#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse sealed Q8 payloads and compact GGUF offsets without weight conversion."""
import argparse,copy,hashlib,json,shutil,struct,sys,types
from pathlib import Path
from expert_q4 import require,record,write_json
def finalize_native_metadata(previous,out):
    previous=Path(previous);out=Path(out);prep=json.loads(previous.read_text())
    require(prep['completed']and prep.get('GGUF_tensor_offsets_contiguous')is True,'Completed compact tensor layout required')
    for r in (prep['parent'],prep['candidate'],prep['pack']):require(record(r['path'])==r,'Compacted input changed')
    candidate=json.loads(Path(prep['candidate']['path']).read_text());layout=candidate['resident_Q8_overlay'].pop('tensor_layout',None)
    out.mkdir(parents=True,exist_ok=False);target=out/'model-receipt.json';raw=json.dumps(candidate,separators=(',',':'),ensure_ascii=False)+'\n'
    require(len(raw.encode())<=1<<20,'Native model receipt must remain within the original metadata bound')
    target.write_text(raw,encoding='utf-8',newline='\n');report=copy.deepcopy(prep)
    report.update(candidate=record(target),previous_compact_preparation=record(previous),native_metadata_within_original_bound=True,
        redundant_layout_rows_removed=len(layout)if layout is not None else 0,new_weight_conversions=0)
    write_json(out/'receipt.private.json',report);return report
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','cache','original','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.preparation.read_text());require(old['completed']and old['selected_tensors']==144,'Complete original bounded conversion required')
    for r in (old['parent'],old['candidate'],old['pack']):require(record(r['path'])==r,'Original Q8 preparation changed')
    parent=json.loads(Path(old['parent']['path']).read_text());candidate=json.loads(Path(old['candidate']['path']).read_text());details=candidate['resident_Q8_overlay']
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.gguf_reader import GGUFReader
    a.out.mkdir(parents=True,exist_ok=False);pack=a.out/'resident-shared-Q8.bin';shutil.copyfile(old['pack']['path'],pack)
    files={f['path']:f for f in parent['files']};base={t['name']:t for t in parent['tensors']};changed={t['name']:t for t in details['tensors']};layout=[]
    with pack.open('r+b')as out:
        for h in details['headers']:
            name=h['file'];f=files[name];reader=GGUFReader(a.original/name,'r');original={t.name:t for t in reader.tensors};cursor=f['header_bytes']
            out.seek(h['pack_offset']);header=bytearray(out.read(h['bytes']));require(hashlib.sha256(header).hexdigest()==h['sha256'],'Exact previous Q8 header required')
            for t in candidate['tensors']:
                if t['file']!=name:continue
                prior=base[t['name']];field_at=int(original[t['name']].field.offset)+8+len(t['name'].encode())+4+8*len(t['shape'])+4
                require(struct.unpack_from('<Q',header,field_at)[0]==prior['offset']-f['header_bytes'],'Previous Q8 header offset differs from its base')
                struct.pack_into('<Q',header,field_at,cursor-f['header_bytes']);t['offset']=cursor
                layout.append(dict(name=t['name'],file=name,parent_logical_offset=prior['offset'],logical_offset=cursor,bytes=t['bytes'],type=t['type']))
                if t['name']in changed:changed[t['name']]['parent_logical_offset']=prior['offset'];changed[t['name']]['logical_offset']=cursor
                cursor+=t['bytes'];require(cursor%32==0,'Current projection sizes must remain GGUF aligned')
            require(cursor<=f['bytes'],'Compacted candidate exceeds its immutable base range')
            h['sha256']=hashlib.sha256(header).hexdigest();out.seek(h['pack_offset']);out.write(header)
    details.pop('logical_offsets_and_lengths_preserved');details.update(logical_file_lengths_preserved=True,tensor_offsets_compacted=True,tensor_layout=layout)
    for v in details['overlays']:v['logical_offset']=changed[v['tensor']]['logical_offset']
    details['pack']=record(pack);target=a.out/'model-receipt.json';write_json(target,candidate)
    report=copy.deepcopy(old);report.update(parent=old['parent'],candidate=record(target),pack=record(pack),previous_noncontiguous_preparation=record(a.preparation),
        GGUF_tensor_offsets_contiguous=True,weight_payloads_reused_without_requantization=True,changed_header_bytes_only=True)
    write_json(a.out/'receipt.private.json',report);print(json.dumps(dict(compacted_shared_Q8_prepared=True,relocated_tensors=len(layout),selected_Q8_tensors=144,new_weight_conversions=0)))
if __name__=='__main__':main()
