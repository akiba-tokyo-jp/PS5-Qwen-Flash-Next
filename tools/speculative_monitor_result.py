#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Isolated combined-mode validators; legacy validators remain unchanged."""
import copy
import hashlib
import inspect
import json
import math
from pathlib import Path
from review_speculative_qualification import probe_summary
from resident_route_review import token_streams

def require(ok,message):
    if not ok:raise ValueError(message)

def captured(row):
    path=Path(row['path']);raw=path.read_bytes()
    require(len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'],'Frozen qualification artifact changed')
    return json.loads(raw)

def checked_quality(quality,scope):
    expected=dict(schema='ps5-qwen-matched-cache-monitor-result-v1',schema_extension='ps5-qwen-prefix-speculative-monitor-v1',
        completed=True,active_cache_slots=128,full_F32_rows_compared=23,prefix_reuse_enabled=True,
        second_request_reused_prompt_tokens=30,six_demand_enabled=True,all_original_expert_geometry_present=True,
        all_model_source_device_owners_retired=True,device_ledger_live_bytes=0,
        original_passive_VideoOut_and_two_API_requests_preserved=True,persistent_caches_enabled=False,
        prefix_snapshot_handed_off_after_positive_final_restore=True,known_control_drafts_used=False,
        same_width_probe_enabled=scope['same_width_probe_enabled'])
    require(all(type(quality.get(k))is type(v)and quality[k]==v for k,v in expected.items()),'Exact combined passive monitor ownership/scope required')
    require(quality.get('speculation')==dict(attempts=1,accepted=1,rejected=0,queued_bonus_samples=1),'Actual causal acceptance and bonus required')
    require(quality.get('snapshot_replacement')==dict(old_logical_bytes=119881728,new_logical_bytes=120311808,
        equal_rounded_capacity_bytes=121634816,old_buffer_freed_before_new_allocation=True,new_Direct_metadata_allowance_pages=19),
        'Exact positively consumed final-prefix buffer replacement required')
    hashes=quality.get('full_F32_row_SHA256')
    require(type(hashes)is list and len(hashes)==2 and all(type(rows)is list and len(rows)==23 and
        all(type(x)is str and len(x)==64 and set(x)<=set('0123456789abcdef')for x in rows)for rows in hashes),
        'All original F32 rows need complete bit-pattern fingerprints')
    rows=quality.get('full_F32_distribution')
    require(type(rows)is list and len(rows)==23,'All actual API F32 comparison rows required')
    for row in rows:
        for key in('reference_top5','candidate_top5'):
            ids=row.get(key)
            require(type(ids)is list and len(ids)==5 and len(set(ids))==5 and
                all(type(x)is int and 0<=x<248320 for x in ids),'Every full row needs five distinct original vocabulary IDs')
        require(row.get('columns')==248320 and row.get('all_finite')is True and
            row.get('reference_top5',[None])[0]==row.get('candidate_top5',[None])[0]and
            all(type(row.get(k))in(int,float)and math.isfinite(row[k])and row[k]>=0 for k in
                ('maximum_absolute_error','RMS_error','p50_absolute_error','p95_absolute_error','p99_absolute_error','mean_centered_RMS_error','KL_reference_to_candidate')),
            'Every complete vocabulary row must remain finite with identical greedy top one')
    require(max(r['maximum_absolute_error']for r in rows)==quality['maximum_absolute_F32_error'],'Aggregate full F32 maximum differs')
    require(type(quality.get('delivery_batches'))is list and len(quality['delivery_batches'])==2 and
        all(type(x)is int and x>0 for x in quality['delivery_batches']),'Both actual six-demand consumers required')
    if scope['same_width_probe_enabled']:
        require(scope.get('qualification_reference')is None and probe_summary(quality['same_width_probe'])['passed'],
            'The actual combined application must qualify its same-width F32 and active state')
    else:
        require(quality.get('same_width_probe')is None and type(scope.get('qualification_reference'))is dict,
            'Normal mode needs a closed diagnostic reference')
        prior=captured(scope['qualification_reference'])
        require(prior.get('same_width_probe_enabled')is True and probe_summary(prior['same_width_probe'])['passed']and
            quality['full_F32_row_SHA256']==prior['full_F32_row_SHA256'],
            'All 46 complete actual normal-mode F32 rows must be bit-exact to the same-SELF diagnostic reference')
    return dict(full_rows_observed=46,full_rows_compared=23,all_greedy_top1_equal=True,
        full_row_reference_bit_exact=not scope['same_width_probe_enabled'],maximum_F32_width_one_vs_two_error=quality['maximum_absolute_F32_error'])

def install(binding):
    """Install only in the explicitly selected finite observer process."""
    import cache128_result
    import expert_route_result
    import performance_result
    scope=binding.get('require_prefix_speculative_monitor')
    require(type(scope)is dict and scope.get('schema')=='ps5-qwen-prefix-speculative-observer-v1'and
        type(scope.get('same_width_probe_enabled'))is bool,'Explicit combined observer binding required')
    native_scope=scope.get('native_scope',{})
    require(native_scope.get('schema')=='ps5-qwen-prefix-speculative-handoff-v1'and native_scope.get('final_request_ordinal')==2 and
        native_scope.get('maximum_actual_attempts')==1 and native_scope.get('same_engine_class_layout')is True and
        native_scope.get('old_prefix_snapshot_bytes')==119881728 and native_scope.get('new_speculative_snapshot_bytes')==120311808 and
        native_scope.get('old_buffer_freed_before_new_allocation')is True and native_scope.get('allocator_caps_changed')is False,
        'Exact compiled final-consumer handoff scope required')
    for name in('speed','behavior','probe'):
        proof=scope[name+'_review'];review=captured(proof)
        require(review.get('summary',{}).get('passed')is True and native_scope.get(name+'_review_SHA256')==proof['sha256']and
            review.get('normal_OS_close_and_exact_production_restore')is True,
            'Every closed native correctness/speed gate must match the compiled application scope')
    reference=captured(scope['speed_reference_routes']);reference_streams=token_streams(reference)
    require(reference.get('ordinal')==2 and len(reference_streams[0])==52,'Closed original 128-slot causal route reference required')
    widths=[r['tokens']for r in reference['records'][::48]][8:]
    require(len(widths)==21 and widths.count(2)==1 and sum(widths)==22,'Exactly one actual accepted target batch in the bound speed reference required')
    first_two=widths.index(2);extra=2 if scope['same_width_probe_enabled']else 0
    expected_widths=widths[:first_two]+[2]*extra+widths[first_two:]
    state=dict(quality=None,quality_review=None)

    def geometry(record,result):
        actual=[r['tokens']for r in record['records'][::48]]
        require(actual==expected_widths,'Combined route geometry must include every diagnostic reference and actual accepted target batch')
        return actual

    original_routes=expert_route_result.validate_routes
    source=inspect.getsource(original_routes)
    require(source.count('        tokens=[1]*22')==1,'One legacy combined-prefix geometry boundary required')
    source=source.replace('        tokens=[1]*22','        tokens=combined_geometry(record,result)')
    route_env=dict(expert_route_result.__dict__,combined_geometry=geometry)
    exec(compile(source,__file__+'#explicit-combined-routes','exec'),route_env)
    combined_routes=route_env['validate_routes']

    def compare_actual_routes(route):
        actual=token_streams(route)
        if extra:
            actual=[stream[:first_two]+stream[first_two+4:]for stream in actual]
        require(all(a[30:]==b for a,b in zip(reference_streams,actual)),
            'Actual ordered Experts must match the closed same-batch causal reference after diagnostic replay removal')

    # Keep the original complete layout, SHA256 and native Direct pool checks.
    original_model=inspect.getsource(cache128_result.validate_model)
    boundary=original_model.index('    summaries=[]')
    model_source=original_model[:boundary]+'''    return combined_model_tail(path,expected,result,read_record)
'''
    def model_tail(path,expected,result,read_record):
        quality=read_record(Path(str(path)+'.cache128-monitor'));checked=checked_quality(quality,scope)
        state.update(quality=quality,quality_review=checked)
        summaries=[]
        for ordinal,suffix in enumerate(('.first','.demo1','.demo2')):
            route=read_record(Path(str(path)+suffix+'.expert-routes'))
            require(route.get('sidecar_written_after_model_and_source_retirement')is True and route.get('JSON_created_after_model_and_source_retirement')is True,
                'All original routes must be saved after positive model/source retirement')
            request=result if ordinal==0 else result['demonstration']['requests'][ordinal-1]
            validator=combined_routes if ordinal==2 else original_routes
            summaries.append(validator(route,request,width=4,pid=expected['pid'],run_id=expected['run_id'],
                cold=ordinal<2,expected_slots=128,reused_prompt_tokens=30 if ordinal==2 else 0))
            if ordinal==2:compare_actual_routes(route)
        return dict(active_slots=128,physical_planes=129,cache_request_bytes=1274462208,
            complete_layout_SHA256_verified=True,requests=summaries,combined_qualification=checked)
    model_env=dict(cache128_result.__dict__,combined_model_tail=model_tail)
    exec(compile(model_source,__file__+'#original-layout-plus-explicit-combined-proof','exec'),model_env)
    cache128_result.validate_model=model_env['validate_model']

    perf_source=inspect.getsource(performance_result.validate_performance)
    old="reason!='end_of_generation' or speculative or checkpoint_validation is not None or prefix_validation is not None):"
    require(perf_source.count(old)==1,'One legacy independent prefix timing guard required')
    perf_source=perf_source.replace(old,"reason!='end_of_generation' or checkpoint_validation is not None or prefix_validation is not None):")
    old="        expected+=count['rejected']-count['queued_bonus_samples']"
    require(perf_source.count(old)==1,'One actual speculative process-accounting boundary required')
    perf_source=perf_source.replace(old,old+'\n        if reused_prompt_tokens:expected+=combined_extra_calls')
    perf_env=dict(performance_result.__dict__,combined_extra_calls=extra)
    exec(compile(perf_source,__file__+'#explicit-combined-performance','exec'),perf_env)
    original_performance=performance_result.validate_performance;combined_performance=perf_env['validate_performance']
    def validate_performance(record,result,**kwargs):
        if kwargs.get('reused_prompt_tokens')!=30:return original_performance(record,result,**kwargs)
        require(state['quality']is not None,'Combined native quality must be validated before timing')
        count=record.get('speculation',{})
        require(all(count.get(k)==v for k,v in state['quality']['speculation'].items()),'Performance and native acceptance counts differ')
        kwargs=dict(kwargs,speculative_validation=count)
        return combined_performance(record,result,**kwargs)
    performance_result.validate_performance=validate_performance
    return state
