#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve an actual returned fixture terminal for guarded ordinary close only."""
import argparse,importlib.util,json
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);a=p.parse_args();spec=importlib.util.spec_from_file_location('case_operator',ROOT/f'.local/resident_cohort_operator_{a.case}.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o);b=o.base;case=o.CASE
 with b.writer_lease(o.C/'model-data-continuation.writer.lock'):
  o.frozen();state=b.current();require(state['native_running'],'Original fixture owner must still be current');plan=b.load(case/'prepared-launch.private.json');raw=b.lan.web('/fs'+plan['management_admission_report']+'.failure',1<<20,8);report=json.loads(raw)
  require(report.get('message')and not report.get('CPU_worker_completion_unknown',False),'An actual returned non-worker-unknown terminal required');require((case/'checkpoint.failure.private.json').read_bytes()==raw,'Previously captured failure must remain exact')
  pid=state['observed_native_pid'];require(any(x['pid']==pid and x['name']=='eboot.bin'for x in b.processes()),'Same native process required');stages=b.lan.web('/fs'+o.journal_remote(pid),8<<20,8)
  (case/'native-model-terminal.private.json').write_bytes(raw);(case/'current-startup-for-owner.private.txt').write_bytes(stages)
  write_json(case/'CPU-terminal-owner-basis.private.json',dict(live_owner_start_and_AppInfo_must_be_admitted_by_normal_close=True,expected_PID=pid,owner_start_and_AppInfo_observation_deferred_to_qualified_normal_close=True))
  write_json(case/'CPU-calibration-analysis.private.json',dict(completed=True,all_declared_comparisons_completed=False,native_fixture_completed=False,
   model_requests_completed=0,GPU_initializations=int(bool(report.get('native_resources_started'))),all_resources_positively_retired=False,
   ordinary_OS_close_authorized=True,unknown_completion=True,uncertain_resources_retained_for_ordinary_OS_close=True,native_terminal=record(case/'native-model-terminal.private.json')))
  print(json.dumps(dict(returned_fixture_failure=report['message'],ordinary_close_only=True,new_GPU_calls=0,automatic_retry=False)))
if __name__=='__main__':main()
