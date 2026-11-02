#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare all existing full-vocabulary rows from positively closed native cases."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from start_success_route import load,need,save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sequence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();sequence=load(args.sequence)
    need(sequence['completed'] and sequence['scope']=='F32' and sequence['all_ordinary_closes_and_exact_restores'],
         'A completed closed numerical qualification sequence required')
    need(2<=len(sequence['cases'])<=4,'At least two completed programs are required for a matched comparison')
    evidence=[record(args.sequence)];cases=[]
    for case in sequence['cases']:
        need(case['all_intended_events_exercised'],'Every original completed row must be observed')
        for key in ('case_plan','close','native_terminal'):need(record(case[key]['path'])==case[key],'Native evidence changed')
        closed=load(case['close']['path']);terminal=load(case['native_terminal']['path'])
        need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
             not closed['unknown_completion'] and terminal['completed'] and terminal['device_ledger_live_bytes']==0 and
             terminal['all_model_source_device_owners_positively_retired'],'Positive native completion and close required')
        root=Path(case['case_plan']['path']).parent;journal=root/'native-stages.private.log'
        rows=[(int(a),int(b),int(c),digest.decode()) for a,b,c,digest in re.findall(
            rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})',journal.read_bytes())]
        need([(a,b,c) for a,b,c,_ in rows]==[(a,b,248320) for a in range(1,4) for b in range(1,24)],'All 69 ordered full rows required')
        routes=[]
        for ordinal in range(3):
            path=root/('native-arm'+str(ordinal)+'.routes.private.bin');trace=load(path)
            need(trace['complete'] and not trace['capture_failed'] and trace['sidecar_written_after_model_and_source_retirement'],
                 'Complete actual ordered routes required');routes.append(trace['records']);evidence.append(record(path))
        need(all(r['full_F32_finite'] and r['counting_quality_passed'] and r['request_reset_completed'] for r in terminal['requests']),
             'Finite F32, counting quality and complete state reset required')
        cases.append(dict(case=case['case'],rows=rows,routes=routes,
            tokens=[r['token_ids'] for r in terminal['requests']],bytes=[r['output_bytes'] for r in terminal['requests']]))
        evidence.extend((case['close'],case['native_terminal'],record(journal)))
    reference=cases[0];comparisons=[]
    for case in cases[1:]:
        comparisons.append(dict(control=reference['case'],candidate=case['case'],
            all_69_full_F32_rows_SHA256_exact=case['rows']==reference['rows'],
            ordered_routes_exact=case['routes']==reference['routes'],
            tokens_and_output_bytes_exact=case['tokens']==reference['tokens'] and case['bytes']==reference['bytes']))
    qualified=all(all(r[k] for k in ('all_69_full_F32_rows_SHA256_exact','ordered_routes_exact','tokens_and_output_bytes_exact')) for r in comparisons)
    report=dict(completed=True,native_cases=len(cases),comparisons=comparisons,
        matched_whole_vocabulary_columns=248320,full_F32_rows_per_case=69,bytes_hashed_per_case=69*248320*4,
        whole_F32_bytes_routes_tokens_exact=qualified,all_ordinary_closes_and_exact_restores=True,
        performance_timings_usable=False,unobserved_boundary_states_qualified=False,evidence=evidence,PS5_operations=0)
    save(args.out,report);print(json.dumps({k:v for k,v in report.items() if k!='evidence'}))


if __name__=='__main__':main()
