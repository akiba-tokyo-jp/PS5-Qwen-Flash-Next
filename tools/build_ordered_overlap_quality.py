#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Charge a separate warmup pair before four ordered-overlap input pairs."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from finite_route_capacity import bind_route_capacity
original_link=quality.link

def paired_link(parent,out,variants,inputs):
    prior=json.loads(Path(parent).read_text());command,text=variants['entry']
    for original in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
        old=dict(original,maximum_requests=8,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True)
        text=once(text,literal(old),literal(dict(old,maximum_requests=10)))
    text=once(text,'const unsigned request_count=8;','const unsigned request_count=10;')
    text=bind_route_capacity(text,10)
    text=once(text,'const unsigned task=ordinal/2;','const unsigned task=ordinal<2?0:ordinal/2-1;')
    text='extern "C" void qwen_app_overlap_select(bool);\n'+text
    text=once(text,'            const auto current_hits_before=qwen_app_current_bundle_hits();',
        '            const bool overlap_candidate=ordinal>=2&&((task%2)?!repeat:repeat);qwen_app_overlap_select(overlap_candidate);\n            const auto current_hits_before=qwen_app_current_bundle_hits();')
    text=once(text,'            row["quality_task"]=task;','            row["overlap_candidate"]=overlap_candidate;row["warmup_pair"]=ordinal<2;\n            row["quality_task"]=task;')
    return original_link(parent,out,dict(entry=(command,text)),[*inputs,Path(__file__),Path(__file__).with_name('finite_route_capacity.py')])

def main():
    require('--only-task'not in sys.argv,'Four fixed tasks and separate warmup pair required');quality.link=paired_link;quality.main();out=Path(sys.argv[sys.argv.index('--out')+1]);path=out/'receipt.private.json';r=json.loads(path.read_text())
    for key in ('normal_performance','output_Q8_normal','all_Q2_optimized_monitor','routing_sharing','routing_winners_normal','memory_quality_cohort'):
        for name in ('scope','model_scope','probation_scope'):
            if name in r[key]and isinstance(r[key][name],dict)and r[key][name].get('maximum_requests')==8:r[key][name]['maximum_requests']=10
    r['expert_q2_model']['scope']['maximum_requests']=10;r['memory_quality_cohort']['requests']=10;r['memory_quality_cohort']['independent_pairs']=5
    r['cold_request']['actual_sources']['entry']=r['memory_quality_cohort']['actual_sources']['entry'];r['cold_request']['commands']['entry']=r['memory_quality_cohort']['commands']['entry']
    r['overlap_quality']=dict(requests=10,warmup_requests=2,fixed_tasks=4,timed_requests=8,order='control/candidate then candidate/control alternating by task',empty_cache_each_request=True,prefix_reuse=False,causal_speculation=False,full_F32_and_ordered_routes_equal_required=True,live_input_or_output_alias_refusal=True,graph_mode_epoch_bound=True,graph_metadata_restored_only_after_positive_completion=True,original_workspace_and_physical_caps=True,production_adopted=False)
    write_json(path,r);write_json(out/'core-safety.private.json',dict(completed=True,kind='ordered_overlap_warmup_and_four_pairs',driver_and_original_reserves_unchanged=True,dependent_or_aliased_work_refused=True,positive_completion_required=True,finite_requests=10,explicit_warmup=2,candidate=record(path),PS5_operations=0,CI_runs=0))
    print('Ten requests: excluded control warmup pair and four exact-F32/routes ordered-overlap input pairs.')

if __name__=='__main__':main()
