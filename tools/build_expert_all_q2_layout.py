#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare complete logical GGUF headers while reusing sealed mixed payloads."""
import argparse,copy,json,struct
from pathlib import Path
from expert_q4 import EXPERT,pinned_gguf,record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('cache','original','mixed-receipt','mixed-seal','down-plan','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);gguf,_=pinned_gguf(a.cache)
 mixed=json.loads(a.mixed_receipt.read_text());seal=json.loads(a.mixed_seal.read_text());down=json.loads(a.down_plan.read_text())
 require(mixed['completed']and mixed['Expert_format']=='Gate_Up_Q2_K_Down_Q4_0'and seal['model_receipt_sha256']==record(a.mixed_receipt)['sha256'],'Exact complete retained mixed model required')
 require(down['completed_build']and down['new_file_bytes']==11560550400 and down['encoding']=='signed_FP16_scale_MSE_fit','Qualified original-BF16 Down plan required')
 old={x['name']:x for x in mixed['tensors']};bydown={x['name']:x for x in down['tensors']};files=[];tensors=[];pack=a.out/'headers.bin'
 with pack.open('xb')as output:
  for i,f in enumerate(mixed['files']):
   src=a.original/f['path'];before=src.stat();reader=gguf.GGUFReader(src,'r');require(reader.alignment==32,'Original GGUF alignment changed')
   header=bytearray(reader.data[:reader.data_offset]);cursor=int(reader.data_offset);first=len(tensors);regions=[]
   if not f['reused_original']:regions.append(dict(logical_offset=0,bytes=cursor,storage='new_header',storage_offset=0))
   for t in reader.tensors:
    previous=old[t.name];role=EXPERT.fullmatch(t.name);expert=bool(role);isdown=bool(role and role[2]=='down');kind='Q2_0'if isdown else 'Q2_K'if expert else previous['type']
    size=(int(t.n_elements)//64*18 if isdown else int(t.n_elements)//256*84)if expert else int(t.n_bytes)
    field=t.field.offset+sum(x.nbytes for x in t.field.parts[:5]);struct.pack_into('<I',header,field-4,int(getattr(gguf.GGMLQuantizationType,kind)));struct.pack_into('<Q',header,field,cursor-reader.data_offset)
    row=dict(previous,type=kind,bytes=size,offset=cursor);row['shape']=[int(v)for v in t.shape]
    require(row['shape']==previous['shape'],'Every original Expert and tensor dimension must remain')
    if isdown:
     require(bydown[t.name]['source_offset']==int(t.data_offset)and bydown[t.name]['source_bytes']==int(t.n_bytes),'Original Down source location differs')
     row.pop('payload_sha256',None);regions.append(dict(logical_offset=cursor,bytes=size,storage='Down_Q2_0',storage_offset=0,tensor=t.name,layer=int(role[1]),output_name=bydown[t.name]['output_name']))
    elif not f['reused_original']:
     require(size==previous['bytes']and len(previous['payload_sha256'])==64,'Retained payload byte count and hash must remain exact')
     regions.append(dict(logical_offset=cursor,bytes=size,storage='retained_mixed',storage_offset=previous['offset'],retained_file=f['path'],tensor=t.name,payload_sha256=previous['payload_sha256']))
    tensors.append(row);cursor+=size;require(cursor%32==0,'This exact model requires no synthetic tensor padding')
   del reader;after=src.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'Original header source identity changed')
   if f['reused_original']:
    require(cursor==f['bytes'],'Unchanged original split geometry differs');files.append(dict(f));continue
   offset=output.tell();output.write(header);output.write(bytes((-output.tell())%16384));files.append(dict(index=i,path=f['path'],bytes=cursor,header_bytes=len(header),packed_bytes=len(header),header_pack_offset=offset,regions=regions,first_tensor=first,tensor_count=len(tensors)-first,original_sha256=f['original_sha256'],reused_original=False))
 require(len(files)==76 and len(tensors)==1256 and sum(t['type']=='Q2_K'for t in tensors)==98 and sum(t['type']=='Q2_0'for t in tensors)==49,'Complete 49-layer all-Expert Q2 layout required')
 require(sum(t['bytes']for t in tensors)==151146015232 and sum(f['bytes']for f in files)==151157049472,'Complete all-Q2 tensor/logical byte accounting differs')
 require(sum(f['header_bytes']for f in files if not f['reused_original'])<64<<20,'New header storage must remain within the disk metadata reservation')
 write_json(a.out/'plan.private.json',dict(schema='ps5-qwen-expert-all-q2-layout-plan-v1',completed=True,files=files,tensors=tensors,headers=record(pack),mixed_receipt=record(a.mixed_receipt),mixed_seal=record(a.mixed_seal),down_plan=record(a.down_plan),new_directory=down['new_directory'],mapped_file_bytes=151157049472,all_Expert_payload_bytes=38535168000,all_tensor_bytes=151146015232,complete_logical_GGUF=True,Gate_Up_payloads_reused_byte_exact=True,non_Expert_payloads_reused_byte_exact=True,original_BF16_receipt=mixed['original_BF16_receipt'],original_receipt_sha256=mixed['original_receipt_sha256'],original_revision=mixed['original_revision'],upstream_revision=mixed['upstream_revision'],model_inference=False,PS5_operations=0))
 print(json.dumps(dict(all_Expert_Q2_layout_prepared=True,logical_files=76,tensors=1256,new_header_bytes=sum(f['header_bytes']for f in files if not f['reused_original']),logical_bytes=151157049472,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
