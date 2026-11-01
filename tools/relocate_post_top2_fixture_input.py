#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Move only the exact newly published fixture into the title's app0 directory."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('publication','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.publication.read_text());src='/data/ps5qwen-shared-basis-rank32-40400.bin';dst='/data/ai/native-moss-image-sft/PPSA99190/ps5qwen-shared-basis-rank32-40400.bin';r=prior['source']
 require(prior['completed']and prior['new_only']and prior['remote']==src and record(r['path'])==r,'Exact owned new fixture publication required')
 s=importlib.util.spec_from_file_location('operator',ROOT/'.local/first_operator_038.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o);o.R=Path(o.load(o.ACTIVE)['context']).parent
 with o.writer_lease(Path('D:/PS5-AI/qwen-flash-next/model-data-continuation.writer.lock')):
  state=o.current();o.no_native();require(not any(state[k]for k in('native_running','gateway_running','model_loaded')),'Idle restored console required');a.out.mkdir(parents=True,exist_ok=False);o.lan.absent(dst)
  raw=o.lan.web('/fs'+src,r['bytes'],30);require(len(raw)==r['bytes']and hashlib.sha256(raw).hexdigest()==r['sha256'],'Complete original owned fixture bytes must match')
  write_json(a.out/'intent.private.json',dict(source=src,target=dst,source_bytes=r,new_target_only=True,directory_move=False,GPU_calls=0))
  with o.lan.ftplib.FTP()as ftp:
   ftp.connect(o.lan.HOST,2121,timeout=30);ftp.login();reply=ftp.rename(src,dst)
  require(reply.startswith(('226','250')),'Positive single-file rename required');raw=o.lan.web('/fs'+dst,r['bytes'],30);require(len(raw)==r['bytes']and hashlib.sha256(raw).hexdigest()==r['sha256'],'Complete app0 input readback must match')
  try:o.lan.web('/fs'+src,1,8)
  except o.lan.urllib.error.HTTPError as e:require(e.code==404,'Original owned name must be absent after rename')
  else:raise ValueError('Unexpected original fixture after rename')
  write_json(a.out/'complete.private.json',dict(completed=True,source=src,target=dst,app0_path='/app0/ps5qwen-shared-basis-rank32-40400.bin',source_bytes=r,all_bytes_identical=True,original_name_absent=True,production_sources_unchanged=True,GPU_calls=0,title_launches=0))
  print('Exact new fixture moved into app0; all bytes verified, original name absent, no title/GPU calls.')
if __name__=='__main__':main()
