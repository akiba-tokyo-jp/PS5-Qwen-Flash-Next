#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind sampled Direct mapping overhead without repricing payload as kernel VM."""
import hashlib,json,re
from pathlib import Path

PROFILE = dict(schema='ps5-qwen-sampled-Direct-VM-policy-v1',profile=20261028,
    observed_overhead_pages=17,idle_margin_pages=2,additional_pages=19,
    maximum_Direct_bytes=28<<20,page_bytes=16384,allocations=27,
    universal_minimum_claimed=False,actual_allocation_return_required=True)


def bind(path):
    path=Path(path);raw=path.read_bytes();e=json.loads(raw)
    if (e['allocations']!=27 or e['completed_profiles']!=3 or e['live_Direct_bytes'] or
        len(e['profiles'])!=3 or not all(p['completed'] and p['all_page_patterns_exact'] for p in e['profiles']) or
        max(p['maximum_observed_VM_drop_pages'] for p in e['profiles'])!=17 or
        max(p['maximum_observed_idle_drop_pages'] for p in e['profiles'])!=2):
        raise ValueError('The complete 27-cycle native calibration is required')
    return dict(PROFILE,calibration=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))


def additional_pages(lines,manifest,total,alignment=16384):
    profile=manifest.get('Direct_VM_policy')
    markers=[line for line in lines if line.startswith('DIRECT_VM_ACCOUNTING ')]
    if profile is None:
        if markers:raise ValueError('Measured accounting appeared without an explicit bound manifest')
        return total//16384
    if any(profile.get(k)!=v for k,v in PROFILE.items()):
        raise ValueError('Measured Direct VM policy differs from its sampled scope')
    proof=profile.get('calibration',{})
    if not isinstance(proof.get('bytes'),int) or proof['bytes']<=0 or not re.fullmatch('[0-9a-f]{64}',proof.get('sha256','')):
        raise ValueError('Complete calibration identity is required')
    if not 0<total<=28<<20 or total%16384 or alignment not in (16384,65536) or total%alignment:
        raise ValueError('Direct allocation exceeds the calibrated scope')
    expected=(f'DIRECT_VM_ACCOUNTING profile=20261028 overhead_pages=17 idle_margin_pages=2 '
        f'total_VM_additional_pages=19 Direct_payload_bytes={total} alignment_bytes={alignment}')
    if markers!=[expected]:raise ValueError('Native accounting does not match the declared calibration')
    return 19
