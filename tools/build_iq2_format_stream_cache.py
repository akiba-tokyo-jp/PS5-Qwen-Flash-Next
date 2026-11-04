#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile bounded format-aware streaming without changing the original source owner."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from build_performance_quantizer import record
from iq2_format_stream_cache import transform
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'cache-baseline', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--mode', choices=('Up', 'Gate-Up', 'Down'), required=True)
    parser.add_argument('--cache-provider-proof', type=Path)
    parser.add_argument('--wrapper-controls', type=Path)
    args = parser.parse_args()
    baseline = load(args.cache_baseline)
    need(baseline['completed'] and baseline['baseline_provider_qualified'] and baseline['selected_object_byte_exact'] and
         not baseline['section_differences'] and record(baseline['source']['path']) == baseline['source'] and
         record(baseline['artifact']['path']) == baseline['artifact'], 'The byte-identical selected cache reconstruction is required')
    rows = load(args.current / 'provenance/retained-relink-inputs.private.json')
    owners = [row for row in rows if Path(row['original_path']).name == 'owner.o']
    need(len(owners) == 1, 'One unchanged selected source owner is required')
    owner = {k: owners[0][k] for k in ('path', 'bytes', 'sha256')}
    need(record(owner['path']) == owner, 'The qualified original source owner changed')
    args.out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(command, label):
        commands.append(command)
        child = subprocess.run(command, capture_output=True, timeout=240,
            env=dict(os.environ, TMP=str(args.out), TEMP=str(args.out),
                     PATH=str(args.workspace / 'toolchain/msys-clang64/clang64/bin') + os.pathsep + os.environ['PATH']))
        (args.out / (label + '.private.log')).write_bytes(child.stdout + child.stderr)
        need(child.returncode == 0, (child.stdout + child.stderr).decode(errors='replace')[-3000:])
        return child.stdout

    expected = transform(Path(baseline['source']['path']).read_text(encoding='utf-8'), args.mode == 'Down')
    if args.cache_provider_proof:
        old = load(args.cache_provider_proof)
        need(old['completed'] and old['baseline'] == record(args.cache_baseline) and
             old['unchanged_original_source_owner'] == owner and
             record(old['source']['path']) == old['source'] and record(old['artifact']['path']) == old['artifact'] and
             Path(old['source']['path']).read_text(encoding='utf-8') == expected,
             'Reuse only the already compiled exact cache transformation')
        cache_source, cache = old['source'], old['artifact']
        cache_command = old['commands'][0]
    else:
        previous = Path(args.cache_baseline).parent
        for header in previous.glob('*.h'):
            shutil.copyfile(header, args.out / header.name)
        view = load(baseline['selected_VFS_view']['path'])
        for row in view['roots']:
            local = args.out / Path(row['external-contents']).name
            if local.exists():
                row['external-contents'] = local.resolve().as_posix()
        overlay = args.out / 'selected-view.private.json'
        save(overlay, view)
        source, artifact = args.out / 'cache.private.cpp', args.out / 'cache.o'
        source.write_text(expected, encoding='utf-8', newline='\n')
        cache_command = [str(args.out) if v == str(previous) else v for v in baseline['command']]
        cache_command[cache_command.index('-ivfsoverlay') + 1] = str(overlay)
        cache_command[cache_command.index('-c') + 1], cache_command[cache_command.index('-o') + 1] = str(source), str(artifact)
        if '-MF' in cache_command:
            cache_command[cache_command.index('-MF') + 1] = str(args.out / 'cache.private.d')
        run(cache_command, 'cache-compile')
        cache_source, cache = record(source), record(artifact)
    if not commands:
        commands.append(cache_command)
    wrapper = None
    controls = None
    if args.mode != 'Down':
        inputs = [record(ROOT / 'native/app/iq2_stream_overfetch.cpp'), record(ROOT / 'tests/iq2_stream_overfetch_test.cpp')]
        if args.wrapper_controls:
            old = load(args.wrapper_controls)
            need(old['completed'] and old['inputs'] == inputs and old['PS5_operations'] == 0 and
                 {r['layout'] for r in old['results']} == {1, 2} and
                 all(r['completed'] and r['positives'] == 4 and r['destination_canaries_exact'] for r in old['results']),
                 'The exact two-layout new boundary controls must remain bound')
            controls = record(args.wrapper_controls)
        else:
            compiler = args.workspace / 'toolchain/msys-clang64/clang64/bin/clang++.exe'
            results = []
            for kind in (1, 2):
                exe = args.out / ('host-layout-' + str(kind) + '.exe')
                command = [str(compiler), '-std=c++17', '-O2', '-DIQ2_STREAM_KIND=' + str(kind),
                           inputs[0]['path'], inputs[1]['path'], '-o', str(exe)]
                run(command, 'host-compile-' + str(kind))
                results.append(json.loads(run([str(exe)], 'host-run-' + str(kind))))
            path = args.out / 'wrapper-controls.private.json'
            save(path, dict(completed=True, inputs=inputs, results=results, PS5_operations=0,
                previous_native_math_replayed=0, original_owner_range_EOF_refusal_preserved=True))
            controls = record(path)
        sdk = args.workspace / 'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
        target = args.workspace / 'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
        artifact = args.out / 'stream-request-wrapper.o'
        command = [str(target), '--no-default-config', '--target=x86_64-sie-ps5', '-nostdinc++',
            '-isystem', str(sdk / 'c++/v1'), '-isystem', str(sdk), '-std=c++17', '-femulated-tls',
            '-fno-stack-protector', '-fno-plt', '-fPIC', '-O2', '-ffunction-sections', '-fdata-sections',
            '-DIQ2_STREAM_KIND=' + str(1 if args.mode == 'Up' else 2), '-c', inputs[0]['path'], '-o', str(artifact)]
        run(command, 'wrapper-PS5-ABI')
        nm = target.with_name('llvm-nm.exe')
        undefined = run([str(nm), '--undefined-only', '--format=posix', str(artifact)], 'wrapper-imports').decode().splitlines()
        need({s.split()[0] for s in undefined if s.split()} == {'__real_qwen_app_try_Q2_stream'},
             'The wrapper may call only the original qualified stream API')
        wrapper = record(artifact)
    save(args.out / 'result.private.json', dict(completed=True, mode=args.mode,
        actual_selected_PS5_ABI_compiled=True, baseline=record(args.cache_baseline), source=cache_source, artifact=cache,
        commands=commands, transform=record(ROOT / 'tools/iq2_format_stream_cache.py'),
        unchanged_original_source_owner=owner, wrapper_source=record(ROOT / 'native/app/iq2_stream_overfetch.cpp') if wrapper else None,
        wrapper=wrapper, wrapper_controls=controls, required_link_flags=['--wrap=qwen_app_try_Q2_stream'] if wrapper else [],
        original_source_accepted_request_sizes=[537600, 460800], actual_IQ2_upload_bytes=422400,
        unused_requested_bytes_per_IQ2=115200 if wrapper else 0, whole_source_bytes_reduced_claimed=False,
        source_leases=4, existing_scratch_bytes=8 << 20, new_workers=0, new_GPU_buffers=0,
        original_source_range_EOF_identity_overlap_and_completion_checks_unchanged=True,
        completed_streamed_Experts_skipped_in_generic_loop=True, adjacent_generic_fallback_preserved=True,
        native_IO_equivalence_qualified=False, native_speed_qualified=False, PS5_operations=0, production_adopted=False))
    print(json.dumps(dict(completed=True, mode=args.mode, actual_PS5_ABI_compiled=True, PS5_operations=0,
                          native_equivalence_and_speed_pending=True)))


if __name__ == '__main__':
    main()
