#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check compact Q2 bundle geometry against the actual sealed model metadata."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 source=record(a.receipt);m=json.loads(a.receipt.read_text());require(m['completed']and m['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Actual complete all-Q2 receipt required')
 tensors={t['name']:t for t in m['tensors']};stride=1540096;part_limit=512<<20;per_part=part_limit//stride;layers=[]
 for layer in range(49):
  roles=[]
  for role,size,kind,offset in [('gate',537600,'Q2_K',0),('up',537600,'Q2_K',537600),('down',460800,'Q2_0',1075200)]:
   t=tensors[f'blk.{layer}.ffn_{role}_exps.weight'];require(t['type']==kind and t['shape'][2]==512 and t['bytes']==size*512,'Original quantized Expert geometry changed')
   roles.append(dict(role=role,bytes_per_Expert=size,bundle_offset=offset,tensor=t))
  layers.append(dict(layer=layer,roles=roles,parts=[dict(first_Expert=first,Experts=min(per_part,512-first),bytes=min(per_part,512-first)*stride)for first in range(0,512,per_part)]))
 report=dict(schema='ps5-qwen-Q2-bundle-plan-v1',completed_metadata_check=True,source_receipt=source,layer_count=49,Experts_per_layer=512,top_k=10,part_limit_bytes=part_limit,alignment_bytes=16384,bundle_payload_bytes=1536000,bundle_stride_bytes=stride,padding_fraction=4096/1536000,Experts_per_full_part=per_part,physical_parts=98,total_bundle_bytes=49*512*stride,additional_virtual_mapping_ranges=0,layers=layers,native_payload_pack_written=False,native_IO_speed_measured=False,production_changed=False,PS5_operations=0,CI_runs=0)
 require(record(a.receipt)==source,'Immutable model receipt changed');a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items()if k not in ('layers','source_receipt')}))
if __name__=='__main__':main()
