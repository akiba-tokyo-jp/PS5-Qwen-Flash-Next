#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate completed selected-ID metadata; never execute learned inference."""


def validate_routes(record,result,*,width,pid,run_id,cold,checkpoint_validation=None,prefix_validation=None,expected_slots=53):
    if type(expected_slots)is not int or expected_slots not in (53,128):raise ValueError('Unsupported independently bound cache capacity')
    expected=dict(schema='ps5-qwen-completed-expert-routes-v1',complete=True,capture_failed=False,
        pid=pid,run_id=run_id,cache_reset_before_request=cold,layers_per_process=48,experts=512,
        experts_per_token=10,cache_slots=expected_slots,maximum_records=4608,
        all_existing_downloads_and_synchronizations_returned=True,additional_GPU_downloads=0,
        routing_and_cache_policy_unchanged=True)
    if type(width)is not int or width not in (1,2,4):raise ValueError('Unsupported route capture width')
    if any(type(record.get(k))is not type(v)or record[k]!=v for k,v in expected.items()):
        raise ValueError('Completed expert-route scope differs')
    metrics=result['metrics'];prompt=metrics['prompt_tokens'];generated=metrics['generated_tokens'];reason=result['stop_reason']
    if type(prompt)is not int or not 1<=prompt<=64 or type(generated)is not int or not 1<=generated<=32:
        raise ValueError('Route request counts exceed their admitted bounds')
    if reason not in ('end_of_generation','output_token_limit'):raise ValueError('Route capture requires a completed request')
    tokens=[min(width,prompt-n)for n in range(0,prompt,width)]+[1]*(generated-(reason=='output_token_limit'))
    if checkpoint_validation is not None:
        from model_checkpoint_result import checkpoint_process_geometry,validate_checkpoint
        if width!=4:raise ValueError('Checkpoint routes require the qualified four-token path')
        validate_checkpoint(checkpoint_validation,result,pid=pid,run_id=run_id)
        tokens=checkpoint_process_geometry(result,checkpoint_validation)
    if prefix_validation is not None:
        from prefix_reuse_result import prefix_process_geometry
        if checkpoint_validation is not None or width!=4:raise ValueError('Prefix routes require an independent four-token comparison')
        if prefix_validation.get('pid')!=pid or prefix_validation.get('run_id')!=run_id:raise ValueError('Prefix route owner differs')
        tokens=prefix_process_geometry(result,prefix_validation)
    calls=len(tokens);rows=record.get('records')
    if type(record.get('process_calls'))is not int or record['process_calls']!=calls or type(rows)is not list or len(rows)!=48*calls:
        raise ValueError('Expert routes do not cover the complete request')
    unique=0;selected=0
    for n,row in enumerate(rows):
        if type(row)is not dict or set(row)!={'layer','tokens','ids'}:
            raise ValueError('Invalid expert-route record')
        if type(row['layer'])is not int or row['layer']!=n%48 or type(row['tokens'])is not int or row['tokens']!=tokens[n//48]:
            raise ValueError('Expert-route causal batch or layer order differs')
        ids=row['ids']
        if type(ids)is not list or len(ids)!=10*row['tokens']or any(type(i)is not int or not 0<=i<512 for i in ids):
            raise ValueError('Selected expert IDs exceed the original model')
        if any(len(set(ids[start:start+10]))!=10 for start in range(0,len(ids),10)):
            raise ValueError('An original top-k selection contains duplicate IDs')
        unique+=len(set(ids));selected+=len(ids)
    for name in ('selected_indices','unique_selected_experts','cache_hits','cache_misses','uploaded_bytes','prefetch_advice_bytes'):
        if type(record.get(name))is not int or not 0<=record[name]<2**63:raise ValueError('Invalid expert-route counters')
    if (record['selected_indices']!=selected or record['unique_selected_experts']!=unique or
        record['cache_hits']+record['cache_misses']!=unique or record['uploaded_bytes']!=record['cache_misses']*9830400 or
        record['prefetch_advice_bytes']!=0):raise ValueError('Selected IDs disagree with the actual bounded cache transfers')
    return dict(process_calls=calls,layer_records=len(rows),selected_indices=selected,
        unique_selected_experts=unique,cache_hits=record['cache_hits'],cache_misses=record['cache_misses'],
        uploaded_bytes=record['uploaded_bytes'],cache_policy_replay_pending=True)
