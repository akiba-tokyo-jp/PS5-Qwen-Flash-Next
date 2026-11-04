#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Place one remaining source role once, then screen its two distinct refinements."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from build_performance_quantizer import record
from run_headless_decode_sequence import returned
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'model-proof', 'direct-staging-proof',
                 'native-VM-proof', 'preparation', 'publication', 'cache-baseline',
                 'arithmetic-qualification', 'baseline-case', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--role', choices=('Gate', 'Down'), required=True)
    parser.add_argument('--Up-cache-provider', type=Path)
    parser.add_argument('--MMVQ-decode-qualification', type=Path)
    parser.add_argument('--Down-resource-provider', type=Path)
    parser.add_argument('--Down-prefix-provider', type=Path)
    parser.add_argument('--followups', type=Path, help='Bind additional source-role follow-ups after the original two screens')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(args.execute, 'Explicit execution is required for source placement and native screens')
    prep = load(args.preparation)
    need(prep['completed'] and prep.get('IQ2_Gate_layers' if args.role == 'Gate' else 'IQ2_Down_layers') == list(range(48)),
         'One complete prepared forty-eight-layer role is required')
    if args.role == 'Gate':
        need(args.Up_cache_provider and args.MMVQ_decode_qualification and not args.Down_resource_provider,
             'Gate screens reuse the exact Up cache and independently qualified MMVQ path')
    else:
        need(args.Down_resource_provider and args.Down_prefix_provider and not args.MMVQ_decode_qualification,
             'Down screens require the qualified index-safe operator and compiled prefix provider')
        from iq2_down_large_cache_scope import require_model_qualification
        require_model_qualification(record(args.arithmetic_qualification), record(args.Down_resource_provider))
    baseline_plan = load(args.baseline_case / 'case/plan.private.json')
    baseline = returned(args.baseline_case, Path(baseline_plan['package']['path']))
    names = ('publish_iq2_up_model_overlay.py', 'retire_published_iq2_source_cache.py',
             'build_iq2_up_model.py', 'iq2_up_model_scope.py', 'iq2_down_prefix_scope.py',
             'iq2_down_prefix_cache.py', 'run_successful_headless_audit.py',
             'run_successful_model_case.py', 'close_successful_current_model.py',
             'success_case_control.py', 'analyze_iq2_pair_screen.py')
    frozen = [record(ROOT / 'tools' / name) for name in names]
    frozen.append(record(Path(__file__)))
    followups = args.followups or args.publication / 'model-followups.private.json'
    if followups.exists():
        frozen += [record(followups), record(ROOT / 'tools/run_iq2_stream_followups.py')]
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / 'intent.private.json', dict(role=args.role, preparation=record(args.preparation),
        publication_directory=str(args.publication), baseline=baseline, tools=frozen,
        native_profiles=2, readiness_pages=7374, initial_native_collection_quiet_seconds=35,
        automatic_retries=0, initializer_requests=0,
        matched_control_and_quality_required_before_adoption=True, production_adoption=False))

    def idle():
        state = load(args.current / 'active-console.private.json')
        need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
             not state['unknown_completion'] and not state.get('GPU_retirement_readmission_pending') and
             not state.get('source_publication_owner') and not state.get('CPU_source_seal_owner'),
             'Positive ordinary restoration and fresh retained-device capacity readmission must precede the next scope')

    def run(name, flags, label, timeout=1800):
        need(all(record(row['path']) == row for row in frozen), 'A queued input changed; stop before the next scope')
        command = [sys.executable, '-B', str(ROOT / 'tools' / name), *map(str, flags)]
        save(args.out / (label + '-command.private.json'), dict(command=command, automatic_retries=0))
        print(json.dumps(dict(phase=label, started_once=True)), flush=True)
        log = args.out / (label + '.private.log')
        with log.open('xb') as stream:
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                     env=dict(os.environ, PYTHONPATH=str(ROOT / 'tools')))
            save(args.out / (label + '-host-owner.private.json'), dict(pid=child.pid, command=command))
            deadline, notice, cursor = time.monotonic() + timeout, 0, 0
            while child.poll() is None:
                now = time.monotonic()
                need(now < deadline, 'The same host child remains owned; inspect its saved PID and log without resubmitting')
                if now >= notice:
                    with log.open('rb') as reader:
                        reader.seek(cursor)
                        lines = reader.read(65536).splitlines()
                        cursor = reader.tell()
                    progress = None
                    for line in reversed(lines):
                        try:
                            value = json.loads(line)
                            if isinstance(value, dict):
                                progress = value
                                break
                        except (ValueError, UnicodeDecodeError):
                            pass
                    print(json.dumps(dict(phase=label, host_child_running=True,
                        local_log_progress=progress, additional_PS5_probes=0)), flush=True)
                    notice = now + 30
                time.sleep(1)
        need(child.returncode == 0, 'Stop without retry; inspect ' + str(log))

    common = ['--workspace', args.workspace, '--current', args.current, '--mount-plan', args.mount_plan]
    idle()
    publication_result = args.publication / 'result.private.json'
    if not publication_result.exists():
        run('publish_iq2_up_model_overlay.py', common + ['--preparation', args.preparation,
            '--out', args.publication, '--submit-prepared'], 'source-placement', 16 * 3600)
    publication = load(publication_result)
    need(publication['completed'] and publication['preparation'] == record(args.preparation) and
         publication['whole_new_bytes_and_all_parent_identities_qualified'], 'All source bytes must positively seal first')
    idle()
    cache_scopes = []
    for index in range(8):
        out = args.out / ('source-cache-' + str(index))
        flags = common + ['--publication', publication_result, '--' + args.role + '48',
                          '--target-free-pages', '16384', '--out', out, '--execute']
        for completed in cache_scopes:
            flags += ['--completed-scope', completed]
        run('retire_published_iq2_source_cache.py', flags, 'source-cache-' + str(index), 300)
        result_path = out / 'result.private.json'
        value = load(result_path)
        need(value['completed'] and value['all_mappings_and_FDs_positively_retired'], 'The exact source-cache window must retire')
        cache_scopes.append(result_path)
        if value['observations']['free_after'] >= 16384:
            break
        if value['remaining_windows'] == 0:
            need(value['observations']['free_after'] >= 7374, 'The exhausted source scope cannot satisfy unchanged model readiness')
            break
    else:
        need(value['observations']['free_after'] >= 7374,
             'The finite source-cache allowance ended below unchanged model readiness; never replay consumed windows')
    profiles = ('MMVQ-off', 'MMVQ-on') if args.role == 'Gate' else ('full-plane', 'source-prefix')
    screens = []
    for variant in profiles:
        idle()
        package_root = args.out / (variant + '-package')
        flags = ['--workspace', args.workspace, '--current', args.current, '--preparation', args.preparation,
                 '--publication', publication_result, '--cache-baseline', args.cache_baseline,
                 '--arithmetic-qualification', args.arithmetic_qualification, '--candidate-only', '--out', package_root]
        if args.role == 'Gate':
            flags += ['--cache-provider-proof', args.Up_cache_provider]
            if variant == 'MMVQ-on':
                flags += ['--MMVQ-decode-qualification', args.MMVQ_decode_qualification]
        else:
            flags += ['--Down-resource-provider', args.Down_resource_provider]
            if variant == 'source-prefix':
                flags += ['--Down-prefix-cache', '--cache-provider-proof', args.Down_prefix_provider]
        run('build_iq2_up_model.py', flags, variant + '-build')
        package = package_root / 'candidate/SELF/result.private.json'
        case = args.out / (variant + '-case')
        run('run_successful_headless_audit.py', common + ['--package', package, '--model-proof', args.model_proof,
            '--direct-staging-proof', args.direct_staging_proof, '--native-VM-proof', args.native_VM_proof,
            '--readiness-pages', '7374', '--quiet-seconds', '35', '--out', case], variant + '-native')
        idle()
        returned_case = load(case / 'result.private.json')
        if not returned_case['all_counting_and_finite_checks']:
            screens.append(dict(variant=variant, result=record(case / 'result.private.json'),
                                counting_or_finite_screen_negative=True, production_adopted=False))
            continue
        analysis = args.out / (variant + '-screen.private.json')
        run('analyze_iq2_pair_screen.py', ['--control-case', args.baseline_case, '--candidate-case', case,
            '--out', analysis], variant + '-analysis', 120)
        screens.append(dict(variant=variant, result=record(case / 'result.private.json'), analysis=record(analysis)))
    followed = None
    if followups.exists():
        scopes = args.out / 'initial-followup-cache-scopes.private.json'
        save(scopes, [str(path) for path in cache_scopes])
        followed = args.out / 'stream-followups'
        run('run_iq2_stream_followups.py', common + ['--model-proof', args.model_proof,
            '--direct-staging-proof', args.direct_staging_proof, '--native-VM-proof', args.native_VM_proof,
            '--cache-baseline', args.cache_baseline, '--baseline-case', args.baseline_case,
            '--config', followups, '--initial-cache-scopes', scopes, '--out', followed], 'stream-followups', 6 * 3600)
    save(args.out / 'result.private.json', dict(completed=True, role=args.role, source=record(publication_result),
        screens=screens, observations_per_arm=1, matched_ABBA=False, ordinary_restoration_after_every_case=True,
        initializer_requests=0, automatic_retries=0, production_adopted=False,
        matched_control_and_heldout_quality_required_for_any_gain=True,
        format_stream_followups=record(followed / 'result.private.json') if followed else None))
    print(json.dumps(dict(completed=True, role=args.role, screened_profiles=2, production_adopted=False)), flush=True)


if __name__ == '__main__':
    main()
