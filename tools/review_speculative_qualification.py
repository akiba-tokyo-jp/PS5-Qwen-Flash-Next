#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review retired numerical/behavior evidence; never execute or admit console work."""
import argparse
import json
import math
from pathlib import Path
from resident_route_review import token_streams
from review_resident_results import capture,load

NAMES=('ja-arithmetic','ja-summary','en-explanation','en-contrast','arithmetic-sequence','code-python','structured-json','repeated-context')
REJECTION_POSITIONS={1:1,2:2,3:3,5:4}

def require(value,message):
    if not value:raise ValueError(message)

def integer(value):return type(value)is int and value>=0

def probe_summary(probe):
    require(probe.get('schema')=='ps5-qwen-same-batch-probe-v1'and probe.get('enabled')is True and
        probe.get('observations')==3 and probe.get('readback_window_bytes')==65536 and
        probe.get('class_layout_changed')is False and probe.get('speed_measurement')is False,'Complete diagnostic-only same-width scope required')
    states=probe.get('ordinary_reference_repeat_candidate_states');rows=probe.get('ordinary_repeat_and_candidate_rows')
    require(type(states)is list and len(states)==3 and type(rows)is list and len(rows)==4,'Both reference executions and candidate evidence required')
    keys=('metadata_SHA256','active_tensor_SHA256','tensor_geometry_SHA256','metadata_bytes','active_tensor_bytes','tensor_sections','minimum_position','maximum_position')
    for state in states:
        require(all(type(state.get(k))is str and len(state[k])==64 and set(state[k])<=set('0123456789abcdef')for k in keys[:3]),'Complete state digests required')
        require(all(integer(state.get(k))for k in keys[3:])and 0<state['metadata_bytes']<=1<<20 and
            0<state['active_tensor_bytes']<=136<<20 and state['active_tensor_bytes']%4==0 and
            0<state['tensor_sections']<=512 and integer(state.get('bounded_readback_calls'))and state['bounded_readback_calls']>0,
            'Complete bounded active original F32 state required')
    same=all(all(state[k]==states[0][k]for k in keys)for state in states[1:])
    within=True
    for row in rows:
        require(row.get('columns')==248320 and row.get('all_finite')is True,'All original vocabulary columns must be finite')
        require(integer(row.get('outside_original_tolerance')),'Typed original-tolerance count required')
        for key in('maximum_absolute_error','RMS_error','p50_absolute_error','p95_absolute_error','p99_absolute_error','mean_centered_RMS_error','KL_reference_to_candidate'):
            require(type(row.get(key))in(int,float)and math.isfinite(row[key])and row[key]>=0,'Finite diagnostic statistics required')
        within=within and row['outside_original_tolerance']==0
    passed=(same and within and probe.get('same_width_logits_within_original_tolerance')is True and
        probe.get('ordinary_repeat_active_state_bit_exact')is True and probe.get('candidate_active_state_bit_exact')is True and
        probe.get('draft_actually_accepted')is True and probe.get('bonus_logits_pinned')is True and
        probe.get('committed_position')==states[-1]['maximum_position']+1)
    return dict(passed=bool(passed),same_width_full_F32_rows=4,maximum_same_width_F32_error=max(row['maximum_absolute_error']for row in rows),
        all_active_state_and_metadata_bit_exact=same,active_state_bytes=states[0]['active_tensor_bytes'],tensor_sections=states[0]['tensor_sections'],
        no_general_quality_or_speed_verdict_from_single_maximum=True)

def retired_case(cache,number):
    case=cache/f'hardware-first-generation-{number}';report=load(case/'native-model-terminal.private.json')
    restored=load(case/'restored-complete.private.json');binding=load(case/'case-inputs.private.json')['binding']
    analysis=load(case/'CPU-calibration-analysis.private.json');close=load(case/'ordinary-close/complete.private.json')
    require(restored.get('completed')is True and restored.get('CPU_title_normally_closed')is True and
        restored.get('full_native_readback_SHA256_identity_EOF_verified')is True and restored.get('exact_prior_configuration_restored')is True and
        restored.get('model_loaded')is False and restored.get('unknown_completion')is False and
        report.get('completed')is True and report.get('run_id')==binding['run_id']and
        report.get('candidate_SELF_sha256')==binding['candidate_SELF_sha256']and report.get('model_receipt_sha256')==binding['model_receipt_sha256']and
        report.get('all_model_source_device_owners_positively_retired')is True and report.get('device_ledger_live_bytes')==0 and
        analysis.get('all_resources_positively_retired')is True and analysis.get('unknown_completion')is False and
        close.get('normal_OS_close_accepted')is True and close.get('native_eboot_count')==0,
        'Full bound retirement, normal close, exact production/settings restore and idle required')
    return case,report

def route_geometry(route,row):
    streams=token_streams(route)
    require(route.get('sidecar_written_after_model_and_source_retirement')is True and route.get('pid')==row['pid']and
        route.get('run_id')==row['run_id']and route.get('ordinal')==row['ordinal'],'Every route sidecar needs its closed request identity')
    for record in route['records']:
        require(all(len(set(record['ids'][i:i+10]))==10 for i in range(0,len(record['ids']),10)),'Original Experts must be distinct per token/layer')
    widths=[route['records'][i]['tokens']for i in range(0,len(route['records']),48)]
    prompt=row['prompt_tokens'];prefill=[min(4,prompt-i)for i in range(0,prompt,4)]
    require(widths[:len(prefill)]==prefill and all(w in(1,2)for w in widths[len(prefill):]),'Original prefill and bounded decode geometry required')
    stats=row['speculation']
    require(all(integer(stats.get(k))for k in('attempts','accepted','rejected','queued_bonus_samples'))and
        stats['attempts']==stats['accepted']+stats['rejected']and stats['accepted']-stats['queued_bonus_samples']in(0,1),
        'Complete accepted/rejected/bonus accounting required')
    require(widths[len(prefill):].count(2)==stats['attempts'],'Every actual two-token process must be accounted')
    expected=prompt+len(row['token_ids'])-(row['stop_reason']=='output_token_limit')+2*stats['rejected']+stats['accepted']-stats['queued_bonus_samples']
    require(all(len(stream)==expected for stream in streams)and row['completed_performance']['delta']['process_calls']==len(widths),
        'All processed tokens and original layer/call counts must agree')
    return dict(process_calls=len(widths),processed_tokens_per_layer=expected,two_token_calls=stats['attempts'],all_original_layers_and_Experts_observed=True)

def behavior_summary(report):
    rows=report.get('requests')
    require(type(rows)is list and 20<=len(rows)<=28 and report.get('all_eight_native_inputs_executed')is True and
        report.get('speed_measurement')is False,'Complete finite eight-input non-timing cohort required')
    groups={i:[]for i in range(8)}
    for ordinal,row in enumerate(rows):
        require(row.get('ordinal')==ordinal and type(row.get('group'))is int and row['group']in groups and
            row.get('name')==NAMES[row['group']]and row.get('arm')in('ordinary','causal','accepted-coverage','forced-rejection')and
            row.get('request_reset_completed')is True and row.get('native_renderer_and_token_IDs_exact')is True and row.get('speed_measurement')is False,
            'Every closed request needs the frozen input identity and original reset')
        require(row.get('stop_reason')in('end_of_generation','output_token_limit')and type(row.get('token_ids'))is list and
            0<len(row['token_ids'])<=32 and all(integer(x)and x<248320 for x in row['token_ids'])and
            row.get('full_F32_rows_observed')==len(row['token_ids'])+(row['stop_reason']=='end_of_generation'),
            'Every emitted position and complete-vocabulary callback required')
        require(integer(row.get('prompt_tokens'))and 0<row['prompt_tokens']<=64,'Original prompt scope required')
        require(row.get('known_control_draft_used')is(row['arm']=='accepted-coverage'),'Diagnostic known-control drafts must be explicit')
        groups[row['group']].append(row)
    exact=True;accepted=causal=coverage=rejected=0;forced_exact=True;per_input=[]
    for group,items in groups.items():
        roles={kind:[r for r in items if r['arm']==kind]for kind in('ordinary','causal','accepted-coverage','forced-rejection')}
        require(len(roles['ordinary'])==len(roles['causal'])==1 and len(roles['accepted-coverage'])<=1 and
            len(roles['forced-rejection'])==int(group in REJECTION_POSITIONS),'All planned per-input comparisons required')
        control=roles['ordinary'][0];adaptive=roles['causal'][0]
        require(len(roles['accepted-coverage'])==int(adaptive['speculation']['accepted']==0),'Known-control coverage is conditional on absent causal acceptance')
        input_exact=True
        for row in items:
            actual=(row['token_ids']==control['token_ids']and row['output_bytes']==control['output_bytes']and row['stop_reason']==control['stop_reason'])
            if row['stop_reason']=='end_of_generation':actual=actual and row['ending_memory_minimum']==control['ending_memory_minimum']and row['ending_memory_maximum']==control['ending_memory_maximum']
            require(row['token_IDs_and_bytes_match_control']is bool(actual),'Native and host generated-behavior decisions differ')
            input_exact=input_exact and actual
            if row['arm']!='ordinary':
                accepted+=row['speculation']['accepted'];causal+=row['speculation']['accepted']if row['arm']=='causal'else 0
                coverage+=row['speculation']['accepted']if row['arm']=='accepted-coverage'else 0
            else:require(row['speculation']['attempts']==0,'An ordinary control must not speculate')
        if roles['forced-rejection']:
            row=roles['forced-rejection'][0];s=row['speculation'];rejected+=s['rejected']
            forced_exact=(forced_exact and row['forced_position']==REJECTION_POSITIONS[group]and s['attempts']==s['rejected']==1 and not s['accepted']and
                row['full_F32_rows_observed']==row['reference_rows']and row['maximum_absolute_logit_error']==0 and row['forced_rejection_F32_restore_passed']is True)
        if roles['accepted-coverage']:
            row=roles['accepted-coverage'][0];s=row['speculation']
            input_exact=input_exact and s['attempts']==s['accepted']==s['queued_bonus_samples']==1 and not s['rejected']and row['accepted_coverage_passed']is True
        exact=exact and input_exact
        per_input.append(dict(name=NAMES[group],requests=len(items),generated_tokens=len(control['token_ids']),all_behavior_checks_passed=bool(input_exact),
            causal_accepted=adaptive['speculation']['accepted'],diagnostic_known_control_accepted=sum(r['speculation']['accepted']for r in roles['accepted-coverage'])))
    require(report['actual_accepted_batches']==accepted and report['causal_accepted_batches']==causal and
        report['diagnostic_known_control_accepted_batches']==coverage and report['actual_forced_rejections']==rejected,'Aggregate path accounting differs')
    passed=(exact and forced_exact and accepted>=8 and rejected==4 and report.get('accepted_path_coverage_complete')is True and
        report.get('all_original_tokens_and_bytes_exact')is True and report.get('forced_rejection_and_full_F32_restore_passed')is True)
    return dict(passed=bool(passed),eight_inputs_completed=True,requests_completed=len(rows),all_generated_behavior_equal=bool(exact),
        actual_accepted_batches=accepted,causal_accepted_batches=causal,diagnostic_known_control_accepted_batches=coverage,
        actual_forced_rejections=rejected,forced_rejection_full_F32_exact=bool(forced_exact),inputs=per_input,
        known_control_drafts_do_not_establish_causal_speed=True,speed_qualified=False)

def distribution_summary(sidecar,row,reference_request=None):
    """Validate every stored full-row diagnostic without inventing a max cutoff."""
    require(sidecar.get('full_vocabulary')==248320 and sidecar.get('timing_qualification')is False and
        type(sidecar.get('rows'))is list,'Original full-vocabulary diagnostic sidecar required')
    rows=sidecar['rows']
    if reference_request is None:reference_request=row['arm']=='ordinary'
    if reference_request:
        require(not rows,'The ordinary request records the reference, not self-comparisons')
        return dict(rows_compared=0,reference_request=True)
    require(len(rows)==row['full_F32_rows_observed'],'Every observed output/EOG row requires a diagnostic record')
    complete=True;maximum=outside=worst_KL=0;top1_equal=0
    fields=('maximum_absolute_error','RMS_error','p50_absolute_error','p95_absolute_error','p99_absolute_error',
        'mean_centered_RMS_error','KL_reference_to_candidate','reference_top1_margin','candidate_top1_margin')
    for diagnostic in rows:
        require(type(diagnostic.get('reference_available'))is bool and type(diagnostic.get('same_committed_history'))is bool,
            'Comparison availability and exact causal history must be explicit')
        if not diagnostic['reference_available']:
            complete=False
            continue
        require(diagnostic.get('columns')==248320 and diagnostic.get('all_finite')is True and
            integer(diagnostic.get('outside_original_tolerance'))and diagnostic['outside_original_tolerance']<=248320,
            'Every compared row must contain all finite vocabulary columns')
        require(all(type(diagnostic.get(k))in(int,float)and math.isfinite(diagnostic[k])and diagnostic[k]>=0 for k in fields)and
            type(diagnostic.get('mean_shift'))in(int,float)and math.isfinite(diagnostic['mean_shift']),
            'Finite full-row distribution and margin diagnostics required')
        require(diagnostic['p50_absolute_error']<=diagnostic['p95_absolute_error']<=diagnostic['p99_absolute_error']<=
            diagnostic['maximum_absolute_error']+1e-6,'Absolute error percentiles must be ordered')
        for key in('reference_top5','candidate_top5'):
            require(type(diagnostic.get(key))is list and len(diagnostic[key])==5 and len(set(diagnostic[key]))==5 and
                all(integer(x)and x<248320 for x in diagnostic[key]),'Complete distinct top-five IDs required')
        complete=complete and diagnostic['same_committed_history']
        maximum=max(maximum,diagnostic['maximum_absolute_error']);outside+=diagnostic['outside_original_tolerance']
        worst_KL=max(worst_KL,diagnostic['KL_reference_to_candidate'])
        top1_equal+=diagnostic['reference_top5'][0]==diagnostic['candidate_top5'][0]
    require(maximum==row['maximum_absolute_logit_error']and outside==row['outside_original_tolerance'],
        'Full-row and request-level numerical totals must agree')
    return dict(rows_compared=len(rows),all_references_and_histories_available=bool(complete),
        full_vocabulary_columns=248320,top1_equal_rows=top1_equal,maximum_absolute_error=maximum,
        maximum_row_KL_reference_to_candidate=worst_KL,maximum_alone_is_not_a_quality_verdict=True)

def speed_summary(report,ordinary):
    rows=report.get('requests')
    require(type(rows)is list and len(rows)==5 and [r.get('arm')for r in rows]==['warmup','ordinary','causal','causal','ordinary']and
        report.get('matched_ABBA_request_ordinals')==[1,2,3,4]and report.get('active_cache_slots')==128 and
        report.get('six_demand_enabled')is True and report.get('timing_Expert_cache_start')=='empty'and
        report.get('known_control_drafts_used')is False and report.get('causal_policy_maximum_actual_attempts')==1,
        'One unchanged finite 128-slot causal ABBA with explicit cache ownership required')
    behavior=True;coverage=True;payload=None
    for ordinal,row in enumerate(rows):
        require(row.get('ordinal')==ordinal and row.get('request_reset_completed')is True and row.get('native_renderer_and_token_IDs_exact')is True and
            row.get('speed_measurement')is bool(ordinal)and row.get('known_control_draft_used')is False and
            row.get('actual_single_attempt_policy')is True and row.get('F32_reference_role')=='causal_warmup_diagnostic_only',
            'Each arm needs its positive reset, native tokens, causal policy and timing role')
        actual=(row['token_ids']==ordinary['token_ids']and row['output_bytes']==ordinary['output_bytes']and row['stop_reason']==ordinary['stop_reason'])
        require(row.get('matches_frozen_ordinary')is bool(actual),'Host and native frozen ordinary decisions differ')
        behavior=behavior and actual and row['token_IDs_and_bytes_match_control']
        require(row.get('full_F32_rows_observed')==len(row['token_ids'])+(row['stop_reason']=='end_of_generation'),
            'Every speed arm needs all full vocabulary rows')
        for key in('total_ms','prefill_ms','decode_tokens_per_second'):
            require(type(row.get(key))in(int,float)and math.isfinite(row[key])and row[key]>0,'Finite completed timing metrics required')
        require(row['total_ms']>row['prefill_ms'],'Decode time must be included in total time')
        delivery=row.get('six_demand',{})
        require(all(integer(delivery.get(k))and delivery[k]>0 for k in('batches','reads','logical_bytes'))and
            delivery['reads']==6*delivery['batches'],'Every arm must complete real six-demand source work')
        stats=row['speculation'];capacity=row['checkpoint_capacity']
        require(stats['attempts']==stats['accepted']+stats['rejected']and stats['attempts']<=1 and
            capacity.get('same_original_context')is True,'Complete bounded attempts and same snapshot owner required')
        if row['arm']in('warmup','causal'):
            coverage=coverage and stats['accepted']==stats['attempts']==stats['queued_bonus_samples']==1 and stats['rejected']==0
            if stats['attempts']:
                actual=capacity['logical_payload_bytes']
                require(118038528<=actual<=142606336,'Every actual capture must retain complete original state')
                require(capacity['new_allocation_bytes']==(0 if payload==actual else ((actual+(2<<20)-1)//(2<<20))*(2<<20)),
                    'New or reused capacity must follow a positively completed real snapshot of identical size')
                payload=actual
            # A causal cost refusal is a completed negative coverage result.
            # The native last-admission fields are not a new capture receipt
            # when this arm made zero actual attempts.
        else:
            require(not stats['attempts']and not capacity['logical_payload_bytes']and not capacity['new_allocation_bytes'],
                'Ordinary controls must not execute speculative capture')
    require(report.get('all_original_tokens_and_bytes_exact')is bool(behavior)and
        report.get('causal_warmup_and_candidate_acceptance_passed')is bool(coverage),'Native and host speed gate decisions differ')
    controls=[rows[1],rows[4]];candidates=[rows[2],rows[3]]
    pair_wins=[b['total_ms']<a['total_ms']and b['decode_tokens_per_second']>a['decode_tokens_per_second']for a,b in zip(controls,candidates)]
    separated=max(r['total_ms']for r in candidates)<min(r['total_ms']for r in controls)and\
        min(r['decode_tokens_per_second']for r in candidates)>max(r['decode_tokens_per_second']for r in controls)
    qualified=bool(behavior and coverage and all(pair_wins)and separated)
    mean_control_total=sum(r['total_ms']for r in controls)/2;mean_candidate_total=sum(r['total_ms']for r in candidates)/2
    mean_control_decode=sum(r['decode_tokens_per_second']for r in controls)/2
    mean_candidate_decode=sum(r['decode_tokens_per_second']for r in candidates)/2
    return dict(passed=qualified,generated_behavior_equal=bool(behavior),actual_causal_acceptance_complete=bool(coverage),
        both_reverse_pairs_win=pair_wins,candidate_ranges_outside_control=bool(separated),
        control_total_ms=[r['total_ms']for r in controls],candidate_total_ms=[r['total_ms']for r in candidates],
        control_decode_tokens_per_second=[r['decode_tokens_per_second']for r in controls],
        candidate_decode_tokens_per_second=[r['decode_tokens_per_second']for r in candidates],
        mean_total_speedup=mean_control_total/mean_candidate_total,mean_decode_speedup=mean_candidate_decode/mean_control_decode,
        one_additional_block_eligible=bool(behavior and coverage and all(pair_wins)and not qualified and not separated and
            mean_candidate_total<mean_control_total and mean_candidate_decode>mean_control_decode),
        cache_initially_empty=True,OS_file_pages_coldness_claimed=False,known_control_drafts_used=False,
        physical_application_integration_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--case',type=int,required=True);p.add_argument('--kind',choices=('probe','behavior','speed'),required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();case,report=retired_case(a.cache,a.case)
    if a.kind=='probe':
        require(len(report['requests'])==3,'Original three-request numerical closure required')
        summary=probe_summary(load(case/'native-arm1.same-batch.private.json'))
        require(report['forced_rejection_and_full_F32_restore_passed']is True and report['requests'][2]['maximum_absolute_logit_error']==0,'Independent forced rejection must restore every original F32 value')
    elif a.kind=='behavior':
        summary=behavior_summary(report)
        summary['route_geometry']=[route_geometry(load(case/f'native-arm{i}.routes.private.json'),row)for i,row in enumerate(report['requests'])]
        summary['distribution']=[distribution_summary(load(case/f'native-arm{i}.logit-distribution.private.json'),row)for i,row in enumerate(report['requests'])]
        summary['passed']=summary['passed']and all(r.get('all_references_and_histories_available',True)for r in summary['distribution'])
    else:
        _,prior=retired_case(a.cache,5720)
        summary=speed_summary(report,prior['requests'][0])
        summary['route_geometry']=[route_geometry(load(case/f'native-arm{i}.routes.private.json'),row)for i,row in enumerate(report['requests'])]
        summary['distribution']=[distribution_summary(load(case/f'native-arm{i}.logit-distribution.private.json'),
            row,reference_request=(i==0))for i,row in enumerate(report['requests'])]
    result=dict(schema='ps5-qwen-speculative-qualification-review-v1',case=a.case,kind=a.kind,summary=summary,
        native_evidence=capture(case/'native-model-terminal.private.json'),restore_evidence=capture(case/'restored-complete.private.json'),
        all_model_source_device_owners_retired=True,normal_OS_close_and_exact_production_restore=True,PS5_calls=0,production_adopted=False)
    with a.out.open('x',encoding='utf-8',newline='\n')as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(case=a.case,kind=a.kind,summary=summary,PS5_calls=0)),flush=True)

if __name__=='__main__':main()
