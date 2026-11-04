#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finish both distinct cache refinements; extend only promising timing screens."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from analyze_headless_decode_sequence import compare, compare_time
from analyze_headless_numerics import positive
from build_performance_quantizer import record
from run_headless_decode_sequence import returned
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'model-proof', 'direct-staging-proof', 'native-VM-proof',
                 'build', 'group-case', 'reference', 'compact-marker-control', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--completed-prefix-from', type=Path,
        help='Reuse both numerical results and the first two already closed timing cases after a host collection interruption')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    # This wait reads local completion receipts only; the accepted owner remains sole console IO owner.
    need((a.group_case / 'case/plan.private.json').is_file(), 'The group qualification must already be submitted')
    while not (a.group_case / 'result.private.json').is_file():
        need(not (a.group_case / 'case/native.failure.private.json').exists() and
             not (a.group_case / 'case/native.fatal.private.json').exists(), 'The preceding native owner failed; retain it')
        print(json.dumps(dict(phase='waiting-for-accepted-group-ordinary-close', PS5_operations=0)), flush=True)
        time.sleep(30)
    packages = load(a.build)['packages']
    frozen = [record(ROOT / 'tools' / name) for name in (
        'run_strata_sync_campaign.py', 'analyze_strata_numerics.py', 'run_successful_headless_audit.py',
        'run_successful_model_case.py', 'retained_identity_proof.py', 'retire_completed_model_source_cache.py',
        'success_case_control.py', 'close_successful_current_model.py')]
    frozen += [record(a.build), *packages.values()]
    save(a.out / 'intent.private.json', dict(frozen=frozen, reused_group_case=record(a.group_case / 'result.private.json'),
        reference=record(a.reference / 'result.private.json'), primary_metric='(generated_tokens-1)*1000/decode_ms',
        model_screen_pages=7374, original_guards_preserved=True, old_cases_replayed=0, production_adopted=False,
        completed_prefix_from=str(a.completed_prefix_from) if a.completed_prefix_from else None))

    def run(tool, flags, label):
        need(all(record(row['path']) == row for row in frozen), 'A frozen campaign input changed')
        command = [sys.executable, '-X', 'utf8', '-B', str(ROOT / 'tools' / tool), *map(str, flags)]
        save(a.out / (label + '-command.private.json'), dict(command=command, automatic_retries=0))
        with (a.out / (label + '.private.log')).open('xb') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            save(a.out / (label + '-host-owner.private.json'), dict(pid=child.pid))
            notice = 0
            while child.poll() is None:
                if time.monotonic() >= notice:
                    print(json.dumps(dict(phase=label, host_child_running=True, additional_PS5_probes=0)), flush=True)
                    notice = time.monotonic() + 30
                time.sleep(1)
        need(child.returncode == 0, 'Inspect ' + str(a.out / (label + '.private.log')) + '; never replay a consumed native operation')

    common = ['--workspace', a.workspace, '--current', a.current, '--mount-plan', a.mount_plan]
    serial = 0
    latest = a.group_case

    def capacity(label):
        nonlocal serial
        state = load(a.current / 'active-console.private.json')
        case_row = record(latest / 'result.private.json')
        cohort = [entry for entry in state.get('completed_model_source_cache_cohorts', []) if entry['case_result'] == case_row]
        need(len(cohort) <= 1, 'One ledger per actual completed model owner required')
        completed = cohort[0]['completed_scopes'].copy() if cohort else []
        for _ in range(8):
            serial += 1
            out = a.out / ('source-cache-' + str(serial))
            flags = common + ['--case', latest, '--compact-marker-control', a.compact_marker_control, '--out', out]
            for row in completed:
                flags += ['--completed-scope', row['path']]
            run('retire_completed_model_source_cache.py', flags, label + '-cache-prepare-' + str(serial))
            run('retire_completed_model_source_cache.py', flags + ['--execute-prepared'], label + '-cache-execute-' + str(serial))
            result = load(out / 'result.private.json')
            need(result['completed'] and result['all_mappings_and_FDs_positively_retired'], 'The completed read owner must retire')
            completed.append(record(out / 'result.private.json'))
            if result['observations']['free_after'] >= 7374:
                return
        raise RuntimeError('Finite new source windows did not reach the unchanged model screen; retain every positive prefix')

    def native(package, label):
        nonlocal latest
        capacity(label)
        root = a.out / label
        flags = common + ['--model-proof', a.model_proof, '--direct-staging-proof', a.direct_staging_proof,
            '--native-VM-proof', a.native_VM_proof, '--readiness-pages', '7374', '--package', package, '--out', root]
        run('run_successful_headless_audit.py', flags, label)
        result = load(root / 'result.private.json')
        positive(load(result['terminal']['path']), load(result['closure']['path']))
        latest = root
        return root

    qualified = {}
    for mode in ('group', 'readback'):
        if a.completed_prefix_from:
            proof = a.completed_prefix_from / (mode + '-numerical.private.json')
            value = load(proof)
            need(value['completed'] and value['numerical_qualified'] and value['all69_full_vocabulary_F32_rows_SHA256_exact'] and
                 all(value['ordered_routes_exact_per_request']) and value['tokens_and_output_bytes_exact'] and
                 value['candidate_package'] == packages[mode + '-observed'], 'Reuse only the exact completed numerical qualification')
            qualified[mode] = record(proof)
            continue
        root = a.group_case if mode == 'group' else native(packages[mode + '-observed']['path'], mode + '-numerical')
        output = a.out / (mode + '-numerical.private.json')
        run('analyze_strata_numerics.py', ['--reference', a.reference, '--case', root, '--out', output], mode + '-numerical-analysis')
        need(load(output)['numerical_qualified'], 'Only numerically exact refinements may be timed')
        qualified[mode] = record(output)

    timed = {}
    if a.completed_prefix_from:
        need(a.completed_prefix_from.resolve() != a.out.resolve() and
             not (a.completed_prefix_from / 'readback-first').exists() and
             not (a.completed_prefix_from / 'screens.private.json').exists(), 'Continue only the exact stopped two-case timing prefix')
        for mode, label in (('control', 'control-first'), ('group', 'group-first')):
            timed[label] = returned(a.completed_prefix_from / label, packages[mode + '-timed']['path'])
        closure = load(timed['group-first']['closure']['path'])
        need(closure['same_submitted_close_collected_after_host_timeout']['additional_close_calls'] == 0,
             'The original accepted close must be collected before continuation')
        latest = a.completed_prefix_from / 'group-first'
    for mode, label in (('control', 'control-first'), ('group', 'group-first'), ('readback', 'readback-first'), ('control', 'control-last')):
        if label in timed:
            save(a.out / (label + '-reused.private.json'), timed[label])
            continue
        package = packages[mode + '-timed']['path']
        root = native(package, label)
        timed[label] = returned(root, package)
        save(a.out / (label + '-positive.private.json'), timed[label])

    def rows(label):
        return load(timed[label]['terminal']['path'])['requests']

    screens = {}
    promising = []
    for mode in ('group', 'readback'):
        values = []
        for index, condition in enumerate(('cold', 'retained', 'exact-prefix')):
            labels = ('control-first', mode + '-first', 'control-last')
            actual = [rows(label)[index] for label in labels]
            need(all(r['token_ids'] == actual[0]['token_ids'] and r['output_bytes'] == actual[0]['output_bytes'] for r in actual),
                 'Timed output changed after numerical qualification')
            routes = []
            for label in labels:
                path = Path(timed[label]['root']) / ('case/headless-observer/native.arm' + str(index) + '.routes.private.json')
                trace = load(path)
                need(trace['complete'] and not trace['capture_failed'], 'Every screen route capture must complete')
                routes.append(trace['records'])
            need(all(route == routes[0] for route in routes), 'Screen routing changed; no speed comparison is qualified')
            rates = [(r['metrics']['generated_tokens'] - 1) * 1000 / r['metrics']['decode_ms'] for r in actual]
            mean = (rates[0] + rates[2]) / 2
            spread = abs(rates[2] - rates[0])
            times = {name: [r['metrics'][name] for r in actual] for name in ('prefill_ms', 'TTFT_ms', 'total_ms')}
            values.append(dict(condition=condition, control_rates=[rates[0], rates[2]], candidate_rate=rates[1],
                control_mean=mean, rate_change_percent=100 * (rates[1] / mean - 1), control_spread=spread,
                candidate_gain_exceeds_control_spread=rates[1] - mean > spread, time_metrics=times))
        # A prefill-only mechanism may merit a separate time result even without a decode gain.
        cold = values[0]['time_metrics']
        prefill_promising = any((v[0] + v[2]) / 2 - v[1] > abs(v[2] - v[0]) for v in (cold['prefill_ms'], cold['TTFT_ms']))
        extend = any(v['candidate_gain_exceeds_control_spread'] for v in values) or prefill_promising
        screens[mode] = dict(groups=values, extend=extend, prefill_only_promise=prefill_promising)
        if extend:
            promising.append(mode)
    save(a.out / 'screens.private.json', dict(completed=True, screens=screens, timed=timed, adoption_qualified=False))
    print(json.dumps(dict(phase='timing-screens-complete', screens=screens)), flush=True)

    comparisons = {}
    for mode in promising:
        package = packages[mode + '-timed']['path']
        root = native(package, mode + '-second')
        timed[mode + '-second'] = returned(root, package)
    if promising:
        package = packages['control-timed']['path']
        root = native(package, 'control-final')
        timed['control-final'] = returned(root, package)
        for mode in promising:
            order = ['control-first', mode + '-first', mode + '-second', 'control-final']
            groups = []
            for index, condition in enumerate(('cold', 'retained', 'exact-prefix')):
                actual = [rows(label)[index] for label in order]
                rates = [(r['metrics']['generated_tokens'] - 1) * 1000 / r['metrics']['decode_ms'] for r in actual]
                routes = []
                for label in order:
                    path = Path(timed[label]['root']) / ('case/headless-observer/native.arm' + str(index) + '.routes.private.json')
                    trace = load(path)
                    need(trace['complete'] and not trace['capture_failed'], 'Actual timed routes must complete')
                    routes.append(trace['records'])
                need(all(r['token_ids'] == actual[0]['token_ids'] and r['output_bytes'] == actual[0]['output_bytes'] for r in actual) and
                     all(route == routes[0] for route in routes), 'Matched timing outputs and routes must agree')
                groups.append(dict(condition=condition, decode_tokens_per_second=compare(rates),
                    time_metrics={name: compare_time([r['metrics'][name] for r in actual]) for name in ('prefill_ms', 'TTFT_ms', 'total_ms')}))
            comparisons[mode] = dict(order=[timed[label] for label in order], groups=groups)
    save(a.out / 'result.private.json', dict(completed=True, numerical_proofs=qualified, screens=screens,
        completed_timing_cases=timed, extended_comparisons=comparisons, primary_metric='(generated_tokens-1)*1000/decode_ms',
        all_ordinary_closes_and_exact_restores=True, no_unchanged_cases_replayed=True, production_adopted=False,
        final_original_model_case=str(latest)))
    print(json.dumps(dict(completed=True, timed_cases=len(timed), extended_modes=promising, production_adopted=False)), flush=True)


if __name__ == '__main__':
    main()
