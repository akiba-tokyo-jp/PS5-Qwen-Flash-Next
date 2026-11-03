#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse completed ordinary/MTP evidence without claiming identical computation."""
import argparse
from pathlib import Path
from analyze_headless_numerics import full_rows, positive
from build_performance_quantizer import record
from start_success_route import load, need, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('ordinary', 'retained', 'causal-proof', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    causal = load(a.causal_proof)
    need(causal['completed'] and causal['actual_target_tokens_bytes_causal_inputs_routes_and_all69_F32_rows_exact'] and
         causal['case'] == record(a.retained / 'result.private.json'),
         'The exact retained compact MTP causal/lifetime qualification is required')
    terminals, rows, routes, evidence = [], [], [], [record(a.causal_proof)]
    for root, kind in ((a.ordinary, 'S1-ordinary-target-control'), (a.retained, 'S1-persistent-MTP-online')):
        done = load(root / 'result.private.json')
        for key in ('terminal', 'closure'):
            need(record(done[key]['path']) == done[key], 'Completed immutable evidence changed')
            evidence.append(done[key])
        terminal, closed = load(done['terminal']['path']), load(done['closure']['path'])
        positive(terminal, closed)
        need(done['completed'] and terminal['kind'] == kind and not terminal['timings_usable_for_performance'],
             'Separate completed numerical scopes are required')
        terminals.append(terminal)
        stages = root / 'case/native-stages.private.log'
        rows.append(full_rows(stages)); evidence.extend((record(stages), record(root / 'result.private.json')))
        traces = []
        for index in range(3):
            path = root / f'case/headless-observer/native.arm{index}.routes.private.json'
            trace = load(path)
            need(trace['complete'] and not trace['capture_failed'] and trace['sidecar_written_after_model_and_source_retirement'],
                 'Each actual feature route capture must be complete')
            traces.append(trace['records']); evidence.append(record(path))
        routes.append(traces)
    tokens = all(x['token_ids'] == y['token_ids'] and x['output_bytes'] == y['output_bytes']
                 for x, y in zip(terminals[0]['requests'], terminals[1]['requests']))
    need(tokens, 'All original target tokens and bytes must agree for this feature comparison')
    differences = [dict(request=x[0], row=x[1], ordinary_sha256=x[3], retained_sha256=y[3])
                   for x, y in zip(*rows) if x != y]
    save(a.out, dict(completed=True, scope='S1-ordinary-vs-retained',
        tokens_and_output_bytes_exact=True, compact_retained_causal_and_lifetime_qualified=True,
        causal_proof=record(a.causal_proof), matching_F32_rows=69-len(differences), differing_rows=differences,
        whole_F32_rows_exact=not differences, ordered_routes_exact_per_request=[x == y for x, y in zip(*routes)],
        route_record_counts=[[len(x) for x in arm] for arm in routes],
        route_evidence_by_feature=[[record(root / f'case/headless-observer/native.arm{i}.routes.private.json') for i in range(3)]
                                   for root in (a.ordinary, a.retained)],
        computation_schedule_changes=True, full_F32_error_magnitude_measured=False,
        all_counting_finite_reset_and_retirement_checks=True, all_ordinary_closes_and_exact_restores=True,
        broader_prompt_quality_qualified=False, performance_timings_usable=False, evidence=evidence, PS5_operations=0))
    print(dict(completed=True, matching_F32_rows=69-len(differences), target_tokens_and_bytes_exact=tokens,
               identical_computation_claimed=False, PS5_operations=0))


if __name__ == '__main__':
    main()
