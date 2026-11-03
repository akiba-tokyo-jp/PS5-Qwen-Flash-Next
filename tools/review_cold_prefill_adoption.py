#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the completed cold P1 timing, full rows and bounded first-row diagnostic."""
import argparse
import json
from pathlib import Path
import re
from build_performance_quantizer import record
from start_success_route import load,need,save

PATTERN=rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})'


def exact(row):
    need(record(row['path'])==row,'An existing completed P1 evidence file changed')
    return load(row['path'])


def numeric_case(path):
    c=load(path);need(c['all_intended_events_exercised'],'Every declared numerical row must have completed')
    plan,closed,terminal=map(exact,(c['case_plan'],c['close'],c['native_terminal']))
    need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and terminal['completed'] and terminal['device_ledger_live_bytes']==0 and
         terminal['all_model_source_device_owners_positively_retired'],'Positive whole-row owner retirement and ordinary exit required')
    root=Path(c['case_plan']['path']).parent;journal=root/'native-stages.private.log'
    rows=[(int(a),int(b),int(n),h.decode()) for a,b,n,h in re.findall(PATTERN,journal.read_bytes())]
    need([(a,b,n) for a,b,n,_ in rows]==[(a,b,248320) for a in range(1,4) for b in range(1,24)],
         'Every one of the original 69 full-vocabulary rows is required')
    routes=[];evidence=[record(path),c['case_plan'],c['close'],c['native_terminal'],record(journal)]
    for i in range(3):
        file=root/f'native-arm{i}.routes.private.bin';r=load(file)
        need(r['complete'] and not r['capture_failed'] and r['sidecar_written_after_model_and_source_retirement'],
             'Complete ordered native routes are required')
        routes.append(r['records']);evidence.append(record(file))
    need(all(r['full_F32_finite'] and r['counting_quality_passed'] and r['request_reset_completed'] and
             r['token_ledger_closed_before_request_result'] for r in terminal['requests']),
         'Actual finite counting, reset and durable completion are required')
    return c,terminal,rows,routes,evidence


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('analysis','control-case','candidate-case','diagnostic','diagnostic-close','capacity','out'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();rates=load(a.analysis)
    need(rates['completed'] and rates['scope']=='P1-cold' and rates['native_requests']==12 and
         all(rates[k] for k in ('all_ordinary_closes_and_exact_restores','all_actual_native_token_bytes_exact',
             'all_actual_ordered_routes_exact','all_source_demand_equal','all_completed_durable_token_payloads_exact',
             'all_counting_and_finite_F32_checks_passed')) and
         all(r['decode_tokens_per_second']['both_pairs_exceed_control_spread'] for r in rates['groups'][:2]),
         'The completed original-metric cold and retained paired gains are required')
    control,ct,cr,ctr,ce=numeric_case(a.control_case);candidate,bt,br,btr,be=numeric_case(a.candidate_case)
    different=[dict(request=x[0],row=x[1],control_sha256=x[3],candidate_sha256=y[3]) for x,y in zip(cr,br) if x!=y]
    need([(x['request'],x['row']) for x in different]==[(1,1)] and ctr==btr and
         all(x['token_ids']==y['token_ids'] and x['output_bytes']==y['output_bytes'] for x,y in zip(ct['requests'],bt['requests'])),
         'Only the disclosed first cold row may differ; complete tokens and routes must agree')
    diagnostic_rows=a.diagnostic/'case/completed-first-rows';first=load(diagnostic_rows/'arm0.private.json');second=load(diagnostic_rows/'arm1.private.json')
    journal=a.diagnostic/'case/native-stages.private.log';dr=re.findall(PATTERN,journal.read_bytes())
    need([(int(x),int(y),int(n),h.decode()) for x,y,n,h in dr]==[(1,1,248320,br[0][3]),(2,1,248320,cr[0][3])] and
         second['full_F32_logit_rows_compared']==1 and first['request_reset_completed'] and second['request_reset_completed'] and
         first['full_F32_finite'] and second['full_F32_finite'] and second['maximum_absolute_logit_error']==0.1812725067138672,
         'The two completed diagnostic rows must reproduce the exact differing and original hashes')
    close,capacity=load(a.diagnostic_close),load(a.capacity)
    need(close['completed'] and close['ordinary_exit_observed'] and close['current_seven_restored_and_native_hashed'] and
         close['target_request_operations']==2 and close['last_active_epoch_positive_checkpoint'] and
         capacity['completed'] and capacity['native_passed'] and capacity['ordinary_exit_observed'] and
         capacity['current_seven_restored_and_native_hashed'],'Positive diagnostic close and original capacity readmission required')
    sequence=exact(rates['evidence'][0]);timed_package=exact(sequence['cases'][1]['package'])
    numerical_package=exact(candidate['package']);tp=exact(timed_package['effective_application_policy']['profile'])
    np=exact(numerical_package['effective_application_policy']['profile'])
    need(tp['kind']==np['kind']=='P1-cold-prefill' and tp['P1_arm']==np['P1_arm']=='candidate' and
         tp['entry_artifact']==np['entry_artifact'] and tp['P1_refinement']==np['P1_refinement'],
         'The actual same normal-UI entry must have passed the separate numerical and timing cohorts')
    save(a.out,dict(completed=True,scope='P1-cold-adoption-review',performance=record(a.analysis),
        measured_package=sequence['cases'][1]['package'],refinement=tp['P1_refinement'],native_cases=2,
        matching_F32_rows=68,full_F32_rows_per_case=69,matched_whole_vocabulary_columns=248320,differing_rows=different,
        first_row_maximum_absolute_error_against_original=second['maximum_absolute_logit_error'],
        tokens_and_output_bytes_exact=True,ordered_routes_exact_per_request=[True]*3,
        cold_and_retained_decode_gains_beyond_AA=True,exact_prefix_speed_improvement_established=False,
        general_prompt_quality_qualified=False,all_boundary_states_qualified=False,production_adopted=False,
        numerical_evidence=ce+be+[record(journal),record(diagnostic_rows/'arm0.private.json'),record(diagnostic_rows/'arm1.private.json'),
            record(a.diagnostic_close),record(a.capacity)],PS5_operations=0,completed_native_work_replayed=0))
    print(json.dumps(dict(completed=True,matching_F32_rows=68,first_row_maximum_absolute_error=second['maximum_absolute_logit_error'],PS5_operations=0)))


if __name__=='__main__':main()
