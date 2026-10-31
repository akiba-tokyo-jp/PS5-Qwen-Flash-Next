#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a matched cohort with its close helper staged before measurement."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=int,required=True)
    for k in ('build-name','package-name'):p.add_argument('--'+k,required=True)
    p.add_argument('--publication',type=Path,required=True);a=p.parse_args()
    if a.case<31500:raise ValueError('Fresh current-comparison case required')
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_next_five_Q4_case.py'),
        '--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,'--publication',str(a.publication)],check=True,cwd=ROOT)
    path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';source=path.read_text()
    source=once(source,'paths=[Path(__file__),base_path,',"paths=[Path(__file__),base_path,ROOT/'tools/post_top2_close.py',")
    ast.parse(source);path.write_text(source,newline='\n')
    runner='''from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[1]
steps=[('.local/prepared_phase_model_CASE.private.py',)]+[('.local/resident_cohort_operator_CASE.py',a)for a in('stage','publish','launch')]+[
 ('tools/post_top2_close.py','prepare','--case','CASE'),('.local/resident_cohort_operator_CASE.py','collect'),
 ('tools/post_top2_close.py','finish','--case','CASE'),('.local/restore_resident_cohort_RESTORE.py',)]
for step in steps:
 print('Post-Top2 cohort: '+' '.join(step),flush=True)
 result=subprocess.run([sys.executable,'-X','utf8','-B',str(R/step[0]),*step[1:]],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('CASE',str(a.case)).replace('RESTORE',str(a.case+5))
    path=ROOT/f'.local/run_post_top2_comparison_{a.case}.py'
    if path.exists():raise FileExistsError(path)
    ast.parse(runner);path.write_text(runner,newline='\n')
    print('Matched cohort and pre-staged-close protocol prepared; zero console operations.')

if __name__=='__main__':main()
