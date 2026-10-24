#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay admitted expert IDs at the native 53-slot capacity; no model execution."""
import argparse
import json
from pathlib import Path
import re

from expert_route_result import validate_routes


class RouteCache:
    """Current aged-LFU with optional decay or recency-only eviction.

    All actual selections contain at least ten unique experts, so the native
    soft floor is (53 - selected) // 48 == 0. Empty slots and slot-order ties
    follow the linked planner. Hits precede sorted misses; the whole current
    selected set stays protected throughout every fill.
    """
    def __init__(self, decay=4096, recency_only=False):
        if type(decay) is not int or decay <= 0:
            raise ValueError('A positive layer-route decay interval is required')
        self.decay = decay
        self.recency_only = recency_only
        self.keys = [-1] * 53
        self.mapping = {}
        self.counts = [0] * (49 * 512)
        self.recency = [0] * len(self.counts)
        self.tick = 0
        self.routes = 0
        self.previous = [[] for _ in range(48)]

    def step(self, row):
        layer, ids = row['layer'], row['ids']
        selected = list(dict.fromkeys(ids))
        if not 0 <= layer < 48 or not 10 <= len(selected) <= 40:
            raise ValueError('Replay exceeds the actual text-layer active-set scope')
        if any(type(e) is not int or not 0 <= e < 512 for e in selected):
            raise ValueError('Replay expert IDs exceed the original model')
        active = {layer * 512 + expert for expert in selected}
        predictions = []
        for limit in (1, 10):
            candidates = [e for e in self.previous[layer][:limit]
                          if layer * 512 + e not in self.mapping]
            useful = sum(e in selected for e in candidates)
            predictions.append(dict(limit=limit, nonresident=len(candidates),
                                    useful=useful, wasted=len(candidates)-useful))
        self.tick += 1
        for key in active:
            if not self.recency_only:
                self.counts[key] = min(self.counts[key]+1, 2**32-1)
            self.recency[key] = self.tick
        self.routes += 1
        if self.routes == self.decay:
            self.counts = [count // 2 for count in self.counts]
            self.routes = 0
        hits = sum(key in self.mapping for key in active)
        misses = []
        for expert in sorted(selected):
            key = layer * 512 + expert
            if key in self.mapping:
                continue
            try:
                slot = self.keys.index(-1)
            except ValueError:
                eligible = [n for n, resident in enumerate(self.keys)
                            if resident not in active]
                if not eligible:
                    raise ValueError('No victim preserves the entire selected set')
                slot = min(eligible, key=lambda n: (self.counts[self.keys[n]],
                                                   self.recency[self.keys[n]]))
                del self.mapping[self.keys[slot]]
            self.keys[slot] = key
            self.mapping[key] = slot
            misses.append(dict(expert=expert, slot=slot))
        if not active <= self.mapping.keys() or any(self.keys[s] != k for k, s in self.mapping.items()):
            raise ValueError('Replay lost an active expert or retained a stale slot map')
        self.previous[layer] = ids[-10:]
        return dict(hits=hits, misses=len(misses), unique=len(active), predictions=predictions)


def replay(records, decay=4096, recency_only=False):
    cache = None
    requests = []
    for index, record in enumerate(records):
        if record['cache_reset_before_request'] != (index < 2):
            raise ValueError('Expected cold arithmetic/cold external/retained external order')
        if index < 2:
            cache = RouteCache(decay, recency_only)
        totals = dict(hits=0, misses=0, unique=0, predictions=[
            dict(limit=limit, nonresident=0, useful=0, wasted=0) for limit in (1, 10)])
        for row in record['records']:
            item = cache.step(row)
            for key in ('hits', 'misses', 'unique'):
                totals[key] += item[key]
            for total, current in zip(totals['predictions'], item['predictions']):
                for key in ('nonresident', 'useful', 'wasted'):
                    total[key] += current[key]
        requests.append(totals)
    return requests


def screen(records):
    if len(records) != 3:
        raise ValueError('All three completed requests are required')
    candidates = [(4096, False), (4096, True)] + [
        (interval, False) for interval in (48, 96, 192, 384, 768, 1536, 3072, 8192)]
    rows = []
    for decay, recency_only in candidates:
        requests = replay(records, decay, recency_only)
        if not rows:
            for actual, native in zip(requests, records):
                if (actual['hits'] != native['cache_hits'] or actual['misses'] != native['cache_misses'] or
                        actual['unique'] != native['unique_selected_experts'] or
                        actual['misses'] * 9830400 != native['uploaded_bytes']):
                    raise ValueError('Baseline replay differs from actual completed native transfers')
        uploaded = sum(request['misses'] for request in requests[1:]) * 9830400
        rows.append(dict(policy='lru' if recency_only else 'lfu', decay_layer_routes=decay,
                         requests=requests, external_uploaded_bytes=uploaded))
    for row in rows:
        row['external_byte_reduction_percent'] = (
            1-row['external_uploaded_bytes']/rows[0]['external_uploaded_bytes']) * 100
    return dict(schema='ps5-qwen-expert-route-replay-v1',
                all_three_baseline_counters_match=True, slots=53, policies=rows,
                all_selected_experts_retained=True, console_requests=0,
                learned_model_execution=False, comparative_native_speed_qualified=False,
                scope='Fixed completed requests; saved bytes do not establish latency or generalization.')


def bounded_json(path):
    before = path.stat()
    if not 0 < before.st_size <= 2 << 20:
        raise ValueError('Route/result evidence exceeds its bound')
    with path.open('rb') as source:
        raw = source.read((2 << 20)+1)
    after = path.stat()
    if (len(raw) != before.st_size or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        raise ValueError('Route/result evidence changed during bounded read')
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routes', type=Path, action='append', required=True)
    parser.add_argument('--results', type=Path, action='append', required=True)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--width', type=int, choices=(1, 2, 4), default=4)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 0 < args.pid < 2**31 or not re.fullmatch('[0-9a-f]{32}', args.run_id):
        raise ValueError('An exact native PID and 32-character run binding are required')
    if len(args.routes) != 3 or len(args.results) != 3:
        raise ValueError('Pass arithmetic and both external route/result pairs in order')
    records = []
    for index, (route, result) in enumerate(zip(args.routes, args.results)):
        record = bounded_json(route)
        validate_routes(record, bounded_json(result), width=args.width,
                        pid=args.pid, run_id=args.run_id, cold=index < 2)
        records.append(record)
    report = screen(records)
    with args.out.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(all_three_baseline_counters_match=True, policies=len(report['policies']),
                          console_requests=0, learned_model_execution=False)))


if __name__ == '__main__':
    main()
