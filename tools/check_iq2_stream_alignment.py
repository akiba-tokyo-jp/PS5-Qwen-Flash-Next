#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check only the new logical/rounded-physical stream boundaries on the PC."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    tool = a.workspace / 'toolchain/msys-clang64/clang64/bin/clang++.exe'
    inputs = [record(ROOT / name) for name in ('native/app/iq2_stream_minimum_request.cpp', 'tests/iq2_stream_alignment_test.cpp')]
    results, commands = [], []
    env = dict(os.environ, PATH=str(tool.parent) + os.pathsep + os.environ['PATH'], TMP=str(a.out), TEMP=str(a.out))
    for layout in (1, 2):
        exe = a.out / ('alignment-' + str(layout) + '.exe')
        command = [str(tool), '-std=c++17', '-O2', '-DIQ2_STREAM_KIND=' + str(layout),
                   *[r['path'] for r in inputs], '-o', str(exe)]
        commands.append(command)
        child = subprocess.run(command, capture_output=True, timeout=120, env=env)
        (a.out / ('compile-' + str(layout) + '.private.log')).write_bytes(child.stdout + child.stderr)
        need(child.returncode == 0, child.stderr.decode(errors='replace')[-2000:])
        child = subprocess.run([str(exe)], capture_output=True, timeout=30, env=env)
        (a.out / ('run-' + str(layout) + '.private.log')).write_bytes(child.stdout + child.stderr)
        need(child.returncode == 0, 'The new alignment/EOF boundary failed')
        row = json.loads(child.stdout)
        need(row['completed'] and row['new_alignment_positives'] == 4 and row['new_EOF_negatives'] == 5 and
             row['destination_canaries_exact'] and row['logical_and_physical_bounds_separate'], 'All new boundaries must complete')
        results.append(row)
    save(a.out / 'result.private.json', dict(completed=True, inputs=inputs, results=results, commands=commands,
        old_wrapper_controls_replayed=0, native_graphs_replayed=0, new_native_builds=0, PS5_operations=0,
        real_owner_unchanged=True, native_IO_and_speed_not_qualified=True))
    print(json.dumps(dict(completed=True, layouts=2, new_alignment_positives=8, new_EOF_negatives=10,
                         PS5_operations=0, old_controls_replayed=0)))


if __name__ == '__main__':
    main()
