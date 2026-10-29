# SPDX-License-Identifier: MIT
"""Resolve original sealed quantized role bytes without reading weight payloads."""
import json
from pathlib import Path
from expert_q4 import require,record
TITLE='/data/ai/native-moss-image-sft/PPSA99190'
class Q2PhysicalSpans:
 def __init__(self,path):
  self.inputs=[record(path)];m=json.loads(Path(path).read_text());require(m['completed']and m['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Sealed all-Q2 model required')
  def load(row):require(record(row['path'])==row,'Immutable ancestry changed');self.inputs.append(row);return json.loads(Path(row['path']).read_text())
  self.finish=load(m['complete_conversion']);mixed=load(m['retained_mixed_model_receipt']);self.seal=load(m['retained_mixed_source_seal'])
  self.tensors={t['name']:t for t in mixed['tensors']};self.files={f['path']:f for f in mixed['files']};self.logical={f['path']:f for f in self.seal['logical_files']}
 def role(self,layer,expert,role):
  require(0<=layer<49 and 0<=expert<512 and role in ('gate','up','down'),'Exact Expert role required');size=460800 if role=='down'else 537600
  if role=='down':
   p=next(x for x in self.finish['physical_parts']if x['path'].endswith(f'/down-{layer}.q2_0'));return [self.span(p['path'],p['identity'],expert*size,size)]
  tensor=self.tensors[f'blk.{layer}.ffn_{role}_exps.weight'];f=self.files[tensor['file']];start=tensor['offset']+expert*size
  region=next(x for x in f['regions']if x['logical_offset']<=start and start+size<=x['logical_offset']+x['bytes']);require(region['storage']=='new','Actual Q2_K role required')
  at=region['storage_offset']+start-region['logical_offset'];left=size;out=[]
  for p in self.logical[tensor['file']]['parts']:
   if left and p['offset']<=at<p['offset']+p['bytes']:
    n=min(left,p['offset']+p['bytes']-at);out.append(self.span(p['path'],p['identity'],at-p['offset'],n));at+=n;left-=n
  require(left==0,'Complete role coverage required');return out
 @staticmethod
 def span(path,identity,offset,size):
  path=TITLE+path[5:]if path.startswith('/app0/')else path
  require(path.startswith(TITLE+'/expert-q2-')and identity[2]==0o100644 and identity[3]==identity[4]==0,'Only exact sealed quantized sources permitted')
  return dict(path=path,identity=identity,offset=offset,bytes=size)
