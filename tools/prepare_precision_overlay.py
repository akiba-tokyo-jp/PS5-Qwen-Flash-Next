#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare isolated precision candidates from verified original tensor payloads."""
import argparse,collections,copy,ctypes,hashlib,json,os,re,struct,subprocess,sys,types,zipfile
from pathlib import Path
from expert_q4 import LOCK,record,require,write_json
from resident_all_q8 import placement

CONTROL='8b67b85e6cb2f3fd910e900b0299c3325d8717814f0ffab9ef505cab1dfc686b'

class Parts:
    def __init__(self,out):self.out,self.parts,self.stream=out,[],None
    def allocate(self,count):
        require(0<count<=512<<20,'One changed tensor must fit a bounded part')
        if self.stream is None or ((self.stream.tell()+16383)//16384*16384+count>512<<20):
            if self.stream:self.stream.close()
            p=self.out/f'precision.part{len(self.parts)}.bin';self.parts.append(p);self.stream=p.open('xb')
        self.stream.write(bytes((-self.stream.tell())%16384));return len(self.parts)-1,self.stream.tell()
    def close(self):
        if self.stream:self.stream.close()

def selection(parent,mode):
    chosen=[]
    for t in parent['tensors']:
        name=t['name'];layer=re.match(r'blk\.(\d+)\.',name)
        trunk=layer is not None and int(layer[1])<48
        use=(trunk and re.fullmatch(r'blk\.\d+\.ffn_(gate|up)_exps\.weight',name) is not None) if mode=='expert-Q2_0' else (
            trunk and any(name.endswith('.'+s+'.weight') for s in ('attn_qkv','attn_gate','ssm_out'))) if mode=='dense-Q4' else (
            trunk and name.endswith('.ffn_gate_inp.weight'))
        if use:chosen.append(t)
    count,old=(96,26424115200) if mode=='expert-Q2_0' else (108,2205941760) if mode=='dense-Q4' else (48,251658240)
    require(len(chosen)==count and sum(t['bytes']for t in chosen)==old,'Exact candidate tensor set required')
    return chosen

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','parent','original','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('expert-Q2_0','dense-Q4','router-Q8'),required=True)
    p.add_argument('--native-Q2',action='store_true',help='Use the existing pinned-reference C encoder with per-chunk sampled byte checks')
    a=p.parse_args();pr=record(a.parent);require(pr['sha256']==CONTROL,'Exact resident-Q8 control required')
    parent=json.loads(a.parent.read_text());chosen=selection(parent,a.mode)
    original_receipt=a.original/'model-receipt.json';original=json.loads(original_receipt.read_text())
    require(record(original_receipt)['sha256']==parent['original_receipt_sha256'],
            'Original precision receipt must match the existing ancestry')
    mixed_record=parent['retained_mixed_model_receipt']
    require(record(mixed_record['path'])==mixed_record,'Original Expert ancestry changed')
    mixed=json.loads(Path(mixed_record['path']).read_text())
    conversion_record=mixed['retained_Q4_conversion'];inventory_record=mixed['inventory']
    for row in (conversion_record,inventory_record):require(record(row['path'])==row,'Original tensor provenance changed')
    conversion=json.loads(Path(conversion_record['path']).read_text())
    inventory=json.loads(Path(inventory_record['path']).read_text())
    hashes={t['name']:t for t in conversion['tensors']}
    original_by_name={t['name']:dict(t,type=t['original_type'],
        payload_sha256=hashes[t['name']]['original_payload_sha256'])for t in inventory['tensors']
        if t['name'] in {selected['name']for selected in chosen}}
    revision=LOCK['llama_cpp']['revision'];up=a.cache/('upstream/llama.cpp-'+revision)
    archive=a.cache/('llama-'+revision+'.zip')
    require(record(archive)['sha256']==LOCK['llama_cpp']['archive_sha256'],'Pinned quantizer archive required')
    with zipfile.ZipFile(archive)as bundle:
        for name in bundle.namelist():
            if '/gguf-py/gguf/'in name and name.endswith('.py'):
                require((up/'gguf-py'/name.split('/gguf-py/',1)[1]).read_bytes()==bundle.read(name),'Pinned GGUF module changed')
    pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    from gguf.quants import Q2_0,Q4_0,Q8_0
    import numpy as np
    quantizer=Q2_0 if a.mode=='expert-Q2_0' else Q4_0 if a.mode=='dense-Q4' else Q8_0
    target_type='Q2_0' if a.mode=='expert-Q2_0' else 'Q4_0' if a.mode=='dense-Q4' else 'Q8_0'
    block,stored=(64,18)if target_type=='Q2_0'else(32,18)if target_type=='Q4_0'else(32,34)
    a.out.mkdir(parents=True,exist_ok=False);candidate=copy.deepcopy(parent)
    native_encoder=None;native_record=None
    if a.native_Q2:
        require(a.mode=='expert-Q2_0','The C encoder is specific to Q2_0')
        root=Path(__file__).resolve().parents[1];host=root.parents[1]/'toolchain/msys-clang64/clang64/bin'
        dll=a.out/'encoder.dll';source_path=root/'tools/expert_q2_quantize.c'
        command=[str(host/'clang.exe'),'-std=c11','-O3','-shared',str(source_path),'-o',str(dll)]
        run=subprocess.run(command,capture_output=True,timeout=120)
        (a.out/'encoder-build.private.log').write_bytes(run.stdout+run.stderr)
        require(run.returncode==0,run.stderr.decode(errors='replace'))
        os.add_dll_directory(str(host));library=ctypes.CDLL(str(dll))
        native_encoder=library.qwen_quantize_bf16_q2_0
        native_encoder.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];native_encoder.restype=ctypes.c_int
        native_record=dict(library=record(dll),source=record(source_path),command=command,
                           sampled_byte_equality_required_every_chunk=True,sampled_values_per_chunk=4096)
    candidate.pop('resident_all_Q8_overlay');candidate['schema']='ps5-qwen-precision-overlay-v1'
    candidate['precision_candidate']=a.mode
    by_name={t['name']:t for t in candidate['tensors']};grouped=collections.defaultdict(list)
    for t in chosen:grouped[t['file']].append(t)
    parts=Parts(a.out);changes=[];headers=[]
    try:
        for filename,tensors in grouped.items():
            path=a.original/filename;before=path.stat();reader=GGUFReader(path,'r')
            source_tensors={t.name:t for t in reader.tensors}
            with path.open('rb')as source:
                header=bytearray(source.read(reader.data_offset))
                for t in tensors:
                    orig=source_tensors[t['name']];trusted=original_by_name[t['name']]
                    require(list(orig.shape)==t['shape']==trusted['shape'] and
                            int(orig.n_bytes)==trusted['bytes'] and str(orig.tensor_type.name)==trusted['type'],
                            'Original tensor geometry differs')
                    values_total=int(np.prod(orig.shape));count=values_total//block*stored
                    require(values_total%block==0 and t['shape'][0]%block==0,'Quantized row alignment differs')
                    part,at=parts.allocate(count);source.seek(orig.data_offset)
                    old_hash,new_hash=hashlib.sha256(),hashlib.sha256();left=int(orig.n_bytes)
                    sampled_error=sampled_norm=0.;samples=0
                    while left:
                        raw=source.read(min(8<<20,left));require(raw and len(raw)%(block*(2 if trusted['type']=='BF16'else 4))==0,'Complete original blocks required')
                        left-=len(raw);old_hash.update(raw)
                        if trusted['type']=='BF16':values=(np.frombuffer(raw,dtype='<u2').astype('<u4')<<16).view('<f4')
                        else:
                            require(trusted['type']=='F32','Only original BF16/F32 conversion is supported')
                            values=np.frombuffer(raw,dtype='<f4')
                        require(np.isfinite(values).all(),'Nonfinite original precision weight')
                        if native_encoder is not None:
                            source_bits=np.frombuffer(raw,dtype='<u2');encoded=np.empty(values.size//64*18,dtype=np.uint8)
                            require(native_encoder(source_bits.ctypes.data,encoded.ctypes.data,values.size)==0,'Pinned C Q2 encoder refused input')
                            probe_values=min(values.size,4096)
                            reference=quantizer.quantize(values[:probe_values]).reshape(-1)
                            require(np.array_equal(encoded[:reference.size],reference),'C Q2 bytes differ from pinned reference sample')
                            q=encoded.tobytes()
                        else:q=quantizer.quantize(values).reshape(-1).tobytes()
                        parts.stream.write(q);new_hash.update(q)
                        probe=np.frombuffer(q,dtype=np.uint8).reshape(-1,stored)[:128]
                        decoded=quantizer.dequantize(probe).reshape(-1).astype(np.float64)
                        ref=values[:decoded.size].astype(np.float64)
                        sampled_error+=float(np.square(decoded-ref).sum());sampled_norm+=float(np.square(ref).sum());samples+=ref.size
                    require(old_hash.hexdigest()==trusted['payload_sha256'],'Whole original tensor payload changed')
                    require(parts.stream.tell()==at+count,'Complete quantized payload length differs')
                    dst=by_name[t['name']];dst.update(type=target_type,bytes=count,payload_sha256=new_hash.hexdigest())
                    changes.append(dict(name=t['name'],part=part,pack_offset=at,bytes=count,original_bytes=t['bytes'],
                        parent_payload_sha256=t['payload_sha256'],original_precision_payload_sha256=old_hash.hexdigest(),
                        payload_sha256=new_hash.hexdigest(),type=target_type,
                        sampled_weight_NRMSE=(sampled_error/sampled_norm)**.5 if sampled_norm else 0.,sampled_values=samples))
                cursor=reader.data_offset
                for t in candidate['tensors']:
                    if t['file']!=filename:continue
                    orig=source_tensors[t['name']];field=int(orig.field.offset)+8+len(t['name'].encode())
                    struct.pack_into('<I',header,field,len(t['shape']));struct.pack_into('<'+'Q'*len(t['shape']),header,field+4,*t['shape'])
                    field+=4+8*len(t['shape']);struct.pack_into('<IQ',header,field,int(Type[t['type']]),cursor-reader.data_offset)
                    t['offset']=cursor;cursor+=t['bytes'];require(cursor%32==0,'Compact GGUF offset lost alignment')
                require(cursor<=next(f['bytes']for f in parent['files']if f['path']==filename),'Compact tensor set exceeds immutable logical file')
                part,at=parts.allocate(len(header));parts.stream.write(header)
                headers.append(dict(file=filename,part=part,pack_offset=at,bytes=len(header),sha256=hashlib.sha256(header).hexdigest()))
            after=path.stat();require((before.st_size,before.st_ino,before.st_mtime_ns)==(after.st_size,after.st_ino,after.st_mtime_ns),'Original file changed during conversion')
            del reader,source_tensors
            print(json.dumps(dict(precision_candidate=a.mode,converted_tensors=len(changes),total=len(chosen),PS5_operations=0)),flush=True)
    finally:parts.close()
    old=sum(t['original_bytes']for t in changes);new=sum(t['bytes']for t in changes)
    candidate['precision_overlay']=dict(schema='ps5-qwen-precision-overlay-v1',mode=a.mode,
        parent={k:v for k,v in pr.items()if k!='path'},tensors=changes,headers=headers,
        parts=[record(path)for path in parts.parts],saved_payload_bytes=old-new,
        pinned_quantizer_revision=revision,quantizer='pinned_'+target_type+'_reference',
        F32_activation_input_required=True,KV_precision_preserved=True,
        logical_file_lengths_preserved=True,tensor_offsets_compacted=True,narrow_convolution_BF16_preserved=True)
    target=a.out/'model-receipt.json';target.write_text(json.dumps(candidate,separators=(',',':'))+'\n',newline='\n')
    require(target.stat().st_size<=1<<20,'Candidate metadata exceeds existing native bound')
    footprint=collections.Counter()
    for t in candidate['tensors']:footprint[placement(t['name'])]+=t['bytes']
    write_json(a.out/'receipt.private.json',dict(completed=True,mode=a.mode,parent=pr,candidate=record(target),
        original_precision_receipt=record(original_receipt),selected_tensors=len(changes),
        changed_payload_bytes=new,saved_payload_bytes=old-new,parts=[record(path)for path in parts.parts],
        native_encoder=native_record,
        footprint=dict(footprint),all_original_selected_tensor_hashes_verified=True,
        original_sources_modified=False,PS5_operations=0,native_verification_pending=True))

if __name__=='__main__':main()
