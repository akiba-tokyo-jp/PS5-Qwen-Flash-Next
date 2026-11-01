#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the108 qualified Q4 payloads and quantize only the original output head."""
import argparse,collections,copy,hashlib,json,struct,sys,types
from pathlib import Path
from expert_q4 import LOCK,record,require,write_json
from prepare_precision_overlay import Parts,CONTROL
from resident_all_q8 import placement

def selection(parent,mode):
    from prepare_precision_overlay import selection as base
    selected=base(parent,mode)
    require(mode=='dense-Q4','Only the combined dense/output Q4 candidate is supported')
    return selected+[next(t for t in parent['tensors']if t['name']=='output.weight')]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('cache','current-preparation','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.current_preparation.read_text())
    require(prior['completed']and prior['parent']['sha256']==CONTROL and prior['selected_tensors']==108,'Qualified108-tensor dense Q4 preparation required')
    for r in [prior['parent'],prior['candidate'],*prior['parts']]:require(record(r['path'])==r,'Current precision input changed')
    current=json.loads(Path(prior['candidate']['path']).read_text());parent=json.loads(Path(prior['parent']['path']).read_text())
    original=current['resident_output_Q8']['original'];require(record(original['path'])==original,'Complete original BF16 output file required')
    require(prior['candidate']['sha256']=='5f991ad0e335993fd2c0d2e97d1d8925e8e95adda013f2549ea923cefd679ec9','Actual selected precision receipt required')
    up=a.cache/('upstream/llama.cpp-'+LOCK['llama_cpp']['revision'])
    pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.gguf_reader import GGUFReader
    from gguf.quants import Q4_0
    from gguf.constants import GGMLQuantizationType as Type
    import numpy as np
    a.out.mkdir(parents=True,exist_ok=False);parts=Parts(a.out);changes=[];headers=[]
    def copy_span(c,digest_key):
        oldpart=prior['parts'][c['part']];part,at=parts.allocate(c['bytes']);h=hashlib.sha256();left=c['bytes']
        with Path(oldpart['path']).open('rb')as f:
            f.seek(c['pack_offset'])
            while left:
                raw=f.read(min(left,8<<20));require(raw,'Complete reused Q4 span required');left-=len(raw);h.update(raw);parts.stream.write(raw)
        require(h.hexdigest()==c[digest_key],'Reused qualified Q4 bytes changed')
        return dict(c,part=part,pack_offset=at)
    try:
        for c in current['precision_overlay']['tensors']:changes.append(copy_span(c,'payload_sha256'))
        for h in current['precision_overlay']['headers']:headers.append(copy_span(h,'sha256'))
        reader=GGUFReader(original['path'],'r');require(len(reader.tensors)==1,'Single original output tensor required')
        t=reader.tensors[0];require(t.name=='output.weight'and t.tensor_type==Type.BF16 and list(t.shape)==[2560,248320],'Original output geometry differs')
        count=int(np.prod(t.shape))//32*18;require(count==357580800,'Exact Q4 output extent required')
        part,at=parts.allocate(count);oh=hashlib.sha256();qh=hashlib.sha256();error=norm=0.;samples=0
        with Path(original['path']).open('rb')as f:
            header=bytearray(f.read(reader.data_offset));f.seek(t.data_offset);left=int(t.n_bytes)
            while left:
                raw=f.read(min(left,8<<20));require(raw and len(raw)%64==0,'Complete BF16 output blocks required');left-=len(raw);oh.update(raw)
                values=(np.frombuffer(raw,dtype='<u2').astype('<u4')<<16).view('<f4');require(np.isfinite(values).all(),'Nonfinite original output weights')
                q=Q4_0.quantize(values).reshape(-1).tobytes();qh.update(q);parts.stream.write(q)
                probe=np.frombuffer(q,dtype=np.uint8).reshape(-1,18)[:128];v=Q4_0.dequantize(probe).reshape(-1).astype(np.float64);ref=values[:len(v)].astype(np.float64)
                error+=float(np.square(v-ref).sum());norm+=float(np.square(ref).sum());samples+=len(v)
        require(parts.stream.tell()==at+count,'Complete output Q4 bytes required')
        old=next(x for x in parent['tensors']if x['name']=='output.weight')
        changes.append(dict(name=t.name,part=part,pack_offset=at,bytes=count,original_bytes=old['bytes'],
            parent_payload_sha256=old['payload_sha256'],original_precision_payload_sha256=oh.hexdigest(),payload_sha256=qh.hexdigest(),
            type='Q4_0',sampled_weight_NRMSE=(error/norm)**.5,sampled_values=samples))
        field=int(t.field.offset)+8+len(t.name.encode())+4+8*len(t.shape);struct.pack_into('<IQ',header,field,int(Type.Q4_0),0)
        part,at=parts.allocate(len(header));parts.stream.write(header)
        headers.append(dict(file=old['file'],part=part,pack_offset=at,bytes=len(header),sha256=hashlib.sha256(header).hexdigest()))
    finally:parts.close()
    require(record(original['path'])==original,'Original output source changed during conversion')
    candidate=copy.deepcopy(current);dst=next(x for x in candidate['tensors']if x['name']=='output.weight')
    dst.update(type='Q4_0',bytes=count,payload_sha256=qh.hexdigest())
    overlay=candidate['precision_overlay'];overlay.update(tensors=changes,headers=headers,parts=[record(x)for x in parts.parts],
        saved_payload_bytes=sum(x['original_bytes']-x['bytes']for x in changes))
    target=a.out/'model-receipt.json';target.write_text(json.dumps(candidate,separators=(',',':'))+'\n',newline='\n')
    require(target.stat().st_size<=1<<20,'Existing receipt bound exceeded')
    footprint=collections.Counter()
    for x in candidate['tensors']:footprint[placement(x['name'])]+=x['bytes']
    write_json(a.out/'receipt.private.json',dict(completed=True,mode='dense-Q4',parent=prior['parent'],candidate=record(target),
        original_precision_receipt=prior['original_precision_receipt'],selected_tensors=109,changed_payload_bytes=sum(x['bytes']for x in changes),
        saved_payload_bytes=overlay['saved_payload_bytes'],parts=overlay['parts'],footprint=dict(footprint),
        all_original_selected_tensor_hashes_verified=True,original_sources_modified=False,PS5_operations=0,native_verification_pending=True,
        reused_current_dense_Q4_tensors=108,additional_output_saved_bytes=317849600,original_output_file=original,
        source_current_preparation=record(a.current_preparation),source_current_model=prior['candidate'],
        original_BF16_output_used=True,output_requantized_from_Q8=False))
    print(json.dumps(dict(completed=True,reused_Q4_tensors=108,newly_quantized_tensors=1,additional_output_saved_bytes=317849600,PS5_operations=0)))

if __name__=='__main__':main()
