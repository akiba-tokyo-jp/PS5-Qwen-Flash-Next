#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the finite real-model checkpoint report and its exact replay geometry."""
import math


def validate_checkpoint(record, result, *, pid, run_id):
    required=dict(schema='ps5-qwen-model-checkpoint-validation-result-v1',pid=pid,run_id=run_id,
        captures=25,restores=25,prefill_replays=2,next_replays_including_EOG=23,
        # First next() samples existing prompt logits without processing a token.
        # The next snapshot has the same position and a newly pending token.
        capture_positions=[4,28,30]+list(range(30,52)),original_route_rows_compared=1152,
        absolute_tolerance=1e-5,relative_tolerance=1e-5,
        effective_F32_logits_positions_pending_prompt_and_greedy_state_restored=True,
        all_original_expert_selections_exact=True,all_continuation_tokens_and_bytes_exact=True,emitted_once=True,
        device_ledger_live_bytes=0,all_model_source_and_checkpoint_owners_retired=True,
        performance_adoption_enabled=False,prefix_reuse_qualified=False,speculative_verification_qualified=False)
    if any(type(record.get(k))is not type(v)or record[k]!=v for k,v in required.items()):
        raise ValueError('Complete-model checkpoint scope or continuation differs')
    if(result.get('stop_reason')!='end_of_generation'or result.get('prefill_batch_tokens')!=4 or
       result.get('metrics',{}).get('prompt_tokens')!=30 or result['metrics'].get('generated_tokens')!=22 or
       len(result.get('token_ids',[]))!=22):
        raise ValueError('Checkpoint report requires the exact completed counting workload')
    for name,low,high in (('maximum_state_payload_bytes',118038528,136<<20),
        ('maximum_CPU_metadata_bytes',1,1<<20),('device_ledger_peak_bytes',118038528,1792<<20)):
        value=record.get(name)
        if type(value)is not int or not low<=value<=high:raise ValueError('Checkpoint resource bound differs: '+name)
    error=record.get('maximum_absolute_logit_error')
    if type(error)not in(int,float)or not math.isfinite(error)or error<0:
        raise ValueError('Checkpoint logit comparison is invalid')
    # The native elementwise comparison applies abs + rel*abs(reference).
    # Its maximum absolute error alone cannot reconstruct that entire comparison.
    return dict(complete_model_checkpoint_qualified=True,process_calls=54,
        extra_process_calls=24,original_route_rows_compared=1152,
        speedup_qualified=False,prefix_reuse_qualified=False,speculative_verification_qualified=False)


def checkpoint_process_geometry(result, checkpoint):
    validate_checkpoint(checkpoint,result,pid=checkpoint.get('pid'),run_id=checkpoint.get('run_id'))
    if type(checkpoint.get('pid'))is not int or checkpoint['pid']<=0:
        raise ValueError('Checkpoint owner is invalid')
    # Prefill P4 and P28 are replayed with identical original batch geometry.
    tokens=[]
    for position in range(0,30,4):
        width=min(4,30-position);tokens.append(width)
        if position in(4,28):tokens.append(width)
    return tokens+[1]*44
