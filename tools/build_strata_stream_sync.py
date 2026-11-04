#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build two narrow stream-wait refinements and matched observer-free controls."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from retained_identity_proof import require_same_provider
from start_success_route import load, need, save
from strata_stream_sync import transform

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'cache-proof', 'identity-provider', 'observer', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    selected = load(args.current / 'provenance/selected-entry-build.private.json')
    original_profile = load(selected['application_policy']['path'])
    source = Path(original_profile['source']['path'])
    need(record(source) == original_profile['source'], 'Exact selected P1 source required')
    cache = load(args.cache_proof)
    need(cache['completed'] and record(cache['source']['path']) == cache['source'] and
         record(cache['actual_provider']['path']) == cache['actual_provider'], 'Selected cache provenance changed')
    original_identity = load(args.current / 'provenance/current-package.private.json')['required_bundle_identity_audit']['provider']
    require_same_provider(original_identity, record(args.identity_provider), args.current)
    for header in source.parent.glob('*.h'):
        shutil.copyfile(header, args.out / header.name)
    entry_command = next(row.copy() for row in selected['commands'] if '-ivfsoverlay' in row)
    view = load(entry_command[entry_command.index('-ivfsoverlay') + 1])
    for row in view['roots']:
        local = args.out / Path(row['external-contents']).name
        if local.is_file():
            row['external-contents'] = local.resolve().as_posix()
    overlay = args.out / 'selected-view.private.json'
    save(overlay, view)
    entry_command[entry_command.index('-ivfsoverlay') + 1] = str(overlay)
    entry_command[1:1] = ['-I', str(args.out)]
    commands = []

    def run(command, label):
        command = list(map(str, command))
        commands.append(command)
        result = subprocess.run(command, capture_output=True, timeout=600,
            env=dict(os.environ, TMP=str(args.out), TEMP=str(args.out)))
        with (args.out / (label + '.private.log')).open('xb') as stream:
            stream.write(result.stdout + result.stderr)
        need(result.returncode == 0, (result.stdout + result.stderr).decode(errors='replace')[-3500:])
        print(json.dumps(dict(phase=label, completed=True, PS5_operations=0)), flush=True)

    observer = load(args.observer)
    need(observer['completed'] and observer['qualification_only'] and not observer['performance_timings_usable'] and
         observer['host_forwarding_clear_and_geometry_fault_controls_passed'] and observer['independent_SHA256_fixture_passed'] and
         all(record(row['path']) == row for row in observer['inputs']), 'Reuse only the unchanged qualified F32 observer')
    inputs = load(args.current / 'provenance/retained-relink-inputs.private.json')
    engine = next(row for row in inputs if Path(row['original_path']).name == 'engine.o')
    need(all(engine[key] == observer['engine'][key] for key in ('bytes', 'sha256')), 'Actual engine observer ABI changed')
    observer_object = args.out / 'full-f32-observer.o'
    command = observer['commands'][-1].copy()
    command[command.index('-o') + 1] = str(observer_object)
    run(command, 'observer-byte-identical-rebuild')
    need(all(record(observer_object)[key] == observer['artifact'][key] for key in ('bytes', 'sha256')),
         'Retired observer must reconstruct byte identically; do not replay its completed controls')
    observer_receipt = args.out / 'observer.private.json'
    save(observer_receipt, dict(observer, artifact=record(observer_object), original_receipt=record(args.observer), old_tests_replayed=0))
    cache_objects = {'control': cache['actual_provider']}
    original_cache = Path(cache['source']['path']).read_text(encoding='utf-8')
    for mode in ('group', 'readback'):
        text = transform(original_cache, mode)
        path, target = args.out / (mode + '-cache.private.cpp'), args.out / (mode + '-cache.o')
        path.write_text(text, encoding='utf-8', newline='\n')
        command = cache['command'].copy()
        command[command.index('-c') + 1], command[command.index('-o') + 1] = str(path), str(target)
        if '-MF' in command:
            command[command.index('-MF') + 1] = str(args.out / (mode + '-cache.private.d'))
        run(command, mode + '-cache')
        cache_objects[mode] = record(target)
    baseline = source.read_text(encoding='utf-8')
    entries = {}
    scopes = {}
    for measured in (False, True):
        label = 'timed' if measured else 'observed'
        scope = dict(schema='ps5-qwen-strata-stream-sync-v1', kind='ST3-stream-sync', requests=3,
            model_loads=1, HTTP_requests=0, VideoOut_starts=0, original_cold_retained_exact_prefix_sequence=True,
            original_arithmetic_and_GPU_buffers_preserved=True, original_source_leases_preserved=True,
            selected_ID_readback_completion_preserved=True, positive_upload_callback_completion_preserved=True,
            timings_usable_for_performance=measured)
        marker = '        const auto policy = Json::parse(policy_file);'
        entry = once(baseline, marker, marker + '\n        if(policy.at("native_headless_model_audit")!=Json::parse(' +
            json.dumps(json.dumps(scope, separators=(',', ':'))) + '))throw std::runtime_error("Exact ST3 scope required");')
        entry = headless_entry(entry, scope['kind'], 3, 'Json{{"completed",true},{"requests",completed}}')
        if measured:
            entry = once(entry, '{"timings_usable_for_performance",false}', '{"timings_usable_for_performance",true}')
        for name in ('observed_system_headroom', 'require_model_CPU_budget', 'wait_for_initial_model_CPU_budget',
                     'model_file_identity', 'model_directory_identity', 'resident_reset_empty_context'):
            need(body(entry, name) == body(baseline, name), 'Original guard changed: ' + name)
        path, target = args.out / (label + '-entry.private.cpp'), args.out / (label + '-entry.o')
        path.write_text(entry, encoding='utf-8', newline='\n')
        command = entry_command.copy()
        command[command.index('-c') + 1], command[command.index('-o') + 1] = str(path), str(target)
        if '-MF' in command:
            command[command.index('-MF') + 1] = str(args.out / (label + '-entry.private.d'))
        run(command, label + '-entry')
        entries[label], scopes[label] = (record(path), record(target)), scope
    packages = {}
    for mode, label in (('group', 'observed'), ('readback', 'observed'), ('control', 'timed'), ('group', 'timed'), ('readback', 'timed')):
        name = mode + '-' + label
        source_row, entry_row = entries[label]
        profile = copy.deepcopy(original_profile)
        profile.update(kind='headless-model-audit', source=source_row, entry_artifact=entry_row,
            headless_model_audit=True, headless_audit_kind='ST3-stream-sync', headless_requests=3,
            model_and_GPU_topology_unchanged=False, model_and_GPU_guards_preserved=True,
            overrides=dict(original_profile['overrides'], native_headless_model_audit=scopes[label]),
            performance_timings_usable=label == 'timed', ST3_mode=mode,
            ST3_cache_artifact=cache_objects[mode], native_performance_qualified=False, production_adopted=False)
        if label == 'observed':
            profile['qualification_observer'] = record(observer_receipt)
        policy = args.out / (name + '-policy.private.json')
        save(policy, profile)
        link_dir, package_dir = args.out / (name + '-link'), args.out / (name + '-SELF')
        command = [sys.executable, '-B', ROOT / 'tools/relink_retained_current.py', '--current', args.current,
            '--out', link_dir, '--replace', 'entry.o=' + entry_row['path'], '--replace', 'cache.o=' + cache_objects[mode]['path'],
            '--replace', 'early-SELF.o=' + profile['CPU_SELF_provider']['artifact']['path'], '--application-policy', policy]
        if label == 'observed':
            command += ['--add-object', observer_object] + ['--link-flag=' + flag for flag in observer['link_flags']]
        run(command, name + '-link')
        run([sys.executable, '-B', ROOT / 'tools/package_retained_current.py', '--workspace', args.workspace,
             '--current', args.current, '--relink', link_dir / 'result.private.json', '--out', package_dir,
             '--formatter-from', args.current / 'provenance/current-package.private.json',
             '--identity-provider', args.identity_provider], name + '-package')
        packages[name] = record(package_dir / 'result.private.json')
    save(args.out / 'result.private.json', dict(completed=True, packages=packages, commands=commands,
        selected_entry=original_profile['source'], selected_cache=cache['source'], observer=record(observer_receipt),
        driver_and_shaders_unchanged=True, extra_GPU_buffers=0, old_tests_replayed=0, PS5_operations=0, production_adopted=False))


if __name__ == '__main__':
    main()
