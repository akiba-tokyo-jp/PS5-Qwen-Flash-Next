# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from resident_combined_comparison import generate, qualify_prefix_entry
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
        begin=main.index('        std::array<CompletedRouteEvidence,9> retained_prefix_routes;')
        end=main.index('        retained_prefix_routes=std::move(routes);',begin)
        prefix=main[begin:end]
        self.assertNotIn('qwen_native_driver_complete();resident_sample("original_model_context_completed")',prefix)
        self.assertEqual(prefix.count('combined_prefix_start_after_positive_request_reset'),1)
        self.assertEqual(prefix.count('.resident.prefix-startup-memory'),1)
        self.assertIn('require_resident_source_VM(after_fixture)',main)
        self.assertIn('context_floor+245',main)
        self.assertEqual(main.count('postloader_current_SELF_Direct_full_SHA256_before_read_GPU_not_started'),1)
        self.assertNotIn('admit_native_fixture_memory(',main)
        self.assertIn('require_resident_source_VM(qwen_app::admit_native_system_memory())',main)
        self.assertLess(main.index('postloader_current_SELF_Direct_full_SHA256_before_read_GPU_not_started'),
                        main.index('resident_measured_GPU_phase_admitted_starting_GPU'))
        self.assertLess(main.index('retained_prefix_routes=std::move(routes)'),main.index('llama_model_free(model)'))
        self.assertLess(main.index('llama_model_free(model)'),main.index('completed_route_report(retained_prefix_routes'))
        changed=dict(flags);changed['postloader_integrity']=False
        with self.assertRaises(ValueError):generate('combined',source,tail,changed)
        with self.assertRaises(ValueError):specialize(source,tail,postloader_integrity=True)

    def test_existing_fixed_entry_is_idempotent_and_ambiguous_entries_refuse(self):
        additional=(ROOT/'native/app/resident_additional_tail.inc').read_text()
        prefix=additional[:additional.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();')]
        fixed=qualify_prefix_entry(prefix)
        self.assertEqual(qualify_prefix_entry(fixed),fixed)
        with self.assertRaises(ValueError):qualify_prefix_entry(prefix+prefix)
        with self.assertRaises(ValueError):qualify_prefix_entry('')


if __name__=='__main__':unittest.main()
