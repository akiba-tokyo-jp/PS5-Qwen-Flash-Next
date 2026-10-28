#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit bounded mixed-width validation; keep legacy validators unchanged."""
import inspect,math
from pathlib import Path
from speculative_monitor_result import require,captured
from resident_route_review import token_streams

PROMPT='Copy this sequence twice exactly: red blue red blue red blue.'
IDS=[1114,6105,2438,6105,2438,6105,2438,6105,2438,6105,2438,6105]
COMPACT=b'redblueredblueredblueredblueredblueredblue'


def counters(value):
    keys=('attempts','accepted','rejected','queued_bonus_samples')
    require(type(value)is dict and set(value)==set(keys)and all(type(value[k])is int and value[k]>=0 for k in keys),'Typed actual mixed-width counters required')
    n=value['accepted'];bonus=value['queued_bonus_samples']
    require(1<=n<=8 and value['attempts']==n and value['rejected']==0 and bonus>=n and(bonus-n)%2==0 and(bonus-n)//2<=n,
        'The bounded adopted profile requires actual accepted widths two/four without rejected work')
    return value


def wide_probe(probe):
    from review_speculative_qualification import probe_summary
    text=inspect.getsource(probe_summary).replace("'ps5-qwen-same-batch-probe-v1'","'ps5-qwen-wide-same-batch-probe-v1'").replace('len(rows)==4','len(rows)==8').replace('same_width_full_F32_rows=4','same_width_full_F32_rows=8')
    env=dict(__import__('review_speculative_qualification').__dict__);exec(compile(text,__file__+'#exact-four-row-state-proof','exec'),env)
    result=env['probe_summary'](probe)
    require(probe.get('verified_target_width')==4 and result['passed']and result['maximum_same_width_F32_error']==0,'All eight same-width F32 comparisons and complete active states must match exactly')
    return result


def checked_quality(quality,scope):
    slots=scope.get('native_scope',{}).get('active_cache_slots',128)
    require(type(slots)is int and slots in(128,134),'An independently qualified cache capacity is required')
    exact=dict(schema='ps5-qwen-matched-cache-monitor-result-v1',schema_extension='ps5-qwen-adaptive-prefix-monitor-v1',
        completed=True,adaptive_profile_selected=True,active_cache_slots=slots,full_F32_rows_compared=13,prefix_reuse_enabled=True,
        second_request_reused_prompt_tokens=25,six_demand_enabled=True,all_original_expert_geometry_present=True,
        all_model_source_device_owners_retired=True,device_ledger_live_bytes=0,original_passive_VideoOut_and_two_API_requests_preserved=True,
        persistent_caches_enabled=False,prefix_snapshot_handed_off_after_positive_final_restore=True,known_control_drafts_used=False,
        same_width_probe_enabled=scope['same_width_probe_enabled'],snapshot_F32_sections=109)
    require(all(type(quality.get(k))is type(v)and quality[k]==v for k,v in exact.items()),'Exact completed adaptive passive profile required')
    count=counters(quality['speculation']);require(count['queued_bonus_samples']-count['accepted']>=2,'At least one accepted width-four target must execute')
    require(type(quality.get('snapshot_replacements'))is int and quality['snapshot_replacements']==count['attempts'],'Every final-prefix replacement must positively complete')
    replacement=quality['snapshot_replacement']
    require(set(replacement)=={'old_logical_bytes','new_logical_bytes','each_actual_layout_witnessed','old_buffer_freed_before_new_allocation','new_Direct_metadata_allowance_pages'}and
        replacement['each_actual_layout_witnessed']is True and replacement['old_buffer_freed_before_new_allocation']is True and replacement['new_Direct_metadata_allowance_pages']==19 and
        all(type(replacement[k])is int and 118038528<=replacement[k]<=142606336 for k in('old_logical_bytes','new_logical_bytes')),'Actual witnessed single-buffer snapshot replacement required')
    hashes=quality['full_F32_row_SHA256'];rows=quality['full_F32_distribution']
    require(type(hashes)is list and len(hashes)==2 and all(type(r)is list and len(r)==13 and all(type(h)is str and len(h)==64 and set(h)<=set('0123456789abcdef')for h in r)for r in hashes),'All 26 full-vocabulary row hashes are required')
    require(type(rows)is list and len(rows)==13,'All thirteen cross-width vocabulary comparisons required')
    for row in rows:
        require(row['columns']==248320 and row['all_finite']is True and row['candidate_top5'][0]==row['reference_top5'][0]and
            all(type(row[k])in(int,float)and math.isfinite(row[k])and row[k]>=0 for k in('maximum_absolute_error','RMS_error','p50_absolute_error','p95_absolute_error','p99_absolute_error','mean_centered_RMS_error','KL_reference_to_candidate')),
            'Every original F32 row must be finite with identical greedy top one')
    require(max(r['maximum_absolute_error']for r in rows)==quality['maximum_absolute_F32_error'],'Aggregate full F32 maximum differs')
    require(type(quality['delivery_batches'])is list and len(quality['delivery_batches'])==2 and all(type(x)is int and x>0 for x in quality['delivery_batches']),'Both actual six-demand consumers must execute')
    if scope['same_width_probe_enabled']:
        require(scope.get('qualification_reference')is None,'The diagnostic cannot cite itself as prior qualification');probe=wide_probe(quality['same_width_probe'])
    else:
        require(quality['same_width_probe']is None,'Normal mode cannot execute diagnostic target replays')
        prior=captured(scope['qualification_reference']);probe=wide_probe(prior['same_width_probe'])
        require(prior['same_width_probe_enabled']is True and prior['full_F32_row_SHA256']==hashes,'All 26 normal-mode full F32 rows must reproduce the closed same-SELF diagnostic reference')
    return dict(full_rows_observed=26,full_rows_compared=13,all_greedy_top1_equal=True,full_row_reference_bit_exact=not scope['same_width_probe_enabled'],wide_state_probe=probe)


def install(binding):
    import cache128_result,expert_route_result,performance_result,first_generation_result
    scope=binding.get('require_adaptive_prefix_monitor')
    require(type(scope)is dict and scope.get('schema')=='ps5-qwen-adaptive-prefix-observer-v1'and type(scope.get('same_width_probe_enabled'))is bool,'Explicit adaptive observer binding required')
    slots=scope['native_scope'].get('active_cache_slots')
    require(scope['native_scope']['schema']=='ps5-qwen-causal-adaptive-monitor-v1'and type(slots)is int and slots in(128,134)and scope['native_scope']['maximum_actual_attempts']==8,'Exact compiled adaptive monitor scope required')
    for name in('speed','behavior'):
        record=scope[name+'_reference'];data=captured(record)
        require(data['completed']and data['all_model_source_device_owners_positively_retired']and scope['native_scope'][name+'_evidence_SHA256']==record['sha256'],'Closed original-model speed and behavior references must match the compiled scope')
    state=dict(quality=None,quality_review=None,routes={})
    # Keep every original layout digest, native Direct pool observation, frame,
    # source, owner and exact-once API transport condition. Only the declared
    # prompt/output and mixed-width accounting differ in this isolated observer.
    text=inspect.getsource(cache128_result.validate_binding).replace("prefix['prompt_tokens']==30","prefix['prompt_tokens']==25").replace("prefix['full_F32_rows']==23","prefix['full_F32_rows']==13")
    env=dict(cache128_result.__dict__);exec(compile(text,__file__+'#explicit-adaptive-prefix-binding','exec'),env);cache128_result.validate_binding=env['validate_binding']
    text=inspect.getsource(first_generation_result.validate)
    text=text.replace('Count from 1 to 8, separated by commas. Reply with only the sequence.',PROMPT)
    text=text.replace('b"1,2,3,4,5,6,7,8"','ADAPTIVE_COMPACT')
    needle='        token_ids, pieces, values = terminal.get("token_ids"), terminal.get("output_bytes"), terminal.get("metrics")'
    require(text.count(needle)==1,'One complete external token-validation boundary required')
    text=text.replace(needle,needle+'\n        require(token_ids==ADAPTIVE_IDS,"The native adaptive output differs from the frozen ordinary model")')
    env=dict(first_generation_result.__dict__,ADAPTIVE_COMPACT=COMPACT,ADAPTIVE_IDS=IDS);exec(compile(text,__file__+'#original-owner-frames-and-explicit-output','exec'),env);first_generation_result.validate=env['validate']

    original_routes=expert_route_result.validate_routes
    text=inspect.getsource(original_routes).replace('not in(0,30)','not in(0,25)').replace('prompt!=30','prompt!=25').replace('generated!=22','generated!=12')
    text=text.replace('        tokens=[1]*22','        tokens=adaptive_geometry(record,result)')
    def geometry(route,result):
        count=counters(state['quality']['speculation']);widths=[r['tokens']for r in route['records'][::48]]
        extra=2 if scope['same_width_probe_enabled']else 0;n4=(count['queued_bonus_samples']-count['accepted'])//2;n2=count['accepted']-n4
        require(all(type(w)is int and w in(1,2,4)for w in widths)and widths.count(4)==n4+extra and widths.count(2)==n2 and
            widths.count(1)==12-4*n4-2*n2 and sum(widths)==12+4*extra,'Every actual ordinary, width-two/four and diagnostic process must be accounted')
        return widths
    env=dict(expert_route_result.__dict__,adaptive_geometry=geometry);exec(compile(text,__file__+'#explicit-adaptive-route-geometry','exec'),env);adaptive_routes=env['validate_routes']
    original_model=inspect.getsource(cache128_result.validate_model);at=original_model.index('    summaries=[]')
    def model_tail(path,expected,result,read_record):
        quality=read_record(Path(str(path)+'.cache128-monitor'));checked=checked_quality(quality,scope);state.update(quality=quality,quality_review=checked)
        summaries=[]
        for ordinal,suffix in enumerate(('.first','.demo1','.demo2')):
            route=read_record(Path(str(path)+suffix+'.expert-routes'));require(route['sidecar_written_after_model_and_source_retirement']and route['JSON_created_after_model_and_source_retirement'],'All actual route sidecars must follow positive retirement')
            request=result if ordinal==0 else result['demonstration']['requests'][ordinal-1]
            summaries.append((adaptive_routes if ordinal==2 else original_routes)(route,request,width=4,pid=expected['pid'],run_id=expected['run_id'],cold=ordinal<2,expected_slots=slots,reused_prompt_tokens=25 if ordinal==2 else 0));state['routes'][ordinal]=route
        return dict(active_slots=slots,physical_planes=slots+1,cache_request_bytes=1274462208 if slots==128 else 1333739520,complete_layout_SHA256_verified=True,requests=summaries,adaptive_qualification=checked)
    env=dict(cache128_result.__dict__,adaptive_model_tail=model_tail);exec(compile(original_model[:at]+'    return adaptive_model_tail(path,expected,result,read_record)\n',__file__+'#unchanged-layout-and-explicit-adaptive-tail','exec'),env);cache128_result.validate_model=env['validate_model']

    original_performance=performance_result.validate_performance;text=inspect.getsource(original_performance)
    text=text.replace('range(1,7)','range(1,8)')
    text=text.replace("speculative=schema=='ps5-qwen-completed-performance-v6'","speculative=schema in('ps5-qwen-completed-performance-v6','ps5-qwen-completed-performance-v7')")
    text=text.replace("'ps5-qwen-completed-performance-v6'","'ps5-qwen-completed-performance-v6','ps5-qwen-completed-performance-v7'")
    text=text.replace("'v4','v5','v6'","'v4','v5','v6','v7'").replace("'v5','v6'","'v5','v6','v7'")
    text=text.replace('not in(0,30)','not in(0,25)').replace("metrics['prompt_tokens']!=30","metrics['prompt_tokens']!=25").replace("metrics['generated_tokens']!=22","metrics['generated_tokens']!=12").replace('        expected=22','        expected=12')
    text=text.replace("reason!='end_of_generation' or speculative or checkpoint_validation", "reason!='end_of_generation' or checkpoint_validation")
    text=text.replace('        from model_free_speculation_result import counters','        counters=adaptive_counters')
    text=text.replace("record.get('target_verification_batch_tokens')!=2","record.get('maximum_target_verification_batch_tokens')!=4 or record.get('target_verification_batch_widths')!=[2,4]")
    text=text.replace("        expected+=count['rejected']-count['queued_bonus_samples']","        expected+=count['rejected']-count['queued_bonus_samples']+adaptive_extra_calls")
    env=dict(performance_result.__dict__,adaptive_counters=counters,adaptive_extra_calls=2 if scope['same_width_probe_enabled']else 0);exec(compile(text,__file__+'#mixed-width-performance-and-real-source-counters','exec'),env);adaptive_performance=env['validate_performance']
    def performance(record,result,**kwargs):
        if kwargs.get('reused_prompt_tokens')!=25:return original_performance(record,result,**kwargs)
        require(state['quality']is not None and record['schema']=='ps5-qwen-completed-performance-v7'and record['speculation']==state['quality']['speculation'],'Actual mixed-width timing and quality counters must agree')
        return adaptive_performance(record,result,**dict(kwargs,speculative_validation=record['speculation']))
    performance_result.validate_performance=performance
    return state
