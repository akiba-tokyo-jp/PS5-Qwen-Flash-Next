#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare cache-only Strata refinements with the completed selected P1 F32 case."""
import argparse
from pathlib import Path

from analyze_headless_numerics import full_rows, positive
from build_performance_quantizer import record
from start_success_route import load, need, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'case', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    observations = []
    evidence = []
    for root in (args.reference, args.case):
        result = load(root / 'result.private.json')
        plan = load(root / 'case/plan.private.json')
        for row in (result['terminal'], result['closure'], plan['package']):
            need(record(row['path']) == row, 'Immutable completed numerical evidence changed')
            evidence.append(row)
        terminal, closed = load(result['terminal']['path']), load(result['closure']['path'])
        positive(terminal, closed)
        profile_row = load(plan['package']['path'])['effective_application_policy']['profile']
        need(record(profile_row['path']) == profile_row, 'The actual compiled qualification profile changed')
        profile = load(profile_row['path'])
        need(not terminal['timings_usable_for_performance'] and
             (root == args.reference or profile.get('qualification_observer')),
             'Reuse only complete qualification observations, never their rates')
        journal = root / 'case/native-stages.private.log'
        hashes = full_rows(journal)
        routes = []
        for index in range(3):
            path = root / ('case/headless-observer/native.arm' + str(index) + '.routes.private.json')
            trace = load(path)
            need(trace['complete'] and not trace['capture_failed'] and trace['sidecar_written_after_model_and_source_retirement'],
                 'Every ordered route sidecar must positively complete')
            routes.append(trace['records'])
            evidence.append(record(path))
        evidence.extend((record(root / 'result.private.json'), record(journal), profile_row))
        observations.append((terminal, profile, hashes, routes))
    left, right = observations
    need(left[1]['headless_audit_kind'] == 'P1-tail-eight' and left[1]['P1_arm'] == 'candidate' and
         left[1]['overrides']['native_P1_headless_arm'] == 1 and right[1]['headless_audit_kind'] == 'ST3-stream-sync' and
         right[1]['ST3_mode'] in ('group', 'readback') and
         left[0]['model_receipt_sha256'] == right[0]['model_receipt_sha256'],
         'Use the actual selected eight-row P1 original-model reference')
    request = right[0]['requests']
    need([r['cache_initially_empty'] for r in request] == [True, False, False] and
         [r['prefix']['request_hit'] for r in request] == [False, False, True],
         'Cold, retained and exact-prefix conditions must remain intact')
    rows_equal = left[2] == right[2]
    routes_equal = [a == b for a, b in zip(left[3], right[3])]
    tokens_equal = all(a['token_ids'] == b['token_ids'] and a['output_bytes'] == b['output_bytes']
                       for a, b in zip(left[0]['requests'], request))
    qualified = rows_equal and all(routes_equal) and tokens_equal
    save(args.out, dict(completed=True, mode=right[1]['ST3_mode'], numerical_qualified=qualified,
        all69_full_vocabulary_F32_rows_SHA256_exact=rows_equal, whole_F32_bytes_routes_tokens_exact=qualified,
        matching_F32_rows=sum(a == b for a, b in zip(left[2], right[2])), ordered_routes_exact_per_request=routes_equal,
        tokens_and_output_bytes_exact=tokens_equal, candidate_package=record(load(args.case / 'case/plan.private.json')['package']['path']),
        all_ordinary_closes_and_exact_restores=True, performance_timings_usable=False, evidence=evidence, PS5_operations=0))
    print(dict(completed=True, mode=right[1]['ST3_mode'], numerical_qualified=qualified, matching_rows=69 if rows_equal else 0), flush=True)
    need(qualified, 'Numerical or route difference: do not time or adopt this cache refinement')


if __name__ == '__main__':
    main()
