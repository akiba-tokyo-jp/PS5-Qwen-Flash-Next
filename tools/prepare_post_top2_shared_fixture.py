#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare the three-format first-layer fixture with early ordinary-close staging."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True)
 for k in('build-name','package-name'):p.add_argument('--'+k,required=True)
 a=p.parse_args();subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_post_top2_fixture.py'),'--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name],check=True)
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';s=path.read_text();s=once(s,'paths=[Path(__file__),base_path,',"paths=[Path(__file__),base_path,ROOT/'tools/post_top2_close.py',")
 s=once(s,"'ps5-qwen-gate-up-fixture-result-v1'","'ps5-qwen-shared-basis-fixture-result-v1'")
 left=s.index("    for ordinal,row in enumerate(report['cases']):");right=s.index("    pid=state['observed_native_pid'];stages=",left)
 s=s[:left]+'''    for ordinal,row in enumerate(report['cases']):
        assert row['scenario']==ordinal and row['positive_retirement'] and row['complete_F64_and_canaries_passed']
        assert row['tokens']==[1,2,1,2,30][ordinal] and row['selected']==(6 if ordinal==4 else 2)
        assert [a['arm']for a in row['arms']]==[0,1,2,2,1,0]
        assert all(len(a['backend_samples_us'])==len(a['whole_samples_us'])==5 for a in row['arms'])
        assert all(v<=5e-4 for v in row['maximum_NMSE'])
'''+s[right:]
 s=s.replace('Gate_Up_fixture_complete_waiting_for_ordinary_close','shared_basis_fixture_complete_waiting_for_ordinary_close');ast.parse(s);path.write_text(s,newline='\n')
 path=ROOT/f'.local/run_post_top2_fixture_{a.case}.py';s=path.read_text();s=once(s,"for a in('stage','publish','launch','collect')]+","for a in('stage','publish','launch')]+[('../tools/post_top2_close.py','prepare','--case','"+str(a.case)+"'),('resident_cohort_operator_"+str(a.case)+".py','collect')]+")
 s=once(s,"('close_resident_cohort_"+str(a.case+4)+".py',)","('../tools/post_top2_close.py','finish','--case','"+str(a.case)+"')");ast.parse(s);path.write_text(s,newline='\n')
 print('Three-format shared-basis numerical fixture prepared; no console operation.')
if __name__=='__main__':main()
