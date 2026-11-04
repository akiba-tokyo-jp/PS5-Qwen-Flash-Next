#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare a positively closed ABBA, preserving actual scope and quality limits."""
import argparse
import json
from pathlib import Path
import statistics
import re

from build_performance_quantizer import record
from start_success_route import load,need,save


def authenticated(row):
    need(record(row['path'])==row,'Completed sequence evidence changed')
    return load(row['path'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sequence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();sequence=load(args.sequence)
    need(sequence['completed'] and sequence['all_ordinary_closes_and_exact_restores'] and len(sequence['cases'])==4,
         'One positively closed four-case sequence required')
    terminals=[];roots=[];events=[];evidence=[record(args.sequence)]
    for row in sequence['cases']:
        need(row['all_intended_events_exercised'],'Every declared phase must actually execute')
        closed=authenticated(row['close']);terminal=authenticated(row['native_terminal'])
        need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
             not closed['unknown_completion'] and terminal['completed'] and terminal['device_ledger_live_bytes']==0 and
             terminal['all_model_source_device_owners_positively_retired'] and terminal['full_F32_continuation_and_routes_passed'],
             'Positive ordinary restore and native resource/state outcomes required')
        need(len(terminal['requests'])==3,'All three cache conditions are required')
        terminals.append(terminal);roots.append(Path(row['case_plan']['path']).parent);events.append(row['scope_events'][0][0])
        evidence.extend((row['native_terminal'],row['close']))
    need(events==[0,1,1,0],'Declared control/candidate ABBA must match actually exercised native modes')
    f32_pattern=re.compile(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})')
    f32_rows=[f32_pattern.findall((root/'native-stages.private.log').read_bytes()) for root in roots]
    f32_exact=all(len(rows)==69 and rows==f32_rows[0] and all(r[2]==b'248320' for r in rows) for rows in f32_rows)
    groups=[];all_tokens=True;all_routes=True;all_sources=True;all_quality=True;all_ledger=True
    source_keys=('source_bytes','source_physical_read_bytes','source_physical_read_calls')
    for ordinal in range(3):
        requests=[t['requests'][ordinal] for t in terminals];reference=requests[0]
        tokens=all(r['token_ids']==reference['token_ids'] and r['output_bytes']==reference['output_bytes'] for r in requests)
        quality=all(r['counting_quality_passed'] and r['full_F32_finite'] and r['request_reset_completed'] for r in requests)
        traces=[];ledgers=[]
        for root,request in zip(roots,requests):
            trace_path=root/('native-arm'+str(ordinal)+'.routes.private.bin');trace=load(trace_path)
            need(trace['complete'] and not trace['capture_failed'] and trace['all_existing_downloads_and_synchronizations_returned'] and
                 trace['sidecar_written_after_model_and_source_retirement'] and trace['cache_slots']==3712,
                 'Complete actual ordered route evidence required')
            traces.append(trace['records']);evidence.append(record(trace_path))
            ledger_path=root/('native-arm'+str(ordinal)+'.token-ledger.private.bin')
            ledger=[json.loads(line) for line in ledger_path.read_text(encoding='utf-8').splitlines()]
            need(len(ledger)==request['metrics']['generated_tokens']==22 and
                 [r['token_id'] for r in ledger]==request['token_ids'] and
                 [b for r in ledger for b in r['piece_bytes']]==request['output_bytes'] and
                 [r['generated_tokens'] for r in ledger]==list(range(1,23)),
                 'Every completed durable token payload must match the actual native output')
            ledgers.append([{k:r[k] for k in ('token_id','piece_bytes','generated_tokens')} for r in ledger]);evidence.append(record(ledger_path))
        routes=all(t==traces[0] for t in traces);ledger_equal=all(t==ledgers[0] for t in ledgers)
        source_equal=all(len({r['completed_performance']['delta'][k] for r in requests})==1 for k in source_keys)
        complete_metrics=[]
        for request in requests:
            nested=request['CPU_nested_calls_inclusive_exclusive_ns']
            # The pinned Cpu ABI has 14 triples and request_run is category13.
            # This native steady-clock span ends after TokenLedger::close().
            # The legacy result.metrics.total_ms is captured before that close.
            need(len(nested)==42 and nested[39]==1 and nested[40]>=nested[41]>=0 and
                 nested[40]/1e6>=request['metrics']['total_ms'], 'One complete post-close native request span required')
            values=dict(request['metrics'],complete_request_span_ms=nested[40]/1e6)
            complete_metrics.append(values)
        A=[complete_metrics[i] for i in (0,3)];B=[complete_metrics[i] for i in (1,2)]
        metrics={}
        for name in ('prefill_ms','TTFT_ms','total_ms','decode_ms','complete_request_span_ms'):
            savings=[A[i][name]-B[i][name] for i in range(2)]
            spread=abs(A[1][name]-A[0][name])
            metrics[name]=dict(control=[r[name] for r in A],candidate=[r[name] for r in B],
                paired_savings_ms=savings,control_AA_spread_ms=spread,
                both_pairs_exceed_control_spread=min(savings)>spread,
                mean_reduction_percent=100*(1-statistics.mean(r[name] for r in B)/statistics.mean(r[name] for r in A)))
        rates=[]
        for r in complete_metrics:
            calculated=(r['generated_tokens']-1)*1000/r['decode_ms']
            need(abs(calculated-r['decode_tokens_per_second'])<=1e-9,'Original decode tok/s formula changed')
            rates.append(calculated)
        control_rates=[rates[i] for i in (0,3)];candidate_rates=[rates[i] for i in (1,2)]
        aa=abs(control_rates[1]-control_rates[0]);gains=[candidate_rates[i]-control_rates[i] for i in range(2)]
        groups.append(dict(condition=reference['arm'],tokens_and_bytes_exact=tokens,ordered_routes_exact=routes,
            source_demand_equal=source_equal,all_counting_and_finite_F32_checks_passed=quality,
            durable_token_payloads_exact=ledger_equal,metrics=metrics,
            decode_tokens_per_second=dict(control=control_rates,candidate=candidate_rates,
                control_mean=statistics.mean(control_rates),candidate_mean=statistics.mean(candidate_rates),
                rate_change_percent=100*(statistics.mean(candidate_rates)/statistics.mean(control_rates)-1),
                control_AA_spread=aa,paired_gains=gains,both_pairs_exceed_control_spread=min(gains)>aa)))
        all_tokens&=tokens;all_routes&=routes;all_sources&=source_equal;all_quality&=quality;all_ledger&=ledger_equal
    report=dict(completed=True,scope=sequence['scope'],cases=[r['case'] for r in sequence['cases']],native_requests=12,
        automatic_retries=0,all_ordinary_closes_and_exact_restores=True,all_actual_native_token_bytes_exact=all_tokens,
        all_actual_ordered_routes_exact=all_routes,all_source_demand_equal=all_sources,
        all_completed_durable_token_payloads_exact=all_ledger,all_counting_and_finite_F32_checks_passed=all_quality,
        groups=groups,retained_prefill_gain_beyond_control_spread=groups[1]['metrics']['prefill_ms']['both_pairs_exceed_control_spread'],
        both_warm_whole_request_gains_beyond_control_spread=all(g['metrics']['complete_request_span_ms']['both_pairs_exceed_control_spread'] for g in groups[1:]),
        final_token_ledger_sync_and_close_included_in_complete_request_span=True,
        primary_metric='(generated_tokens-1)/decode_seconds',
        cross_program_full_F32_row_SHA256_compared=all(len(rows)==69 for rows in f32_rows),
        full_vocabulary_F32_rows_observed_per_case=[len(rows) for rows in f32_rows],all69_full_vocabulary_F32_rows_exact=f32_exact,
        cross_program_full_F32_row_bytes_compared=False,all_boundary_states_qualified=False,
        production_adopted=False,evidence=evidence,PS5_operations=0)
    save(args.out,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('groups','evidence')}))
    for group in groups:
        print(json.dumps(dict(condition=group['condition'],prefill=group['metrics']['prefill_ms'],whole=group['metrics']['complete_request_span_ms'],
                             legacy_pre_close_metrics_total_ms=group['metrics']['total_ms'])))


if __name__=='__main__':main()
