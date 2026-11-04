#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive route accounting from all actual main-model Expert tensors."""
from build_speculative_batch_probe import once
from start_success_route import need


def triplet_bytes(model):
    tensors = {r['name']: r for r in model['tensors']}
    totals = []
    for layer in range(48):
        total = 0
        for role in ('gate', 'up', 'down'):
            t = tensors[f'blk.{layer}.ffn_{role}_exps.weight']
            shape = [640, 2560, 512] if role == 'down' else [2560, 640, 512]
            need(t['shape'] == shape and type(t['bytes']) is int and t['bytes'] % 512 == 0,
                 'Every actual main-layer Expert tensor must have complete uniform planes')
            plane = t['bytes'] // 512
            expected = {'Q2_K': 537600, 'IQ2_XXS': 422400, 'Q2_0': 460800}
            need(t['type'] in expected and plane == expected[t['type']] and
                 (t['type'] == 'Q2_0') == (role == 'down'), 'The exact supported role/format plane size is required')
            total += plane
        totals.append(total)
    need(len(set(totals)) == 1, 'All executed trunk layers must use the same complete triplet geometry')
    return totals[0]


def correct_accounting(source, actual_bytes):
    need(actual_bytes in (1536000, 1420800, 1305600), 'An exact supported uniform triplet is required')
    return once(source, 'uploaded!=misses*1536000ull+result.predictive_bytes',
                'uploaded!=misses*' + str(actual_bytes) + 'ull+result.predictive_bytes')
