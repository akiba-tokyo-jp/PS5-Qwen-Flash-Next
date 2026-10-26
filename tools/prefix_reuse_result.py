#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate finite exact-prefix continuation, separate from any speed adoption."""
import re


def _scope(record, *, pid, run_id):
    enabled=record.get('prefix_reuse_enabled')
    if(type(enabled)is not bool or type(pid)is not int or pid<=0 or
       type(run_id)is not str or not re.fullmatch('[0-9a-f]{32}',run_id)):
        raise ValueError('Prefix owner or switch is invalid')
    required=dict(schema='ps5-qwen-exact-prefix-validation-result-v1',pid=pid,run_id=run_id,complete=True,
        full_F32_logit_arrays_compared=23,all_F32_logit_fingerprints_exact=True,
        original_route_rows_compared=1056 if enabled else 1440,all_original_expert_selections_exact=True,
        all_emitted_tokens_and_bytes_exact=True,emitted_once=True,additional_GPU_downloads=0,
        device_ledger_live_bytes=0,all_model_source_and_snapshot_owners_retired=True,speedup_qualified=False)
    if any(type(record.get(k))is not type(v)or record[k]!=v for k,v in required.items()):
        raise ValueError('Prefix continuation or retired resource scope differs')
    hashes=record.get('request_logit_SHA256')
    if(type(hashes)is not list or len(hashes)!=2 or any(type(row)is not list or len(row)!=23 or
       any(type(h)is not str or not re.fullmatch('[0-9a-f]{64}',h)for h in row)for row in hashes)or hashes[0]!=hashes[1]):
        raise ValueError('Every original F32 logit array and EOG must match')
    for key,low,high in(('saved_state_payload_bytes',118038528 if enabled else 0,(136<<20)if enabled else 0),
        ('CPU_metadata_bytes',1 if enabled else 0,(1<<20)if enabled else 0),('device_ledger_peak_bytes',1,1792<<20)):
        value=record.get(key)
        if type(value)is not int or not low<=value<=high:raise ValueError('Prefix allocation bound differs: '+key)
    requests=record.get('requests')
    if type(requests)is not list or len(requests)!=2:raise ValueError('Two bounded prefix requests required')
    capture_ns=0
    for i,row in enumerate(requests):
        required=dict(ordinal=i+1,prefix_hit=enabled and i==1,reused_prompt_tokens=30 if enabled and i==1 else 0,
            cumulative_captures=1 if enabled else 0,cumulative_restores=1 if enabled and i==1 else 0)
        if type(row)is not dict or any(type(row.get(k))is not type(v)or row[k]!=v for k,v in required.items()):
            raise ValueError('Prefix hit/capture/restore accounting differs')
        for key in('cumulative_capture_ns','cumulative_restore_ns'):
            if type(row.get(key))is not int or not 0<=row[key]<3600*10**9:raise ValueError('Prefix interval is invalid')
        if i==0:capture_ns=row['cumulative_capture_ns']
        if(row['cumulative_capture_ns']!=capture_ns or bool(capture_ns)!=enabled or
           bool(row['cumulative_restore_ns'])!=(enabled and i==1)):
            raise ValueError('Capture and restore work must remain priced in their own requests')
    return enabled


def _request(result, *, pid, run_id, ordinal):
    metrics=result.get('metrics',{})
    if(type(result.get('pid'))is not int or result['pid']!=pid or result.get('run_id')!=run_id or
       type(result.get('ordinal'))is not int or result['ordinal']!=ordinal or
       type(result.get('prefill_batch_tokens'))is not int or result['prefill_batch_tokens']!=4 or
       result.get('stop_reason')!='end_of_generation'or type(metrics)is not dict or
       type(metrics.get('prompt_tokens'))is not int or metrics['prompt_tokens']!=30 or
       type(metrics.get('generated_tokens'))is not int or metrics['generated_tokens']!=22):
        raise ValueError('Exact prefix comparison requires its fixed original counting workload')
    tokens=result.get('token_ids');output=result.get('output_bytes')
    if(type(tokens)is not list or len(tokens)!=22 or any(type(t)is not int or not 0<=t<262144 for t in tokens)or
       type(output)is not list or not 1<=len(output)<=65536 or any(type(b)is not int or not 0<=b<=255 for b in output)or
       bytes(b for b in output if b not in b' \t\r\n')!=b'1,2,3,4,5,6,7,8'):
        raise ValueError('Prefix emitted tokens or original output bytes are invalid')


def validate_prefix(record, first, second, *, pid, run_id, expected_enabled):
    enabled=_scope(record,pid=pid,run_id=run_id)
    if type(expected_enabled)is not bool or enabled!=expected_enabled:raise ValueError('Prefix switch differs from the frozen case')
    _request(first,pid=pid,run_id=run_id,ordinal=1);_request(second,pid=pid,run_id=run_id,ordinal=2)
    if first['token_ids']!=second['token_ids']or first['output_bytes']!=second['output_bytes']:
        raise ValueError('Cold and repeated continuations differ')
    return dict(complete_model_exact_prefix_continuation_qualified=enabled,control_switch_qualified=not enabled,
        full_F32_logit_arrays_compared=23,original_route_rows_compared=record['original_route_rows_compared'],
        repeated_prompt_tokens_reused=30 if enabled else 0,repeated_process_calls=22 if enabled else 30,speedup_qualified=False)


def prefix_process_geometry(result, record):
    enabled=_scope(record,pid=record.get('pid'),run_id=record.get('run_id'));ordinal=result.get('ordinal')
    if type(ordinal)is not int or ordinal not in(1,2):raise ValueError('Unknown prefix request ordinal')
    _request(result,pid=record['pid'],run_id=record['run_id'],ordinal=ordinal)
    return([]if enabled and ordinal==2 else[4]*7+[2])+[1]*22
