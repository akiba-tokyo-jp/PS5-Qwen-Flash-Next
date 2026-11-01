#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish one new owned small fixture; its app verifies native SHA before GPU use."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('dataset','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();d=json.loads(a.dataset.read_text());r=d['artifact'];require(d['completed']and record(r['path'])==r and r['bytes']==7864320,'Exact first-layer small fixture required')
 remote='/data/ps5qwen-shared-basis-rank32-40400.bin';spec=importlib.util.spec_from_file_location('operator',ROOT/'.local/first_operator_038.py');op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op);op.R=Path(op.load(op.ACTIVE)['context']).parent
 with op.writer_lease(Path('D:/PS5-AI/qwen-flash-next/model-data-continuation.writer.lock')):
  state=op.current();op.no_native();require(not any(state[k]for k in('native_running','gateway_running','model_loaded')),'Idle console required');a.out.mkdir(parents=True,exist_ok=False)
  try:op.lan.web('/fs'+remote,1,10)
  except op.lan.urllib.error.HTTPError as e:require(e.code==404,'Only an absent new fixture path may be created')
  else:raise ValueError('New fixture path already exists; no overwrite')
  write_json(a.out/'intent.private.json',dict(new_only=True,remote=remote,source=r,bytes=r['bytes'],GPU_calls=0,title_launches=0))
  with op.lan.ftplib.FTP()as ftp:
   ftp.connect(op.lan.HOST,2121,timeout=30);ftp.login()
   with Path(r['path']).open('rb')as stream:reply=ftp.storbinary('STOR '+remote,stream,262144)
  data=op.lan.web('/fs'+remote,r['bytes'],30);require(reply.startswith(('226','250'))and len(data)==r['bytes']and hashlib.sha256(data).hexdigest()==r['sha256'],'Positive transfer close and exact full readback required')
  write_json(a.out/'complete.private.json',dict(completed=True,new_only=True,remote=remote,source=r,full_host_readback_SHA256=True,native_whole_SHA_before_GPU_required_in_fixture=True,production_sources_unchanged=True,GPU_calls=0,title_launches=0))
  print('New7.5MiB fixture input transfer closed and all bytes verified; no title/GPU call.')
if __name__=='__main__':main()
