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
    parser.add_argument('--host-preflight-continuation', type=Path,
                        help='Continue only a recorded zero-publication, zero-title host refusal')
    parser.add_argument('--prebuilt-first-profile', type=Path,
                        help='Reuse the exact candidate whose host-only startup preflight was refused')
    parser.add_argument('--completed-cache-scope', type=Path, action='append', default=[])
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
    if args.host_preflight_continuation:
        continuation = load(args.host_preflight_continuation)
        need(continuation['completed'] and continuation['PS5_operations'] == 0 and
             continuation['previous_title_launches'] == continuation['previous_source_publications'] == 0 and
             continuation['serializer'] == record(ROOT / 'tools/run_successful_model_case.py') and
             continuation['all_original_policy_fields_and_values_preserved'] and
             continuation['unchanged_native_metadata_limit_bytes'] == 1 << 20 and
             args.prebuilt_first_profile and len(args.completed_cache_scope) == 1 and
             continuation['prior_source_cache_scope'] == record(args.completed_cache_scope[0]),
             'Only the exact corrected host-only preflight may reuse its unexecuted candidate and completed cache prefix')
        frozen.append(record(args.host_preflight_continuation))
    else:
        need(not args.prebuilt_first_profile and not args.completed_cache_scope,
             'Previously prepared inputs require their exact zero-operation preflight continuation')
    if args.prebuilt_first_profile:
        built = load(args.prebuilt_first_profile)
        need(built['completed'] and built['preparation'] == record(args.preparation) and
             built['publication'] == record(args.publication / 'result.private.json') and
             built['arithmetic_qualification'] == record(args.arithmetic_qualification) and
             built['cache_baseline'] == record(args.cache_baseline) and not built['F32_qualification'] and
             not built['MMVQ_decode_qualification'] and not built['Down_source_prefix_cache'] and
             not built['format_stream_provider'] and
             built['packages']['candidate'] == continuation['reused_candidate_package'],
             'The exact already built first profile must match every source and arithmetic input')
        frozen.append(record(args.prebuilt_first_profile))
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

    def run(name, flags, label, timeout=1800, prelaunch_out=None):
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
        if child.returncode != 0 and prelaunch_out is not None:
            path = prelaunch_out / 'VM-before/result.private.json'
            if path.exists() and not (prelaunch_out / 'case').exists():
                refusal = load(path)
                need(refusal['completed'] and not refusal['may_launch'] and
                     refusal['selected_readiness_pages'] == 7374,
                     'Only a readiness-only refusal before staging may advance to a distinct cache scope')
                idle()
                save(prelaunch_out / 'readiness-only-refusal.private.json', dict(completed=True,
                    observation=record(path), title_launches=0, source_publications=0,
                    changed_cache_scope_required_before_next_admission=True))
                return False
        need(child.returncode == 0, 'Stop without retry; inspect ' + str(log))
        return True

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
    cache_scopes = args.completed_cache_scope.copy()
    first = 0
    for path in cache_scopes:
        value, intent = load(path), load(path.parent / 'intent.private.json')
        need(value['completed'] and value['all_mappings_and_FDs_positively_retired'] and
             value['starting_window'] == first and intent['publication'] == record(publication_result) and
             intent['publication_scope'] == args.role + '48' and
             intent['boot'] == load(args.current / 'active-console.private.json')['current_boot'],
             'Only the exact same-boot positive source-cache prefix may be retained')
        first += value['observations']['scanned']
    def retire_cache():
        out = args.out / ('source-cache-' + str(len(cache_scopes)))
        flags = common + ['--publication', publication_result, '--' + args.role + '48',
                          '--target-free-pages', '16384', '--out', out, '--execute']
        for completed in cache_scopes:
            flags += ['--completed-scope', completed]
        run('retire_published_iq2_source_cache.py', flags, out.name, 300)
        result_path = out / 'result.private.json'
        result = load(result_path)
        need(result['completed'] and result['all_mappings_and_FDs_positively_retired'],
             'The exact source-cache window must retire')
        cache_scopes.append(result_path)
        return result

    for index in range(8):
        if cache_scopes and (value['observations']['free_after'] >= 16384 or value['remaining_windows'] == 0):
            need(value['observations']['free_after'] >= 7374, 'The preserved prefix cannot replace model readiness')
            break
        value = retire_cache()
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
        if variant == profiles[0] and args.prebuilt_first_profile:
            package = Path(built['packages']['candidate']['path'])
            save(args.out / (variant + '-reused-build.private.json'), dict(completed=True,
                build=record(args.prebuilt_first_profile), package=record(package), compilations_replayed=0))
        else:
            run('build_iq2_up_model.py', flags, variant + '-build')
            package = package_root / 'candidate/SELF/result.private.json'
        case = args.out / (variant + '-case')
        native_flags = common + ['--package', package, '--model-proof', args.model_proof,
            '--direct-staging-proof', args.direct_staging_proof, '--native-VM-proof', args.native_VM_proof,
            '--readiness-pages', '7374', '--quiet-seconds', '35']
        if not run('run_successful_headless_audit.py', native_flags + ['--out', case],
                   variant + '-native', prelaunch_out=case):
            for _ in range(8):
                need(value['remaining_windows'] > 0, 'Never replay an exhausted source-cache pool')
                value = retire_cache()
                if value['observations']['free_after'] >= 7374:
                    break
            else:
                need(False, 'No distinct cache scope returned enough capacity; do not query readiness again')
            case = case.with_name(case.name + '-after-distinct-cache')
            run('run_successful_headless_audit.py', native_flags + ['--out', case], variant + '-native-after-distinct-cache')
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
