#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile every ordered service/kernel native comparison and selected normal."""
import argparse,json,statistics
from pathlib import Path
from analyze_next_five import analyze
from analyze_load_followup import cpu_rows
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def analyze_all(cache,normal_case=None):
 w=load(ROOT/'docs/service-kernel-worklog-20261101.json');require(all(w['stages'][str(i)]['completed']for i in range(1,6)),'All five explicit native dispositions required');stages=[]
 for i in range(1,6):
  declared=w['stages'][str(i)];case=cache/f"hardware-first-generation-{declared['case']}";r=load(case/'native-model-terminal.private.json');closed=load(case/'restored-complete.private.json');ledger=load(case/'token-ledger-readback-complete.private.json');speed=analyze(case)
  require(closed['completed']and not closed['unknown_completion']and ledger['completed']and ledger['all_records_ids_bytes_order_exact']and all(x['full_F32_finite']for x in r['requests']),'Every declared native comparison must close positively and read back complete actual ledgers')
  require(speed['same_counting_output'],'Fixed counting output must pass');
  if declared['status'].startswith(('selected','adopted')):require(speed['all_fixed_semantic_tasks_passed'],'Selected factors must pass every fixed semantic task')
  if i<=3:require(all(x['maximum_absolute_logit_error']==0 and x['same_tokens_as_independent']for x in r['requests']),'CPU-only factors must preserve every full target F32 row/token')
  else:require(all(r['requests'][j]['candidate_independent_full_F32_and_routes_exact']for j in(6,7)),'Independent GPU candidate target rows/routes must be exact')
  groups={}
  for name,ids in(('control',(3,9)),('candidate',(5,7))):
   rows=[r['requests'][j]for j in ids];groups[name]=dict(whole_ms=statistics.mean(x['metrics']['total_ms']for x in rows),decode_tok_s=statistics.mean(x['metrics']['decode_tokens_per_second']for x in rows),persistence_inclusive_ms=statistics.mean(x['CPU_nested_calls_inclusive_exclusive_ns'][28]/1e6 for x in rows),stage_exclusive_ms=statistics.mean(x['CPU_nested_calls_inclusive_exclusive_ns'][11]/1e6 for x in rows))
  stages.append(dict(id=i,case=declared['case'],status=declared['status'],completed=True,groups=groups,speed=speed,maximum_cross_control_F32_error=max(x['maximum_absolute_logit_error']for x in r['requests']),GPU_choices_final=r['requests'][-1].get('service_GPU_totals'),completion_final=r['requests'][-1].get('service_completion_totals'),positive_ledger_readback=ledger['ledgers'],evidence=[{k:v for k,v in record(p).items()if k!='path'}for p in(case/'native-model-terminal.private.json',case/'restored-complete.private.json',case/'token-ledger-readback-complete.private.json')]))
 result=dict(schema='ps5-qwen-service-kernel-results-v1',all_five_native_stages_completed=True,completed=normal_case is not None,production_changed=False,selected_service_mode=w['selected_service_mode'],stages=stages,CI_runs=0,reboots=0,learned_host_inference=False)
 if normal_case is not None:
  case=cache/f'hardware-first-generation-{normal_case}';n=load(case/'native-model-terminal.private.json');require(n['completed']and n['device_ledger_live_bytes']==0 and n['all_model_source_device_owners_positively_retired']and load(case/'restored-complete.private.json')['completed']and load(case/'token-ledger-readback-complete.private.json')['ledgers']==3,'Actual complete normal and ledger readback required');result['normal']=dict(case=normal_case,CPU=cpu_rows(n['requests']),quality=[r['counting_quality_passed']for r in n['requests']],rates=[r['metrics']['decode_tokens_per_second']for r in n['requests']],service_modes=[r['service_mode']for r in n['requests']],CPU_peak=n['CPU_heap_peak_bytes'],device_peak=n['device_ledger_peak_bytes'])
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--normal-case',type=int);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=analyze_all(a.cache,a.normal_case);write_json(a.out,r);print(json.dumps(dict(all_five_native_stages_completed=True,normal_completed='normal'in r,selected_service_mode=r['selected_service_mode'],stages=[(s['id'],s['status'],s['speed']['retained_decode_gain_percent'])for s in r['stages']])))
if __name__=='__main__':main()
