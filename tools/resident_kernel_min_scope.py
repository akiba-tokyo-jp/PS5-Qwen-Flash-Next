#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Isolated post-context minimum-plus-metadata experiment; no OS counter writes."""
import copy
import json
import resident_OS_reserve_scope as original

SCOPE = copy.deepcopy(original.SCOPE)
SCOPE.update(schema='ps5-qwen-post-context-kernel-minimum-v2',
    selected_extra_formula='max(observed_kernel_minimum,observed_OS_reserved_pages)+64',
    OS_reserve_counter_unchanged=True, kernel_minimum_threshold_preserved=True,
    original_additive_application_reserve_replaced=True,
    observed_refused_prefix_free_pages=1106, observed_refused_C2_free_pages=1030,
    selected_post_context_free_pages=962)
SCOPE.pop('preserve_full_observed_OS_reserved_pages')


def system_header(text):
    text = original.system_header(text)
    old = 'qwen_app_resident_GPU_OS_reserve_active()?std::max<std::uint64_t>(s.kernel_reserved,64):'
    if text.count(old) != 1:
        raise ValueError('One scoped post-context reserve selector required')
    return text.replace(old, 'qwen_app_resident_GPU_OS_reserve_active()?64ull:')


def source_header(text):
    text = original.source_header(text)
    old = 'qwen_app_resident_GPU_OS_reserve_active()?std::max<std::uint64_t>(m.kernel_reserved,64):'
    if text.count(old) != 1:
        raise ValueError('One scoped new-source-allocation reserve selector required')
    return text.replace(old, 'qwen_app_resident_GPU_OS_reserve_active()?64ull:')


implementation = original.implementation


def entry(text):
    text = original.entry(text)
    before = json.dumps(original.SCOPE, separators=(',', ':'))
    after = json.dumps(SCOPE, separators=(',', ':'))
    changes = ((before, after), ('OS_scope_memory.kernel_free<1104', 'OS_scope_memory.kernel_free<962'),
        ('{"selected_operational_floor_pages",1104}', '{"selected_operational_floor_pages",962}'),
        ('{"selected_full_OS_reserved_pages",206}', '{"observed_OS_reserved_pages",206},{"OS_reserve_counter_unchanged",true}'),
        ('{"OS_reserved_pages_preserved",true}', '{"OS_reserve_counter_unchanged",true},{"kernel_minimum_threshold_preserved",true}'))
    for old, new in changes:
        if text.count(old) != 1:
            raise ValueError('Unique original reserve experiment frontier required')
        text = text.replace(old, new)
    if text.count('206ull*16384') != 3:
        raise ValueError('All selected application-margin reports must change together')
    return text.replace('206ull*16384', '64ull*16384')
