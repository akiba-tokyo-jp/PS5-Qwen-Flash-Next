#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded metadata mapping ownership with host stubs; no console access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    host = args.workspace / 'toolchain/msys-clang64/clang64/bin'
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''))
    exe = args.out / 'file-residency.exe'
    commands = [
        ('compile', [host / 'clang.exe', '-std=c11', '-O2', '-Wall', '-Wextra',
                     '-Werror', '-I', ROOT / 'native/app', ROOT / 'tests/file_residency.c',
                     '-o', exe]),
        ('ownership-controls', [exe]),
    ]
    steps = []
    for label, command in commands:
        result = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                                capture_output=True, timeout=120)
        (args.out / (label + '.private.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(label + ': ' + result.stderr.decode(errors='replace')[-2500:])
        steps.append(dict(name=label, returncode=0))
        print(label + ' passed', flush=True)
    sources = [Path(__file__), ROOT / 'native/app/file_residency.h',
               ROOT / 'tests/file_residency.c']
    receipt = dict(steps=steps, inputs=[dict(path=str(p),
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources],
        host_API_stubs=True, PS5_operations=0, GPU_execution=False, CI_runs=0)
    (args.out / 'receipt.private.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
