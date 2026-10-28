# SPDX-License-Identifier: MIT
"""Host-only negative cases for the new native adoption evidence contract."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from adaptive_monitor_result import checked_quality,counters


def quality():
    row=dict(columns=248320,all_finite=True,candidate_top5=[1,2,3,4,5],reference_top5=[1,2,3,4,5],
        outside_original_tolerance=0,maximum_absolute_error=0,RMS_error=0,p50_absolute_error=0,p95_absolute_error=0,p99_absolute_error=0,mean_centered_RMS_error=0,KL_reference_to_candidate=0)
    state=dict(metadata_SHA256='1'*64,active_tensor_SHA256='2'*64,tensor_geometry_SHA256='3'*64,metadata_bytes=1024,
        active_tensor_bytes=119267328,tensor_sections=109,minimum_position=0,maximum_position=29,bounded_readback_calls=1820)
    probe=dict(schema='ps5-qwen-wide-same-batch-probe-v1',enabled=True,observations=3,readback_window_bytes=65536,
        class_layout_changed=False,speed_measurement=False,verified_target_width=4,ordinary_reference_repeat_candidate_states=[copy.deepcopy(state)for _ in range(3)],
        ordinary_repeat_and_candidate_rows=[copy.deepcopy(row)for _ in range(8)],same_width_logits_within_original_tolerance=True,
        ordinary_repeat_active_state_bit_exact=True,candidate_active_state_bit_exact=True,draft_actually_accepted=True,bonus_logits_pinned=True,committed_position=30)
    return dict(schema='ps5-qwen-matched-cache-monitor-result-v1',schema_extension='ps5-qwen-adaptive-prefix-monitor-v1',completed=True,
        adaptive_profile_selected=True,active_cache_slots=128,full_F32_rows_compared=13,prefix_reuse_enabled=True,second_request_reused_prompt_tokens=25,
        six_demand_enabled=True,all_original_expert_geometry_present=True,all_model_source_device_owners_retired=True,device_ledger_live_bytes=0,
        original_passive_VideoOut_and_two_API_requests_preserved=True,persistent_caches_enabled=False,prefix_snapshot_handed_off_after_positive_final_restore=True,
        known_control_drafts_used=False,same_width_probe_enabled=True,snapshot_F32_sections=109,speculation=dict(attempts=4,accepted=4,rejected=0,queued_bonus_samples=6),
        snapshot_replacements=4,snapshot_replacement=dict(old_logical_bytes=119267328,new_logical_bytes=120434688,each_actual_layout_witnessed=True,
            old_buffer_freed_before_new_allocation=True,new_Direct_metadata_allowance_pages=19),full_F32_row_SHA256=[['4'*64]*13,['5'*64]*13],
        full_F32_distribution=[copy.deepcopy(row)for _ in range(13)],maximum_absolute_F32_error=0,delivery_batches=[3,2],same_width_probe=probe)


class AdoptionContract(unittest.TestCase):
    def test_complete_diagnostic(self):
        self.assertEqual(checked_quality(quality(),dict(same_width_probe_enabled=True,qualification_reference=None))['full_rows_observed'],26)
    def test_incomplete_or_wrong_state_is_rejected(self):
        for mutation in ('missing_row','wrong_state','live_owner','missing_width_four','wrong_prefix','unpriced_allocation','nonfinite'):
            q=quality()
            if mutation=='missing_row':q['full_F32_row_SHA256'][1].pop()
            elif mutation=='wrong_state':q['same_width_probe']['ordinary_reference_repeat_candidate_states'][2]['active_tensor_SHA256']='6'*64
            elif mutation=='live_owner':q['device_ledger_live_bytes']=2097152
            elif mutation=='missing_width_four':q['speculation']['queued_bonus_samples']=4
            elif mutation=='wrong_prefix':q['second_request_reused_prompt_tokens']=30
            elif mutation=='unpriced_allocation':q['snapshot_replacement']['new_Direct_metadata_allowance_pages']=0
            else:q['full_F32_distribution'][3]['RMS_error']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):checked_quality(q,dict(same_width_probe_enabled=True,qualification_reference=None))
    def test_impossible_accepted_width_counts(self):
        for bonus in (0,3,5,13):
            with self.subTest(bonus=bonus),self.assertRaises(ValueError):counters(dict(attempts=4,accepted=4,rejected=0,queued_bonus_samples=bonus))


if __name__=='__main__':unittest.main()
