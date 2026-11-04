#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify each new stream profile once and extend only promising speed screens."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from build_performance_quantizer import record
from iq2_up_model_scope import require_IQ2_comparison
from run_headless_decode_sequence import returned
from source_cache_pools import command as cache_command, has_windows, validate as validate_cache_pools
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'model-proof', 'direct-staging-proof', 'native-VM-proof',
                 'cache-baseline', 'baseline-case', 'config', 'initial-cache-scopes', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    config = load(a.config)
    need(1 <= len(config['profiles']) <= 2, 'Only the explicit complete source roles may be followed up')
    a.out.mkdir(parents=True, exist_ok=False)
    frozen = [record(ROOT / 'tools' / name) for name in (
        'build_iq2_up_model.py', 'iq2_up_model_scope.py', 'iq2_format_stream_scope.py', 'iq2_format_stream_cache.py',
        'iq2_stream_minimum_request.py',
        'relink_retained_current.py', 'analyze_iq2_stream_equivalence.py', 'run_successful_headless_audit.py',
        'run_successful_model_case.py', 'close_successful_current_model.py', 'success_case_control.py',
        'retire_published_iq2_source_cache.py', 'analyze_iq2_pair_screen.py', 'analyze_headless_decode_sequence.py',
        'build_iq2_heldout_quality.py', 'analyze_iq2_heldout_quality.py')]
    frozen += [record(ROOT / 'tools' / name) for name in (
        'source_cache_pools.py', 'observe_source_cache_complement.py', 'observe_completed_source_cache.py')]
    frozen += [record(a.config), record(Path(__file__))]
    model_cache_controls = config.get('completed_model_cache_controls')
    compact_marker_control = config.get('compact_marker_control')
    if model_cache_controls:
        from model_source_cache_continuation import qualification
        need(compact_marker_control, 'An exact diagnostic marker qualification is required')
        frozen += qualification(Path(model_cache_controls), Path(compact_marker_control))
    if config.get('minimum_request_alignment_control'):
        path = Path(config['minimum_request_alignment_control'])
        control = load(path)
        need(control['completed'] and control['PS5_operations'] == control['old_wrapper_controls_replayed'] == 0 and
             {r['layout'] for r in control['results']} == {1, 2} and
             all(r['new_alignment_positives'] == 4 and r['new_EOF_negatives'] == 5 and
                 r['logical_and_physical_bounds_separate'] and r['destination_canaries_exact'] for r in control['results']) and
             all(load(item['compiled_stream'])['wrapper_source'] == control['inputs'][0] for item in config['profiles']),
             'The supplementary logical/rounded-physical bounds must match both actual minimum-request wrappers')
        frozen += [record(path), *control['inputs']]
    pools = config['cache_pools']
    if config.get('fallback_cache_pools_from'):
        prior = Path(config['fallback_cache_pools_from'])
        pools += load(prior)
        frozen.append(record(prior))
    initial = load(a.initial_cache_scopes)
    pools[0]['completed_scopes'] = initial + pools[0].get('completed_scopes', [])
    validate_cache_pools(pools)
    (a.out / 'cache-pools.private.json').write_text(json.dumps(pools, indent=2) + '\n', encoding='utf-8')
    save(a.out / 'intent.private.json', dict(tools=frozen, profiles=config['profiles'],
        changed_source_cache_pools=pools, primary_metric='(generated_tokens-1)*1000/decode_ms',
        unchanged_readiness_pages=7374, initial_native_collection_quiet_seconds=35,
        negative_screens_not_replayed=True, production_adoption=False))

    def idle():
        s = load(a.current / 'active-console.private.json')
        need(s['original_restored'] and not s['native_running'] and not s['model_loaded'] and not s['unknown_completion'] and
             not s.get('source_publication_owner') and not s.get('CPU_source_seal_owner') and
             not s.get('GPU_retirement_readmission_pending'), 'Only the positively restored single console owner may advance')

    def run(tool, flags, label, timeout=2400, prelaunch_out=None):
        need(all(record(r['path']) == r for r in frozen), 'A running follow-up input changed; stop without replay')
        command = [sys.executable, '-B', str(ROOT / 'tools' / tool), *map(str, flags)]
        save(a.out / (label + '-command.private.json'), dict(command=command, automatic_retries=0))
        with (a.out / (label + '.private.log')).open('xb') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     env=dict(os.environ, PYTHONPATH=str(ROOT / 'tools')))
            save(a.out / (label + '-host-owner.private.json'), dict(pid=child.pid, command=command))
            deadline, notice = time.monotonic() + timeout, 0
            while child.poll() is None:
                need(time.monotonic() < deadline, 'The same host child remains owned; never resubmit it')
                if time.monotonic() >= notice:
                    print(json.dumps(dict(phase=label, host_child_running=True, additional_PS5_probes=0)), flush=True)
                    notice = time.monotonic() + 30
                time.sleep(1)
        if child.returncode != 0 and prelaunch_out is not None:
            path = prelaunch_out / 'VM-before/result.private.json'
            if path.exists() and not (prelaunch_out / 'case').exists():
                value = load(path)
                need(value['completed'] and not value['may_launch'] and value['selected_readiness_pages'] == 7374,
                     'Only an exact readiness-only refusal may proceed to changed-source cache retirement')
                idle()
                save(prelaunch_out / 'readiness-only-refusal.private.json', dict(completed=True,
                    observation=record(path), title_launches=0, source_publications=0,
                    changed_cache_scope_required_before_next_admission=True))
                return False
        need(child.returncode == 0, 'Retain the exact completed prefix and inspect ' + label + '.private.log')
        return True

    common = ['--workspace', a.workspace, '--current', a.current, '--mount-plan', a.mount_plan]
    native = common + ['--model-proof', a.model_proof, '--direct-staging-proof', a.direct_staging_proof,
                      '--native-VM-proof', a.native_VM_proof, '--readiness-pages', '7374', '--quiet-seconds', '35']
    serial = 0
    model_cache_scopes = []

    def capacity(label):
        nonlocal serial
        # Each finite scope advances to unscanned windows. This is a soft cache
        # target; the subsequent title still needs its own fresh7374-page guard.
        for pool in pools:
            done = pool['completed_scopes']
            if not has_windows(pool):
                continue
            for _ in range(8):
                out = a.out / ('cache-' + str(serial))
                serial += 1
                tool, flags = cache_command(common, pool, out)
                run(tool, flags, label + '-cache-' + str(serial), 300)
                path = out / 'result.private.json'
                result = load(path)
                need(result['completed'] and result['all_mappings_and_FDs_positively_retired'], 'The changed source window must retire')
                done.append(str(path))
                (a.out / 'cache-pools.private.json').write_text(json.dumps(pools, indent=2) + '\n', encoding='utf-8')
                if result['observations']['free_after'] >= 7374:
                    return True
                if result['remaining_windows'] == 0:
                    break
        if model_cache_controls:
            from model_source_cache_continuation import available, flags
            for _ in range(8):
                if not available(a.current):
                    break
                out = a.out / ('completed-model-cache-' + str(serial))
                serial += 1
                arguments = flags(a.current, common, Path(compact_marker_control), out)
                run('retire_completed_model_source_cache.py', arguments, label + '-model-cache-prepare-' + str(serial), 300)
                run('retire_completed_model_source_cache.py', arguments + ['--execute-prepared'], label + '-model-cache-retire-' + str(serial), 300)
                path = out / 'result.private.json'
                result = load(path)
                need(result['completed'] and result['all_mappings_and_FDs_positively_retired'], 'The exact latest model cache owner must retire')
                model_cache_scopes.append(record(path))
                (a.out / 'completed-model-cache-scopes.private.json').write_text(json.dumps(model_cache_scopes, indent=2) + '\n', encoding='utf-8')
                if result['observations']['free_after'] >= 7374:
                    return True
        # Insufficient returned capacity cannot justify another admission query.
        print(json.dumps(dict(phase=label, distinct_cache_pool_allowance_ended=True,
            model_admission=False, readiness_pages=7374, cache_windows_replayed=0)), flush=True)
        return False

    def case(package, root, label):
        idle()
        if not run('run_successful_headless_audit.py', native + ['--package', package, '--out', root],
                   label, prelaunch_out=root):
            need(capacity(label), 'No distinct cache scope returned adequate capacity; never repeat the refused admission unchanged')
            root = root.with_name(root.name + '-after-distinct-cache')
            run('run_successful_headless_audit.py', native + ['--package', package, '--out', root], label + '-after-distinct-cache')
        idle()
        return root, load(root / 'result.private.json')

    decisions = []
    for item in config['profiles']:
        idle()
        label = item['label']
        out = a.out / label
        out.mkdir()
        prep, pub = load(item['preparation']), load(item['publication'])
        need(prep['completed'] and pub['completed'] and pub['preparation'] == record(item['preparation']), 'Reuse only the exact whole sealed model')
        build_flags = ['--workspace', a.workspace, '--current', a.current, '--preparation', item['preparation'],
            '--publication', item['publication'], '--cache-baseline', a.cache_baseline,
            '--arithmetic-qualification', item['arithmetic_qualification']]
        if item.get('Down_resource_provider'):
            build_flags += ['--Down-resource-provider', item['Down_resource_provider']]
        observed = []
        negative_observation = None
        for arm in ('plain', 'stream'):
            built = item.get('prebuilt_' + arm)
            if built:
                checked = load(built)
                need(checked['completed'] and checked['F32_qualification'] and checked['preparation'] == record(item['preparation']) and
                     checked['publication'] == record(item['publication']) and
                     checked['format_stream_provider'] == (record(item['compiled_stream']) if arm == 'stream' else None),
                     'Reuse only the exact already built same-model observed candidate')
                model = Path(built).parent
            else:
                model = out / (arm + '-observed-model')
                flags = build_flags + ['--F32-observer', config['F32_observer'], '--candidate-only', '--out', model]
                if arm == 'stream':
                    flags += ['--format-stream-provider', item['compiled_stream'], '--cache-provider-proof', item['compiled_stream']]
                run('build_iq2_up_model.py', flags, label + '-' + arm + '-observed-build')
            root = out / (arm + '-observed-case')
            if arm == 'plain' and item.get('completed_plain_case'):
                from model_source_cache_continuation import reused_observation
                root = Path(item['completed_plain_case'])
                outcome, archived = reused_observation(root, model / 'candidate/SELF/result.private.json')
                frozen += archived
                save(out / 'plain-reused-observation.private.json', dict(completed=True, case=str(root), evidence=archived,
                    native_cases_replayed=0, source_publications=0, title_launches=0))
            else:
                root, outcome = case(model / 'candidate/SELF/result.private.json', root, label + '-' + arm + '-observed-native')
            if not outcome['all_counting_and_finite_checks']:
                negative_observation = dict(label=label, observed_arm=arm,
                    result=record(root / 'result.private.json'), counting_or_finite_negative=True,
                    IO_equivalence_qualified=False, adopted=False)
                break
            observed.append(root)
        if negative_observation:
            decisions.append(negative_observation)
            save(out / 'decision.private.json', negative_observation)
            continue
        proof = out / 'IO-equivalence.private.json'
        run('analyze_iq2_stream_equivalence.py', ['--control-case', observed[0], '--candidate-case', observed[1],
            '--compiled-stream', item['compiled_stream'], '--out', proof], label + '-IO-analysis', 120)
        if not load(proof)['IO_equivalence_qualified']:
            decisions.append(dict(label=label, IO_equivalence=record(proof), native_IO_negative=True, adopted=False))
            continue
        model = out / 'timed-model'
        run('build_iq2_up_model.py', build_flags + ['--format-stream-provider', item['compiled_stream'],
            '--cache-provider-proof', item['compiled_stream'], '--format-stream-IO-proof', proof, '--out', model], label + '-timed-build')
        candidate, control = (model / arm / 'SELF/result.private.json' for arm in ('candidate', 'control'))
        root = out / 'first-timed-screen'
        root, outcome = case(candidate, root, label + '-first-timed-native')
        decision = dict(label=label, IO_equivalence=record(proof), timed_case=record(root / 'result.private.json'), adopted=False)
        if not outcome['all_counting_and_finite_checks']:
            decision['counting_or_finite_negative'] = True
            decisions.append(decision)
            continue
        screen = out / 'first-screen.private.json'
        run('analyze_iq2_pair_screen.py', ['--control-case', a.baseline_case, '--candidate-case', root, '--out', screen], label + '-screen-analysis', 120)
        decision['single_screen'] = record(screen)
        if load(screen)['all_conditions_slower']:
            decisions.append(decision)
            continue
        scope = 'Q3' if item.get('Down_resource_provider') else 'Q2'
        profiles = [load(load(path)['effective_application_policy']['profile']['path']) for path in (control, candidate)]
        require_IQ2_comparison(profiles, scope, record(item['arithmetic_qualification']))
        sequence = out / 'ABBA'
        sequence.mkdir()
        rows = []
        for index, package in enumerate((control, candidate, candidate, control)):
            root = sequence / ('case-' + str(index))
            root, _ = case(package, root, label + '-ABBA-' + str(index))
            rows.append(returned(root, package))
        save(sequence / 'result.private.json', dict(completed=True, scope=scope, cases=rows, order=[0, 1, 1, 0],
            numerical_proof=record(item['arithmetic_qualification']), all_ordinary_closes_and_exact_restores=True,
            native_requests=12, automatic_retries=0, production_adopted=False))
        analysis = out / 'ABBA-analysis.private.json'
        run('analyze_headless_decode_sequence.py', ['--sequence', sequence / 'result.private.json', '--out', analysis], label + '-ABBA-analysis', 120)
        decision['matched_ABBA'] = record(analysis)
        groups = load(analysis)['groups']
        gain = any(g['decode_tokens_per_second']['both_paired_gains_exceed_control_spread'] for g in groups)
        regression = any(g['decode_tokens_per_second']['both_paired_regressions_exceed_control_spread'] for g in groups)
        if gain and not regression:
            quality = out / 'heldout-model'
            run('build_iq2_heldout_quality.py', ['--workspace', a.workspace, '--current', a.current,
                '--model-build', model / 'result.private.json', '--out', quality], label + '-heldout-build')
            roots = []
            for arm in ('control', 'candidate'):
                root = out / ('heldout-' + arm)
                root, _ = case(quality / arm / 'SELF/result.private.json', root, label + '-heldout-' + arm)
                roots.append(root)
            result = out / 'heldout-analysis.private.json'
            run('analyze_iq2_heldout_quality.py', ['--control', roots[0], '--candidate', roots[1],
                '--decode-analysis', analysis, '--out', result], label + '-heldout-analysis', 120)
            decision['heldout_quality'] = record(result)
        decisions.append(decision)
        save(out / 'decision.private.json', decision)
    save(a.out / 'result.private.json', dict(completed=True, profiles=decisions,
        ordinary_restoration_after_every_case=True, unchanged_primary_metric=True, production_adopted=False,
        completed_model_cache_scopes=model_cache_scopes))
    print(json.dumps(dict(completed=True, profiles=len(decisions), production_adopted=False)), flush=True)


if __name__ == '__main__':
    main()
