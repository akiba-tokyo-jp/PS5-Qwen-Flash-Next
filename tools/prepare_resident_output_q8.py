#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare an isolated Q8 output head from original BF16; no model inference."""
import argparse,hashlib,json,struct,sys,types,zipfile
from pathlib import Path
from expert_q4 import require,record,write_json,LOCK

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('cache','original','all-Q2-receipt','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();revision=LOCK['llama_cpp']['revision'];upstream=a.cache/'upstream'/('llama.cpp-'+revision);archive=a.cache/('llama-'+revision+'.zip')
 require(record(archive)['sha256']==LOCK['llama_cpp']['archive_sha256'],'Pinned converter archive required')
 # Load only the unmodified reader/quantizer modules. Package-level metadata
 # discovery and its unrelated YAML dependency are unnecessary for this task.
 with zipfile.ZipFile(archive)as z:
  for name in z.namelist():
   if '/gguf-py/gguf/'in name and name.endswith('.py'):
    require((upstream/'gguf-py'/name.split('/gguf-py/',1)[1]).read_bytes()==z.read(name),'Pinned GGUF module changed')
 pkg=types.ModuleType('gguf');pkg.__path__=[str(upstream/'gguf-py/gguf')];sys.modules['gguf']=pkg
 from gguf.gguf_reader import GGUFReader
 from gguf.constants import GGMLQuantizationType as Type
 from gguf.quants import Q8_0
 import numpy as np
 old=json.loads((a.original/'model-receipt.json').read_text());tail=old['files'][-1];source=a.original/tail['path'];before=record(source)
 require(before['bytes']==tail['bytes']and before['sha256']==tail['sha256'],'Exact original BF16 projection file required')
 reader=GGUFReader(source,'r');require(len(reader.tensors)==1,'One complete output tensor required');t=reader.tensors[0]
 require(t.name=='output.weight'and t.tensor_type==Type.BF16 and list(t.shape)==[2560,248320]and t.data_offset==160,'Original output geometry changed')
 header=bytearray(source.open('rb').read(reader.data_offset));type_at=int(t.field.offset)+8+len(t.name.encode())+4+8*len(t.shape)
 require(struct.unpack_from('<I',header,type_at)[0]==int(Type.BF16),'Exact tensor type field required');struct.pack_into('<I',header,type_at,int(Type.Q8_0))
 a.out.mkdir(parents=True,exist_ok=False);target=a.out/tail['path'];payload=hashlib.sha256();squared=norm=0.0;max_error=0.0
 # Explicit roundf ties and zero blocks independently cover the reference rule.
 edge=np.zeros((3,32),dtype=np.float32);edge[1,:8]=[-127,-1.5,-.5,0,.5,1.5,126.5,127];edge[2,:]=np.linspace(-1,1,32,dtype=np.float32)
 encoded=Q8_0.quantize_blocks(edge);require(np.array_equal(encoded[1,2:].view(np.int8)[:8],[-127,-2,-1,0,1,2,127,127])and not encoded[0].any(),'Pinned Q8 reference tie/zero controls failed')
 with source.open('rb')as src,target.open('xb')as dst:
  src.seek(t.data_offset);dst.write(header)
  for row in range(0,248320,512):
   rows=min(512,248320-row);raw=src.read(rows*2560*2);require(len(raw)==rows*2560*2,'Original BF16 output read was short')
   values=(np.frombuffer(raw,dtype='<u2').astype('<u4')<<16).view('<f4').reshape(-1,32);require(np.isfinite(values).all(),'Original output contains nonfinite values')
   packed=Q8_0.quantize_blocks(values);data=packed.tobytes();dst.write(data);payload.update(data)
   d=packed[:,:2].copy().view('<f2').astype('<f4');q=packed[:,2:].copy().view(np.int8).astype('<f4');decoded=d*q
   difference=decoded-values;max_error=max(max_error,float(np.max(np.abs(difference))));squared+=float(np.sum(difference.astype(np.float64)**2));norm+=float(np.sum(values.astype(np.float64)**2))
   if row%32768==0:print(json.dumps(dict(output_Q8_rows=row+rows,total_rows=248320,PS5_operations=0)),flush=True)
  require(src.read(1)==b'','Original output EOF differs')
 require(record(source)==before,'Original BF16 source changed during conversion')
 actual=GGUFReader(target,'r');require(actual.tensors[0].tensor_type==Type.Q8_0 and list(actual.tensors[0].shape)==[2560,248320]and int(actual.tensors[0].n_bytes)==675430400,'New complete output GGUF metadata differs');del actual,reader
 parts=[]
 with target.open('rb')as src:
  for i,offset in enumerate(range(0,target.stat().st_size,512<<20)):
   part=a.out/('output-Q8.part'+str(i)+'.bin');remaining=min(512<<20,target.stat().st_size-offset)
   with part.open('xb')as dst:
    while remaining:
     data=src.read(min(8<<20,remaining));require(bool(data),'Q8 split was short');dst.write(data);remaining-=len(data)
   parts.append(dict(offset=offset,**record(part)))
 parent=json.loads(a.all_Q2_receipt.read_text());candidate=json.loads(json.dumps(parent));candidate['schema']='ps5-qwen-expert-all-q2-output-Q8-model-v1';candidate['non_Expert_payload_bytes_preserved']=False;candidate['non_Expert_except_output_payload_bytes_preserved']=True
 f=candidate['files'][-1];require(f['path']==tail['path']and f['reused_original'],'Only original resident output may change');f.update(bytes=target.stat().st_size,sha256=record(target)['sha256'],reused_original=False)
 output=next(x for x in candidate['tensors']if x['name']=='output.weight');require(output['type']=='BF16'and output['bytes']==1271398400,'Parent output tensor differs');output.update(type='Q8_0',bytes=675430400,payload_sha256=payload.hexdigest())
 candidate['mapped_file_bytes']-=595968000;candidate['resident_output_Q8']=dict(original=before,converted=record(target),parts=parts,original_BF16_payload_bytes=1271398400,Q8_payload_bytes=675430400,saved_payload_bytes=595968000,payload_sha256=payload.hexdigest(),pinned_reference='quantize_row_q8_0_ref',F32_activation_input_required=True)
 candidate_path=a.out/'model-receipt.json';write_json(candidate_path,candidate)
 result=dict(schema='ps5-qwen-resident-output-Q8-preparation-v1',completed=True,original=before,parent=record(a.all_Q2_receipt),candidate_receipt=record(candidate_path),file=record(target),parts=parts,reference_revision=revision,
  maximum_weight_absolute_error=max_error,relative_weight_RMSE=(squared/norm)**.5,saved_resident_payload_bytes=595968000,
  native_upload_and_GPU_component_validation_completed=False,PS5_operations=0,host_model_inference=False,Expert_payloads_unchanged=True,production_adopted=False)
 write_json(a.out/'receipt.private.json',result);print(json.dumps({k:v for k,v in result.items()if k not in ('original','parent','candidate_receipt','file','parts')},indent=2))
if __name__=='__main__':main()
