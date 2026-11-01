#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finish only the missing read-only seal after a known padded-tail-size refusal."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('case','qualified-case','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads((a.case/'result.private.json').read_text());pre=json.loads((a.case/'predeclared.private.json').read_text());m=json.loads(Path(pre['build']['path']).read_text());raw=(a.case/'terminal.private.log').read_bytes()
 require(prior['known_CPU_returned_refusal']and b'REFUSED reason=Whole bundle tail read was short 'in raw and
  raw.count(b'END success=0 nonce='+m['nonce'].encode())==1 and b'DIRECT known_completion_cleanup_returned=1 fully_released=1'in raw,'Only the exact returned tail-size refusal with positive cleanup is eligible')
 blocks=[dict(re.findall(r'(\w+)=([^ ]+)',line))for line in raw.decode().splitlines()if line.startswith('BUNDLE ')];require(len(blocks)==3,'All three original native triplet hashes required')
 s=importlib.util.spec_from_file_location('operator',ROOT/'.local/first_operator_038.py');op=importlib.util.module_from_spec(s);s.loader.exec_module(op);op.R=Path(op.load(op.ACTIVE)['context']).parent
 with op.writer_lease(Path('D:/PS5-AI/qwen-flash-next/model-data-continuation.writer.lock')):
  state=op.current();op.no_native();require(not any(state[k]for k in('native_running','gateway_running','model_loaded')),'Current console must be idle')
  a.out.mkdir(parents=True,exist_ok=False);data=op.lan.web('/fs'+m['new_output'],m['new_output_bytes']+1,20);require(len(data)==m['new_output_bytes'],'Complete immutable sample capture required')
  stride=1540096
  for i,b in enumerate(blocks):require(int(b['index'])==i and hashlib.sha256(data[i*stride:(i+1)*stride]).hexdigest()==b['SHA256'],'Every downloaded triplet must match its original native all-byte hash')
  require(data[3*stride:]==bytes(len(data)-3*stride),'Complete existing final padding must be zero')
  local=a.out/'same-layer-triplets.private.bin';local.write_bytes(data);source=a.out/'sources.private.json';write_json(source,dict(schema='ps5-qwen-closed-artifacts-v1',sources=[dict(remote_path=m['new_output'],capture=record(local),producer_positively_closed=True)]))
  build=a.out/'integrity-build';subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/build_next_five_integrity.py'),
   '--qualified-build',str(a.qualified_case/'launch-Direct-integrity/manifest.private.json'),'--execution-record',str(a.qualified_case/'original-Direct-integrity/execution.once.private.json'),
   '--sources',str(source),'--out',str(build)],check=True,cwd=ROOT)
  check=op.load(build/'manifest.private.json')
  for row in check['inputs']+[check['artifact']]:op.unchanged(row)
  terminal=op.lan.execute_once(check['artifact']['path'],check['artifact']['sha256'],'',check['remote_elf'],check['remote_log'],a.out/'integrity-execution',60)
  require(b'END success=1 'in terminal and ('nonce='+check['nonce']).encode()in terminal and terminal.count(b'FILE_COMPLETE ')==1,'New read-only whole native SHA/identity/EOF completion required')
  op.no_native();write_json(a.out/'result.private.json',dict(completed=True,kind='native_three_same_layer_samples_readonly_seal_completion',
   original_copy_refusal=record(a.case/'result.private.json'),original_copy_and_all_triplet_readbacks=record(a.case/'terminal.private.log'),
   native_readonly_whole_SHA_identity_EOF=record(a.out/'integrity-execution/console.private.log'),local=record(local),
   selected_source_triplets=m['selected_source_triplets'],output=dict(path=m['new_output'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest()),
   bundles=blocks,new_copy_executions=0,source_writes=0,GPU_calls=0,title_launches=0,learned_inference=False,CPU_Direct_positively_retired=True,production_adopted=False))
  print(json.dumps(dict(completed=True,three_native_triplet_hashes_and_whole_native_readonly_SHA_passed=True,new_copy_executions=0,GPU_calls=0,title_launches=0)))
if __name__=='__main__':main()
