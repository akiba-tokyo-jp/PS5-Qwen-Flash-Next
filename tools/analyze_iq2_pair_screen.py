#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen one completed IQ2 pair without replaying a clearly slower candidate."""
import argparse
import math
from pathlib import Path

from build_performance_quantizer import record
from run_headless_decode_sequence import returned
from start_success_route import load, need, save


def observations(root):
    plan = load(root / 'case/plan.private.json')
    evidence = returned(root, Path(plan['package']['path']))
    terminal = load(evidence['terminal']['path'])
    rows = terminal['requests']
    need([r['ordinal'] for r in rows] == [0, 1, 2] and
         [r['cache_initially_empty'] for r in rows] == [True, False, False] and
         [r['prefix']['request_hit'] for r in rows] == [False, False, True] and
         rows[2]['prefix']['last_reused_prompt_tokens'] == rows[2]['metrics']['prompt_tokens'],
         'Preserve the original cold, retained and exact-prefix conditions')
    result = []
    for condition, row in zip(('cold', 'retained', 'exact-prefix'), rows):
        metrics = row['metrics']
        rate = (metrics['generated_tokens'] - 1) * 1000 / metrics['decode_ms']
        need(metrics['generated_tokens'] > 1 and metrics['decode_ms'] > 0 and
             math.isfinite(rate) and math.isclose(rate, metrics['decode_tokens_per_second'], rel_tol=1e-12),
             'The established complete-model decode metric must reproduce exactly')
        delta = row['completed_performance']['delta']
        result.append(dict(condition=condition, generated_tokens=metrics['generated_tokens'],
            prompt_tokens=metrics['prompt_tokens'], decode_ms=metrics['decode_ms'], decode_tokens_per_second=rate,
            request_source_physical_read_calls=delta['source_physical_read_calls'],
            request_source_physical_read_bytes=delta['source_physical_read_bytes'],
            request_source_producer_wait_ns=delta['source_read_ns'],
            request_bundled_Experts=row['bundled_Experts'], token_ids=row['token_ids'], output_bytes=row['output_bytes']))
    return evidence, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('control-case', 'candidate-case', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    control, a = observations(args.control_case)
    candidate, b = observations(args.candidate_case)
    rows = []
    for first, second in zip(a, b):
        need(first['prompt_tokens'] == second['prompt_tokens'], 'The original prompt cohort must match')
        rows.append(dict(condition=first['condition'], control=first, candidate=second,
            decode_change_percent=100 * (second['decode_tokens_per_second'] / first['decode_tokens_per_second'] - 1),
            tokens_and_bytes_exact=all(first[k] == second[k] for k in ('token_ids', 'output_bytes'))))
    need(not args.out.exists(), 'Never overwrite a completed screen')
    save(args.out, dict(completed=True, metric='(generated_tokens-1)*1000/decode_ms',
        control=control, candidate=candidate, observations_per_arm=1, conditions=rows,
        complete_ABBA=False, matched_means=False, statistical_speedup_qualified=False,
        all_conditions_slower=all(r['decode_change_percent'] < 0 for r in rows),
        source_intervals_cover_whole_request_not_decode_only=True,
        causal_attribution_from_single_pair=False, PS5_operations=0,
        native_cases_replayed=0, production_adopted=False, source=record(Path(__file__))))
    print({r['condition']: r['decode_change_percent'] for r in rows})


if __name__ == '__main__':
    main()
