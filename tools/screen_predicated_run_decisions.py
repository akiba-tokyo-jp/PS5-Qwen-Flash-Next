#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Count hypothetical fixed-window decisions from counter-exact cached-layer runs."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need,save


def count(flags,window):
    position=queries=fallback=covered=recorded=0
    while position<len(flags):
        # A fixed window is chosen before examining its completed outcomes.
        width=min(window,len(flags)-position);queries+=1;recorded+=width
        completed=flags[position:position+width]
        first_miss=next((i for i,hit in enumerate(completed) if not hit),width)
        covered+=first_miss;position+=first_miss
        if first_miss<width:
            # This assumes every later state write was predicated off and an
            # exact ordinary one-layer resume exists. Neither is implemented
            # or qualified by this offline counter.
            fallback+=1;position+=1
    need(covered+fallback==len(flags),'Each original layer must be accounted exactly once')
    return dict(completed_window_decisions=queries,ordinary_miss_resumes=fallback,all_hit_layers=covered,
        hypothetical_decisions_and_resumes=queries+fallback,recorded_layer_positions=recorded,
        predicated_off_positions=recorded-len(flags))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--screen',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    proof=load(a.screen);need(proof['completed'] and proof['actual_three_request_native_cache_counters_reproduced'] and
        not proof['actual_GPU_all_hit_continuation_implemented'],'Exact three-request counter replay is required')
    source=a.screen.parent/'replayed.private.json';requests=load(source);results=[]
    for request in requests:
        processes=[request['rows'][i:i+48] for i in range(0,len(request['rows']),48)];decoded=[group for group in processes if group[0]['tokens']<=2]
        need(all(len(group)==48 and [row['layer'] for row in group]==list(range(48)) for group in decoded),'Ordered complete decode processes required')
        variants=[]
        for window in (1,2,4,8,16,32):
            rows=[count([row['all_selected_cached'] for row in group],window) for group in decoded]
            totals={key:sum(row[key] for row in rows) for key in rows[0]};totals.update(window_layers=window,original_layer_decisions=48*len(rows))
            variants.append(totals)
        results.append(dict(ordinal=request['ordinal'],variants=variants))
    a.out.mkdir(parents=True,exist_ok=False);save(a.out/'result.private.json',dict(completed=True,screen=record(a.screen),replayed=record(source),source=record(__file__),requests=results,
        fixed_windows_chosen_before_outcomes=True,future_hit_flags_used_only_to_grade_completed_hypothetical_windows=True,
        requires_exact_predication_of_all_state_writes=True,requires_bounded_exact_hidden_state_and_miss_resume=True,
        no_actual_latency_contention_or_GPU_execution_simulated=True,whole_speed_qualified=False,
        full_GPU_continuation_implemented=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,requests=results,whole_speed_qualified=False,PS5_operations=0)))


if __name__=='__main__':main()
