#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a fresh fourteen-request experiment and its positive close protocol."""
import argparse,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);a=p.parse_args()
    if a.case<20000 or a.case%100:raise ValueError('Fresh hundred-aligned case required')
    names=['prepared_phase_model_17600.private.py','resident_cohort_operator_17600.py','first_operator_17600_base.py','close_resident_cohort_17604.py','restore_resident_cohort_17605.py','build_resident_owner_17603.py','collect_Q2_monitor_17600.py']
    def shift(s):return re.sub(r'(?<![0-9A-Za-z])176\d{2}(?![0-9A-Za-z])',lambda m:str(int(m[0])-17600+a.case),s)
    for name in names:
        dest=ROOT/'.local'/shift(name);assert not dest.exists();s=shift((ROOT/'.local'/name).read_text())
        s=s.replace('Four-next-rollback-ranked-SELF-17628',a.package_name).replace('Four-next-rollback-ranked-17620',a.build_name)
        # The initial shift also changes numeric suffixes inside build names.
        s=s.replace('Four-next-rollback-ranked-SELF-'+str(a.case+28),a.package_name).replace('Four-next-rollback-ranked-'+str(a.case+20),a.build_name)
        s=s.replace('tools/build_preservation_integrity.py','tools/build_next_five_integrity.py')
        if name.startswith('prepared_'):
            needle="policy['native_GDN_model_comparison']=actual_native['GDN_model_comparison']['scope']";assert s.count(needle)==1;s=s.replace(needle,needle+";policy['native_next_five']=actual_native['next_five_comparison']['scope']")
            s=s.replace('ordinary original/fused A-B-B-A cold-retained pairs','installed control/candidate A-B-B-A cold-retained pairs')
        if name.startswith('resident_'):
            left=s.index('        assert all(not r[\'prefix\'][\'enabled\']');right=s.index('\n        selected=',left)
            s=s[:left]+'''        assert all(not r['prefix']['enabled'] and r['speculation']['accepted']+r['speculation']['rejected']==r['speculation']['attempts'] and r['compact_rollback']['enabled'] for r in report['requests'])
        assert all(r['maximum_absolute_logit_error']==0 and r['same_tokens_as_independent'] for r in report['requests'] if r['candidate_arm']==0)
        assert report['requests'][-1]['compact_rollback']['all_memory_rollbacks']==sum(r['speculation']['rejected']for r in report['requests'])
        assert report['requests'][-1]['compact_rollback']['complete_captures_elided']==sum(r['speculation']['attempts']for r in report['requests'])
'''+s[right:]
        ast.parse(s);dest.write_text(s,newline='\n')
    runner='''from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[1]
steps=[('prepared_phase_model_CASE.private.py',)]+[('resident_cohort_operator_CASE.py',a)for a in('stage','publish','launch','collect')]+[('close_resident_cohort_CLOSE.py',),('restore_resident_cohort_RESTORE.py',)]
for step in steps:
 print('Next-five native comparison: '+' '.join(step),flush=True)
 result=subprocess.run([sys.executable,'-X','utf8','-B',str(R/'.local'/step[0]),*step[1:]],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('CASE',str(a.case)).replace('CLOSE',str(a.case+4)).replace('RESTORE',str(a.case+5))
    dest=ROOT/f'.local/run_next_five_{a.case}.py';assert not dest.exists();dest.write_text(runner,newline='\n');print('Fresh native comparison scripts prepared; no console operation.')

if __name__=='__main__':main()
