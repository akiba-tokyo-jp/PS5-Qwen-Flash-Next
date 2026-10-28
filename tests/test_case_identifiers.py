# SPDX-License-Identifier: MIT
"""Preserve the actual normal-close digest across case generation."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from case_identifiers import replace_case_ids


class CaseIdentifiers(unittest.TestCase):
    def test_real_close_digest_and_adjacent_owner_identifiers_are_preserved(self):
        digest = 'a65054e7a4402a8b9539ee889b0c2e483a777ff727ffc3d3a2855cb1606d4cd2'
        source = f"sha='{digest}';case='hardware-first-generation-5050';close='close_resident_cohort_5054.py';owner=150540;tag='owner5054'"
        result = replace_case_ids(source, {'5050': '5080', '5054': '5084'})
        self.assertEqual(result, f"sha='{digest}';case='hardware-first-generation-5080';close='close_resident_cohort_5084.py';owner=150540;tag='owner5054'")

    def test_mapped_targets_are_not_recursively_rebound(self):
        self.assertEqual(replace_case_ids('case-5050 case-5080', {5050: 5080, 5080: 5100}), 'case-5080 case-5100')
        for mapping in ({}, {'0': '1'}, {'1': '-2'}, {'1': '2147483648'}, {'a': 1}):
            with self.assertRaises(ValueError):
                replace_case_ids('case-1', mapping)


if __name__ == '__main__':
    unittest.main()
