#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare a returned headless model against an immutable completed F32 control."""
import argparse
from pathlib import Path
import re

from build_performance_quantizer import record
from start_success_route import load,need,save


def positive(terminal,closed):
    need(terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and len(terminal['requests'])==3 and
         all(r['counting_quality_passed'] and r['full_F32_finite'] and r['request_reset_completed'] for r in terminal['requests']),
         'All original requests, positive retirement and ordinary restoration are required')


def full_rows(path):
    values=re.findall(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})',path.read_bytes())
    rows=[(int(a),int(b),int(c),h.decode('ascii')) for a,b,c,h in values]
    need([(a,b,c) for a,b,c,_ in rows]==[(a,b,248320) for a in range(1,4) for b in range(1,24)],'All69 ordered full-vocabulary rows required')
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','reference-case-record','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--scope',choices=('P1-tail-eight','G1-fused-full-sort','I1-relative-model-prefetch'),required=True);a=p.parse_args()
    original=load(a.reference_case_record)
    for key in ('case_plan','close','native_terminal'):need(record(original[key]['path'])==original[key],'Original control evidence changed')
    reference=load(original['native_terminal']['path']);reference_close=load(original['close']['path']);positive(reference,reference_close)
    result=load(a.case/'result.private.json')
    for key in ('terminal','closure'):need(record(result[key]['path'])==result[key],'Completed headless evidence changed')
    terminal=load(result['terminal']['path']);closed=load(result['closure']['path']);positive(terminal,closed)
    need(result['completed'] and terminal['kind']==a.scope and not terminal['timings_usable_for_performance'],'Only a numerical qualification run is admitted')
    root=Path(original['case_plan']['path']).parent;left=root/'native-stages.private.log';right=a.case/'case/native-stages.private.log'
    expected=full_rows(left);actual=full_rows(right);differences=[dict(request=x[0],row=x[1],control_sha256=y[3],candidate_sha256=x[3]) for x,y in zip(actual,expected) if x!=y]
    tokens=all(x['token_ids']==y['token_ids'] and x['output_bytes']==y['output_bytes'] for x,y in zip(terminal['requests'],reference['requests']))
    route_equal=[];evidence=[record(a.reference_case_record),record(a.case/'result.private.json'),record(left),record(right)]
    for ordinal in range(3):
        old=root/f'native-arm{ordinal}.routes.private.bin';new=a.case/f'case/headless-observer/native.arm{ordinal}.routes.private.json'
        x,y=load(new),load(old)
        need(all(t['complete'] and not t['capture_failed'] and t['sidecar_written_after_model_and_source_retirement'] for t in (x,y)),
             'Complete returned route sidecars required')
        route_equal.append(x['records']==y['records']);evidence.extend((record(old),record(new)))
    first_error=None
    if differences==[dict(request=1,row=1,control_sha256=expected[0][3],candidate_sha256=actual[0][3])]:
        need(actual[23][3]==expected[0][3],'The existing first-row comparator must bind the original first-row reference')
        first_error=terminal['requests'][1].get('first_row_maximum_absolute_logit_error')
    identical=not differences and tokens and all(route_equal)
    source_prefetch=None
    if a.scope=='I1-relative-model-prefetch':
        from model_relative_prefetch_evidence import review
        source_prefetch=review(terminal,True,allow_aggregate_only=True)
    save(a.out,dict(completed=True,scope=a.scope,whole_F32_bytes_routes_tokens_exact=identical,
        all69_full_vocabulary_F32_rows_SHA256_exact=not differences,matching_F32_rows=69-len(differences),differing_rows=differences,
        first_row_maximum_absolute_error_against_original=first_error,tokens_and_output_bytes_exact=tokens,
        ordered_routes_exact_per_request=route_equal,all_counting_finite_reset_and_retirement_checks=True,
        all_ordinary_closes_and_exact_restores=True,performance_timings_usable=False,broader_prompt_quality_qualified=False,
        full_F32_bytes_compared=False,columns=248320,evidence=evidence,actual_source_prefetch=source_prefetch,PS5_operations=0,production_adopted=False))
    print(dict(completed=True,scope=a.scope,matching_F32_rows=69-len(differences),tokens_exact=tokens,routes_exact=all(route_equal),first_row_error=first_error))


if __name__=='__main__':main()
