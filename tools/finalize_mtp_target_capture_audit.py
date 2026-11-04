#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify real target acceptance/rejection hidden retention after ordinary exit."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from mtp_shadow_host_check import require_target_capture_profile
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','reference-case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=load(a.case/'result.private.json');plan=load(a.case/'case/plan.private.json')
    package=load(plan['package']['path']);profile=load(package['effective_application_policy']['profile']['path']);require_target_capture_profile(profile)
    for key in ('terminal','audit','closure'):need(record(result[key]['path'])==result[key],'Completed target capture evidence changed')
    terminal=load(result['terminal']['path']);audit=load(result['audit']['path']);closed=load(result['closure']['path'])
    reference_path=a.reference_case/'passive-observer/native.private.bin';reference=load(reference_path)
    need(result['completed'] and result['kind']=='S1-target-hidden-capture-audit' and terminal['audit']==audit and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['ordinary_OS_closes']==1 and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'],
         'Positive target/source/device retirement and ordinary current restoration required')
    need(audit['completed'] and audit['capture_and_decision_checks_passed'] and audit['actual_target_attempts']==2 and
         audit['actual_target_accepted']==audit['actual_target_rejected']==1 and audit['auxiliary_contexts']==audit['MTP_proposals_used']==0 and
         audit['original_target_process_calls_added_by_capture']==0 and audit['hidden_elements']==10240 and
         audit['run_id']==plan['run_id'] and audit['candidate_SELF_sha256']==plan['SELF']['sha256'],
         'The two actual target decisions and original completion capture must be exact')
    rows=audit['observations'];need(len(rows)==23 and all(row['call']==index and row['capture_valid'] and row['decision_check_passed']
        and all(re.fullmatch('[0-9a-f]{64}',row[key]) for key in ('first_hidden_sha256','last_hidden_sha256')) for index,row in enumerate(rows)),
        'All23 completed target decisions must retain valid full hidden-row hashes')
    need(rows[1]['pair'] and rows[1]['controlled_draft']==11 and rows[1]['capture_serial_delta']==1 and rows[1]['last_process_width']==2 and
         rows[2]['capture_serial_delta']==0 and rows[2]['queued_bonus_samples']==1 and
         rows[3]['pair'] and rows[3]['controlled_draft']==42 and rows[3]['target_rejected']==1 and
         rows[3]['capture_serial_delta']==1 and rows[3]['last_process_width']==2,
         'Actual accepted bonus and compact rejection must preserve their original two-row completion')
    current=terminal['requests'][0];baseline=reference['requests'][0]
    need(current['counting_quality_passed'] and current['full_F32_finite'] and current['request_reset_completed'] and
         current['token_ids']==baseline['token_ids'] and current['output_bytes']==baseline['output_bytes'],
         'All original greedy target tokens and output bytes must match the independent reference')
    pattern=re.compile(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})')
    stages=a.case/'case/native-stages.private.log';reference_stages=a.reference_case/'native-stages.private.log'
    actual=[row[1:] for row in pattern.findall(stages.read_bytes()) if row[0]==b'1']
    expected=[row[1:] for row in pattern.findall(reference_stages.read_bytes()) if row[0]==b'1']
    need(len(actual)==len(expected)==23 and all(row[1]==b'248320' for row in actual),'All23 existing full-vocabulary rows must be observed')
    differences=[index+1 for index,(left,right) in enumerate(zip(actual,expected)) if left!=right]
    need(current['completed_performance']['delta']['process_calls']==22,'One accepted bonus must reduce original target process count by one')
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'result.private.json',dict(completed=True,case=record(a.case/'result.private.json'),native_audit=result['audit'],closure=result['closure'],
        reference=record(reference_path),stages=record(stages),reference_stages=record(reference_stages),
        target_attempts=2,accepted=1,rejected=1,queued_bonus_without_new_process=True,compact_rejection_first_hidden_retained=True,
        full_target_tokens_and_output_bytes_exact=True,all23_full_vocab_rows_finite=True,byte_different_rows=differences,
        unlike_width_F32_bit_equality_qualified=not differences,actual_target_process_calls=22,
        CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],device_peak_bytes=terminal['device_ledger_peak_bytes'],
        native_auxiliary_catchup_exercised=False,online_MTP_proposal_quality_or_speed_qualified=False,production_adopted=False,
        native_owners=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,accepted=1,rejected=1,output_exact=True,full_F32_finite_rows=23,byte_different_rows=len(differences),native_owners=0)))


if __name__=='__main__':main()
