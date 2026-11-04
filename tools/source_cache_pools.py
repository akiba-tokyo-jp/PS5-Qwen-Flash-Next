#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Select only unconsumed, positively tracked application source-cache scopes."""
from pathlib import Path

from start_success_route import load, need

SCOPES = ('Gate48', 'Down48', 'Up-prefix', 'Up-final4', 'original-complement')


def validate(pools):
    keys = [(pool['scope'], str(Path(pool.get('publication', pool.get('trace_proof', '')))))
            for pool in pools]
    need(len(keys) == len(set(keys)), 'A source-cache pool cannot appear twice with divergent cursors')
    for pool in pools:
        has_windows(pool)


def has_windows(pool):
    need(pool['scope'] in SCOPES, 'Only the explicit owned source-cache pools are eligible')
    done = pool['completed_scopes']
    need(len(done) == len(set(map(str, done))), 'Never repeat a completed cache scope')
    return not done or load(done[-1])['remaining_windows'] > 0


def command(common, pool, out):
    need(has_windows(pool), 'Never submit an exhausted source-cache pool')
    flags = list(common) + ['--target-free-pages', '16384', '--out', out, '--execute']
    if pool['scope'] == 'original-complement':
        flags += ['--trace-proof', Path(pool['trace_proof'])]
        for path in pool['completed_read_scopes']:
            flags += ['--completed-read-scope', Path(path)]
        for path in pool['completed_scopes']:
            flags += ['--completed-complement', Path(path)]
        return 'observe_source_cache_complement.py', flags
    flags += ['--publication', Path(pool['publication'])]
    if pool['scope'] != 'Up-final4':
        flags += ['--' + pool['scope']]
    for path in pool['completed_scopes']:
        flags += ['--completed-scope', Path(path)]
    return 'retire_published_iq2_source_cache.py', flags
