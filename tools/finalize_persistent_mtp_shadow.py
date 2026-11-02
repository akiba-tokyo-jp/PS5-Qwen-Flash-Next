#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify completed causal MTP replay without claiming online speed or adoption."""
import argparse
import json
import math
from pathlib import Path
import re
import statistics

from build_performance_quantizer import record
from mtp_shadow_host_check import require_profile
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','reference-case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=load(a.case/'result.private.json');plan=load(a.case/'case/plan.private.json')
    package=load(plan['package']['path']);profile=load(package['effective_application_policy']['profile']['path']);require_profile(profile)
    for key in ('terminal','audit','closure'):need(record(result[key]['path'])==result[key],'A completed replay receipt changed')
    terminal=load(result['terminal']['path']);audit=load(result['audit']['path']);closed=load(result['closure']['path'])
    need(result['completed'] and result['kind']=='S1-MTP-shadow' and result['native_requests']==1 and
         result['native_owners']==0 and not result['unknown_completion'] and terminal['audit']==audit and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['ordinary_OS_closes']==1 and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'],
         'Exact finite target/replay completion, positive retirement and ordinary restoration required')
    need(audit['completed'] and audit['run_id']==plan['run_id']==terminal['run_id'] and
         audit['candidate_SELF_sha256']==plan['SELF']['sha256']==terminal['candidate_SELF_sha256'] and
         audit['pid']==terminal['pid'] and audit['maximum_simultaneous_auxiliary_contexts']==1 and
         audit['auxiliary_contexts_created']==2 and audit['auxiliary_contexts_positively_retired'] and
         audit['actual_causal_inputs_replayed_after_target_completion'] and audit['target_tokens_selected_by_auxiliary']==0 and
         not audit['online_scheduling_qualified'] and not audit['whole_model_speed_qualified'],
         'Completed sequential replay must remain separate from online target verification')
    n=audit['proposals'];need(0<n<=24 and audit['KV_clear_counts']==[n+1,1] and len(audit['observations'])==2*n,'Exact bounded replay and clear counts required')
    arms=[[row for row in audit['observations'] if row['arm']==arm] for arm in (0,1)]
    keys=('position','pending_token','target_token','target_end')
    need(all(len(rows)==n for rows in arms) and [[tuple(row[k] for k in keys) for row in rows] for rows in arms][0]==
         [tuple(row[k] for k in keys) for row in arms[1]],'Both arms must consume the same actual target causal frames')
    need(all(math.isfinite(row[k]) and row[k]>=0 for row in audit['observations'] for k in
         ('clear_us','compute_fence_us','complete_proposal_us')),'All component costs must be finite')
    matches=[sum(row['prediction']==row['target_token'] for row in rows) for rows in arms]
    need(matches==audit['target_prediction_matches'],'Independently counted target matches differ')
    pattern=re.compile(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})')
    stages=a.case/'case/native-stages.private.log';ref_stages=a.reference_case/'native-stages.private.log'
    observed=[row[1:] for row in pattern.findall(stages.read_bytes()) if row[0]==b'1']
    expected=[row[1:] for row in pattern.findall(ref_stages.read_bytes()) if row[0]==b'1']
    need(len(observed)==23 and observed==expected and all(row[1]==b'248320' for row in observed),
         'All23 existing full-vocabulary F32 rows must match the selected reference byte-for-byte')
    routes=a.case/'case/headless-observer/native.arm0.routes.private.json'
    ref_routes=a.reference_case/'native-arm0.routes.private.bin'
    route=load(routes);reference=load(ref_routes)
    need(route['complete'] and not route['capture_failed'] and route['records']==reference['records'],
         'Actual complete target routing must remain exact')
    request=terminal['requests'][0]
    need(request['counting_quality_passed'] and request['full_F32_finite'] and request['request_reset_completed'],
         'Original target quality, finite values and reset must complete')
    summaries=[]
    for arm,rows in enumerate(arms):
        warm=rows[2:]
        summaries.append(dict(arm=arm,target_matches=matches[arm],proposals=n,
            compute_fence_sum_us=sum(row['compute_fence_us'] for row in rows),
            complete_proposal_sum_us=sum(row['complete_proposal_us'] for row in rows),
            after_first_two_compute_fence_mean_us=statistics.mean(row['compute_fence_us'] for row in warm),
            after_first_two_complete_proposal_mean_us=statistics.mean(row['complete_proposal_us'] for row in warm)))
    a.out.mkdir(parents=True,exist_ok=False)
    report=dict(completed=True,case=record(a.case/'result.private.json'),native_audit=result['audit'],closure=result['closure'],
        stages=record(stages),reference_stages=record(ref_stages),routes=record(routes),reference_routes=record(ref_routes),
        first_auxiliary_arm=audit['first_auxiliary_arm'],proposals=n,arms=summaries,
        all23_full_F32_rows_248320_columns_byte_exact=True,all_actual_target_routes_exact=True,
        both_auxiliary_causal_histories_native_qualified=True,CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],
        device_ledger_peak_bytes=terminal['device_ledger_peak_bytes'],
        actual_accepted_draft_catchup_or_rejection_exercised=False,online_target_verification_qualified=False,
        component_timings_order_and_cache_confounded=True,whole_model_speed_qualified=False,production_adopted=False,
        native_owners=0,initializer_requests=0,automatic_retries=0)
    save(a.out/'result.private.json',report)
    print(json.dumps(dict(completed=True,proposals=n,target_matches=matches,F32_rows_exact=23,routes_exact=True,whole_speed_qualified=False)))


if __name__=='__main__':main()
