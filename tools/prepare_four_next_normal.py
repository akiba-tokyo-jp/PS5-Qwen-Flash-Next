#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh normal/API/frame scripts with zero-copy speculative counters."""
import argparse,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);a=p.parse_args()
 if a.case<18000 or a.case%100:raise ValueError('Fresh hundred-aligned normal case required')
 names=['prepared_phase_model_17000.private.py','resident_cohort_operator_17000.py','first_operator_17000_base.py','close_resident_cohort_17004.py','restore_resident_cohort_17005.py','build_resident_owner_17003.py','collect_Q2_monitor_17000.py']
 def shift(s):return re.sub(r'(?<![0-9A-Za-z])170\d{2}(?![0-9A-Za-z])',lambda m:str(int(m[0])-17000+a.case),s)
 for name in names:assert (ROOT/'.local'/name).is_file() and not(ROOT/'.local'/shift(name)).exists()
 for name in names:
  s=shift((ROOT/'.local'/name).read_text());s=s.replace('Strata-winners-SELF-16908',a.package_name).replace('Strata-winners-16900',a.build_name);dest=ROOT/'.local'/shift(name)
  if name.startswith('prepared_'):
   marker="policy['native_strata_followup_normal']=actual_native['strata_followup_normal']['scope']";assert s.count(marker)==1;s=s.replace(marker,marker+";policy['native_four_next_normal']=actual_native['four_next_normal']['scope']")
  if name.startswith('resident_'):
   old="checkpoint['captures']==spec['attempts'] and checkpoint['restores']==spec['rejected']";assert s.count(old)==1
   s=s.replace(old,"checkpoint['captures']==0 and checkpoint['restores']==0 and report['four_next']['complete_captures_elided']==spec['attempts'] and report['four_next']['all_memory_rollbacks']==spec['rejected']")
   marker="ROOT/'tools/observe_weight_followup_normal.py',";assert s.count(marker)==1;s=s.replace(marker,marker+"ROOT/'tools/observe_four_next_normal.py',")
  if name.startswith('collect_'):s=s.replace("R/'tools/observe_weight_followup_normal.py'","R/'tools/observe_four_next_normal.py'")
  ast.parse(s);assert not dest.exists();dest.write_text(s,newline='\n')
 runner='''from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[1]
steps=[('prepared_phase_model_CASE.private.py',)]+[('resident_cohort_operator_CASE.py',a)for a in('stage','publish','launch')]+[('collect_Q2_monitor_CASE.py',),('resident_cohort_operator_CASE.py','collect'),('close_resident_cohort_CLOSE.py',),('restore_resident_cohort_RESTORE.py',)]
for step in steps:
 print('Normal two-winner qualification: '+' '.join(step),flush=True)
 result=subprocess.run([sys.executable,'-X','utf8','-B',str(R/'.local'/step[0]),*step[1:]],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('CASE',str(a.case)).replace('CLOSE',str(a.case+4)).replace('RESTORE',str(a.case+5))
 dest=ROOT/f'.local/run_four_next_normal_{a.case}.py';assert not dest.exists();dest.write_text(runner,newline='\n');print('Fresh normal protocol prepared; observer POST/frame sequence precedes the collector lease; no console operation.')
if __name__=='__main__':main()
