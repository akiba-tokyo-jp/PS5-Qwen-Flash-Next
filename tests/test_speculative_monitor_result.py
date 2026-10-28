# SPDX-License-Identifier: MIT
"""Check actual same-width evidence and normal-mode full-row hash requirements."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from speculative_monitor_result import checked_quality

class CombinedMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained=os.environ.get('QWEN_FROZEN_BUILD_DIR')
        if not retained:raise unittest.SkipTest('Set QWEN_FROZEN_BUILD_DIR to retained native evidence')
        cls.probe=json.loads((Path(retained).parent/'hardware-first-generation-5720/native-arm1.same-batch.private.json').read_text())

    def fixture(self):
        distribution=copy.deepcopy(self.probe['ordinary_repeat_and_candidate_rows'][0])
        distribution['maximum_absolute_error']=2.0
        quality=dict(schema='ps5-qwen-matched-cache-monitor-result-v1',schema_extension='ps5-qwen-prefix-speculative-monitor-v1',
            completed=True,active_cache_slots=128,full_F32_rows_compared=23,prefix_reuse_enabled=True,second_request_reused_prompt_tokens=30,
            six_demand_enabled=True,all_original_expert_geometry_present=True,all_model_source_device_owners_retired=True,
            device_ledger_live_bytes=0,original_passive_VideoOut_and_two_API_requests_preserved=True,persistent_caches_enabled=False,
            prefix_snapshot_handed_off_after_positive_final_restore=True,known_control_drafts_used=False,same_width_probe_enabled=True,
            speculation=dict(attempts=1,accepted=1,rejected=0,queued_bonus_samples=1),
            snapshot_replacement=dict(old_logical_bytes=119881728,new_logical_bytes=120311808,equal_rounded_capacity_bytes=121634816,
                old_buffer_freed_before_new_allocation=True,new_Direct_metadata_allowance_pages=19),
            full_F32_row_SHA256=[['ab'*32]*23,['cd'*32]*23],full_F32_distribution=[distribution]*23,
            maximum_absolute_F32_error=2.0,delivery_batches=[30,20],same_width_probe=copy.deepcopy(self.probe))
        return quality,dict(same_width_probe_enabled=True,qualification_reference=None)

    def test_maximum_two_is_not_an_automatic_failure_but_wrong_state_is(self):
        quality,scope=self.fixture();self.assertTrue(checked_quality(quality,scope)['all_greedy_top1_equal'])
        quality['same_width_probe']['ordinary_reference_repeat_candidate_states'][2]['active_tensor_SHA256']='0'*64
        with self.assertRaises(ValueError):checked_quality(quality,scope)

    def test_nonfinite_missing_rows_or_unsafe_replacement_are_refused(self):
        for mutate in(lambda q:q['full_F32_distribution'].pop(),
                      lambda q:q['full_F32_distribution'][0].pop('candidate_top5'),
                      lambda q:q['full_F32_distribution'][0].update(KL_reference_to_candidate=float('nan')),
                      lambda q:q['snapshot_replacement'].update(old_buffer_freed_before_new_allocation=False)):
            quality,scope=self.fixture();mutate(quality)
            with self.assertRaises(ValueError):checked_quality(quality,scope)

    def test_normal_mode_requires_every_bit_pattern_hash_from_the_diagnostic_mode(self):
        prior,scope=self.fixture();temporary_root=ROOT/'.local/monitor-result-host-check';temporary_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root)as temporary:
            folder=Path(temporary);self.assertTrue(folder.resolve().is_relative_to(temporary_root.resolve()))
            path=folder/'qualification.private.json';raw=json.dumps(prior).encode();path.write_bytes(raw)
            scope=dict(same_width_probe_enabled=False,qualification_reference=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            normal=copy.deepcopy(prior);normal.update(same_width_probe_enabled=False,same_width_probe=None)
            self.assertTrue(checked_quality(normal,scope)['full_row_reference_bit_exact'])
            normal['full_F32_row_SHA256'][1][-1]='ef'*32
            with self.assertRaises(ValueError):checked_quality(normal,scope)

    def test_actual_closed_normal_application_matches_every_diagnostic_row(self):
        retained=os.environ.get('QWEN_FROZEN_BUILD_DIR');cache=Path(retained).parent
        case=cache/'hardware-first-generation-5980';diagnostic=cache/'hardware-first-generation-5940'
        if not (case/'ordinary-close/complete.private.json').exists():self.skipTest('Closed normal application evidence not available')
        scope=json.loads((case/'observer-binding.private.json').read_text())['require_prefix_speculative_monitor']
        quality=json.loads((case/'native-cache128-monitor.private.json').read_text())
        self.assertFalse(scope['same_width_probe_enabled'])
        self.assertTrue(checked_quality(quality,scope)['full_row_reference_bit_exact'])
        prior=json.loads((diagnostic/'native-cache128-monitor.private.json').read_text())
        self.assertEqual(quality['full_F32_row_SHA256'],prior['full_F32_row_SHA256'])
        self.assertEqual(sum(map(len,quality['full_F32_row_SHA256'])),46)

if __name__=='__main__':unittest.main()
