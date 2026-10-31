#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh normal-parent fixture cases; no console access."""
import argparse,ast,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--case',type=int,required=True);p.add_argument('--kind',choices=['two-token','gate-up'],required=True)
 p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_checkpoint_fixture_case.py'),'--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,'--fixture-kind','gdn-conv-norm'],check=True,cwd=ROOT)
 s=(ROOT/'.local/prepared_phase_model_17000.private.py').read_text();s=re.sub(r'(?<![0-9])170\d{2}(?![0-9])',lambda m:str(int(m[0])-17000+a.case),s)
 s=s.replace('Strata-winners-SELF-16908',a.package_name).replace('Strata-winners-16900',a.build_name).replace('maximum_generation_requests=3','maximum_generation_requests=0')
 anchor="policy['native_strata_followup_normal']=actual_native['strata_followup_normal']['scope']";assert s.count(anchor)==1;s=s.replace(anchor,anchor+";policy['native_GDN_conv_normalization_fixture']=actual_native['GDN_conv_normalization_fixture']['scope']")
 ast.parse(s);(ROOT/f'.local/prepared_phase_model_{a.case}.private.py').write_text(s,newline='\n')
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';s=path.read_text()
 if a.kind=='two-token':
  s=s.replace("report['GPU_graphs']==144 and len(report['cases'])==4","report['GPU_graphs']==216 and len(report['cases'])==6").replace('(ordinal<3)','(ordinal<5)').replace('if ordinal<3 else','if ordinal<5 else').replace('GPU_graphs=144','GPU_graphs=216')
 else:
  s=s.replace('ps5-qwen-GDN-conv-normalization-fixture-result-v1','ps5-qwen-gate-up-fixture-result-v1').replace("report['GPU_graphs']==144 and len(report['cases'])==4 and report['F64_reference_all_outputs_passed']","report['GPU_graphs']==108 and len(report['cases'])==3 and report['all_F64_outputs_passed']").replace("report['additional_shader_verified']==1 and report['additional_shader_modules']>0","report['additional_shader_verified']==1")
  left=s.index('    for ordinal,row in enumerate(report[\'cases\']):');right=s.index('    pid=state',left)
  s=s[:left]+'''    for ordinal,row in enumerate(report['cases']):
        assert row['all_F64_outputs_passed'] and row['canary_passed'] and row['positive_retirement']
        assert (row['candidate_pipeline_selections']>0 if ordinal<2 else row['candidate_pipeline_selections']==0)
        assert len(row['arms'])==4 and all(len(arm['backend_samples_us'])==len(arm['whole_samples_us'])==8 for arm in row['arms'])
'''+s[right:]
  s=s.replace('GDN_conv_normalization_fixture_complete_waiting_for_ordinary_close','Gate_Up_fixture_complete_waiting_for_ordinary_close').replace('GPU_graphs=144','GPU_graphs=108')
 ast.parse(s);path.write_text(s,newline='\n')
 runner='''from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[1]
steps=[('prepared_phase_model_CASE.private.py',)]+[('resident_cohort_operator_CASE.py',a)for a in('stage','publish','launch','collect')]+[('close_resident_cohort_CLOSE.py',),('restore_resident_cohort_RESTORE.py',)]
for step in steps:
 print('Native fixture: '+' '.join(step),flush=True)
 result=subprocess.run([sys.executable,'-X','utf8','-B',str(R/'.local'/step[0]),*step[1:]],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('CASE',str(a.case)).replace('CLOSE',str(a.case+4)).replace('RESTORE',str(a.case+5))
 dest=ROOT/f'.local/run_four_next_fixture_{a.case}.py';assert not dest.exists();dest.write_text(runner,newline='\n')
 print('Fresh finite normal-parent fixture prepared; no console operations.')
if __name__=='__main__':main()
