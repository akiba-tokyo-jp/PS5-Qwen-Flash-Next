#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare five independent delivery modes in one finite empty-cache cohort."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from finite_route_capacity import bind_route_capacity
original_link=quality.link
remaining=False


def screen_link(parent,out,variants,inputs):
    prior=json.loads(Path(parent).read_text());command,text=variants['entry']
    for original in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
        old=dict(original,maximum_requests=2,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True)
        text=once(text,literal(old),literal(dict(old,maximum_requests=10 if remaining else 12)))
    text=once(text,'const unsigned request_count=2;',f'const unsigned request_count={10 if remaining else 12};')
    text=bind_route_capacity(text,10 if remaining else 12)
    text='extern "C" void qwen_app_delivery_select(unsigned);\n'+text
    text=once(text,'            const auto current_hits_before=qwen_app_current_bundle_hits();',
        '            constexpr unsigned delivery_modes[]={'+('0,0,0,6,0,3,4,0,0,5'if remaining else'0,0,0,1,2,0,0,3,4,0,0,5')+'};qwen_app_delivery_select(delivery_modes[ordinal]);\n            const auto current_hits_before=qwen_app_current_bundle_hits();')
    return original_link(parent,out,dict(entry=(command,text)),[*inputs,Path(__file__),Path(__file__).with_name('finite_route_capacity.py')])


def main():
    global remaining
    if '--remaining'in sys.argv:remaining=True;sys.argv.remove('--remaining')
    require('--only-task'in sys.argv and sys.argv[sys.argv.index('--only-task')+1]=='0','The first screen uses the fixed counting input only')
    quality.link=screen_link;quality.main();out=Path(sys.argv[sys.argv.index('--out')+1]);path=out/'receipt.private.json';r=json.loads(path.read_text())
    for key in ('normal_performance','output_Q8_normal','all_Q2_optimized_monitor','routing_sharing','routing_winners_normal','memory_quality_cohort'):
        for name in ('scope','model_scope','probation_scope'):
            if name in r[key]and isinstance(r[key][name],dict)and r[key][name].get('maximum_requests')==2:r[key][name]['maximum_requests']=10 if remaining else 12
    count=10 if remaining else 12;r['expert_q2_model']['scope']['maximum_requests']=count;r['memory_quality_cohort']['requests']=count;r['memory_quality_cohort']['independent_pairs']=count//2
    r['cold_request']['actual_sources']['entry']=r['memory_quality_cohort']['actual_sources']['entry'];r['cold_request']['commands']['entry']=r['memory_quality_cohort']['commands']['entry']
    r['delivery_screen']=dict(requests=count,modes=[0,0,0,6,0,3,4,0,0,5]if remaining else[0,0,0,1,2,0,0,3,4,0,0,5],fixed_task='counting',empty_cache_each_request=True,prefix_reuse=False,causal_speculation=False,complete_F32_and_ordered_routes_equal_required=True,all_original_physical_kernel_and_owner_guards=True,performance_adoption=False)
    write_json(path,r);write_json(out/'core-safety.private.json',dict(completed=True,kind='finite_independent_delivery_screen',requests=count,driver_unchanged=True,original_memory_identity_and_completion_guards=True,candidate=record(path),PS5_operations=0,CI_runs=0))
    print(f'{count} independent requests compare declared delivery modes; no source prediction or extra GPU buffers.')


if __name__=='__main__':main()
