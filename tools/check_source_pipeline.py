#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce source-pipeline and memory-admission checks without console access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model-io-manifest', type=Path,
                        help='Also check the actual compiled expert-cache upload loop')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    host = args.workspace / 'toolchain/msys-clang64/clang64/bin'
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''))
    sources = [ROOT / 'native/app' / name for name in (
        'mapped_source.h', 'mapped_source.cpp', 'mapped_source_bridge.h', 'paired_source_io.h',
        'profile_clock.h', 'memory_backpressure.h', 'system_memory.h', 'system_memory.cpp',
        'source_contention.h', 'source_contention.cpp', 'source_read_schedule.h')]
    sources += [ROOT / 'native/diagnostics/sys/priority.h']
    sources += [ROOT / 'tests' / name for name in (
        'pipeline_source.cpp', 'source_trace.cpp', 'selected_source.cpp', 'memory_backpressure.cpp', 'paired_cache.cpp', 'mapped_source.cpp')]
    sources += [Path(__file__), ROOT / 'tools/check_mapped_source.py', ROOT / 'tools/performance_result.py']
    sources += [ROOT/'tests/test_performance_result.py',ROOT/'tools/observe_native_plan.py']
    sources += [ROOT/'native/app/native_main.cpp',ROOT/'native/app/native_bootstrap.cpp',ROOT/'native/app/stage_memory_probe.h']
    before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    receipt = dict(state='running', console_requests=0, GPU_operations=0,
                   learned_model_inference=False, inputs=before, steps=[])

    def save():
        (args.out / 'receipt.private.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, command):
        result = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                                capture_output=True, timeout=180)
        (args.out / (name + '.private.log')).write_bytes(result.stdout + result.stderr)
        receipt['steps'].append(dict(name=name, returncode=result.returncode))
        save()
        if result.returncode:
            raise RuntimeError(name + ': ' + result.stderr.decode('utf-8', 'replace')[-3000:])
        print(name + ' passed', flush=True)

    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-I', ROOT / 'native/app']
    try:
        for name in ('pipeline_source', 'source_trace', 'selected_source', 'memory_backpressure'):
            exe = args.out / (name + '.exe')
            run(name + '_compile', [host / 'clang++.exe', *flags, ROOT / 'tests' / (name + '.cpp'), '-o', exe])
            run(name + '_controls', [exe])
            if name == 'pipeline_source':
                # Host-only subprocess: an actual ten-second unknown-read case
                # retains backing and exits without invoking unsafe destructors.
                run('unknown_read_retains_worker', [exe, 'uncertain'])
        run('source_controls_and_PS5_objects', [sys.executable, '-X', 'utf8', '-B',
            ROOT / 'tools/check_mapped_source.py', '--workspace', args.workspace,
            '--out', args.out / 'source-controls'])
        if args.model_io_manifest:
            from build_model_io import validate_overrides
            manifest = json.loads(args.model_io_manifest.read_text())
            validate_overrides(args.model_io_manifest, Path(manifest['base_engine_receipt']['path']))
            source = args.model_io_manifest.parent / 'source/src/llama-moe-cache.cpp'
            if sha(source) != manifest['sources']['src/llama-moe-cache.cpp']['patched_sha256']:
                raise ValueError('The compiled cache source differs from its receipt')
            text = source.read_text()
            start = text.index('        size_t bytes = 0;', text.index('    bool copy('))
            end = text.index('        stats & st =', start)
            body = text[start:end]
            if 'qwen_app_model_source_upload_pair(' not in body:
                raise ValueError('The selected cache does not use the qualified source pipeline')
            (args.out / 'actual_paired_cache_loop.h').write_text(
                'static std::size_t actual_cache_upload_loop(int backend,const Layer & l,'
                'const Group & g,const std::vector<Fill> & fills) {\n' + body + 'return bytes;\n}\n')
            exe = args.out / 'cache-loop.exe'
            run('actual_cache_loop_compile', [host / 'clang++.exe', *flags, '-I', args.out,
                ROOT / 'tests/paired_cache.cpp', '-o', exe])
            run('actual_cache_loop_byte_parity_and_failures', [exe])
            receipt['actual_compiled_cache_loop_checked'] = True
            receipt['compiled_cache_source_sha256'] = sha(source)
        else:
            receipt['actual_compiled_cache_loop_checked'] = False
        run('performance_record_controls', [sys.executable, '-X', 'utf8', '-B', '-m',
            'unittest', 'discover', '-s', 'tests', '-p', 'test_performance_result.py'])
        if before != {str(p.relative_to(ROOT)): sha(p) for p in sources}:
            raise RuntimeError('Check inputs changed during execution')
        receipt.update(state='focused_host_checks_passed_not_console_admitted',
                       source_window_bytes=8 << 20, maximum_outstanding_reads=1,
                       candidate_maximum_outstanding_reads=2,candidate_full_aligned_ranges_required=True,
                       maximum_memory_boundary_wait_ms=20000, maximum_memory_total_wait_ms=60000)
    except BaseException:
        receipt['state'] = 'failed'
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
