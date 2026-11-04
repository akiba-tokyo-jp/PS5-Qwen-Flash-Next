#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise causality, immutable identities, reset and bounded metadata."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from read_transition_predictor import ContextSuccessor, LastSuccessor, simulate, span


def event(position, ordinal=0, **changes):
    row = dict(identity=(1, 2, 128 << 20, 0o100444, 0, 0, 1, 0, 1, 0, 1, 0),
               flags=0x20000, candidate=True, identity_equal=True,
               bytes=256 << 10, returned=256 << 10, offset=position * (256 << 10),
               thread=1, ordinal=ordinal, begin=ordinal * 10 + 1, end=ordinal * 10 + 2)
    row.update(changes)
    return row


class TransitionTests(unittest.TestCase):
    def test_unseen_successor_is_never_predicted(self):
        for kind in (LastSuccessor, ContextSuccessor):
            p = kind()
            self.assertIsNone(p.complete(event(0)))
            self.assertIsNone(p.complete(event(1)))
            self.assertIsNone(p.complete(event(2)))

    def test_round_one_learns_completed_transition(self):
        p = LastSuccessor()
        for offset in (0, 1):
            self.assertIsNone(p.complete(event(offset)))
        self.assertEqual(p.complete(event(0)), span(event(1)))

    def test_context_separates_ambiguous_single_predecessor(self):
        p = ContextSuccessor()
        for offset in (0, 1, 2, 3, 1, 4) * 3:
            p.complete(event(offset))
        p.complete(event(0))
        self.assertEqual(p.complete(event(1)), span(event(2)))
        p.complete(event(3))
        self.assertEqual(p.complete(event(1)), span(event(4)))

    def test_two_observations_required_for_context(self):
        p = ContextSuccessor()
        for offset in (0, 1, 2, 0):
            p.complete(event(offset))
        self.assertIsNone(p.complete(event(1)))
        for offset in (2, 0):
            p.complete(event(offset))
        self.assertEqual(p.complete(event(1)), span(event(2)))

    def test_short_invalid_and_changed_reads_break_history(self):
        for kind in (LastSuccessor, ContextSuccessor):
            for change in ({'returned': 42}, {'identity_equal': False}, {'candidate': False},
                           {'offset': 1}, {'offset': -16384}, {'offset': 128 << 20}):
                p = kind()
                p.complete(event(0))
                self.assertIsNone(p.complete(event(1, **change)))
                self.assertEqual(p.previous, [])
                self.assertTrue(all(not table for table in p.tables))

    def test_full_identity_and_open_flags_are_part_of_key(self):
        p = LastSuccessor()
        p.complete(event(0))
        p.complete(event(1))
        base = event(0)
        for index in range(12):
            different = copy.deepcopy(base)
            identity = list(different['identity'])
            identity[index] += 16384 if index == 2 else 1
            different['identity'] = tuple(identity)
            self.assertIsNone(p.complete(different))
        self.assertIsNone(p.complete(event(0, flags=0x40000)))

    def test_metadata_is_bounded(self):
        for kind in (LastSuccessor, ContextSuccessor):
            p = kind(3)
            for i in range(20):
                p.complete(event(i))
                self.assertTrue(all(len(table) <= 3 for table in p.tables))
        for capacity in (0, 513):
            with self.assertRaises(ValueError):
                LastSuccessor(capacity)

    def test_future_suffix_does_not_change_prior_predictions(self):
        prefix = [event(i % 3, i) for i in range(12)]
        for kind in (LastSuccessor, ContextSuccessor):
            def outputs(rows):
                p = kind()
                return [p.complete(row) for row in rows]
            expected = outputs(prefix)
            for suffix in ([event(9, 12)], [event(4, 12), event(7, 13)]):
                self.assertEqual(outputs(prefix + suffix)[:len(prefix)], expected)

    def test_producers_remain_independent_and_predictions_retire(self):
        first = [event(i % 3, i) for i in range(60)]
        second = [event((i % 3) + 20, i, thread=2) for i in range(60)]
        for kind in (LastSuccessor, ContextSuccessor):
            result = simulate(first + second, kind)
            self.assertEqual(result['predictions'], 12)
            self.assertEqual(result['hits'], 12)
            self.assertEqual(result['unused'], 0)
            self.assertEqual(result['original_calls'], 120)

    def test_overlapping_history_is_refused(self):
        with self.assertRaises(ValueError):
            simulate([event(0), event(1, 1, begin=2)], LastSuccessor)


if __name__ == '__main__':
    unittest.main()
