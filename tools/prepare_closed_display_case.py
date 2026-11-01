#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the qualified native owner, ordinary close and exact restoration for CPU cleanup."""
import argparse,ast,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
COLLECT=r'''def collect():
    plan=base.load(CASE/'prepared-launch.private.json');remote=plan['management_admission_report'];deadline=time.monotonic()+600
    while True:
        try:raw=base.lan.web('/fs'+remote,4<<20,8);report=json.loads(raw);break
        except base.lan.urllib.error.HTTPError as e:assert e.code==404
        for path in(remote+'.failure',remote+'.fatal',journal_remote(base.current()['observed_native_pid']).removesuffix('.stages')+'.fatal'):
            try:
                failed=base.lan.web('/fs'+path,1<<20,8);(CASE/'native-CPU-maintenance-failure.private.json').write_bytes(failed);raise RuntimeError('Known CPU maintenance refusal; do not repeat the app launch')
            except base.lan.urllib.error.HTTPError as e:assert e.code==404
        assert time.monotonic()<deadline,'Finite CPU maintenance deadline; do not repeat';time.sleep(2)
    (CASE/'native-model-terminal.private.json').write_bytes(raw);binding=base.load(CASE/'case-inputs.private.json')['binding'];state=base.current()
    assert report['schema']=='ps5-qwen-closed-display-CPU-result-v1'and report['pid']==state['observed_native_pid']and report['run_id']==binding['run_id']and report['candidate_SELF_sha256']==binding['candidate_SELF_sha256']
    assert report['requests']==[]and not report['model_loaded']and not report['model_sources_started']and report['HTTP_requests']==report['VideoOut_starts']==0
    assert report['GPU_initializations']==report['GPU_calls']==report['driver_allocation_attempts']==0 and report['scratch_positively_freed']and report['permission_or_flag_changes']==0
    assert report['all_model_source_device_owners_positively_retired']and report['all_owners_positively_retired']and report['device_ledger_live_bytes']==0
    pid=state['observed_native_pid'];stages=base.lan.web('/fs'+journal_remote(pid),8<<20,8);(CASE/'current-startup-for-owner.private.txt').write_bytes(stages);assert b'closed_display_CPU_maintenance_complete_waiting_for_ordinary_close'in stages
    base.save(CASE/'CPU-terminal-owner-basis.private.json',dict(live_owner_start_and_AppInfo_must_be_admitted_by_normal_close=True,expected_PID=pid,owner_start_and_AppInfo_observation_deferred_to_qualified_normal_close=True))
    base.save(CASE/'CPU-calibration-analysis.private.json',dict(completed=True,model_requests_completed=0,GPU_initializations=0,all_resources_positively_retired=True,ordinary_OS_close_authorized=True,unknown_completion=False,native_terminal=base.record(CASE/'native-model-terminal.private.json'),CPU_maintenance_completed=report['completed']))
    print(json.dumps(dict(CPU_maintenance_completed=report['completed'],verified=report['verified_archives'],removed=report['removed_displays'],GPU_initializations=0,scratch_positively_freed=True)),flush=True)

'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True)
 for k in('build-name','package-name','publication'):p.add_argument('--'+k,required=True)
 a=p.parse_args();subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_service_case.py'),'--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,'--publication',a.publication],check=True)
 path=ROOT/f'.local/prepared_phase_model_{a.case}.private.py';s=path.read_text();marker="policy['native_next_five']=actual_native['next_five_comparison']['scope']";s=once(s,marker,marker+"\n    policy['native_closed_display_CPU']=actual_native['closed_display_CPU_app']['scope']");ast.parse(s);path.write_text(s,newline='\n')
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';s=path.read_text();tree=ast.parse(s);f=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='collect');lines=s.splitlines(keepends=True);s=''.join(lines[:f.lineno-1])+COLLECT+''.join(lines[f.end_lineno:]);ast.parse(s);path.write_text(s,newline='\n')
 print('Owner-context CPU maintenance prepared with ordinary close and exact production restoration; no console operation.')
if __name__=='__main__':main()
