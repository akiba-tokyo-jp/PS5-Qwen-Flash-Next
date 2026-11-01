#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Dispose the completed model comparison using whole time and exact outputs."""
import argparse
import json
import statistics
from pathlib import Path
from expert_q4 import record, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    native = json.loads((args.case / 'native-model-terminal.private.json').read_text())
    closed = json.loads((args.case / 'restored-complete.private.json').read_text())
    quality = json.loads((args.case / 'candidate-contents-decision.private.json').read_text())
    assert native['completed'] and native['all_model_source_device_owners_positively_retired']
    assert native['device_ledger_live_bytes'] == 0 and closed['completed'] and not closed['unknown_completion']
    assert len(native['requests']) == 14 and native['full_F32_continuation_and_routes_passed']
    rows = []
    for request in native['requests']:
        delta = request['scheduler_slot_map_delta']
        assert len(delta) == 10 and delta[0] == delta[1] + delta[2] > 0
        assert delta[4] == 2048 * delta[1] and delta[5] == 2048 * delta[2]
        assert delta[8] == delta[9] == delta[0]
        assert request['scheduler_slot_map_reuse_enabled'] == bool(request['candidate_arm'])
        assert delta[2] > 0 if request['candidate_arm'] else delta[2] == 0
        assert request['full_F32_finite'] and request['request_reset_completed']
        rows.append(dict(ordinal=request['ordinal'], candidate=bool(request['candidate_arm']),
                         metrics=request['metrics'], map_delta=delta))
    control = [native['requests'][i] for i in (3, 9)]
    candidate = [native['requests'][i] for i in (5, 7)]
    exact = all(r['maximum_absolute_logit_error'] == 0 and r['same_tokens_as_independent'] and
                r['cross_control_ordered_routes_exact'] and r['metrics']['generated_tokens'] == 22
                for r in control + candidate)
    source_keys = ('source_bytes', 'source_physical_read_bytes', 'source_physical_read_calls')
    same_source = all(len({r['completed_performance']['delta'][key] for r in control + candidate}) == 1
                      for key in source_keys)
    aa = abs(control[1]['metrics']['total_ms'] - control[0]['metrics']['total_ms'])
    savings = [control[i]['metrics']['total_ms'] - candidate[i]['metrics']['total_ms'] for i in range(2)]
    decode = [control[i]['metrics']['decode_ms'] - candidate[i]['metrics']['decode_ms'] for i in range(2)]
    useful = exact and same_source and quality['all_contents_passed'] and min(savings) > aa and min(decode) > 0
    report = dict(schema='ps5-qwen-scheduler-slot-map-analysis-v1', completed=True,
        disposition='Internal comparison qualifies; original normal comparison required' if useful else 'Tested; no qualified production benefit',
        rows=rows, all_full_F32_routes_tokens_exact=exact, identical_source_demand=same_source,
        fixed_semantic_tasks_passed=quality['all_contents_passed'], control_AA_whole_spread_ms=aa,
        paired_whole_time_savings_ms=savings, paired_decode_time_savings_ms=decode,
        retained_decode_rates_control=[r['metrics']['decode_tokens_per_second'] for r in control],
        retained_decode_rates_candidate=[r['metrics']['decode_tokens_per_second'] for r in candidate],
        mean_whole_time_reduction_percent=100 * (1 - statistics.mean(r['metrics']['total_ms'] for r in candidate) /
            statistics.mean(r['metrics']['total_ms'] for r in control)), internal_comparison_qualifies=useful,
        original_normal_external_qualification_required=useful, production_adopted=False,
        CPU_heap_peak_bytes=native['CPU_heap_peak_bytes'], device_ledger_peak_bytes=native['device_ledger_peak_bytes'],
        evidence=[record(args.case / 'native-model-terminal.private.json'), record(args.case / 'restored-complete.private.json')],
        PS5_operations=0, CI_runs=0)
    write_json(args.out, report)
    print(json.dumps({key: report[key] for key in ('completed', 'disposition', 'all_full_F32_routes_tokens_exact',
        'identical_source_demand', 'fixed_semantic_tasks_passed', 'paired_whole_time_savings_ms',
        'paired_decode_time_savings_ms', 'control_AA_whole_spread_ms', 'retained_decode_rates_control',
        'retained_decode_rates_candidate', 'mean_whole_time_reduction_percent')}))

if __name__ == '__main__': main()
