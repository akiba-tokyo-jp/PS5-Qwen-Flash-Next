#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare shared-Q8 payloads; compact headers before any native publication."""
import argparse,collections,copy,hashlib,json,re,struct,sys,types,zipfile
from pathlib import Path
from expert_q4 import LOCK,require,record,write_json
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('cache','parent','original','headers','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();revision=LOCK['llama_cpp']['revision'];up=a.cache/'upstream'/('llama.cpp-'+revision);archive=a.cache/('llama-'+revision+'.zip')
    require(record(archive)['sha256']==LOCK['llama_cpp']['archive_sha256'],'Pinned quantizer archive required')
    with zipfile.ZipFile(archive)as z:
        for n in z.namelist():
            if '/gguf-py/gguf/'in n and n.endswith('.py'):require((up/'gguf-py'/n.split('/gguf-py/',1)[1]).read_bytes()==z.read(n),'Pinned GGUF module changed')
    pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import Q8_0
    import numpy as np
    parent=json.loads(a.parent.read_text());require(record(a.parent)['sha256']=='458c4b06bcc4c77fa23ce7d1fb6fadf5901439504e712be024e0cc3bf625a6fb','Exact current output-Q8 parent required')
    selected=[t for t in parent['tensors']if re.fullmatch(r'blk\.(?:[0-9]|[1-3][0-9]|4[0-7])\.ffn_(?:gate|up|down)_shexp\.weight',t['name'])]
    require(len(selected)==144 and all(t['type']=='BF16'and t['bytes']==3276800 and t['shape']in([2560,640],[640,2560])for t in selected),'Exactly three original shared projections in each active trunk layer required')
    files={f['path']:f for f in parent['files']};by_file=collections.defaultdict(list)
    for t in selected:by_file[t['file']].append(t)
    a.out.mkdir(parents=True,exist_ok=False);pack=a.out/'resident-shared-Q8.bin';changes=[];overlays=[];headers=[];saved=0
    with pack.open('xb')as out,a.headers.open('rb')as oldheaders:
        def align():
            padding=(-out.tell())%16384
            if padding:out.write(bytes(padding))
        for name,tensors in by_file.items():
            source=a.original/name;before=source.stat();reader=GGUFReader(source,'r');original={t.name:t for t in reader.tensors};f=files[name]
            oldheaders.seek(f['header_pack_offset']);header=bytearray(oldheaders.read(f['header_bytes']))
            require(len(header)==f['header_bytes']and hashlib.sha256(header).hexdigest()==f['parts'][0]['sha256'],'Complete sealed original all-Q2 header required')
            for t in tensors:
                original_tensor=original[t['name']];require(original_tensor.tensor_type==Type.BF16 and list(original_tensor.shape)==t['shape'],'Original shared projection shape/type changed')
                field_at=int(original_tensor.field.offset)+8+len(t['name'].encode())+4+8*len(t['shape'])
                require(struct.unpack_from('<I',header,field_at)[0]==int(Type.BF16),'Only original BF16 header types may change');struct.pack_into('<I',header,field_at,int(Type.Q8_0))
                align();at=out.tell();oldhash=hashlib.sha256();newhash=hashlib.sha256();error=norm=0.;maximum=0.
                with source.open('rb')as src:
                    src.seek(original_tensor.data_offset);left=t['bytes']
                    while left:
                        raw=src.read(min(1<<20,left));require(len(raw)>0 and len(raw)%64==0,'Complete bounded BF16 row blocks required');left-=len(raw);oldhash.update(raw)
                        values=(np.frombuffer(raw,dtype='<u2').astype('<u4')<<16).view('<f4').reshape(-1,32);require(np.isfinite(values).all(),'Original shared weights must be finite')
                        q=Q8_0.quantize_blocks(values);packed=q.tobytes();out.write(packed);newhash.update(packed)
                        decoded=q[:,:2].copy().view('<f2').astype('<f4')*q[:,2:].copy().view(np.int8).astype('<f4')
                        delta=decoded-values;maximum=max(maximum,float(np.max(np.abs(delta))));error+=float(np.sum(delta.astype(np.float64)**2));norm+=float(np.sum(values.astype(np.float64)**2))
                require(oldhash.hexdigest()==t['payload_sha256'],'Selected original BF16 payload differs from the sealed parent')
                count=out.tell()-at;require(count==1740800,'Complete shared Q8 projection geometry differs');saved+=t['bytes']-count
                change=dict(name=t['name'],file=name,shape=t['shape'],original_bytes=t['bytes'],bytes=count,logical_offset=t['offset'],pack_offset=at,
                    parent_payload_sha256=t['payload_sha256'],payload_sha256=newhash.hexdigest(),maximum_absolute_weight_error=maximum,relative_weight_RMSE=(error/norm)**.5)
                changes.append(change);overlays.append(dict(file=name,logical_offset=t['offset'],bytes=count,pack_offset=at,kind='Q8_0',tensor=t['name']))
            align();at=out.tell();out.write(header);headers.append(dict(file=name,logical_offset=0,bytes=len(header),pack_offset=at,sha256=hashlib.sha256(header).hexdigest(),kind='header'))
            after=source.stat();require((before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),'Original BF16 source changed during bounded conversion')
            print(json.dumps(dict(shared_Q8_tensors=len(changes),total=144,PS5_operations=0)),flush=True)
        align()
    require(saved==221184000 and pack.stat().st_size<512<<20,'Bounded active shared-Expert resident saving required')
    candidate=copy.deepcopy(parent);candidate['schema']='ps5-qwen-output-Q8-with-resident-shared-overlay-v1'
    candidate['files_are_immutable_base_descriptors']=True;candidate['candidate_whole_GGUF_hash_claimed']=False
    candidate['non_Expert_except_output_payload_bytes_preserved']=False;candidate['non_Expert_except_output_and_shared_payload_bytes_preserved']=True
    changed={t['name']:t for t in changes}
    for t in candidate['tensors']:
        if t['name']in changed:c=changed[t['name']];t.update(type='Q8_0',bytes=c['bytes'],payload_sha256=c['payload_sha256'])
    candidate['base_output_Q8_receipt_ref']={k:v for k,v in record(a.parent).items()if k!='path'}
    candidate['resident_Q8_overlay']=dict(schema='ps5-qwen-resident-shared-Q8-overlay-v1',family='active_shared_Expert_projections',tensors=changes,
        pack=record(pack),headers=headers,overlays=overlays,saved_resident_payload_bytes=saved,logical_offsets_and_lengths_preserved=True,
        unconsumed_parent_tails_retained=True,original_Expert_payloads_preserved=True,F32_activation_input_required=True,pinned_quantizer_revision=revision)
    target=a.out/'model-receipt.json';write_json(target,candidate)
    write_json(a.out/'receipt.private.json',dict(completed=True,parent=record(a.parent),candidate=record(target),pack=record(pack),selected_tensors=144,
        saved_resident_payload_bytes=saved,maximum_weight_absolute_error=max(t['maximum_absolute_weight_error']for t in changes),
        maximum_tensor_relative_weight_RMSE=max(t['relative_weight_RMSE']for t in changes),GGUF_tensor_offsets_contiguous=False,
        host_only_intermediate=True,required_next_step='compact_resident_q8_overlay.py',native_GPU_validation_completed=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(shared_Q8_overlay_prepared=True,selected_tensors=144,saved_resident_payload_bytes=saved,pack_bytes=pack.stat().st_size)))
if __name__=='__main__':main()
