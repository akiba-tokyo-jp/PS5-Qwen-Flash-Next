#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare closed finite Q4 and original BF16 model runs without component extrapolation."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import require,write_json

def closed_case(path,quantized):
    result=json.loads((path/'native-model-terminal.private.json').read_text())
    restored=json.loads((path/'restored-complete.private.json').read_text())
    require(restored['completed']and restored['CPU_title_normally_closed']and restored['exact_prior_configuration_restored']and
        restored['full_native_readback_SHA256_identity_EOF_verified'],'Normal close and exact BF16 restoration required')
    require(result['completed']and len(result['requests'])==3 and result['model_loads']==1 and
        result['all_model_source_device_owners_positively_retired']and result['device_ledger_live_bytes']==0 and
        result['source_windows']==result['source_completed_windows']and result['full_F32_continuation_and_routes_passed'],
        'Complete actual-model inference, same-model logits/routes and positive retirement required')
    require(result['schema']==('ps5-qwen-expert-q4-model-result-v1'if quantized else 'ps5-qwen-resident-additional-result-v1'), 'Expected exact model comparison schema')
    require(result['active_cache_slots']==(481 if quantized else 134),'Matched cache byte-budget profiles required')
    rows=[]
    for i,row in enumerate(result['requests']):
        metrics=row['metrics'];delta=row['completed_performance']['delta']
        require(row['ordinal']==i and row['request_reset_completed']and metrics['generated_tokens']>1 and
            metrics['decode_tokens_per_second']>0 and delta['source_chunks']==delta['source_completed_windows'], 'Complete positive per-request metrics required')
        rows.append(dict(ordinal=i,warmup=i==0,generated_tokens=metrics['generated_tokens'],prompt_tokens=metrics['prompt_tokens'],
            decode_tokens_per_second=metrics['decode_tokens_per_second'],decode_ms=metrics['decode_ms'],total_ms=metrics['total_ms'],TTFT_ms=metrics['TTFT_ms'],
            whole_request_physical_read_bytes=delta['source_physical_read_bytes'],whole_request_physical_read_calls=delta['source_physical_read_calls'],
            whole_request_source_wait_ns=delta['source_read_ns'],full_same_model_F32_rows_compared=row['full_F32_logit_rows_compared'],
            maximum_same_model_absolute_logit_error=row['maximum_absolute_logit_error'],
            counting_quality_passed=row.get('counting_quality_passed',True),output_utf8=bytes(row['output_bytes']).decode('utf-8')))
    return result,rows,restored

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--control',type=Path,action='append',required=True)
    p.add_argument('--json',type=Path,required=True);p.add_argument('--markdown',type=Path,required=True);a=p.parse_args()
    result,candidate,restored=closed_case(a.candidate,True);controls=[]
    for path in a.control:
        _,rows,_=closed_case(path,False);controls.extend(dict(case=path.name,**row)for row in rows if not row['warmup'])
    timed=[row for row in candidate if not row['warmup']]
    def throughput(rows):return sum(row['generated_tokens']-1 for row in rows)/sum(row['decode_ms']/1000 for row in rows)
    q4,bf16=throughput(timed),throughput(controls);quality=all(row['counting_quality_passed']for row in candidate)
    exact_outputs=all(row['output_utf8']==controls[0]['output_utf8']for row in candidate+controls)
    consistent_gain=min(row['decode_tokens_per_second']for row in timed)>max(row['decode_tokens_per_second']for row in controls)
    gain=q4/bf16;passed=quality and consistent_gain and gain>1
    report=dict(schema='ps5-qwen-expert-q4-model-review-v1',completed=True,actual_PS5_model_inference=True,
        Expert_format='Q4_0',non_Expert_precision_preserved=True,KV_type='F32',activation_quantization=False,
        candidate= candidate,original_BF16_controls=controls,decode_tokens_per_second=dict(Q4=q4,BF16=bf16,ratio=gain),
        all_counting_quality_passed=quality,identical_finite_output_bytes_to_BF16=exact_outputs,
        all_same_Q4_F32_rows_and_routes_passed=True,whole_request_IO_includes_prefill=True,
        same_cache_budget_bytes=1333739520,Q4_slots=481,BF16_slots=134,
        full_model_candidate_screen_passed=passed,normal_passive_application_qualified=False,production_adopted=False,
        screen_conditions=dict(all_counting_answers_correct=True,each_Q4_sample_faster_than_best_BF16=True,pooled_decode_gain_above_one=True),
        limitations=['Finite counting cohort only; not broad reasoning quality.','No BF16/Q4 full-logit equality claim.',
            'Controls precede this Q4 run; no same-time device control.','Source counters cover the entire request, not decode alone.',
            'BF16 uses six-demand padded delivery; Q4 uses compressed contiguous delivery.'],
        BF16_restored=restored['exact_fastest_SELF']['sha256'],driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',profile='cumulative-idle',CI_runs=0)
    write_json(a.json,report)
    table='\n'.join(f"| {row['ordinal']} | {row['decode_tokens_per_second']:.6f} | {row['TTFT_ms']/1000:.3f} | {row['whole_request_physical_read_bytes']/1e9:.3f} | {row['counting_quality_passed']} |"for row in candidate)
    a.markdown.write_text(f'''# Expert-only Q4 actual-model comparison

The completed PS5 run uses all Experts, Q4_0 Expert weights, unchanged non-Expert
BF16/F32 tensors, F32 activation inputs and F32 KV. The original BF16 application
and five settings were restored after positive resource retirement and ordinary
OS close. This report does not declare normal-application production adoption.

| Request (0 is warmup) | Decode tok/s | TTFT seconds | Whole-request physical GB | Counting passed |
| --- | --- | --- | --- | --- |
{table}

Pooled timed decode: Q4 **{q4:.6f} tok/s**, original BF16 **{bf16:.6f} tok/s**,
ratio **{gain:.4f}x**. Each rate counts accepted decode transitions and excludes
prefill. I/O counters include the entire request and must not be labeled decode-only.
All counting answers passed: **{quality}**. Full same-Q4 F32/route comparisons and
positive retirement passed. This is a finite counting result, not broad reasoning
qualification or BF16/Q4 logit equivalence.

The cache budget remains 1,333,739,520 bytes: 134 BF16 slots versus 481 Q4 slots.
The BF16 controls use six-demand padded delivery; Q4 uses contiguous compressed
delivery. These are serial runs of the same original model with different Expert
precision and cache representations. A finite candidate gain/quality screen passed:
**{passed}**. Normal passive monitor/API qualification remains separate.
''',encoding='utf-8',newline='\n')
    print(json.dumps(dict(actual_Q4_decode_tokens_per_second=q4,BF16_control=bf16,ratio=gain,counting_quality=quality,normal_application_adopted=False)),flush=True)
if __name__=='__main__':main()
