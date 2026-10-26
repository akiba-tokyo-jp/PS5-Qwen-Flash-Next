#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check a metadata-reuse prototype against pinned actual batch methods.

This performs no model arithmetic or console access. Host timing is not PS5
timing. Extracted methods are retained with exact source hashes for inspection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = '0a1ef309cdbb9f2024f58a38fb4c42352c5db569'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    upstream = args.cache / ('upstream/llama.cpp-' + REVISION)
    source = upstream / 'src/llama-batch.cpp'
    text = source.read_text(encoding='utf-8')
    start = text.index('llama_batch_ext::llama_batch_ext(\n        size_t')
    end = text.index('// llama_batch_ext C API', start)
    extracted = args.out / 'actual_batch_metadata.cpp'
    extracted.write_text('#include "llama-batch.h"\n#define LLAMA_LOG_ERROR(...) ((void)0)\n' +
                         text[start:end], encoding='utf-8', newline='\n')
    host = args.workspace / 'toolchain/msys-clang64/clang64/bin'
    executable = args.out / 'batch-metadata-tests.exe'
    include_dirs = [ROOT/'native/app', upstream/'src', upstream/'include', upstream/'ggml/include']
    command = [str(host/'clang++.exe'), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']
    for path in include_dirs:
        command += ['-I', str(path)]
    command += [str(extracted), str(ROOT/'tests/batch_metadata_reuse.cpp'), '-o', str(executable)]
    env = dict(os.environ, PATH=str(host)+os.pathsep+os.environ.get('PATH', ''))
    for name, cmd in [('compile', command), ('run', [str(executable)])]:
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=90)
        (args.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(name+' failed: '+result.stderr.decode('utf-8', 'replace')[-3000:])
    measured = json.loads(result.stdout)
    measured.update(schema='ps5-qwen-batch-metadata-screen-v1', upstream_revision=REVISION,
                    original_batch_cpp_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    extracted_methods_sha256=hashlib.sha256(extracted.read_bytes()).hexdigest(),
                    prototype_sha256=hashlib.sha256((ROOT/'native/app/batch_metadata_reuse.h').read_bytes()).hexdigest(),
                    tests_sha256=hashlib.sha256((ROOT/'tests/batch_metadata_reuse.cpp').read_bytes()).hexdigest(),
                    actual_batch_header_sha256=hashlib.sha256((upstream/'src/llama-batch.h').read_bytes()).hexdigest(),
                    native_qualification=False, production_linked=False, CI=False,
                    command=command, error_logging_unexercised_and_disabled_in_metadata_fixture=True)
    (args.out/'receipt.private.json').write_text(json.dumps(measured, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in measured.items() if k not in ['command','rounds']}), flush=True)


if __name__ == '__main__':
    main()
