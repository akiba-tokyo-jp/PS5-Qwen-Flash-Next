# SPDX-License-Identifier: MIT
"""Prevent additional comparisons from bypassing actual model qualification."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from resident_additional_comparisons import generate


class AdditionalTests(unittest.TestCase):
    def test_geometry_and_prefix_are_independent_full_model_paths(self):
        source=(ROOT/'native/app/native_main.cpp').read_text()
        flags=dict(reuse_launch_integrity=True,incremental_tables=True,delegate_shader=True,phase_local_model=True)
        for kind in ('cache','prefix'):
            text,inputs=generate(kind,source,'',flags)
            main=text[text.index('int main('):]
            self.assertIn('llama_model_load_from_file(',main)
            self.assertIn('admit_indexed_vectors(',main)
            self.assertIn('require_resident_source_VM(after_fixture)',main)
            self.assertIn('context_floor+245',main)
            self.assertIn('all_model_source_device_owners_positively_retired',main)
            self.assertIn('full_F32_continuation_and_routes_passed',main)
            self.assertNotIn('RESIDENT_PREFIX_COMPARISON',main)
            self.assertEqual('policy.contains("native_large_cache_scope")'in main,kind=='cache')
            self.assertEqual(len(inputs),3)
        for key in flags:
            changed=dict(flags);changed[key]=False
            with self.assertRaises(ValueError):generate('cache',source,'',changed)
        with self.assertRaises(ValueError):generate('unbounded',source,'',flags)


if __name__=='__main__':unittest.main()
