#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One model/driver lifetime for prediction, verification and prefix cohorts."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def generate(kind,source,tail,flags):
    if kind!='combined' or not flags.get('phase_local_model') or not flags.get('postloader_integrity'):
        raise ValueError('Exact combined and postloader model scope required')
    from build_resident_comparison import specialize
    additional_path=ROOT/'native/app/resident_additional_tail.inc'
    additional=additional_path.read_text()
    begin=additional.index('        const bool prefix_comparison=')
    retirement='        qwen_app_complete_predictive_expert();qwen_native_driver_begin();'
    end=additional.index(retirement)
    prefix=additional[begin:end].replace('RESIDENT_PREFIX_COMPARISON','true')
    prefix=prefix.replace('startup.admission_report+".arm"','startup.admission_report+".prefix.arm"')
    prefix=prefix.replace('run+"-"+std::to_string(ordinal)','run+"-prefix-"+std::to_string(ordinal)')
    prefix+='        retained_prefix_routes=std::move(routes);retained_prefix_results=std::move(completed);\n'
    frontier='        qwen_app_complete_predictive_expert();qwen_native_driver_begin();'
    if tail.count(frontier)!=1:raise ValueError('Unique completed prediction/verification cohort frontier required')
    # The same loaded model survives both finite cohorts. Keep their route
    # evidence until the original common model/source/device retirement.
    extra='''        std::array<CompletedRouteEvidence,9> retained_prefix_routes;
        Json retained_prefix_results;
        {
'''+prefix+'        }\n'
    tail=tail.replace(frontier,extra+frontier)
    terminal='        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);'
    if tail.count(terminal)!=1:raise ValueError('Unique terminal after common ownership retirement required')
    sidecars='''        for(unsigned i=0;i<retained_prefix_routes.size();++i){
            auto r=completed_route_report(retained_prefix_routes[i]);
            r.update({{"pid",getpid()},{"run_id",run},{"ordinal",i},{"cache_reset_before_request",!i||i%2!=0},
                {"sidecar_written_after_model_and_source_retirement",true},{"JSON_created_after_model_and_source_retirement",true}});
            write_fresh_report(startup.admission_report+".prefix.arm"+std::to_string(i)+".routes",r);
        }
'''
    tail=tail.replace(terminal,sidecars+terminal)
    tail=tail.replace('ps5-qwen-resident-comparison-result-v1','ps5-qwen-resident-combined-result-v1')
    tail=tail.replace('{"completed",true},{"requests",completed},{"model_loads",1}',
        '{"completed",true},{"requests",completed},{"prefix_requests",retained_prefix_results},{"model_loads",1},{"total_requests",19}')
    text=specialize(source,tail,**flags)
    text='#include "resident_combined_policy.h"\n'+text.replace('qwen_app::require_resident_comparison_policy(policy);',
        'qwen_app::require_resident_combined_policy(policy);')
    return text,[Path(__file__),additional_path,ROOT/'native/app/resident_combined_policy.h']
