#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit actual sealed all-Expert Q2 metadata with the qualified host parser."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('cache','receipt','seal','control','out'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();model=json.loads(a.receipt.read_text());seal=json.loads(a.seal.read_text());control=json.loads(a.control.read_text())
 require(model['schema']=='ps5-qwen-expert-all-q2-model-v1'and model['completed']and seal['schema']=='ps5-qwen-expert-all-q2-native-source-integrity-v1','Actual completed model and native seal required')
 require(seal['model_receipt_sha256']==record(a.receipt)['sha256']and seal['all_new_parts_complete_Direct_SHA256_readback']and seal['CPU_owners_positively_closed'],'Native whole readback, exact receipt and positive retirement required')
 require(control['completed']and control['metadata_only']and control['not_for_deployment'],'Exact qualified parser control required')
 for row in control['inputs']:require(record(row['path'])==row,'Qualified parser input changed')
 for row in (model['retained_mixed_source_seal'],model['retained_mixed_model_receipt'],model['complete_conversion']):require(record(row['path'])==row,'Actual evidence changed')
 finish=json.loads(Path(model['complete_conversion']['path']).read_text())
 require(finish['all_logical_bytes_native_hashed']and finish['all_payload_hash_spans_verified']and finish['Direct_window_positively_retired'],'Complete actual logical hashes required')
 raw=a.seal.read_bytes().decode('utf-8');require(len(raw.encode())<=2<<20 and a.receipt.stat().st_size<=1<<20,'Qualified metadata bounds exceeded')
 a.out.mkdir(parents=True,exist_ok=False)
 gate=dict(model_receipt_sha256=record(a.receipt)['sha256'],model_receipt_bytes=a.receipt.stat().st_size,
  Expert_all_Q2_source_integrity=dict(schema='ps5-qwen-expert-all-q2-source-policy-v1',raw=raw,sha256=record(a.seal)['sha256']))
 gp=a.out/'actual-gate.private.json';write_json(gp,gate)
 exe=a.control.parent/'all-Q2-composite.exe';require(exe.is_file(),'Previously compiled qualified parser is missing')
 command=[exe,a.receipt,gp,model['retained_mixed_model_receipt']['path'],model['retained_mixed_source_seal']['path'],
  a.cache/'Expert-Q4-receipt-7629.json',a.cache/'build/Expert-Q4-relocation-7670/source-integrity.private.json',
  a.cache/'expert-q4-local-conversion-7605/model-receipt.private.json']
 host=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin'
 run=subprocess.run(list(map(str,command)),capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
 (a.out/'parser.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
 result=json.loads(run.stdout);require(result['complete_all_Expert_Q2_metadata_passed']and result['invalid_candidates_refused']==13,'Complete actual metadata admission failed')
 write_json(a.out/'receipt.private.json',dict(completed=True,actual_sealed_model_metadata=True,PS5_operations=0,
  native_source_open_identity_checks_still_required=True,actual_model=record(a.receipt),actual_seal=record(a.seal),
  parser_executable=record(exe),qualified_control=record(a.control),gate=record(gp),result=result))
 print(json.dumps(dict(actual_all_Q2_source_metadata_admitted=True,physical_sources=result['physical_sources'],source_segments=result['source_segments'],PS5_operations=0)),flush=True)
if __name__=='__main__':main()
