#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one bounded CPU-only weight-preparation copy with positive Direct cleanup."""
import argparse,hashlib,importlib.util,json,re,time
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads(a.build.read_text())
 require(m['completed_build']and m['CPU_only']and m['Expert_samples']==3 and m['GPU_calls']==m['title_launches']==m['source_writes']==0,'Bounded three-triplet CPU preparation only')
 op=module('operator',ROOT/'.local/first_operator_038.py');op.R=Path(op.load(op.ACTIVE)['context']).parent
 with op.writer_lease(Path('D:/PS5-AI/qwen-flash-next/model-data-continuation.writer.lock')):
  state=op.current();op.no_native();require(not any(state[k]for k in('native_running','gateway_running','model_loaded')),'Idle current observed console required')
  reservation=record(op.ACTIVE);context=record(op.R/'active-console.private.json')
  for row in m['inputs']+[m['artifact']]:op.unchanged(row)
  a.out.mkdir(parents=True,exist_ok=False);write_json(a.out/'predeclared.private.json',dict(build=record(a.build),maximum_executions=1,new_output=m['new_output'],
   new_output_bytes=m['new_output_bytes'],original_sources_preserved=True,GPU_calls=0,title_launches=0,learned_inference=False,automatic_retries=0))
  transport=module('transport',ROOT/'.local/long_split_CPU_transport_1631.py');last=[time.monotonic(),b'']
  def tick():
   require(record(op.ACTIVE)==reservation and record(context['path'])==context,'Reservation changed');require(time.monotonic()-last[0]<60,'No positive CPU progress; retain completion state and do not retry')
  def progress(raw):
   require(len(raw)<=16<<20 and raw.startswith(last[1]),'Bounded append-only journal required')
   if raw!=last[1]:last[:]=[time.monotonic(),raw]
  execute,_=transport.derive_once(op.lan,progress,tick);raw=execute(m['artifact']['path'],m['artifact']['sha256'],'',m['remote_elf'],m['remote_log'],a.out/'execution',100)
  log=a.out/'terminal.private.log';log.write_bytes(raw);op.no_native();tick();lines=raw.decode().splitlines();ends=[x for x in lines if x.startswith('END ')];require(len(ends)==1 and 'nonce='+m['nonce']in ends[0],'Exact bounded terminal required')
  if 'END success=1 'not in ends[0]:
   write_json(a.out/'result.private.json',dict(completed=False,known_CPU_returned_refusal=True,new_output_retained=True,raw=record(log),GPU_calls=0,title_launches=0,automatic_retries=0));print(json.dumps(dict(CPU_returned_refusal=[x for x in lines if x.startswith('REFUSED')],unchanged_retry=False)));return
  require(b'DIRECT known_completion_cleanup_returned=1 fully_released=1'in raw,'Positive complete Direct retirement required')
  seals=[dict(re.findall(r'(\w+)=([^ ]+)',x))for x in lines if x.startswith('SEALED ')];blocks=[dict(re.findall(r'(\w+)=([^ ]+)',x))for x in lines if x.startswith('BUNDLE ')]
  require(len(seals)==1 and int(seals[0]['bytes'])==m['new_output_bytes']and len(blocks)==3 and [int(x['index'])for x in blocks]==[0,1,2],'Complete ordered sample and whole seal required')
  data=op.lan.web('/fs'+m['new_output'],m['new_output_bytes']+1,30);require(len(data)==m['new_output_bytes']and hashlib.sha256(data).hexdigest()==seals[0]['SHA256'],'Downloaded sample must match native whole SHA exactly')
  local=a.out/'same-layer-triplets.private.bin';local.write_bytes(data)
  write_json(a.out/'result.private.json',dict(completed=True,kind='native_three_same_layer_triplet_capture',native_build=record(a.build),
   selected_source_triplets=m['selected_source_triplets'],local=record(local),output=dict(path=m['new_output'],bytes=len(data),sha256=seals[0]['SHA256'],identity=[int(x)for x in seals[0]['identity'].split(',')]),
   bundles=blocks,CPU_Direct_positively_retired=True,original_sources_preserved=True,GPU_calls=0,title_launches=0,learned_inference=False,production_adopted=False,raw=record(log)))
  print(json.dumps(dict(completed=True,same_layer=m['selected_source_triplets'][0]['layer'],triplets=3,bytes=len(data),native_whole_SHA_and_download_equal=True,GPU_calls=0,title_launches=0)))
if __name__=='__main__':main()
