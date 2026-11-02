#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently reconcile a completed finite online MTP causal history."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from mtp_shadow_host_check import require_online_profile
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','reference-case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=load(a.case/'result.private.json');plan=load(a.case/'case/plan.private.json')
    package=load(plan['package']['path']);profile=load(package['effective_application_policy']['profile']['path']);require_online_profile(profile)
    for key in ('terminal','audit','closure'):need(record(result[key]['path'])==result[key],'Completed online MTP evidence changed')
    terminal=load(result['terminal']['path']);audit=load(result['audit']['path']);closed=load(result['closure']['path'])
    need(result['completed'] and result['kind']=='S1-persistent-MTP-online' and terminal['audit']==audit and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['ordinary_OS_closes']==1 and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'],
         'Positive original/auxiliary retirement, ordinary exit and exact current restoration required')
    need(audit['completed'] and audit['causal_and_capture_checks_passed'] and audit['auxiliary_contexts_positively_retired'] and
         audit['maximum_simultaneous_auxiliary_contexts']==audit['auxiliary_KV_clear_count']==1 and
         audit['only_original_target_verified_tokens_emitted'] and audit['run_id']==plan['run_id'] and
         audit['candidate_SELF_sha256']==plan['SELF']['sha256'],'Exact bounded native persistent MTP completion required')
    reference_path=a.reference_case/'passive-observer/native.private.bin';reference=load(reference_path)
    request=terminal['requests'][0];baseline=reference['requests'][0]
    need(request['counting_quality_passed'] and request['full_F32_finite'] and request['request_reset_completed'] and
         request['token_ids']==baseline['token_ids'] and request['output_bytes']==baseline['output_bytes'],
         'All original target greedy tokens and output bytes must match the independent reference')
    capture_proof=load(profile['native_target_capture_proof']['path']);capture=load(capture_proof['native_audit']['path'])
    need(record(capture_proof['native_audit']['path'])==capture_proof['native_audit'],'Qualified prompt capture changed')
    pending=request['token_ids'][0];position=request['metrics']['prompt_tokens'];hidden=capture['observations'][0]['last_hidden_sha256']
    auxiliary=audit['auxiliary_causal_inputs'];index=0;accepted=rejected=proposals=catchups=bonus=0;awaiting_bonus=False;fallback_processes=0
    emitted=[]
    for row in audit['observations']:
        emitted.append(row['returned_token'])
        if row['kind']=='bonus':
            need(awaiting_bonus and row['target_process_added'] is False,'Exactly one original queued bonus must follow acceptance')
            pending=row['returned_token'];awaiting_bonus=False;bonus+=1;continue
        need(not awaiting_bonus and row['pending_token']==pending and row['position']==position and row['input_hidden_sha256']==hidden,
             'Every proposal must consume the actual pending token/position/live hidden row once')
        need(index<len(auxiliary) and auxiliary[index]==dict(catchup=False,token=pending,position=position,hidden_sha256=hidden),
             'The actual auxiliary proposal input must match the independent causal state')
        index+=1;proposals+=1
        if row['kind']=='verification' and row['accepted']:
            need(row['used_draft']==row['returned_token'] and row['capture_serial_delta']==1 and row['last_process_width']==2,
                 'An accepted draft requires both original completed target rows')
            need(index<len(auxiliary) and auxiliary[index]==dict(catchup=True,token=row['used_draft'],position=position+1,
                 hidden_sha256=row['target_first_hidden_sha256']),'The accepted draft must enter auxiliary KV with target row0')
            index+=1;catchups+=1;accepted+=1;position+=2;hidden=row['target_last_hidden_sha256'];awaiting_bonus=True
        else:
            if row['kind']=='verification':
                rejected+=1
                need((row['capture_serial_delta']==1 and row['last_process_width']==2) or
                     (row['capture_serial_delta']==2 and row['last_process_width']==1),'A rejected target step requires its actual original completion')
                fallback_processes+=int(row['capture_serial_delta']==2);hidden=row['target_first_hidden_sha256']
            else:
                need(row['kind']=='ordinary' and row['capture_serial_delta']==1 and row['last_process_width']==1,
                     'A declined draft must use one original ordinary target process')
                hidden=row['target_last_hidden_sha256']
            pending=row['returned_token'];position+=1
    need(not awaiting_bonus and index==len(auxiliary) and emitted==request['token_ids'][1:len(emitted)+1],
         'All emitted decisions and auxiliary inputs must reconcile without duplicate consumption')
    need(accepted==audit['target_accepted']==catchups==audit['accepted_draft_catchups'] and
         rejected==audit['target_rejected'] and accepted+rejected==audit['target_attempts']<=6 and
         proposals==audit['auxiliary_proposals'] and bonus==audit['actual_queued_bonus_samples']==accepted,
         'Independently counted accepted/rejected/proposal/catch-up/bonus counters differ')
    if profile['overrides']['native_headless_model_audit']['force_one_wrong_draft']:
        need(audit['forced_wrong_draft_used'] and accepted>0 and rejected>0,'The first finite scope must exercise actual acceptance and rejection')
    actual_processes=request['completed_performance']['delta']['process_calls']
    need(actual_processes==baseline['completed_performance']['delta']['process_calls']-accepted+fallback_processes,
         'Only actual accepted bonuses may reduce the original target process count')
    pattern=re.compile(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})')
    stages=a.case/'case/native-stages.private.log';reference_stages=a.reference_case/'native-stages.private.log'
    observed=[row[1:] for row in pattern.findall(stages.read_bytes()) if row[0]==b'1']
    expected=[row[1:] for row in pattern.findall(reference_stages.read_bytes()) if row[0]==b'1']
    need(len(observed)==len(expected)==23 and all(row[1]==b'248320' for row in observed),'All23 existing full-vocabulary target rows required')
    differences=[ordinal+1 for ordinal,(left,right) in enumerate(zip(observed,expected)) if left!=right]
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'result.private.json',dict(completed=True,case=record(a.case/'result.private.json'),native_audit=result['audit'],closure=result['closure'],
        reference=record(reference_path),stages=record(stages),reference_stages=record(reference_stages),
        target_attempts=accepted+rejected,accepted=accepted,rejected=rejected,actual_auxiliary_catchups=catchups,
        auxiliary_proposals=proposals,queued_bonus_samples=bonus,all_actual_causal_inputs_independently_reconciled=True,
        full_target_tokens_and_output_bytes_exact=True,all23_full_vocab_rows_finite=True,unlike_width_byte_different_rows=differences,
        actual_target_process_calls=actual_processes,CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],device_peak_bytes=terminal['device_ledger_peak_bytes'],
        diagnostic_hashing_and_stages_enabled=True,matched_whole_performance_qualified=False,broader_quality_qualified=False,
        production_adopted=False,native_owners=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,accepted=accepted,rejected=rejected,catchups=catchups,all_causal_inputs_exact=True,output_exact=True,whole_speed_qualified=False)))


if __name__=='__main__':main()
