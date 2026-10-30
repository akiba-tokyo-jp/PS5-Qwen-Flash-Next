#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify all-bundle delivery with a warmup pair and four exact input pairs."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from finite_route_capacity import bind_route_capacity
original_link=quality.link
request_limit=10


def paired_link(parent,out,variants,inputs):
    prior=json.loads(Path(parent).read_text());command,text=variants['entry']
    require(prior['delivery_followup']['modes']['6']=='parallel_bundles_including_previously_coalesced','Exact all-bundle variant required')
    for original in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
        old=dict(original,maximum_requests=8,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True)
        text=once(text,literal(old),literal(dict(old,maximum_requests=request_limit)))
    text=once(text,'const unsigned request_count=8;',f'const unsigned request_count={request_limit};')
    text=bind_route_capacity(text,request_limit)
    text=once(text,'const unsigned task=ordinal/2;','const unsigned task=ordinal<2||ordinal>=10?0:ordinal/2-1;')
    text='extern "C" void qwen_app_delivery_select(unsigned);\n'+text
    text=once(text,'            const auto current_hits_before=qwen_app_current_bundle_hits();',
        '            const bool bundle_candidate=ordinal>=2&&ordinal<10&&((task%2)?!repeat:repeat);qwen_app_delivery_select(ordinal==11?5:(bundle_candidate?6:0));\n            const auto current_hits_before=qwen_app_current_bundle_hits();')
    text=once(text,'            row["quality_task"]=task;','            row["bundle_candidate"]=bundle_candidate;row["warmup_pair"]=ordinal<2;\n            row["quality_task"]=task;')
    return original_link(parent,out,dict(entry=(command,text)),[*inputs,Path(__file__),Path(__file__).with_name('finite_route_capacity.py')])


def main():
    global request_limit
    if '--numeric-pair'in sys.argv:request_limit=12;sys.argv.remove('--numeric-pair')
    require('--only-task'not in sys.argv,'All four tasks required');quality.link=paired_link;quality.main();out=Path(sys.argv[sys.argv.index('--out')+1]);path=out/'receipt.private.json';r=json.loads(path.read_text())
    for key in ('normal_performance','output_Q8_normal','all_Q2_optimized_monitor','routing_sharing','routing_winners_normal','memory_quality_cohort'):
        for name in ('scope','model_scope','probation_scope'):
            if name in r[key]and isinstance(r[key][name],dict)and r[key][name].get('maximum_requests')==8:r[key][name]['maximum_requests']=request_limit
    r['expert_q2_model']['scope']['maximum_requests']=request_limit;r['memory_quality_cohort']['requests']=request_limit;r['memory_quality_cohort']['independent_pairs']=request_limit//2
    r['cold_request']['actual_sources']['entry']=r['memory_quality_cohort']['actual_sources']['entry'];r['cold_request']['commands']['entry']=r['memory_quality_cohort']['commands']['entry']
    r['bundle_delivery_quality']=dict(requests=request_limit,warmup_requests=2,fixed_tasks=4,timed_bundle_requests=8,additional_numeric_pair=request_limit==12,order='alternating control/candidate',empty_cache_each_request=True,OS_cache_flush_claimed=False,prefix_reuse=False,causal_speculation=False,numeric_memory_candidate_ordinals=[11]if request_limit==12 else [],full_F32_and_routes_exact_required=True,evidence_capacity_bound_to_request_count=True,evidence_access_bounds_checked=True,original_memory_and_completion_guards=True,production_adopted=False)
    write_json(path,r);write_json(out/'core-safety.private.json',dict(completed=True,kind='bundle_delivery_four_pairs',driver_and_original_reserves_unchanged=True,finite_requests=request_limit,source_scratch_bytes=8<<20,additional_GPU_buffers=0,candidate=record(path),PS5_operations=0,CI_runs=0))
    print('All-bundle delivery: separate warmup pair and four empty-cache exact-F32/routes pairs.')


if __name__=='__main__':main()
