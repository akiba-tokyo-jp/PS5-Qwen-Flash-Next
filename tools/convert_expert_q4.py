#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stream Expert-only Q4_0 GGUF replacements, retaining unchanged large files."""
import argparse
import concurrent.futures
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
import time
from expert_q4 import EXPERT, LOCK, MATRIX_VALUES, MATRIX_Q4_BYTES, pinned_gguf, record, require, write_json


def identity(path):
    s=Path(path).stat()
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache','original','inventory','encoder','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--workers',type=int,default=6)
    p.add_argument('--batch-experts',type=int,default=32)
    p.add_argument('--resume',type=Path,help='Completed files from a positively stopped earlier host conversion')
    a=p.parse_args();require(1<=a.workers<=8 and a.batch_experts in (8,16,32,64),'Bounded host conversion geometry required')
    inventory=json.loads(a.inventory.read_text());encoder=json.loads(a.encoder.read_text())
    require(inventory['schema']=='ps5-qwen-expert-q4-inventory-v1' and inventory['format']=='Q4_0' and
            encoder['completed'] and encoder['all_native_bytes_match_pinned_Q4_0'], 'Qualified Q4-only inventory and encoder required')
    require(record(encoder['library']['path'])==encoder['library'],'Host encoder library changed')
    require(record(a.original/'model-receipt.json')==inventory['original_receipt'],'Original BF16 receipt changed')
    gguf,np=pinned_gguf(a.cache)
    lib=ctypes.CDLL(encoder['library']['path']);fn=lib.qwen_quantize_bf16_q4_0
    fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];fn.restype=ctypes.c_int
    a.out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    receipt=dict(schema='ps5-qwen-expert-q4-conversion-v1',format='Q4_0',original_receipt=inventory['original_receipt'],
        original_revision=LOCK['model']['revision'],upstream_revision=LOCK['llama_cpp']['revision'],
        inventory=record(a.inventory),encoder=record(a.encoder),conversion_tool=record(Path(__file__)),
        original_BF16_files_modified=False,non_expert_payload_bytes_preserved=True,model_components_omitted=False,
        console_operations=0,model_inference=False,files=[],tensors=[],completed=False)
    previous=None
    if a.resume:
        previous=json.loads((a.resume/'receipt.partial.private.json').read_text())
        stop=json.loads((a.resume/'host-writer-stop-7521.private.json').read_text())
        require(previous['original_receipt']==receipt['original_receipt'] and previous['inventory']==receipt['inventory'] and
                previous['encoder']==receipt['encoder'] and stop['PS5_operations']==0,
                'The stopped conversion must use identical source, inventory and encoder')
        # This check also excludes PID reuse. Completed files alone are reused;
        # the interrupted output stays in its original directory.
        import subprocess
        process=subprocess.run(['powershell','-NoProfile','-Command',
            f"Get-Process -Id {int(stop['pid'])} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],capture_output=True)
        require(not process.stdout.strip(),'The old host writer must be absent before resuming')
        receipt['resume_source']=record(a.resume/'receipt.partial.private.json')
        receipt['prior_conversion_tool']=previous['conversion_tool']
        snapshot=Path(__file__).resolve().parents[1]/'.local/convert_expert_q4_7503.snapshot.py'
        saved=record(snapshot)
        require(saved['sha256']==previous['conversion_tool']['sha256'],'Original conversion source snapshot changed')
        receipt['prior_conversion_tool_snapshot']=saved
    receipt.update(batch_experts=a.batch_experts,workers=a.workers,host_pid=os.getpid())
    def status(phase,**fields):
        write_json(a.out/'status.private.json',dict(phase=phase,host_pid=os.getpid(),elapsed_seconds=time.monotonic()-started,**fields))
    def encode(raw):
        src=np.frombuffer(raw,dtype='<u2');out=np.empty(src.size//32*18,dtype=np.uint8)
        require(src.size>0 and src.size%32==0,'Complete Q4 blocks required')
        def job(first,last):
            require(fn(src.ctypes.data+first*2,out.ctypes.data+first//32*18,last-first)==0,'Native Q4 conversion refused an original block')
        block_count=src.size//32
        futures=[pool.submit(job,(block_count*i//a.workers)*32,(block_count*(i+1)//a.workers)*32)for i in range(a.workers)]
        for f in futures:f.result()
        return out.tobytes()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            for file_index,item in enumerate(inventory['files']):
                original=item['original'];source=a.original/original['path'];target=a.out/original['path']
                before=identity(source);require(before[2]==original['bytes'],'Original file size changed')
                status('converting',file=file_index+1,files=len(inventory['files']),name=source.name)
                old=next((r for r in previous['files'] if r['path']==target.name),None) if previous else None
                if old:
                    preserved=a.resume/target.name;actual=record(preserved)
                    require(old['original_sha256']==original['sha256'] and actual['bytes']==old['bytes'] and actual['sha256']==old['sha256'],
                            'Completed prior Q4 file readback changed')
                    os.link(preserved,target)
                    require(identity(preserved)==identity(target),'Resumed complete file link differs')
                    receipt['files'].append(old)
                    names={t['name'] for t in inventory['tensors'] if t['file']==target.name}
                    receipt['tensors'] += [t for t in previous['tensors'] if t['name'] in names]
                    write_json(a.out/'receipt.partial.private.json',receipt)
                    print(json.dumps(dict(reused_completed_file=file_index+1)),flush=True)
                    continue
                if not item['replacement_required']:
                    os.link(source,target)
                    require(identity(source)==before and identity(target)==before,'Unchanged large GGUF link identity differs')
                    receipt['files'].append(dict(**original,reused_original=True,original_sha256=original['sha256']))
                    continue
                reader=gguf.GGUFReader(source,'r');header=bytearray(reader.data[:reader.data_offset])
                planned=[];cursor=int(reader.data_offset)
                for tensor in reader.tensors:
                    require(cursor%reader.alignment==0,'Generated GGUF tensor alignment differs')
                    match=EXPERT.fullmatch(tensor.name)
                    size=(int(tensor.n_elements)*18//32)if match else int(tensor.n_bytes)
                    offset_position=tensor.field.offset+sum(x.nbytes for x in tensor.field.parts[:5])
                    type_position=offset_position-4
                    if match:struct.pack_into('<I',header,type_position,int(gguf.GGMLQuantizationType.Q4_0))
                    struct.pack_into('<Q',header,offset_position,cursor-reader.data_offset)
                    planned.append(dict(name=tensor.name,source_offset=int(tensor.data_offset),source_bytes=int(tensor.n_bytes),
                        output_offset=cursor,output_bytes=size,quantize=bool(match)))
                    cursor=(cursor+size+reader.alignment-1)//reader.alignment*reader.alignment
                original_hash=hashlib.sha256();output_hash=hashlib.sha256()
                with source.open('rb',buffering=8<<20) as inp,target.open('xb',buffering=32<<20) as output:
                    def write(data):
                        output.write(data);output_hash.update(data)
                    def consume(count,copy=False):
                        while count:
                            raw=inp.read(min(count,8<<20));require(bool(raw),'Original GGUF ended early')
                            original_hash.update(raw)
                            if copy:write(raw)
                            count-=len(raw)
                    write(header)
                    for t in planned:
                        require(inp.tell()<=t['source_offset'],'Original tensors must remain in original payload order')
                        consume(t['source_offset']-inp.tell())
                        require(output.tell()<=t['output_offset'],'Generated tensors overlap')
                        write(bytes(t['output_offset']-output.tell()))
                        payload_hash=hashlib.sha256();quant_hash=hashlib.sha256()
                        if t['quantize']:
                            require(t['source_bytes']==MATRIX_VALUES*2*512,'Original complete 512-Expert tensor required')
                            for expert in range(0,512,a.batch_experts):
                                count=min(a.batch_experts,512-expert)
                                raw=inp.read(MATRIX_VALUES*2*count);require(len(raw)==MATRIX_VALUES*2*count,'Original Expert batch read was short')
                                original_hash.update(raw);payload_hash.update(raw)
                                q4=encode(raw);quant_hash.update(q4);write(q4)
                                status('converting',file=file_index+1,files=len(inventory['files']),tensor=t['name'],expert=expert+count)
                        else:
                            remaining=t['source_bytes']
                            while remaining:
                                raw=inp.read(min(remaining,8<<20));require(bool(raw),'Original non-Expert tensor ended early')
                                original_hash.update(raw);payload_hash.update(raw);write(raw);remaining-=len(raw)
                        require(output.tell()==t['output_offset']+t['output_bytes'],'Generated tensor byte count differs')
                        t.update(original_payload_sha256=payload_hash.hexdigest(),
                            output_payload_sha256=quant_hash.hexdigest()if t['quantize']else payload_hash.hexdigest())
                        write(bytes((-output.tell())%reader.alignment))
                    consume(before[2]-inp.tell())
                    require(inp.read(1)==b'' and original_hash.hexdigest()==original['sha256'],'Full original source SHA256 failed during conversion')
                    output.flush();os.fsync(output.fileno())
                require(identity(source)==before,'Original BF16 source identity changed')
                del reader
                actual=record(target);require(actual['sha256']==output_hash.hexdigest()and actual['bytes']==cursor,'Generated GGUF full readback failed')
                checked=gguf.GGUFReader(target,'r')
                require(len(checked.tensors)==len(planned),'Generated GGUF lost a tensor')
                for actual_tensor,t in zip(checked.tensors,planned):
                    expected_type=gguf.GGMLQuantizationType.Q4_0 if t['quantize']else next(x for x in inventory['tensors']if x['name']==t['name'])['original_type']
                    if isinstance(expected_type,str):expected_type=getattr(gguf.GGMLQuantizationType,expected_type)
                    require(actual_tensor.name==t['name']and actual_tensor.tensor_type==expected_type and
                        actual_tensor.n_bytes==t['output_bytes']and actual_tensor.data_offset==t['output_offset'],'Generated GGUF metadata differs')
                del checked
                receipt['files'].append(dict(path=target.name,bytes=actual['bytes'],sha256=actual['sha256'],
                    reused_original=False,original_sha256=original['sha256']))
                receipt['tensors']+=planned
                write_json(a.out/'receipt.partial.private.json',receipt)
                print(json.dumps(dict(completed_file=file_index+1,total_files=len(inventory['files']),bytes=actual['bytes'])),flush=True)
        require(len(receipt['files'])==76 and sum(t['quantize']for t in receipt['tensors'])==147,'Complete original model and all 147 Expert tensors required')
        receipt.update(completed=True,elapsed_seconds=time.monotonic()-started,new_file_bytes=sum(x['bytes']for x in receipt['files']if not x['reused_original']))
        write_json(a.out/'model-receipt.private.json',receipt);status('completed',files=76)
        print(json.dumps(dict(completed=True,files=76,Expert_tensors=147,new_bytes=receipt['new_file_bytes'])),flush=True)
    except BaseException as error:
        status('failed',error_type=type(error).__name__,message=str(error),partial_outputs_preserved=True)
        raise


if __name__=='__main__':main()
