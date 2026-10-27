# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from resident_combined_comparison import generate
from build_resident_comparison import specialize


class CombinedTests(unittest.TestCase):
    def test_one_model_and_one_shared_retirement_for_both_cohorts(self):
        source=(ROOT/'native/app/native_main.cpp').read_text();tail=(ROOT/'native/app/resident_comparison_tail.inc').read_text()
        flags=dict(reuse_launch_integrity=True,incremental_tables=True,delegate_shader=True,
                   phase_local_model=True,postloader_integrity=True)
        text,_=generate('combined',source,tail,flags);main=text[text.index('int main('):]
        self.assertEqual(main.count('llama_model_load_from_file('),1)
        self.assertEqual(main.count('llama_model_free(model)'),1)
        self.assertIn('{"total_requests",19}',main)
        self.assertIn('{"prefix_requests",retained_prefix_results}',main)
        self.assertIn('.prefix.arm',main)
        self.assertIn('run+"-prefix-"',main)
        self.assertIn('forced_rejection_and_full_F32_restore_passed',main)
        self.assertIn('require_resident_source_VM(after_fixture)',main)
        self.assertIn('context_floor+245',main)
        self.assertEqual(main.count('postloader_current_SELF_Direct_full_SHA256_before_read_GPU_not_started'),1)
        self.assertLess(main.index('postloader_current_SELF_Direct_full_SHA256_before_read_GPU_not_started'),
                        main.index('resident_measured_GPU_phase_admitted_starting_GPU'))
        self.assertLess(main.index('retained_prefix_routes=std::move(routes)'),main.index('llama_model_free(model)'))
        self.assertLess(main.index('llama_model_free(model)'),main.index('completed_route_report(retained_prefix_routes'))
        changed=dict(flags);changed['postloader_integrity']=False
        with self.assertRaises(ValueError):generate('combined',source,tail,changed)
        with self.assertRaises(ValueError):specialize(source,tail,postloader_integrity=True)


if __name__=='__main__':unittest.main()
