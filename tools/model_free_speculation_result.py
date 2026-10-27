#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review finite native width-two controls without asserting speed adoption."""
def counters(row):
    keys=('attempts','accepted','rejected','queued_bonus_samples')
    if any(type(row.get(k))is not int or not 0<=row[k]<=32 for k in keys):
        raise ValueError('Invalid bounded speculative counters')
    if row['accepted']+row['rejected']!=row['attempts']or row['queued_bonus_samples']!=row['accepted']:
        raise ValueError('Every accepted bonus and rejected rollback must complete')
    return {k:row[k]for k in keys}
def validate_speculation(record,result):
    expected=dict(schema='ps5-qwen-causal-width-two-result-v1',pid=result.get('pid'),run_id=result.get('run_id'),
        all_control_token_IDs_and_bytes_exact=True,all_model_source_and_checkpoint_owners_retired=True,
        device_ledger_live_bytes=0,cache_condition_comparison_is_not_speed_qualification=True,speedup_qualified=False,
        complete_checkpoint_qualification_SHA256='e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7')
    if any(type(record.get(k))is not type(v)or record[k]!=v for k,v in expected.items()):
        raise ValueError('Finite width-two binding or positive retirement differs')
    rows=record.get('requests');actual=result.get('demonstration',{}).get('requests')
    policy=record.get('expert_cost_policy','fixed-width-two')
    if policy not in ('fixed-width-two','expert-union-online-v1'):
        raise ValueError('Unknown native verification cost policy')
    if not isinstance(rows,list)or len(rows)!=2 or not isinstance(actual,list)or len(actual)!=2:
        raise ValueError('Original single-token and candidate requests are required')
    for i,request in enumerate(actual):
        ids=request.get('token_ids');output=request.get('output_bytes')
        if (type(request.get('ordinal'))is not int or request['ordinal']!=i+1 or
            not isinstance(ids,list)or not 2<=len(ids)<=32 or
            any(type(x)is not int or not 0<=x<262144 for x in ids)or
            not isinstance(output,list)or not 0<len(output)<=65536 or
            any(type(x)is not int or not 0<=x<=255 for x in output)or
            request.get('stop_reason')not in('end_of_generation','output_token_limit')or
            request.get('metrics',{}).get('generated_tokens')!=len(ids)or
            request.get('request_reset_completed')is not True):
            raise ValueError('Bounded completed target outputs are required')
    for key in ('token_ids','output_bytes','stop_reason'):
        if actual[0].get(key)!=actual[1].get(key):raise ValueError('Original target tokens, bytes or EOG differ')
    for i,row in enumerate(rows):
        if type(row.get('ordinal'))is not int or row['ordinal']!=i+1 or row.get('controller_enabled')is not bool(i)or row.get('request_reset_completed')is not True:
            raise ValueError('Wrong speculative request scope or reset')
        count=counters(row)
        if i==0 and any(count.values()):raise ValueError('The original target control contains speculative work')
        for key in ('proposal_checks','no_draft','prompt_proposals','generated_proposals'):
            if type(row.get(key))is not int or not 0<=row[key]<=32:raise ValueError('Invalid causal proposal counter')
        proposals=row['prompt_proposals']+row['generated_proposals']
        if row['no_draft']+proposals!=row['proposal_checks']:
            raise ValueError('Causal draft and actual verification counts differ')
        if policy=='expert-union-online-v1':
            keys=('cost_checks','cost_ordinary','cost_width_two')
            if (row.get('expert_cost_enabled')is not bool(i)or
                any(type(row.get(k))is not int or not 0<=row[k]<=32 for k in keys)or
                row['cost_checks']!=row['cost_ordinary']+row['cost_width_two']or
                proposals!=row['cost_checks']or row['attempts']!=row['cost_width_two']):
                raise ValueError('Every online expert-cost decision must retain its actual ordinary or width-two outcome')
        elif proposals!=row['attempts']:
            raise ValueError('Fixed-width draft and actual verification counts differ')
    if record.get('target_width_two_exercised')is not(rows[1]['attempts']>0):
        raise ValueError('A zero-attempt run cannot qualify target width-two arithmetic')
    return dict(native_width_two_exercised=rows[1]['attempts']>0,
        native_rejection_exercised=rows[1]['rejected']>0,all_control_tokens_exact=True,
        speedup_qualified=False,requests=rows)
