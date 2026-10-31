#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a fresh selected-model fixture and positive ordinary-close protocol."""
import argparse,ast,json,re
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=int,required=True)
    p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True)
    a=p.parse_args()
    if a.case<=30300 or a.case%100:raise ValueError('Fresh hundred-aligned case required')
    def shift(s):return re.sub(r'(?<![0-9A-Za-z])302\d{2}(?![0-9A-Za-z])',lambda m:str(int(m[0])-30200+a.case),s)
    names=['prepared_phase_model_30200.private.py','resident_cohort_operator_30200.py','first_operator_30200_base.py',
           'close_resident_cohort_30204.py','restore_resident_cohort_30205.py','build_resident_owner_30203.py',
           'collect_Q2_monitor_30200.py']
    for name in names:
        path=ROOT/'.local'/shift(name)
        if path.exists():raise FileExistsError(path)
        text=shift((ROOT/'.local'/name).read_text())
        text=text.replace('Next-five-normal-display-SELF-30128',a.package_name).replace('Next-five-normal-display-30120',a.build_name)
        if name.startswith('prepared_'):
            marker="policy['native_next_five_normal']=actual_native['next_five_normal']['scope']"
            text=once(text,marker,marker+";policy['native_GDN_conv_normalization_fixture']=actual_native['GDN_conv_normalization_fixture']['scope']")
            # The current prepared source deliberately creates its own fresh CPU
            # observer; only the case namespace changes, not any current guard.
            text=text.replace('maximum_generation_requests=3','maximum_generation_requests=0')
        if name.startswith('resident_'):
            donor=(ROOT/'.local/resident_cohort_operator_17800.py').read_text()
            start=donor.index('def collect():\n');end=donor.index('\ndef main():',start)
            collector=donor[start:end]
            collector=collector.replace("report['GPU_graphs']==108 and len(report['cases'])==3", "report['GPU_graphs']==180 and len(report['cases'])==5")
            collector=collector.replace('if ordinal<2 else','if row[\'tokens\']<=2 else').replace('GPU_graphs=108','GPU_graphs=180')
            start=text.index('def collect():\n');end=text.index('\ndef main():',start)
            text=text[:start]+collector+text[end:]
        ast.parse(text);path.write_text(text,newline='\n')
    runner='''from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[1]
steps=[('prepared_phase_model_CASE.private.py',)]+[('resident_cohort_operator_CASE.py',a)for a in('stage','publish','launch','collect')]+[('close_resident_cohort_CLOSE.py',),('restore_resident_cohort_RESTORE.py',)]
for step in steps:
 print('Post-Top2 bounded fixture: '+' '.join(step),flush=True)
 result=subprocess.run([sys.executable,'-X','utf8','-B',str(R/'.local'/step[0]),*step[1:]],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('CASE',str(a.case)).replace('CLOSE',str(a.case+4)).replace('RESTORE',str(a.case+5))
    path=ROOT/f'.local/run_post_top2_fixture_{a.case}.py'
    if path.exists():raise FileExistsError(path)
    path.write_text(runner,newline='\n')
    print('Fresh selected-parent fixture prepared; zero console operations.')

if __name__=='__main__':main()
