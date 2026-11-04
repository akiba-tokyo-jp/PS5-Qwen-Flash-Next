#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Predict a new immutable span from previously completed offset differences."""
from collections import OrderedDict

from read_transition_predictor import LastSuccessor, span


class DeltaSuccessor(LastSuccessor):
    """Bounded two-delta context; absolute offsets need not recur.

    Prefer a previously seen two-delta transition. The less specific one-delta
    fallback requires two consecutive observations of the same successor.
    Each namespace retains the complete immutable identity, flags and size.
    """
    def __init__(self, capacity=512):
        super().__init__(capacity)
        self.tables.append(OrderedDict())
        self.histories = OrderedDict()

    def complete(self, row):
        key = span(row)
        if key is None:
            self.histories.clear()
            return None
        namespace, offset = key[:3], key[3]
        old = self.histories.pop(namespace, None)
        deltas = []
        if old is not None:
            prior_offset, prior_deltas = old
            delta = offset - prior_offset
            if prior_deltas:
                self.remember(self.tables[0], (namespace, prior_deltas[-1]), delta)
            if len(prior_deltas) == 2:
                self.remember(self.tables[1], (namespace, tuple(prior_deltas)), delta)
            deltas = (prior_deltas + [delta])[-2:]
        self.histories[namespace] = offset, deltas
        if len(self.histories) > 64:
            self.histories.popitem(last=False)
        predicted = None
        if len(deltas) == 2:
            predicted = self.lookup(self.tables[1], (namespace, tuple(deltas)), 1)
        if predicted is None and deltas:
            predicted = self.lookup(self.tables[0], (namespace, deltas[-1]), 2)
        if predicted is None:
            return None
        predicted_offset = offset + predicted
        if predicted_offset < 0 or predicted_offset > namespace[0][2] - namespace[2]:
            return None
        return (*namespace, predicted_offset)
