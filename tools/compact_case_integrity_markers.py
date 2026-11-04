#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bound a CPU helper's journal without changing its integrity IO or admission."""
import json
import os
from pathlib import Path
import re
import subprocess

from build_performance_quantizer import record
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = '''static int qwen_launch_marker(void *unused,int before) {
    (void)unused;return report(before?"LAUNCH_INTEGRITY_READ_BEFORE":"LAUNCH_INTEGRITY_READ_RETURNED");
}'''
COMPACT = '''static uint64_t qwen_marker_calls,qwen_marker_returns;
static int qwen_launch_marker(void *unused,int before) {
    (void)unused;
    if(!healthy||journal<0)return 0;
    if(before){
        if(qwen_marker_calls!=qwen_marker_returns||qwen_marker_calls==UINT64_MAX)return 0;
        ++qwen_marker_calls;
    }else{
        if(qwen_marker_calls!=qwen_marker_returns+1||qwen_marker_returns==UINT64_MAX)return 0;
        ++qwen_marker_returns;
    }
    return 1;
}'''


def compact(plan, out, control):
    """Relink a never submitted helper with an isolated marker-only header copy."""
    out, control = Path(out), Path(control)
    checked = load(control)
    need(checked['completed'] and checked['PS5_operations'] == 0 and
         checked['source'] == record(Path(__file__)) and
         checked['healthy_pairs'] == 10000 and checked['negative_cases'] == 6,
         'Qualify compact marker state transitions on the host first')
    need(plan['operation'] == 'retire-completed-images' and
         not (out / 'execution').exists() and not (out / 'result.private.json').exists(),
         'Only an unsubmitted CPU retirement helper may compact its own diagnostic journal')
    original = ROOT / 'native/qwen_flash_next/launch_integrity_native.h'
    text = original.read_text(encoding='utf-8')
    need(text.count(ORIGINAL) == 1, 'One exact diagnostic marker adapter is required')
    adapted = text.replace(ORIGINAL, COMPACT, 1)
    need(adapted.replace(COMPACT, ORIGINAL, 1) == text,
         'Keep every SHA, EOF, IO, clock, headroom, identity and close instruction exact')
    header = out / 'compact_launch_integrity_native.h'
    header.write_text(adapted, encoding='utf-8', newline='\n')
    controller = Path(plan['controller']['path'])
    source = controller.read_text(encoding='utf-8')
    marker = '#include "launch_integrity_native.h"'
    need(source.count(marker) == 1 and record(controller) == plan['controller'],
         'Only the exact unsubmitted controller may select the isolated header')
    save(out / 'uncompacted-plan.private.json', plan)
    controller.write_text(source.replace(marker, '#include ' + json.dumps(header.as_posix()), 1),
                          encoding='utf-8', newline='\n')
    for index, command in enumerate(plan['commands']):
        result = subprocess.run(command, capture_output=True, timeout=120,
                                env=dict(os.environ, TMP=str(out), TEMP=str(out)))
        (out / ('compact-' + str(index) + '.private.log')).write_bytes(result.stdout + result.stderr)
        need(result.returncode == 0, result.stderr.decode(errors='replace')[-3500:])
    nm = Path(plan['commands'][0][0]).with_name('llvm-nm.exe')
    imports = subprocess.check_output([str(nm), '--undefined-only', plan['artifact']['path']], text=True)
    need(imports == plan['imports'], 'The compact journal must not add or remove an imported operation')
    updated = dict(plan, artifact=record(plan['artifact']['path']), controller=record(controller),
                   compact_integrity_markers=dict(header=record(header), original_header=record(original),
                       adapter=record(Path(__file__)), controls=record(control),
                       per_file_Direct_SHA_EOF_and_returned_counts_logged=True,
                       all_integrity_IO_and_admission_unchanged=True,
                       maximum_marker_state_bytes=16))
    (out / 'plan.private.json').write_text(json.dumps(updated, indent=2) + '\n', encoding='utf-8')
    return updated
