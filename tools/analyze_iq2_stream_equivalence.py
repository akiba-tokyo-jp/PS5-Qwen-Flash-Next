#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare two closed executions of one quantized model across the IO change."""
import argparse
import json
from pathlib import Path

from analyze_headless_numerics import full_rows, positive
from build_performance_quantizer import record
from iq2_format_stream_scope import MODES, require_compiled_stream
from iq2_up_model_scope import require_cache_layout
from start_success_route import load, need, save


def observed(root):
    result = load(root / 'result.private.json')
    plan = load(root / 'case/plan.private.json')
    for key in ('terminal', 'closure'):
        need(record(result[key]['path']) == result[key], 'Completed native IO evidence changed')
    package = load(plan['package']['path'])
    need(record(plan['package']['path']) == plan['package'] and package['completed'], 'The exact observed package must remain available')
    profile_row = package['effective_application_policy']['profile']
    need(record(profile_row['path']) == profile_row, 'The actual compiled IO profile changed')
    profile = load(profile_row['path'])
    require_cache_layout(profile)
    terminal, closed = load(result['terminal']['path']), load(result['closure']['path'])
    positive(terminal, closed)
    need(result['completed'] and not terminal['timings_usable_for_performance'] and
         not profile['performance_timings_usable'] and profile['qualification_observer'] and
         profile['headless_audit_kind'] in MODES and profile['headless_requests'] == 3 and
         profile['overrides']['native_headless_model_audit']['arm'] == 'candidate',
         'Both sides must be complete numerical observations of the same quantized candidate')
    observer = profile['qualification_observer']
    need(record(observer['path']) == observer and load(observer['path'])['qualification_only'], 'The exact complete F32 observer is required')
    routes, evidence = [], [record(root / 'result.private.json'), record(root / 'case/plan.private.json'),
        plan['package'], profile_row, result['terminal'], result['closure'], observer]
    journal = root / 'case/native-stages.private.log'
    rows = full_rows(journal)
    evidence.append(record(journal))
    for index in range(3):
        path = root / ('case/headless-observer/native.arm' + str(index) + '.routes.private.json')
        trace = load(path)
        need(trace['complete'] and not trace['capture_failed'] and trace['sidecar_written_after_model_and_source_retirement'],
             'Every ordered route sidecar must finish after source retirement')
        routes.append(trace['records'])
        evidence.append(record(path))
    requests = terminal['requests']
    need([r['ordinal'] for r in requests] == [0, 1, 2] and
         [r['cache_initially_empty'] for r in requests] == [True, False, False] and
         [r['prefix']['request_hit'] for r in requests] == [False, False, True],
         'The original cold, retained and exact-prefix request conditions must remain intact')
    return profile, requests, rows, routes, evidence


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('control-case', 'candidate-case', 'compiled-stream', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    left, lr, lf, lt, le = observed(a.control_case)
    right, rr, rf, rt, re = observed(a.candidate_case)
    ls, rs = (p['overrides']['native_headless_model_audit'] for p in (left, right))
    compiled = record(a.compiled_stream)
    need(left['headless_audit_kind'] == right['headless_audit_kind'] and
         left['model_layer'] == right['model_layer'] and left['qualification_observer'] == right['qualification_observer'] and
         not ls.get('format_stream_provider') and rs['format_stream_provider'] == compiled,
         'Compare only the original IO and streamed IO of one exact quantized model')
    require_compiled_stream(compiled, MODES[right['headless_audit_kind']])
    filtered = lambda s: {k: v for k, v in s.items() if not k.startswith('format_stream_')}
    need(filtered(ls) == filtered(rs), 'Arithmetic, MMVQ, slot geometry and every non-IO scope field must be identical')
    groups = 0
    for row in rr:
        delivery = row['streaming_delivery']
        need(delivery['existing_scratch_bytes'] == 8 << 20 and delivery['extra_GPU_buffers'] == 0 and
             delivery['groups'] >= 0 and delivery['physical_reads'] >= 3 * delivery['groups'],
             'Actual completed source-stream groups must retain the existing scratch and GPU geometry')
        groups += delivery['groups']
    tokens = all(x['token_ids'] == y['token_ids'] and x['output_bytes'] == y['output_bytes'] for x, y in zip(lr, rr))
    report = dict(completed=True, compiled_stream=compiled, mode=MODES[right['headless_audit_kind']],
        model_receipt=right['model_layer']['model_receipt'], arithmetic_qualification=rs['arithmetic_qualification'],
        backend_environment=rs['backend_environment'], same_quantized_model_compared=True,
        all69_full_vocabulary_F32_rows_SHA256_exact=lf == rf, ordered_routes_exact=lt == rt,
        tokens_and_output_bytes_exact=tokens, actual_streamed_groups=groups,
        full_F32_rows_per_case=69, whole_vocabulary_columns=248320,
        all_ordinary_closes_and_exact_restores=True, performance_timings_usable=False,
        IO_equivalence_qualified=lf == rf and lt == rt and tokens and groups > 0,
        source_physical_bytes_reduced_claimed=False, evidence=le + re,
        PS5_operations=0, native_cases_replayed=0, production_adopted=False)
    save(a.out, report)
    print(json.dumps({k: report[k] for k in ('completed', 'mode', 'all69_full_vocabulary_F32_rows_SHA256_exact',
          'ordered_routes_exact', 'tokens_and_output_bytes_exact', 'actual_streamed_groups', 'IO_equivalence_qualified')}))


if __name__ == '__main__':
    main()
