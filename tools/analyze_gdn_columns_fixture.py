#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile completed GDN-only evidence without treating it as model speed."""
import argparse,hashlib,json,math
from pathlib import Path

def need(value,message):
    if not value:raise ValueError(message)

def record(path):
    return dict(label=path.name,bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();terminal=a.case/'native-model-terminal.private.json'
    restored=a.case/'restored-complete.private.json'
    t=json.loads(terminal.read_text());r=json.loads(restored.read_text())
    need(t['schema']=='ps5-qwen-GDN-columns-fixture-result-v1' and t['completed'],
         'A complete GDN fixture terminal is required')
    need(t['model_loads']==0 and not t['model_loaded'] and t['requests']==[],
         'This result must not be confused with a full-model measurement')
    need(t['all_model_source_device_owners_positively_retired'] and t['device_ledger_live_bytes']==0,
         'All fixture resources must retire positively')
    need(r['completed'] and r['CPU_title_normally_closed'] and not r['unknown_completion'],
         'Ordinary close and exact restoration must complete')
    need(t['GPU_graphs']==288 and len(t['cases'])==8,'All declared graphs and cases required')
    rows=[];identities=set()
    for case in t['cases']:
        key=tuple(case[k] for k in ('heads','query_heads','tokens','sequences','snapshots','vector_gate'))
        need(key not in identities,'Duplicate shape cannot replace a missing case');identities.add(key)
        need(case['S_v']==128 and case['F64_reference_all_outputs_passed'] and
             case['snapshot_unwritten_slots_preserved'] and case['canary_passed'] and
             case['positive_buffer_context_backend_retirement'] and case['GPU_graphs']==36 and
             case['candidate_pipeline_selections']>0,'Complete numerical, execution and retirement proofs required')
        need(math.isfinite(case['maximum_absolute_error']) and 0<=case['maximum_absolute_error']<=1e-6,
             'The predeclared F64 absolute error bound must pass')
        arms=case['arms'];need([x['candidate'] for x in arms]==[False,True,True,False],'Exact ABBA order required')
        for arm in arms:
            times=arm['samples_us'];need(len(times)==8 and all(math.isfinite(x) and x>0 for x in times),
                                       'Eight finite positive synchronized samples per group required')
            need(abs(sum(times)/8-arm['mean_us'])<=1e-6,'Raw samples must reconcile with the native mean')
        forward=100*(1-arms[1]['mean_us']/arms[0]['mean_us'])
        reverse=100*(1-arms[2]['mean_us']/arms[3]['mean_us'])
        rows.append(dict(shape=dict(zip(('heads','query_heads','tokens','sequences','snapshots','vector_gate'),key)),
                         forward_reduction_percent=forward,reverse_reduction_percent=reverse,
                         both_orders_at_least_two_percent=min(forward,reverse)>=2,
                         maximum_absolute_error=case['maximum_absolute_error'],
                         control_mean_us=(arms[0]['mean_us']+arms[3]['mean_us'])/2,
                         candidate_mean_us=(arms[1]['mean_us']+arms[2]['mean_us'])/2))
    expected={(48,16,t,1,k,False) for t in (1,32) for k in (1,2)}|{
              (4,2,t,2,k,True) for t in (1,32) for k in (1,2)}
    need(identities==expected,'The exact predeclared scalar/vector and snapshot shapes must complete')
    nominated=all(row['both_orders_at_least_two_percent'] for row in rows if not row['shape']['vector_gate'])
    report=dict(schema='ps5-qwen-GDN-columns-analysis-v1',completed=True,
                case=int(a.case.name.rsplit('-',1)[1]),GPU_graphs=288,rows=rows,
                all_F64_outputs_canaries_and_unwritten_slots_passed=True,
                scalar_unconditional_specialization_nominated_for_full_model=nominated,
                full_model_speed_measured=False,production_adopted=False,
                normal_API_display_qualification_triggered=False,
                original_driver_memory_reserves_and_completion_guards_preserved=True,
                positively_retired_ordinary_close_and_exact_restoration=True,
                evidence=[record(terminal),record(restored)],CI_runs=0)
    need(not a.out.exists(),'Preserve previous analyses')
    a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(report))

if __name__=='__main__':main()
