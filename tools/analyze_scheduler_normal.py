#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile the completed original/candidate normal ABBA without new execution."""
import argparse
import json
import statistics
from pathlib import Path
from expert_q4 import record, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    cases = (59000, 59200, 59400, 59600)
    data = {}; evidence = []
    for case in cases:
        root = args.cache / f'hardware-first-generation-{case}'
        native = json.loads((root / 'native-model-terminal.private.json').read_text())
        closed = json.loads((root / 'restored-complete.private.json').read_text())
        observer = json.loads((root / 'passive-observer/complete.private.json').read_text())
        assert native['completed'] and native['all_model_source_device_owners_positively_retired']
        assert native['device_ledger_live_bytes'] == 0 and closed['completed'] and not closed['unknown_completion']
        assert len(native['requests']) == 3 and observer['completed'] and observer['POSTs'] == 3
        assert len(observer['actual_native_frames']) == 2
        assert all(r['full_F32_finite'] and r['counting_quality_passed'] and r['request_reset_completed'] for r in native['requests'])
        assert all(r['metrics']['generated_tokens'] == 22 and r['metrics']['prompt_tokens'] == 30 for r in native['requests'])
        if case in (59200, 59400):
            assert native['scheduler_slot_map_reuse_enabled'] and native['scheduler_slot_map_counts'][3] > 0
            for request in native['requests']:
                d = request['scheduler_slot_map_delta']
                assert len(d) == 10 and d[0] == d[1] + d[2] == d[8] == d[9] and d[2] > 0
                assert d[4] == 2048 * d[1] and d[5] == 2048 * d[2]
        data[case] = native
        evidence += [record(root / name) for name in ('native-model-terminal.private.json', 'restored-complete.private.json', 'passive-observer/complete.private.json')]
    groups = []
    source_keys = ('source_bytes', 'source_physical_read_bytes', 'source_physical_read_calls')
    for ordinal, label in enumerate(('cold', 'retained', 'prefix')):
        reference = data[59000]['requests'][ordinal]
        routes = json.loads((args.cache / f'hardware-first-generation-59000/native-arm{ordinal}.routes.private.json').read_text())
        for case in cases:
            request = data[case]['requests'][ordinal]
            trace = json.loads((args.cache / f'hardware-first-generation-{case}/native-arm{ordinal}.routes.private.json').read_text())
            assert trace['complete'] and trace['records'] == routes['records']
            assert request['token_ids'] == reference['token_ids'] and request['output_bytes'] == reference['output_bytes']
            assert all(request['completed_performance']['delta'][k] == reference['completed_performance']['delta'][k] for k in source_keys)
        control = [data[c]['requests'][ordinal]['metrics'] for c in (59000, 59600)]
        candidate = [data[c]['requests'][ordinal]['metrics'] for c in (59200, 59400)]
        whole = [control[i]['total_ms'] - candidate[i]['total_ms'] for i in range(2)]
        decode = [control[i]['decode_ms'] - candidate[i]['decode_ms'] for i in range(2)]
        groups.append(dict(condition=label, control=control, candidate=candidate,
            mean_control_decode_tokens_per_second=statistics.mean(x['decode_tokens_per_second'] for x in control),
            mean_candidate_decode_tokens_per_second=statistics.mean(x['decode_tokens_per_second'] for x in candidate),
            mean_decode_rate_gain_percent=100 * (statistics.mean(x['decode_tokens_per_second'] for x in candidate) /
                statistics.mean(x['decode_tokens_per_second'] for x in control) - 1),
            paired_whole_savings_ms=whole, paired_decode_savings_ms=decode,
            control_AA_whole_spread_ms=abs(control[1]['total_ms'] - control[0]['total_ms']),
            control_AA_decode_spread_ms=abs(control[1]['decode_ms'] - control[0]['decode_ms']),
            mean_TTFT_increase_ms=statistics.mean(x['TTFT_ms'] for x in candidate) - statistics.mean(x['TTFT_ms'] for x in control),
            source={k: reference['completed_performance']['delta'][k] for k in source_keys}))
    useful = all(min(g['paired_whole_savings_ms']) > g['control_AA_whole_spread_ms'] and
                 min(g['paired_decode_savings_ms']) > g['control_AA_decode_spread_ms'] for g in groups[1:])
    result = dict(schema='ps5-qwen-scheduler-normal-ABBA-v1', completed=True, cases=list(cases),
        requests=12, actual_native_frames=8, groups=groups,
        all_tokens_and_output_bytes_exact=True, all_actual_ordered_routes_exact=True,
        identical_source_demand=True, all_counting_tasks_passed=True, all_full_F32_finite=True,
        normal_cross_program_full_F32_row_hashes_recorded=False,
        original_normal_generation_benefit_qualifies=useful,
        initial_prefill_latency_regression_reported=True,
        selection_priority='Generation speed; initial TTFT tradeoff is explicit',
        control_device_peak_bytes=data[59000]['device_ledger_peak_bytes'],
        candidate_device_peak_bytes=data[59200]['device_ledger_peak_bytes'],
        additional_device_peak_bytes=data[59200]['device_ledger_peak_bytes'] - data[59000]['device_ledger_peak_bytes'],
        CPU_heap_peak_bytes=data[59200]['CPU_heap_peak_bytes'],
        logical_map_bytes=49 * 640 * 4, backend_reported_map_bytes=data[59200]['scheduler_slot_map_counts'][7],
        evidence=evidence, PS5_operations=0, CI_runs=0)
    write_json(args.out, result)
    print(json.dumps({k: result[k] for k in ('completed', 'original_normal_generation_benefit_qualifies', 'additional_device_peak_bytes')}))
    for group in groups:
        print(json.dumps({k: group[k] for k in ('condition', 'mean_control_decode_tokens_per_second',
            'mean_candidate_decode_tokens_per_second', 'mean_decode_rate_gain_percent', 'mean_TTFT_increase_ms')}))

if __name__ == '__main__': main()
