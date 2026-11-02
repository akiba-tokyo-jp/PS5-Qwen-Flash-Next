#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify finite retained MTP ownership against an independent fresh-context control."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from mtp_shadow_host_check import require_online_profile
from start_success_route import load,need,save


def completed_case(root,retained):
    result=load(root/'result.private.json');plan=load(root/'case/plan.private.json');package=load(plan['package']['path'])
    profile=load(package['effective_application_policy']['profile']['path']);require_online_profile(profile)
    for key in ('terminal','audit','closure'):need(record(result[key]['path'])==result[key],'A completed native owner proof changed')
    terminal=load(result['terminal']['path']);audit=load(result['audit']['path']);closed=load(result['closure']['path'])
    scope=profile['overrides']['native_headless_model_audit']
    need(result['completed'] and terminal['completed'] and terminal['audit']==audit and audit['completed'] and
        terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
        closed['ordinary_OS_closes']==1 and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
        not closed['unknown_completion'] and scope['three_ordinary_requests'] and scope['requests']==3 and
        scope['retain_auxiliary_between_requests']==audit['retained_auxiliary']==retained and
        len(terminal['requests'])==len(audit['requests'])==3 and audit['three_ordinary_requests'] and not audit['exact_prefix_scope'] and
        audit['run_id']==plan['run_id'] and audit['candidate_SELF_sha256']==plan['SELF']['sha256'] and
        audit['all_auxiliary_owners_positively_retired'] and audit['auxiliary_context_creations']==(1 if retained else 3) and audit['auxiliary_KV_clears']==3,
        'The exact ordinary three-request scope must retire all owners and restore current files')
    for ordinal,row in enumerate(audit['requests']):
        need(row['completed'] and row['causal_and_capture_checks_passed'] and row['auxiliary_KV_clear_count']==1 and
            row['maximum_simultaneous_auxiliary_contexts']==1 and row['auxiliary_contexts_positively_retired']==(not retained) and
            row['lifetime_auxiliary_context_creations']==1 and row['request_ordinal']==(ordinal if retained else 0) and
            row['lifetime_auxiliary_KV_clears']==(ordinal+1 if retained else 1),'Actual per-request owner/clear counts differ')
    if retained:
        final=audit['final_auxiliary'];need(final['auxiliary_contexts_positively_retired'] and final['lifetime_auxiliary_context_creations']==1 and
            final['lifetime_auxiliary_KV_clears']==3,'Final retained auxiliary owner must retire before original model cleanup')
    return result,terminal,audit,scope


def reconcile(audit,request,anchor,baseline_processes):
    pending=request['token_ids'][0];position=request['metrics']['prompt_tokens'];hidden=anchor
    inputs=audit['auxiliary_causal_inputs'];index=0;accepted=rejected=proposals=catchups=bonuses=fallback=0;awaiting=False;emitted=[]
    for row in audit['observations']:
        emitted.append(row['returned_token'])
        if row['kind']=='bonus':
            need(awaiting and row['target_process_added'] is False,'Only one actual original queued bonus follows acceptance')
            pending=row['returned_token'];awaiting=False;bonuses+=1;continue
        need(not awaiting and row['pending_token']==pending and row['position']==position and row['input_hidden_sha256']==hidden,
            'Every proposal must follow the actual completed target state')
        need(index<len(inputs) and inputs[index]==dict(catchup=False,token=pending,position=position,hidden_sha256=hidden),'Actual proposal input differs')
        index+=1;proposals+=1
        if row['kind']=='verification' and row['accepted']:
            need(row['used_draft']==row['returned_token'] and row['capture_serial_delta']==1 and row['last_process_width']==2,'An accepted draft requires both original completed target rows')
            need(index<len(inputs) and inputs[index]==dict(catchup=True,token=row['used_draft'],position=position+1,hidden_sha256=row['target_first_hidden_sha256']),
                'Accepted draft must enter auxiliary KV with its saved first target row')
            index+=1;catchups+=1;accepted+=1;position+=2;hidden=row['target_last_hidden_sha256'];awaiting=True
        else:
            if row['kind']=='verification':
                rejected+=1;need((row['capture_serial_delta']==1 and row['last_process_width']==2) or
                    (row['capture_serial_delta']==2 and row['last_process_width']==1),'A rejected draft requires actual completed original processing')
                fallback+=int(row['capture_serial_delta']==2);hidden=row['target_first_hidden_sha256']
            else:
                need(row['kind']=='ordinary' and row['capture_serial_delta']==1 and row['last_process_width']==1,'A declined proposal requires one original process')
                hidden=row['target_last_hidden_sha256']
            pending=row['returned_token'];position+=1
    need(not awaiting and index==len(inputs) and emitted==request['token_ids'][1:len(emitted)+1] and
        accepted==audit['target_accepted']==catchups==audit['accepted_draft_catchups'] and rejected==audit['target_rejected'] and
        accepted+rejected==audit['target_attempts']<=6 and proposals==audit['auxiliary_proposals'] and bonuses==audit['actual_queued_bonus_samples']==accepted,
        'Actual causal inputs, emitted tokens and all independent decision counters must reconcile')
    need(request['completed_performance']['delta']['process_calls']==baseline_processes-accepted+fallback,'Only accepted original bonuses may reduce target calls')
    return dict(accepted=accepted,rejected=rejected,auxiliary_inputs=index,queued_bonuses=bonuses)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','fresh-control','ordinary-reference','capture-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();candidate,terminal,audit,scope=completed_case(a.case,True);control,base,baseline,control_scope=completed_case(a.fresh_control,False)
    left=dict(scope);right=dict(control_scope);left.pop('retain_auxiliary_between_requests');right.pop('retain_auxiliary_between_requests')
    need(left==right,'Only explicit auxiliary lifetime may differ from the independently completed fresh control')
    original=load(a.ordinary_reference/'passive-observer/native.private.bin')['requests'][0]
    proof=load(a.capture_proof);need(proof['completed'] and proof['accepted']==proof['rejected']==1 and
        record(proof['native_audit']['path'])==proof['native_audit'],'Independent qualified cold prompt capture required')
    anchor=load(proof['native_audit']['path'])['observations'][0]['last_hidden_sha256'];rows=[]
    for ordinal,(observed,expected,observed_audit,expected_audit) in enumerate(zip(terminal['requests'],base['requests'],audit['requests'],baseline['requests'])):
        need(observed['counting_quality_passed'] and expected['counting_quality_passed'] and observed['full_F32_finite'] and expected['full_F32_finite'] and
            observed['request_reset_completed'] and expected['request_reset_completed'] and
            observed['token_ids']==expected['token_ids']==original['token_ids'] and observed['output_bytes']==expected['output_bytes']==original['output_bytes'],
            'All ordinary target tokens, bytes, finite checks and resets must match')
        if ordinal:anchor=expected_audit['observations'][0]['input_hidden_sha256']
        reference=reconcile(expected_audit,expected,anchor,original['completed_performance']['delta']['process_calls'])
        actual=reconcile(observed_audit,observed,anchor,original['completed_performance']['delta']['process_calls'])
        need(actual==reference and observed_audit['observations']==expected_audit['observations'] and
            observed_audit['auxiliary_causal_inputs']==expected_audit['auxiliary_causal_inputs'],'All actual causal values must match the independent fresh control')
        for suffix in ('.routes.private.json','.result.private.bin'):
            if suffix.startswith('.routes'):
                x=load(a.case/('case/headless-observer/native.arm'+str(ordinal)+suffix));y=load(a.fresh_control/('case/headless-observer/native.arm'+str(ordinal)+suffix))
                for key in ('pid','run_id'):x.pop(key,None);y.pop(key,None)
                need(x==y,'Complete ordered target routes must match the fresh control')
        rows.append(actual)
    pattern=re.compile(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})')
    stages=a.case/'case/native-stages.private.log';reference_stages=a.fresh_control/'case/native-stages.private.log'
    values=pattern.findall(stages.read_bytes());expected=pattern.findall(reference_stages.read_bytes())
    need(len(values)==69 and values==expected and all(row[2]==b'248320' for row in values),'All69 full-vocabulary F32 rows must match the same-width control')
    a.out.mkdir(parents=True,exist_ok=False);save(a.out/'result.private.json',dict(completed=True,case=record(a.case/'result.private.json'),
        fresh_control=record(a.fresh_control/'result.private.json'),cold_capture_proof=record(a.capture_proof),ordinary_reference=record(a.ordinary_reference/'passive-observer/native.private.bin'),
        requests=rows,actual_target_tokens_bytes_causal_inputs_routes_and_all69_F32_rows_exact=True,auxiliary_context_creations=[3,1],
        KV_clear_counts=[3,3],final_retirement_in_complete_sequence_span=True,positive_original_and_auxiliary_retirement=True,
        matched_ABBA_whole_speed_qualified=False,exact_prefix_qualified=False,broader_answer_quality_qualified=False,production_adopted=False,
        diagnostic_hashing_and_stages_enabled=True,PS5_operations=0))
    print(json.dumps(dict(completed=True,all69_F32_rows_and_actual_causal_inputs_exact=True,auxiliary_context_creations=[3,1],whole_speed_qualified=False)))


if __name__=='__main__':main()
