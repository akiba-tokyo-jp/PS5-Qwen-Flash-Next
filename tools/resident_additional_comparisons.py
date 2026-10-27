#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate finite cache and prefix comparisons, keeping model admission intact."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def generate(kind,source,unused_tail,flags):
    if kind not in ('cache','prefix'):
        raise ValueError('Finite additional comparison kind required')
    if not flags.get('phase_local_model') or not flags.get('reuse_launch_integrity') or not flags.get('incremental_tables') or not flags.get('delegate_shader'):
        raise ValueError('Qualified phase-local model, integrity, tables and shader prerequisites required')
    if any(flags.get(key)for key in ('receipt_diagnostic','measure_worker_memory','gpu_initializer_calibration','gpu_capacity_only')):
        raise ValueError('Additional comparisons cannot combine calibration scopes')
    from build_resident_comparison import specialize
    tail_path=ROOT/'native/app/resident_additional_tail.inc'
    tail=tail_path.read_text().replace('RESIDENT_PREFIX_COMPARISON', 'true'if kind=='prefix'else'false')
    text=specialize(source,tail,allow_large_cache=kind=='cache',**flags)
    old='qwen_app::require_resident_comparison_policy(policy);'
    if text.count(old)!=1:
        raise ValueError('Unique original resident policy boundary required')
    text='#include "resident_additional_policy.h"\n'+text.replace(old,
        'qwen_app::require_resident_additional_policy(policy,"'+kind+'");')
    return text,[Path(__file__),tail_path,ROOT/'native/app/resident_additional_policy.h']
