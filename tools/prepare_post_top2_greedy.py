#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare the finite, first-index GPU argmax fixture with early close staging."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True)
    for k in ('build-name','package-name'):p.add_argument('--'+k,required=True)
    a=p.parse_args();assert a.case>=33400 and a.case%100==0
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_post_top2_fixture.py'),
        '--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name],check=True,cwd=ROOT)
    path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';s=path.read_text()
    s=once(s,'paths=[Path(__file__),base_path,',"paths=[Path(__file__),base_path,ROOT/'tools/post_top2_close.py',")
    s=once(s,"'ps5-qwen-gate-up-fixture-result-v1'","'ps5-qwen-finite-greedy-fixture-result-v1'")
    s=once(s,"report['GPU_graphs']==180 and len(report['cases'])==5 and report['all_F64_outputs_passed']",
        "report['GPU_graphs']==110 and len(report['cases'])==11 and report['all_integer_outputs_and_finite_status_exact'] and report['all_canaries_passed'] and report['synthetic_inputs_only'] and not report['learned_host_inference']")
    s=once(s,"report['additional_shader_verified']==1","report['additional_shaders_verified']==2")
    left=s.index("    for ordinal,row in enumerate(report['cases']):");right=s.index("    pid=state['observed_native_pid'];stages=",left)
    s=s[:left]+'''    for ordinal,row in enumerate(report['cases']):
        assert row['scenario']==ordinal and row['positive_retirement']
        assert row['complete_reference_and_tie_order_exact'] and row['input_and_output_canaries_exact']
        assert row['invalid_input']==(ordinal>=8) and row['CPU_control_includes_full_F32_readback']
        assert row['GPU_live_readback_bytes']==row['rows']*4
        assert len(row['arms'])==4 and all(len(arm['samples_us'])==4 for arm in row['arms'])
        assert [arm['GPU_selection']for arm in row['arms']]==[False,True,True,False]
'''+s[right:]
    s=once(s,'Gate_Up_fixture_complete_waiting_for_ordinary_close','finite_greedy_fixture_completed_waiting_for_ordinary_close')
    s=once(s,'GPU_graphs=180,full_state_F64_passed=True','GPU_graphs=110,finite_first_index_and_canaries_exact=True')
    ast.parse(s);path.write_text(s,newline='\n')
    path=ROOT/f'.local/run_post_top2_fixture_{a.case}.py';s=path.read_text()
    s=once(s,"for a in('stage','publish','launch','collect')]+", "for a in('stage','publish','launch')]+[('../../tools/post_top2_close.py','prepare','--case','"+str(a.case)+"'),('resident_cohort_operator_"+str(a.case)+".py','collect')]+")
    # The inherited runner resolves each script below .local. Use a relative
    # .local/../tools path, without changing the immutable console operators.
    s=s.replace('../../tools/post_top2_close.py','../tools/post_top2_close.py')
    s=once(s,"('close_resident_cohort_"+str(a.case+4)+".py',)","('../tools/post_top2_close.py','finish','--case','"+str(a.case)+"')")
    ast.parse(s);path.write_text(s,newline='\n')
    print('Finite GPU greedy fixture prepared: eleven cases,110 graphs,early guarded close; no console operations.')

if __name__=='__main__':main()
