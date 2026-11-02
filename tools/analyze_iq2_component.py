#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze returned IQ2 ABBA component timings without claiming whole-model benefit."""
import argparse
import math
from pathlib import Path
import statistics

from build_performance_quantizer import record
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();completed=load(a.native)
    need(completed['completed'] and completed['component_timing_window_free_of_host_PS5_requests'],
         'One closed component inside its calibrated host-quiet window is required')
    for key in ('closure','component'):need(record(completed[key]['path'])==completed[key],'Native completion evidence changed')
    closed=load(completed['closure']['path']);component=load(completed['component']['path'])
    need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'],'Positive ordinary restoration required')
    rows=[];all_valid=component['all_outputs_reference_valid']
    for case in component['cases']:
        row={k:case[k] for k in ('layer','width','selected_Experts','unique_original_Experts','supported',
            'all_outputs_and_canaries_passed','maximum_absolute_GPU_reference_error','mismatches','GPU_graphs')}
        arms=case['arms'];row['timings_eligible']=case['all_outputs_and_canaries_passed'] and len(arms)==4
        row['metrics']={}
        if row['timings_eligible']:
            need([x['format'] for x in arms]==['Q2_K','IQ2_XXS','IQ2_XXS','Q2_K'] and all(len(x['samples'])==2 for x in arms),
                 'Exact two-sample ABBA required')
            names=('delivery_us','compute_us','delivery_and_compute_us')
            if component.get('fence_timings_exclude_separately_recorded_completion_guard'):
                names+=('pread_us','copy_fence_us','compute_fence_us','delivery_guard_us','compute_guard_us')
            for name in names:
                values=[statistics.mean(s[name] for s in arm['samples']) for arm in arms]
                need(all(math.isfinite(x) and x>=0 for x in values),'Invalid native interval')
                control=[values[0],values[3]];candidate=[values[1],values[2]]
                savings=[control[i]-candidate[i] for i in range(2)];spread=abs(control[1]-control[0])
                row['metrics'][name]=dict(control=control,candidate=candidate,paired_savings_us=savings,
                    control_AA_spread_us=spread,both_pairs_exceed_control_spread=min(savings)>spread,
                    mean_reduction_percent=100*(1-statistics.mean(candidate)/statistics.mean(control)) if sum(control)>0 else None)
        rows.append(row)
    separated=bool(component.get('fence_timings_exclude_separately_recorded_completion_guard'))
    result=dict(completed=True,native=record(a.native),component=completed['component'],closure=completed['closure'],cases=rows,
        GPU_graphs=component['GPU_graphs'],all_reference_and_canary_checks_passed=all_valid,
        delivery_and_compute_include_completion_and_journal_guards=True,separate_fence_intervals_available=separated,
        model_loads=0,synthetic_operator_inputs=True,real_calibrated_weight_matrices=9,
        component_not_model_speed=True,full_model_quality_or_speed_qualified=False,PS5_operations=0,production_adopted=False)
    save(a.out,result)
    for row in rows:
        key='compute_fence_us' if separated else 'compute_us'
        print(dict(layer=row['layer'],width=row['width'],numerics=row['all_outputs_and_canaries_passed'],
            metric=key,comparison=row['metrics'].get(key)))


if __name__=='__main__':main()
