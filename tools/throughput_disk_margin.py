#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prove writable output margin with real bytes, then retire only the owned reserve."""
import argparse,importlib.util,json,os,secrets,subprocess,sys
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--cache',type=Path,required=True);p.add_argument('--qualified-case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);rows=[]
 for i in range(2):
  path=a.out/('reserve-'+str(i)+'.private.bin')
  with path.open('xb')as f:
   for _ in range(16):f.write(os.urandom(8<<20))
  rows.append(dict(remote_path='/data/ai/moss-qwen-writable-margin-'+secrets.token_hex(16)+'.bin',capture=record(path),producer_positively_closed=True))
 spec=importlib.util.spec_from_file_location('disk_margin_operator',ROOT/'.local/first_operator_038.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o);o.R=Path(o.load(o.ACTIVE)['context']).parent
 with o.writer_lease(a.cache/'model-data-continuation.writer.lock'):
  o.no_native();state=o.current();require(not any(state[k]for k in('native_running','gateway_running','model_loaded')),'Positive idle required for a finite disk-margin proof')
  write_json(a.out/'intent.private.json',dict(rows=rows,total_bytes=256<<20,maximum_transfers=2,GPU_calls=0,title_launches=0,automatic_retries=0))
  with o.lan.ftplib.FTP()as f:
   f.connect(o.lan.HOST,2121,timeout=30);f.login();require(f.sendcmd('SELF')=='226 SELF transfer mode disabled','Ordinary file transfer required')
   for row in rows:
    o.lan.absent(row['remote_path'])
    with Path(row['capture']['path']).open('rb')as source:f.storbinary('STOR '+row['remote_path'],source,262144)
    print(json.dumps(dict(real_output_bytes_written=row['capture']['bytes'],GPU_calls=0)),flush=True)
  sources=a.out/'sources.private.json';write_json(sources,dict(schema='ps5-qwen-closed-artifacts-v1',sources=rows));q=a.cache/f'hardware-first-generation-{a.qualified_case}';build=a.out/'build'
  subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/build_next_five_integrity.py'),'--qualified-build',str(q/'launch-Direct-integrity/manifest.private.json'),'--execution-record',str(q/'original-Direct-integrity/execution.once.private.json'),'--sources',str(sources),'--out',str(build)],cwd=ROOT,check=True)
  m=o.load(build/'manifest.private.json');raw=o.lan.execute_once(m['artifact']['path'],m['artifact']['sha256'],'',m['remote_elf'],m['remote_log'],a.out/'verification',60)
  require(b'END success=1 'in raw and('nonce='+m['nonce']).encode()in raw and raw.count(b'FILE_COMPLETE ')==2,'Both complete native SHA/identity/EOF reserve proofs required')
  write_json(a.out/'verified.private.json',dict(completed=True,rows=rows,total_bytes=256<<20,raw=record(a.out/'verification/console.private.log')))
  with o.lan.ftplib.FTP()as f:
   f.connect(o.lan.HOST,2121,timeout=30);f.login()
   for row in rows:
    require(row['remote_path'].startswith('/data/ai/moss-qwen-writable-margin-'),'Only this exact owned reserve may be retired');reply=f.sendcmd('DELE '+row['remote_path']);require(reply.startswith(('226 ','250 ')),'Positive reserve retirement acknowledgement required');o.lan.absent(row['remote_path'])
  o.no_native();write_json(a.out/'complete.private.json',dict(completed=True,real_writable_bytes_verified=256<<20,full_native_SHA_identity_EOF=True,owned_reserve_positively_retired=True,original_sources_and_programs_unchanged=True,capacity_counter_assumption_used=False,GPU_calls=0,title_launches=0,CI_runs=0));print(json.dumps(dict(writable_margin_verified_bytes=256<<20,reserve_retired=True,GPU_calls=0)))
if __name__=='__main__':main()
