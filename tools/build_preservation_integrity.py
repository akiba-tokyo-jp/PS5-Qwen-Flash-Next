#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build bounded artifact integrity from a positively executed CPU controller; never execute."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE = 128 << 20
MAX_TOTAL = 256 << 20


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def sources(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {'schema', 'sources'} or manifest['schema'] != 'ps5-qwen-closed-artifacts-v1':
        raise ValueError('A closed-artifact manifest is required')
    rows = manifest['sources']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
        raise ValueError('One to 64 bounded sources are required')
    seen, total = set(), 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'remote_path', 'capture', 'producer_positively_closed'} or row['producer_positively_closed'] is not True:
            raise ValueError('Every producer must have positively closed')
        path, capture = row['remote_path'], row['capture']
        if not isinstance(path, str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+', path) or '//' in path or any(x in ('.', '..') for x in path.split('/')):
            raise ValueError('An exact owned regular-file path is required')
        if not (path.startswith('/data/ai/moss-') or path.startswith('/data/ai/native-moss-image-sft/PPSA99190/')) or path in seen:
            raise ValueError('Sources must be distinct owned artifacts')
        if not isinstance(capture, dict) or set(capture) != {'path', 'bytes', 'sha256'}:
            raise ValueError('An exact complete captured-file record is required')
        if type(capture['bytes']) is not int or not 0 < capture['bytes'] <= MAX_FILE or not isinstance(capture['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', capture['sha256']):
            raise ValueError('Captured size or digest is invalid')
        if record(capture['path']) != capture:
            raise ValueError('The captured bytes changed')
        seen.add(path)
        total += capture['bytes']
    if total > MAX_TOTAL:
        raise ValueError('The complete source set exceeds its bounded envelope')
    return rows


def context_header(rows, nonce):
    if not re.fullmatch('[0-9a-f]{32}', nonce):
        raise ValueError('A fresh control nonce is required')
    text = '#define PRESERVATION_NONCE ' + json.dumps(nonce) + '\n'
    text += 'struct preservation_source {const char *path;uint64_t bytes;const char *sha256;};\n'
    text += 'static const struct preservation_source preservation_sources[]={\n'
    for row in rows:
        capture = row['capture']
        text += '{' + json.dumps(row['remote_path']) + ',' + str(capture['bytes']) + 'ULL,' + json.dumps(capture['sha256']) + '},\n'
    return text + '};\n'


def qualified_base(manifest, execution_path):
    artifact = manifest['CPU_probe']
    if record(artifact['path']) != artifact:
        raise ValueError('The qualified CPU image changed')
    execution_path = Path(execution_path)
    execution = json.loads(execution_path.read_text())
    if any(execution['artifact'][k] != artifact[k] for k in ('bytes', 'sha256')) or execution.get('automatic_retries') != 0:
        raise ValueError('The execution does not bind this CPU image')
    log = execution_path.parent / 'console.private.log'
    raw = log.read_bytes()
    ends = [x for x in raw.splitlines() if x.startswith(b'END ')]
    if len(ends) != 1 or b'success=1 ' not in ends[0] or ('nonce=' + manifest['nonce']).encode() not in ends[0] or b'CPU_only=1 title_launches=0 GPU_calls=0' not in raw:
        raise ValueError('A positive CPU-only native completion is required')
    commands = manifest['CPU_probe_commands']
    if len(commands) != 2 or any(not isinstance(c, list) or not c or not all(isinstance(x, str) for x in c) for c in commands):
        raise ValueError('The qualified compile/link commands are required')
    return artifact, commands, log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('qualified-build', 'execution-record', 'sources', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    base_manifest = json.loads(args.qualified_build.read_text())
    image, commands, completion = qualified_base(base_manifest, args.execution_record)
    rows = sources(json.loads(args.sources.read_text()))
    base = Path(image['path']).parent
    required = ['direct-controller.c', 'session_context.h']
    for name in required:
        if not (base / name).is_file():
            raise ValueError('The qualified controller sources are required')
    original_inputs = {r['path']: r for r in base_manifest['inputs']}
    selected = [p for p in base.iterdir() if p.is_file() and p.suffix == '.h' and str(p.resolve()) in original_inputs]
    selected += [base / 'direct-controller.c']
    for path in selected:
        if original_inputs.get(str(path.resolve())) != record(path):
            raise ValueError('A qualified controller source or header changed')
    sha_command = base_manifest['commands'][0]
    if '-c' not in sha_command or str(base / 'sha256.o') not in sha_command:
        raise ValueError('The qualified SHA256 compilation is required')
    sha_inputs = [Path(x) for x in sha_command if Path(x).is_file() and Path(x).suffix in ('.c', '.h', '.exe')]
    if not sha_inputs or any(original_inputs.get(str(p.resolve())) != record(p) for p in sha_inputs):
        raise ValueError('A qualified SHA256 build input changed')
    qualified_headers = [Path(row['path']) for row in original_inputs.values()
                         if Path(row['path']).suffix in ('.h', '.so')]
    if not qualified_headers or any(record(p) != original_inputs[str(p.resolve())] for p in qualified_headers):
        raise ValueError('A qualified ABI header or runtime provider changed')
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'tmp').mkdir()
    for path in selected:
        (args.out / path.name).write_bytes(path.read_bytes())
    nonce = secrets.token_hex(16)
    prefix = '/data/ai/moss-qwen-preserved-' + nonce
    header = args.out / 'session_context.h'
    text, count = re.subn(r'^#define LAUNCH_LOG_PREFIX .*$', '#define LAUNCH_LOG_PREFIX ' + json.dumps(prefix), header.read_text(), flags=re.M)
    if count != 1:
        raise ValueError('The qualified exclusive journal binding differs')
    header.write_text(text, newline='\n')
    (args.out / 'preservation_context.h').write_text(context_header(rows, nonce), newline='\n')
    native_source = ROOT / 'native/qwen_flash_next/preservation_integrity_probe.c'
    (args.out / 'CPU-probe.c').write_bytes(native_source.read_bytes())
    frozen_paths = [Path(__file__), native_source, *sha_inputs, *qualified_headers, args.qualified_build, args.execution_record,
                    completion, args.sources, *[args.out / p.name for p in selected],
                    args.out / 'CPU-probe.c', args.out / 'preservation_context.h',
                    ROOT / 'native/qwen_flash_next/launch_integrity.h',
                    ROOT / 'native/qwen_flash_next/launch_integrity_native.h']
    before = [record(p) for p in frozen_paths]
    rewritten = [[x.replace(str(base), str(args.out)) for x in c] for c in [sha_command, *commands]]
    for i, command in enumerate(rewritten):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120,
            env=dict(os.environ, TMP=str(args.out / 'tmp'), TEMP=str(args.out / 'tmp')))
        (args.out / f'build-{i}.private.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-2500:])
    artifact = args.out / 'CPU-probe.elf'
    nm = Path(commands[0][0]).parent / 'llvm-nm.exe'
    def imports(path):
        raw = subprocess.check_output([str(nm), '-D', '--undefined-only', '--format=posix', str(path)], text=True)
        return {line.split()[0] for line in raw.splitlines() if line.split()}
    names = imports(artifact)
    if not names <= imports(image['path']) or not {'pread', 'fcntl', 'clock_gettime', 'sysctlbyname'} <= names:
        raise ValueError('The actual native imports exceed the qualified CPU image')
    if before != [record(p) for p in frozen_paths]:
        raise ValueError('A frozen build input changed')
    receipt = dict(schema='ps5-qwen-preservation-integrity-build-v1', nonce=nonce,
        artifact=record(artifact), inputs=before, commands=rewritten,
        qualified_CPU_image=image, qualified_execution=record(args.execution_record),
        source_manifest=record(args.sources), sources=rows,
        remote_elf=prefix + '.elf', remote_log=prefix + '-CPU.log',
        actual_native_imports=sorted(names), imports_subset_of_executed_image=True,
        input_window_bytes=1 << 20, maximum_sources=64, maximum_file_bytes=MAX_FILE,
        maximum_total_bytes=MAX_TOTAL, checkpoint_deadline_seconds=20,
        cache_advice_calls=0, automatic_retries=0, PS5_operations=0, CI_runs=0)
    (args.out / 'manifest.private.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(built=True, sources=len(rows), source_bytes=sum(r['capture']['bytes'] for r in rows),
                         imports_subset_of_executed_image=True, PS5_operations=0, CI_runs=0)), flush=True)


if __name__ == '__main__':
    main()
