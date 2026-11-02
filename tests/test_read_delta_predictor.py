#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the changed relative-offset predictor without replaying old controls."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from read_delta_predictor import DeltaSuccessor
from read_transition_predictor import simulate, span


def row(position, index=0, inode=2, **changes):
    value = dict(identity=(1, inode, 128 << 20, 0o100444, 0, 0, 1, 0, 1, 0, 1, 0),
                 flags=0x20000, candidate=True, identity_equal=True,
                 bytes=256 << 10, returned=256 << 10, offset=position * (256 << 10),
                 thread=1, ordinal=index, begin=index * 10 + 1, end=index * 10 + 2)
    value.update(changes)
    return value


class DeltaTests(unittest.TestCase):
    def test_unique_offsets_can_learn_a_repeated_stride(self):
        p = DeltaSuccessor()
        for position in (0, 2, 4):
            self.assertIsNone(p.complete(row(position)))
        self.assertEqual(p.complete(row(6)), span(row(8)))

    def test_two_deltas_separate_ambiguous_successors(self):
        p = DeltaSuccessor()
        position = 0
        p.complete(row(position))
        pattern = [1, 2, 1, 3]
        for i, delta in enumerate(pattern * 4):
            position += delta
            predicted = p.complete(row(position))
            if i >= 7:
                self.assertEqual(predicted, span(row(position + pattern[(i + 1) % 4])))

    def test_other_sources_do_not_inherit_a_delta(self):
        p = DeltaSuccessor()
        for position in range(4):
            p.complete(row(position))
        self.assertIsNone(p.complete(row(10, inode=3)))
        self.assertEqual(p.complete(row(4)), span(row(5)))

    def test_failed_read_breaks_the_relative_context(self):
        p = DeltaSuccessor()
        for position in range(4):
            p.complete(row(position))
        self.assertIsNone(p.complete(row(4, returned=1)))
        self.assertFalse(p.histories)
        self.assertIsNone(p.complete(row(5)))

    def test_predicted_range_cannot_cross_EOF_or_zero(self):
        for positions in ((505, 507, 509, 511), (6, 4, 2, 0)):
            p = DeltaSuccessor()
            for position in positions:
                result = p.complete(row(position))
            self.assertIsNone(result)

    def test_source_and_transition_metadata_are_bounded(self):
        p = DeltaSuccessor(3)
        for inode in range(100):
            for position in range(7):
                p.complete(row(position, inode=inode + 1))
                self.assertLessEqual(len(p.histories), 64)
                self.assertTrue(all(len(table) <= 3 for table in p.tables))

    def test_future_suffix_cannot_change_earlier_predictions(self):
        prefix = [row(i, i) for i in range(10)]
        def predictions(events):
            p = DeltaSuccessor()
            return [p.complete(event) for event in events]
        self.assertEqual(predictions(prefix), predictions(prefix + [row(90, 10)])[:len(prefix)])

    def test_six_predictions_remain_the_limit(self):
        result = simulate([row(i, i) for i in range(60)], DeltaSuccessor)
        self.assertEqual((result['predictions'], result['hits'], result['unused']), (6, 6, 0))


if __name__ == '__main__':
    unittest.main()
