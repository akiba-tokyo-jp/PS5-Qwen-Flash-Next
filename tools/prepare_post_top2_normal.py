#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep the normal API/display proof and pre-stage its exact close helper."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=int,required=True)
    for k in ('build-name','package-name'):p.add_argument('--'+k,required=True)
    for k in ('native','publication'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert a.case>=32400 and a.case%100==0
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_next_five_normal.py'),
        '--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,
        '--native',str(a.native),'--publication',str(a.publication)],check=True,cwd=ROOT)
    path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';s=path.read_text()
    s=once(s,'paths=[Path(__file__),base_path,',"paths=[Path(__file__),base_path,ROOT/'tools/post_top2_close.py',")
    ast.parse(s);path.write_text(s,newline='\n')
    runner='''from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[1]
steps=[('.local/prepared_phase_model_CASE.private.py',)]+[('.local/resident_cohort_operator_CASE.py',a)for a in('stage','publish','launch')]+[
 ('tools/post_top2_close.py','prepare','--case','CASE'),('.local/collect_Q2_monitor_CASE.py',),
 ('.local/resident_cohort_operator_CASE.py','collect'),('tools/post_top2_close.py','finish','--case','CASE'),
 ('.local/restore_resident_cohort_RESTORE.py',)]
for step in steps:
 print('Post-Top2 normal proof: '+' '.join(step),flush=True)
 r=subprocess.run([sys.executable,'-X','utf8','-B',str(R/step[0]),*step[1:]],cwd=R)
 if r.returncode:raise SystemExit(r.returncode)
'''.replace('CASE',str(a.case)).replace('RESTORE',str(a.case+5))
    path=ROOT/f'.local/run_post_top2_normal_{a.case}.py';assert not path.exists()
    ast.parse(runner);path.write_text(runner,newline='\n')
    print('Normal API/display/retirement with early close staging prepared; zero console operations.')
if __name__=='__main__':main()
