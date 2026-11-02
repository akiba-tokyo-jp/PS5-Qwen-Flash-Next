#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen causal per-file stride variants on the qualified original read stream."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path

from build_performance_quantizer import record
from finalize_model_pread_observation import decode
from start_success_route import load,need,save


def simulate(rows,maximum,retain,ttl):
    groups=defaultdict(list)
    for row in rows:groups[row['thread']].append(row)
    total=Counter()
    for events in groups.values():
        history={};pending=None;used=0
        for seen,row in enumerate(sorted(events,key=lambda item:item['begin'])):
            valid=(row['candidate'] and row['identity_equal'] and row['returned']==row['bytes'] and
                row['identity'][2]>=64<<20 and row['offset']+row['bytes']<=row['identity'][2])
            key=(row['identity'],row['flags'],row['bytes'],row['offset'])
            if pending:
                if valid and pending[0]==key:
                    total['hits']+=1;total['hit_bytes']+=row['bytes'];pending=None
                elif not retain or seen-pending[1]>=ttl:total['unused']+=1;pending=None
            if not valid:continue
            previous=history.get(key[:3])
            if previous is not None and used<maximum and not pending and row['offset']>previous:
                prediction=row['offset']+(row['offset']-previous)
                if prediction+row['bytes']<=row['identity'][2]:
                    pending=((*key[:3],prediction),seen);used+=1
                    total['predictions']+=1;total['predicted_bytes']+=row['bytes']
            history[key[:3]]=row['offset']
        if pending:total['unused']+=1
    return dict(maximum_predictions_per_original_producer=maximum,retain_across_unrelated_calls=retain,
        maximum_retention_calls=ttl,**dict(total))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace-proof',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();proof=load(a.trace_proof)
    need(proof['completed'] and proof['all23_full_F32_rows_and_actual_routes_exact'] and proof['all_original_calls_preserved_without_retries'],
         'A positively completed exact original model trace is required')
    for key in ('raw','native_audit','case'):need(record(proof[key]['path'])==proof[key],'A qualified trace input changed')
    case=load(proof['case']['path']);terminal=load(case['terminal']['path']);audit=load(proof['native_audit']['path'])
    rows=decode(Path(proof['raw']['path']).read_bytes(),audit,{key:terminal[key] for key in ('run_id','pid','candidate_SELF_sha256','model_receipt_sha256')})
    profiles=[simulate(rows,maximum,retain,32) for maximum in (6,32,128) for retain in (False,True)]
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'result.private.json',dict(completed=True,trace_proof=record(a.trace_proof),profiles=profiles,
        predictions_use_only_already_completed_original_reads=True,every_original_call_including_unsupported_reads_preserved=True,
        future_calls_used_only_to_score_already_chosen_predictions=True,source_history_preserved_across_unrelated_calls=True,
        one_hypothetical_pending_buffer_per_original_producer=True,source_admission_and_contention_costs_not_simulated=True,
        hypothetical_completion_is_optimistic=True,actual_speculative_IO_submitted=0,PS5_operations=0,
        real_model_prefetch_integration_or_speed_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,profiles=len(profiles),PS5_operations=0,production_adopted=False)))


if __name__=='__main__':main()
