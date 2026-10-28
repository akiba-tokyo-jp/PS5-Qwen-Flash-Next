#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify completed fixture comparisons without treating timing noise as a win."""
import argparse,json,math,random,statistics
from pathlib import Path


def interval(control,candidate,seed):
    rng=random.Random(seed);values=[]
    for _ in range(10000):
        a=sum(rng.choice(control)for _ in control)/len(control)
        b=sum(rng.choice(candidate)for _ in candidate)/len(candidate)
        values.append(a/b)
    values.sort();return [values[249],values[9749]]


def review(data):
    if not data['completed']or data['GPU_graphs']!=324 or len(data['cases'])!=9 or not data['all_outputs_reference_valid']or not data['all_backends_positively_retired']or data['device_ledger_live_bytes'] or data['model_loaded']:
        raise ValueError('All nine numerical/ownership comparisons must complete')
    rows=[]
    for i,row in enumerate(data['cases']):
        arms=row['arms']
        if [r['candidate']for r in arms]!=[False,True,True,False]or row['reference_accumulation']!='F64'or not row['finite_reference_and_canary_passed']:
            raise ValueError('Complete original-precision ABBA observations required')
        for arm in arms:
            times=arm['samples_us']
            if len(times)!=8 or any(type(x)not in(int,float)or not math.isfinite(x)or x<=0 for x in times)or abs(statistics.mean(times)-arm['mean_us'])>1e-6:
                raise ValueError('Eight actual fence-inclusive samples are required in every arm')
        pairs=[(arms[0],arms[1]),(arms[3],arms[2])];bounds=[interval(a['samples_us'],b['samples_us'],6700+3*i+j)for j,(a,b)in enumerate(pairs)]
        estimates=[a['mean_us']/b['mean_us']for a,b in pairs]
        win=all(x>1 for x in estimates)and all(low>1 for low,high in bounds)
        rows.append(dict(candidate=row['candidate'],width=row['width'],reverse_order_ratios=estimates,
            reverse_order_95pct_bootstrap_intervals=bounds,balanced_ratio=(arms[0]['mean_us']+arms[3]['mean_us'])/(arms[1]['mean_us']+arms[2]['mean_us']),
            status='fixture_gain_requires_actual_model_qualification'if win else'tested_no_reproducible_gain',
            numerical_and_canary_passed=True,maximum_absolute_error=row['maximum_absolute_error'],
            model_integration_required=win,retest_unchanged_variant_required=False))
    return dict(schema='ps5-qwen-portable-kernel-review-v1',cases=rows,all_fixture_comparisons_complete=True,
        speed_scope='Fence-inclusive synthetic graph execution; preparation and packing are outside inference timing',
        adoption_rule='Both temporal directions must improve and both 95-percent bootstrap lower bounds must exceed one',
        qualified_fixture_winners=[dict(candidate=r['candidate'],width=r['width'])for r in rows if r['model_integration_required']],
        driver_checkpoint_overhead_included=True,quantization=False,learned_host_inference=False,CI_runs=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=review(json.loads(a.native.read_text()));a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(all_nine_comparisons_complete=True,fixture_winners=result['qualified_fixture_winners'],completed_no_gain_variants=sum(not r['model_integration_required']for r in result['cases']))))
if __name__=='__main__':main()
