#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finalize an all-Q2 receipt only after actual full logical native hashing."""
import argparse,copy,json
from pathlib import Path
from expert_q4 import record,require
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('layout','conversion','finish','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();require(not a.out.exists(),'Fresh actual model receipt required');layout=json.loads(a.layout.read_text());down=json.loads(a.conversion.read_text());finish=json.loads(a.finish.read_text())
 require(down['schema']=='ps5-qwen-expert-all-q2-down-conversion-v1'and down['completed']and down['encoding']=='signed_FP16_scale_MSE_fit'and down['matrices']==25088,'Actual complete fitted-scale Down conversion required')
 require(finish['schema']=='ps5-qwen-expert-all-q2-logical-finish-v1'and finish['completed']and finish['all_logical_bytes_native_hashed']and finish['all_payload_hash_spans_verified']and finish['Direct_window_positively_retired']and finish['source_writes']==0,'Every actual logical byte and payload must pass native hashing')
 require(finish['layout']==record(a.layout)and finish['down_conversion']==record(a.conversion)and finish['new_directory']==down['new_directory']==layout['new_directory'],'Exact same source directory and conversion receipts required')
 tensors=copy.deepcopy(layout['tensors']);converted={t['name']:t for t in down['files']}
 for t in tensors:
  if t['type']=='Q2_0':t['payload_sha256']=converted[t['name']]['sha256']
 require(len(tensors)==1256 and sum(t['type']=='Q2_K'for t in tensors)==98 and sum(t['type']=='Q2_0'for t in tensors)==49 and sum(t['bytes']for t in tensors)==151146015232,'Complete original tensor geometry required')
 old=json.loads(Path(layout['mixed_receipt']['path']).read_text());require(record(layout['mixed_receipt']['path'])==layout['mixed_receipt']and record(layout['mixed_seal']['path'])==layout['mixed_seal'],'Retained mixed source evidence changed')
 rows=[]
 for i in range(49):
  name='blk.'+str(i)+'.ffn_down_exps.weight';t=converted[name];require(t['output_bytes']==235929600 and t['identity'][5]==235929600,'Complete actual Down payload required');rows.append(dict(name=name,layer=i,path=t['output_name'],bytes=t['output_bytes'],sha256=t['sha256'],original_payload_sha256=t['original_payload_sha256']))
 files=finish['files'];require(len(files)==76 and sum(f['bytes']for f in files)==151157049472,'All complete logical model files required')
 result=dict(schema='ps5-qwen-expert-all-q2-model-v1',completed=True,Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',Down_encoding='signed_FP16_scale_MSE_fit',original_revision=layout['original_revision'],upstream_revision=layout['upstream_revision'],original_receipt_sha256=layout['original_receipt_sha256'],original_BF16_receipt=layout['original_BF16_receipt'],all_Experts_retained=True,non_Expert_payload_bytes_preserved=True,activation_quantization=False,KV_quantization=False,host_model_inference=False,packed_composite_sources=True,retained_mixed_source_seal=layout['mixed_seal'],retained_mixed_model_receipt=layout['mixed_receipt'],files=files,tensors=tensors,Down_files=rows,mapped_file_bytes=151157049472,complete_conversion=record(a.finish),Down_conversion=record(a.conversion),layout=record(a.layout),finalizer=record(Path(__file__)))
 a.out.write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf-8',newline='\n');require(a.out.stat().st_size<=1<<20,'Actual receipt must fit the qualified one-MiB metadata window')
 print(json.dumps(dict(actual_all_Expert_Q2_receipt_finalized=True,files=76,tensors=1256,bytes=a.out.stat().st_size,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
