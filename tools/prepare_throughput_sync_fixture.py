#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the ordinary launch/close protocol for the zero-model barrier oracle."""
import argparse,ast,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COLLECT=r'''def collect():
    plan=base.load(CASE/'prepared-launch.private.json');remote=plan['management_admission_report'];deadline=time.monotonic()+600;next_print=0
    while True:
        try:raw=base.lan.web('/fs'+remote,4<<20,8);report=json.loads(raw);break
        except base.lan.urllib.error.HTTPError as e:assert e.code==404
        for path in(remote+'.failure',remote+'.fatal',journal_remote(base.current()['observed_native_pid']).removesuffix('.stages')+'.fatal'):
            try:
                failed=base.lan.web('/fs'+path,1<<20,8);(CASE/'native-fixture-failure.private.json').write_bytes(failed)
                raise RuntimeError('Known native fixture refusal; no repeated launch; use its fresh completion evidence for ordinary close')
            except base.lan.urllib.error.HTTPError as e:assert e.code==404
        pid=base.current()['observed_native_pid'];progress=base.lan.web('/fs'+journal_remote(pid),8<<20,8)
        if time.monotonic()>=next_print:
            lines=progress.decode(errors='replace').splitlines();print(json.dumps(dict(sync_fixture_pending=True,last_stage=lines[-1]if lines else'pending')),flush=True);next_print=time.monotonic()+30
        assert time.monotonic()<deadline,'Finite synthetic fixture deadline; no repeat or forced close';time.sleep(2)
    (CASE/'native-model-terminal.private.json').write_bytes(raw);binding=base.load(CASE/'case-inputs.private.json')['binding'];state=base.current()
    assert report['schema']=='ps5-qwen-throughput-sync-fixture-result-v2'and report['completed']
    assert report['pid']==state['observed_native_pid']and report['run_id']==binding['run_id']and report['candidate_SELF_sha256']==binding['candidate_SELF_sha256']
    assert report['requests']==[]and not report['model_loaded']and report['HTTP_requests']==report['VideoOut_starts']==0
    assert report['device_ledger_live_bytes']==0 and report['all_model_source_device_owners_positively_retired']and report['all_owners_positively_retired']
    assert report['GPU_graphs']==60 and report['all_F32_bytes_and_canaries_exact']and len(report['cases'])==4
    for i,row in enumerate(report['cases']):
        assert row['scenario']==i and row['positive_retirement']and row['independent_prior_write_retained']
        assert len(row['arms'])==4
        for j,arm in enumerate(row['arms']):
            assert len(arm['samples_us'])==3 and arm['complete_F32_bytes_and_canaries_exact']and(bool(arm['execution_only_barriers'])==(j in(1,2)))
            if i==3:assert row['separate_producer_consumer_graphs']and bool(arm['pending_write_tail_flushes'])==(j in(1,2))
    pid=state['observed_native_pid'];stages=base.lan.web('/fs'+journal_remote(pid),8<<20,8);(CASE/'current-startup-for-owner.private.txt').write_bytes(stages)
    assert b'synchronization_fixture_complete_waiting_for_ordinary_close'in stages
    base.save(CASE/'CPU-terminal-owner-basis.private.json',dict(live_owner_start_and_AppInfo_must_be_admitted_by_normal_close=True,expected_PID=pid,owner_start_and_AppInfo_observation_deferred_to_qualified_normal_close=True))
    base.save(CASE/'CPU-calibration-analysis.private.json',dict(completed=True,model_requests_completed=0,GPU_initializations=1,all_resources_positively_retired=True,ordinary_OS_close_authorized=True,unknown_completion=False,native_terminal=base.record(CASE/'native-model-terminal.private.json')))
    print(json.dumps(dict(synthetic_sync_fixture_completed=True,GPU_graphs=60,all_F32_bytes_and_canaries_exact=True,device_live_bytes=0,unknown_completion=False)),flush=True)

'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True)
 for k in('build-name','package-name','publication'):p.add_argument('--'+k,required=True)
 a=p.parse_args();subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/prepare_service_case.py'),'--case',str(a.case),'--build-name',a.build_name,'--package-name',a.package_name,'--publication',a.publication],check=True)
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';s=path.read_text();tree=ast.parse(s);function=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='collect');lines=s.splitlines(keepends=True);s=''.join(lines[:function.lineno-1])+COLLECT+''.join(lines[function.end_lineno:]);ast.parse(s);path.write_text(s,newline='\n')
 print('Synthetic barrier oracle prepared with the unchanged ordinary close and restoration protocol; no console operation.')
if __name__=='__main__':main()
