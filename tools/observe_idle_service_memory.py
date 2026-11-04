#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe bounded existing-service VM metadata once; never alter a service."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from build_performance_quantizer import record
from start_success_route import load, need, save
from success_case_control import build, current_files, execute, lan_module

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    state = load(a.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and state['successful_route_20261102']['runtime_pid'] == 154,
         'The positively closed current-boot services are required')
    a.out.mkdir(parents=True, exist_ok=False)
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    exe = a.out / 'summary-controls.exe'
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''))
    commands = [[str(host / 'clang.exe'), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                 '-Wno-unused-function', '-I', str(ROOT / 'native/qwen_flash_next'),
                 str(ROOT / 'tests/idle_service_memory_test.c'), '-o', str(exe)], [str(exe)]]
    for index, command in enumerate(commands):
        result = subprocess.run(command, capture_output=True, timeout=30, env=env)
        (a.out / (str(index) + '.private.log')).write_bytes(result.stdout + result.stderr)
        need(result.returncode == 0, result.stderr.decode(errors='replace')[-2500:])
    header = ROOT / 'native/qwen_flash_next/idle_service_memory.h'
    rows = current_files(a.current)
    context = '#include "idle_service_memory.h"\n'
    plan = build(a.workspace, a.mount_plan, rows, rows, [], 'retire-completed-images',
                 a.out / 'native', completed_images_context=context)
    save(a.out / 'intent.private.json', dict(source=record(header), summary_controls=6, commands=commands,
        targets=[84, 88, 89, 154], maximum_VM_queries=8, target_memory_reads=0, mapping_changes=0,
        pressure_allocations=0, service_changes=0, title_launches=0, GPU_calls=0, automatic_retries=0))
    if not a.execute:
        return
    result = execute(lan_module(), plan, a.out / 'native', 60)
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'],
         'Positive metadata helper completion and retirement required')
    raw = Path(result['raw']['path']).read_text()
    need('IDLE_SERVICE_COMPLETE read_only=1 all_metadata_calls_returned=1' in raw,
         'One complete metadata observation is required')
    resources = [dict(pid=int(pid), name=name, virtual_bytes=int(size), RSS_pages=int(rss))
                 for pid, name, size, rss in re.findall(
                     r'IDLE_SERVICE_RESOURCE pid=(\d+) name=(\S+) start_sec=\d+ start_usec=\d+ virtual_bytes=(\d+) RSS_pages=(\d+)', raw)]
    summaries = [dict(pid=int(pid), parsed=parsed == '1', entries=int(entries), virtual_bytes=int(size),
                      resident_pages=int(resident), private_pages=int(private), file_entries=int(files), file_resident_pages=int(file_resident))
                 for pid, parsed, entries, size, resident, private, files, file_resident in re.findall(
                     r'IDLE_SERVICE_VM_SUMMARY pid=(\d+) parsed=(\d+) entries=(\d+) virtual_bytes=(\d+) resident_pages=(\d+) private_pages=(\d+) file_entries=(\d+) file_resident_pages=(\d+)', raw)]
    need(len(resources) == 8, 'Before/after process identities must both return')
    save(a.out / 'result.private.json', dict(completed=True, resources=resources, VM_summaries=summaries,
        native=record(a.out / 'native/result.private.json'), source=record(header), RSS_is_not_unique_physical=True,
        target_memory_reads=0, mapping_changes=0, pressure_allocations=0, service_changes=0,
        title_launches=0, GPU_calls=0, initializer_requests=0, automatic_retries=0))
    print(json.dumps(dict(completed=True, resources=resources, VM_summaries=summaries,
                          service_changes=0, title_launches=0, GPU_calls=0)))


if __name__ == '__main__':
    main()
