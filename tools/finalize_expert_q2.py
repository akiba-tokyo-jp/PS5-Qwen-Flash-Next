#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind complete Q4 conversion to the original native admission and tensor set."""
import argparse,json
from pathlib import Path
from expert_q4 import EXPERT,LOCK,record,require,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('conversion','inventory','original','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();require(not a.out.exists(),'A fresh native Q4 receipt is required')
    conversion=json.loads(a.conversion.read_text());inventory=json.loads(a.inventory.read_text());original=json.loads(a.original.read_text())
    require(conversion['completed'] and conversion['format']=='Gate_Up_Q2_K_Down_Q4_0' and conversion['inventory']==record(a.inventory) and
            conversion['original_receipt']==record(a.original)==inventory['original_receipt'],'Complete bound Q4 conversion required')
    require(len(conversion['files'])==76 and len(inventory['tensors'])==1256,'All original splits and tensors required')
    tensors=[];converted={t['name']:t for t in conversion['tensors']}
    for t in inventory['tensors']:
        match=EXPERT.fullmatch(t['name']);expert=bool(match);down=bool(match and match[2]=='down')
        if expert:require(t['name'] in converted and converted[t['name']]['quantize'],'Every Expert projection must be converted')
        row=dict(name=t['name'],file=t['file'],shape=t['shape'],type=('Q4_0' if down else 'Q2_K')if expert else t['original_type'],
                 bytes=(t['bytes']*18//64 if down else t['bytes']*84//512)if expert else t['bytes'])
        if t['name'] in converted:
            c=converted[t['name']];require(c['output_bytes']==row['bytes'],'Converted tensor size differs')
            if not expert:require(c['original_payload_sha256']==c['output_payload_sha256'],'Non-Expert payload changed')
            row['payload_sha256']=c['output_payload_sha256'];row['offset']=c['output_offset']
        tensors.append(row)
    require(sum(t['type']=='Q4_0'for t in tensors)==49 and sum(t['type']=='Q2_K'for t in tensors)==98 and sum(t['bytes']for t in tensors)==162706565632,
            'Complete mixed-precision tensor byte accounting differs')
    result=dict(schema='ps5-qwen-expert-q2-model-v1',completed=True,Expert_format='Gate_Up_Q2_K_Down_Q4_0',
        original_revision=LOCK['model']['revision'],upstream_revision=LOCK['llama_cpp']['revision'],
        original_receipt_sha256=record(a.original)['sha256'],original_BF16_receipt=original,
        all_Experts_retained=True,non_Expert_payload_bytes_preserved=True,activation_quantization=False,KV_quantization=False,
        host_model_inference=False,packed_composite_sources=True,retained_Q4_conversion=conversion['retained_Q4_conversion'],retained_Q4_source_seal=conversion['retained_Q4_source_seal'],files=conversion['files'],tensors=tensors,
        mapped_file_bytes=sum(t['bytes'] for t in conversion['files']),
        complete_conversion=record(a.conversion),inventory=record(a.inventory),finalizer=record(Path(__file__)))
    # Compact serialization retains every field within the existing native metadata limit.
    a.out.write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf-8',newline='\n');require(a.out.stat().st_size<=1<<20,'Native Q4 receipt exceeds bounded metadata window')
    print(json.dumps(dict(native_Q2_receipt_created=True,files=76,tensors=1256,Expert_tensors=147,bytes=a.out.stat().st_size)))

if __name__=='__main__':main()
