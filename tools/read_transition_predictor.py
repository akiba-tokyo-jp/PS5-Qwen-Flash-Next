#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded metadata-only read predictors; this module never performs I/O."""
from collections import OrderedDict


def span(row):
    """Return an exact completed immutable-span key, or break the history."""
    identity = tuple(row['identity'])
    size, offset = row['bytes'], row['offset']
    if (len(identity) != 12 or not row['candidate'] or not row['identity_equal'] or
            row['returned'] != size or identity[2] < 64 << 20 or
            not 256 << 10 <= size <= 8 << 20 or size % 16384 or
            offset < 0 or offset % 16384 or offset > identity[2] - size):
        return None
    return identity, row['flags'], size, offset


class LastSuccessor:
    """Round 1: predict the most recently completed successor of this read."""
    def __init__(self, capacity=512):
        if not isinstance(capacity, int) or capacity < 1 or capacity > 512:
            raise ValueError('A positive bounded transition capacity is required')
        self.capacity = capacity
        self.tables = [OrderedDict()]
        self.previous = []

    def remember(self, table, context, target):
        old, count = table.pop(context, (None, 0))
        table[context] = target, min(255, count + 1) if old == target else 1
        if len(table) > self.capacity:
            table.popitem(last=False)

    def lookup(self, table, context, minimum):
        if context not in table:
            return None
        target, count = table.pop(context)
        table[context] = target, count
        return target if count >= minimum else None

    def complete(self, row):
        key = span(row)
        if key is None:
            self.previous.clear()
            return None
        if self.previous:
            self.remember(self.tables[0], self.previous[-1], key)
        self.previous = [key]
        return self.lookup(self.tables[0], key, 1)


class ContextSuccessor(LastSuccessor):
    """Round 2: two-read context and repeated agreement before speculation."""
    def __init__(self, capacity=512):
        super().__init__(capacity)
        self.tables.append(OrderedDict())

    def complete(self, row):
        key = span(row)
        if key is None:
            self.previous.clear()
            return None
        if self.previous:
            self.remember(self.tables[0], self.previous[-1], key)
        if len(self.previous) == 2:
            self.remember(self.tables[1], tuple(self.previous), key)
        self.previous = (self.previous + [key])[-2:]
        target = None
        if len(self.previous) == 2:
            target = self.lookup(self.tables[1], tuple(self.previous), 2)
        return target if target is not None else self.lookup(self.tables[0], key, 3)


def simulate(rows, predictor_type, maximum=6):
    """Grade one already chosen pending span per original producer.

    Completion is optimistically instantaneous. No read latency, resource
    admission, scratch allocation, contention or model speed is simulated.
    """
    if maximum != 6:
        raise ValueError('Keep the previously screened six-prediction bound')
    groups = {}
    for row in rows:
        groups.setdefault(row['thread'], []).append(row)
    totals = dict(original_calls=0, eligible_calls=0, predictions=0,
                  predicted_bytes=0, hits=0, hit_bytes=0, unused=0,
                  live_table_entries_peak=0)
    producers = []
    for events in groups.values():
        predictor = predictor_type()
        stats = dict.fromkeys(totals, 0)
        pending, ready = None, 0
        for row in sorted(events, key=lambda item: (item['begin'], item['ordinal'])):
            if row['begin'] <= ready:
                raise ValueError('Overlapping calls on one producer cannot use completed history')
            key = span(row)
            stats['original_calls'] += 1
            stats['eligible_calls'] += key is not None
            if pending is not None:
                if key == pending:
                    stats['hits'] += 1
                    stats['hit_bytes'] += row['bytes']
                else:
                    stats['unused'] += 1
                pending = None
            target = predictor.complete(row)
            ready = row['end']
            stats['live_table_entries_peak'] = max(
                stats['live_table_entries_peak'], sum(map(len, predictor.tables)))
            if target is not None and stats['predictions'] < maximum:
                pending = target
                stats['predictions'] += 1
                stats['predicted_bytes'] += target[2]
        if pending is not None:
            stats['unused'] += 1
        if stats['hits'] + stats['unused'] != stats['predictions']:
            raise ValueError('Every prediction must have exactly one terminal grade')
        producers.append(stats)
        for name, value in stats.items():
            if name == 'live_table_entries_peak':
                totals[name] = max(totals[name], value)
            else:
                totals[name] += value
    return dict(**totals, original_producers=len(groups), producers=producers,
                hit_fraction=totals['hits'] / totals['predictions'] if totals['predictions'] else None,
                useful_byte_fraction=totals['hit_bytes'] / totals['predicted_bytes'] if totals['predicted_bytes'] else None,
                eligible_call_coverage=totals['hits'] / totals['eligible_calls'] if totals['eligible_calls'] else None)
