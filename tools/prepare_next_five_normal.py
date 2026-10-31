#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the measured normal composition to fresh API/frame/close evidence."""
import argparse,ast,json,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from self_upload_cache import bind_pending_cache_control
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--case',type=int,required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True)
 p.add_argument('--publication',type=Path);p.add_argument('--native',type=Path,required=True);a=p.parse_args();n=json.loads(a.native.read_text());scope=n['next_five_normal']['scope']
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_four_next_normal.py'),'--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name],check=True,cwd=ROOT)
 path=ROOT/f'.local/prepared_phase_model_{a.case}.private.py';text=path.read_text();marker="policy['native_four_next_normal']=actual_native['four_next_normal']['scope']"
 text=once(text,marker,marker+";policy['native_next_five_normal']=actual_native['next_five_normal']['scope']")
 if a.publication:
  text=once(text,"receipt_record=all_Q8_publication['candidate'];op.unchanged(receipt_record)","precision_publication=op.load(Path("+repr(str(a.publication))+"));receipt_record=precision_publication['candidate'];op.unchanged(receipt_record)")
  marker="    policy['native_resident_all_Q8']=actual_native['resident_all_Q8']"
  text=once(text,marker,marker+"\n    policy['native_precision_candidate']=actual_native['precision_candidate']['scope']\n    precision_seal=Path(precision_publication['source_integrity']['path']);op.unchanged(precision_publication['source_integrity'])\n    gate['precision_source_integrity']=dict(schema='ps5-qwen-precision-source-policy-v1',raw=precision_seal.read_bytes().decode('utf-8'),sha256=op.sha(precision_seal))")
  text=once(text,"app['model_receipt']=op.load(all_Q8_seal)['source_directory']+'/model-receipt.json'","app['model_receipt']=op.load(precision_seal)['source_directory']+'/model-receipt.json'")
 text=text.replace('active_cache_slots=3072','active_cache_slots='+str(scope['active_cache_slots'])).replace('tools/build_preservation_integrity.py','tools/build_next_five_integrity.py')
 ast.parse(text);path.write_text(text,newline='\n')
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';text=path.read_text().replace("reset['slots']==3072","reset['slots']==report['active_cache_slots']").replace('tools/build_preservation_integrity.py','tools/build_next_five_integrity.py').replace("ROOT/'tools/staged_self_upload.py',","ROOT/'tools/staged_self_upload.py',ROOT/'tools/self_upload_cache.py',ROOT/'tools/build_closed_pack_cache_reclaim.py',");ast.parse(text);path.write_text(text,newline='\n')
 text=once(text,"row['full_F32_finite']and row['counting_quality_passed']","row['full_F32_finite']and type(row['counting_quality_passed'])is bool")
 text=text.replace("ROOT/'tools/observe_four_next_normal.py',","ROOT/'tools/observe_four_next_normal.py',ROOT/'tools/observe_next_five_normal.py',");ast.parse(text);path.write_text(text,newline='\n')
 path=ROOT/f'.local/collect_Q2_monitor_{a.case}.py';text=path.read_text();text=once(text,"R/'tools/observe_four_next_normal.py'","R/'tools/observe_next_five_normal.py'");ast.parse(text);path.write_text(text,newline='\n')
 for name in(f'first_operator_{a.case}_base.py',f'restore_resident_cohort_{a.case+5}.py'):
  path=ROOT/'.local'/name;text=path.read_text().replace('tools/build_preservation_integrity.py','tools/build_next_five_integrity.py')
  if name.startswith('first_'):text=bind_pending_cache_control(text)
  ast.parse(text);path.write_text(text,newline='\n')
 print('Fresh measured normal composition prepared; no console operation.')
if __name__=='__main__':main()
