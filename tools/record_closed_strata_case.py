#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record an already completed Strata case after collection-only ordinary close."""
import argparse
from pathlib import Path

from analyze_headless_numerics import positive
from build_performance_quantizer import record
from start_success_route import load, need, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'case'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    intent = load(args.case / 'intent.private.json')
    plan = load(args.case / 'case/plan.private.json')
    package = load(plan['package']['path'])
    need(record(plan['package']['path']) == plan['package'] == intent['package'], 'Exact original accepted package required')
    profile_row = package['effective_application_policy']['profile']
    need(record(profile_row['path']) == profile_row, 'Compiled package profile changed')
    profile = load(profile_row['path'])
    need(profile['headless_audit_kind'] == 'ST3-stream-sync' and profile['headless_requests'] == intent['native_requests'] == 3,
         'Only the completed original three-request Strata case may be finalized')
    observer = args.case / 'case/headless-observer'
    terminal_row = record(observer / 'native.private.bin')
    native, closed = load(terminal_row['path']), load(args.case / 'closed/result.private.json')
    positive(native, closed)
    first, completion = load(args.case / 'case/native-first-start.private.json'), load(observer / 'complete.private.json')
    audit = record(observer / 'native.audit.private.json')
    need(native['pid'] == first['pid'] and native['run_id'] == plan['run_id'] == first['run_id'] and
         native['candidate_SELF_sha256'] == package['SELF']['sha256'] == plan['SELF']['sha256'] and
         native['kind'] == profile['headless_audit_kind'] and native['audit'] == load(audit['path']) and
         closed['native_terminal'] == terminal_row and completion['completed'] and completion['POSTs'] == 0 and
         completion['model_source_GPU_owners_positively_retired'] and completion['native_binding'] == first and
         closed['same_submitted_close_collected_after_host_timeout']['additional_close_calls'] == 0,
         'All original numerical, identity and collection-only close evidence must match')
    for index in range(3):
        trace = load(observer / ('native.arm' + str(index) + '.routes.private.json'))
        need(trace['complete'] and not trace['capture_failed'] and trace['pid'] == first['pid'] and
             trace['run_id'] == plan['run_id'] and trace['sidecar_written_after_model_and_source_retirement'],
             'Every original route sidecar must positively complete')
    state = load(args.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'] and
         state['active_successful_native_case']['run_id'] == plan['run_id'] and
         state['active_successful_native_case']['phase'] == 'model-complete-ordinary-close-original-restored',
         'The exact original owner must already be normally closed and current restored')
    save(args.case / 'result.private.json', dict(completed=True, kind=profile['headless_audit_kind'], native_requests=3,
        terminal=terminal_row, audit=audit, closure=record(args.case / 'closed/result.private.json'),
        all_counting_and_finite_checks=True, native_owners=0, unknown_completion=False, HTTP_requests=0,
        VideoOut_starts=0, automatic_retries=0, production_adopted=False,
        same_native_measurement_reused_after_close_collection=True, PS5_operations=0))
    print('Original Strata measurement retained; same ordinary close collected; current restored; model relaunches: 0')


if __name__ == '__main__':
    main()
