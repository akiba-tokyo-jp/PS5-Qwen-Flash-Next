# SPDX-License-Identifier: MIT
"""Reject incomplete coverage and keep finite negative behavior results reviewable."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from review_speculative_qualification import NAMES,REJECTION_POSITIONS,behavior_summary,probe_summary,route_geometry,speed_summary,distribution_summary
from build_speculative_speed import speed_loop

def behavior_fixture():
    rows=[]
    for group,name in enumerate(NAMES):
        roles=['ordinary','causal']+(['forced-rejection']if group in REJECTION_POSITIONS else[])
        for role in roles:
            ordinary=role=='ordinary';reject=role=='forced-rejection';accepted=int(role=='causal')
            rows.append(dict(ordinal=len(rows),group=group,name=name,arm=role,request_reset_completed=True,
                native_renderer_and_token_IDs_exact=True,speed_measurement=False,stop_reason='end_of_generation',
                token_ids=list(range(20*group+10,20*group+22)),output_bytes=[65+group]*12,
                full_F32_rows_observed=13,reference_rows=13,prompt_tokens=24,
                known_control_draft_used=False,token_IDs_and_bytes_match_control=True,ending_memory_minimum=35,ending_memory_maximum=35,
                speculation=dict(attempts=int(not ordinary),accepted=accepted,rejected=int(reject),queued_bonus_samples=accepted),
                forced_position=REJECTION_POSITIONS.get(group)if reject else None,
                maximum_absolute_logit_error=0,forced_rejection_F32_restore_passed=True))
    return dict(requests=rows,all_eight_native_inputs_executed=True,speed_measurement=False,actual_accepted_batches=8,
        causal_accepted_batches=8,diagnostic_known_control_accepted_batches=0,actual_forced_rejections=4,
        accepted_path_coverage_complete=True,all_original_tokens_and_bytes_exact=True,forced_rejection_and_full_F32_restore_passed=True)

class BehaviorReviewTests(unittest.TestCase):
    def test_independent_inputs_and_all_positions_are_compared(self):
        data=behavior_fixture();self.assertTrue(behavior_summary(data)['passed'])
        data['requests'][1]['token_ids'][-1]+=1;data['requests'][1]['token_IDs_and_bytes_match_control']=False
        data['all_original_tokens_and_bytes_exact']=False
        self.assertFalse(behavior_summary(data)['passed'])

    def test_missing_coverage_wrong_counts_and_disguised_oracle_are_refused(self):
        original=behavior_fixture()
        for mutate in(lambda d:d['requests'].pop(),lambda d:d.update(actual_forced_rejections=3),
                      lambda d:d['requests'][1].update(known_control_draft_used=True),lambda d:d.update(speed_measurement=True)):
            data=copy.deepcopy(original);mutate(data)
            with self.assertRaises(ValueError):behavior_summary(data)

    def test_numerical_rejection_failure_is_a_negative_scientific_result(self):
        data=behavior_fixture();row=next(r for r in data['requests']if r['arm']=='forced-rejection')
        row['maximum_absolute_logit_error']=.01;row['forced_rejection_F32_restore_passed']=False
        data['forced_rejection_and_full_F32_restore_passed']=False
        self.assertFalse(behavior_summary(data)['passed'])

class SpeedReviewTests(unittest.TestCase):
    def fixture(self):
        ordinary=behavior_fixture()['requests'][0];rows=[]
        payload=120434688
        for ordinal,role in enumerate(('warmup','ordinary','causal','causal','ordinary')):
            row=copy.deepcopy(ordinary);adaptive=role!='ordinary'
            row.update(ordinal=ordinal,arm=role,speed_measurement=bool(ordinal),actual_single_attempt_policy=True,
                F32_reference_role='causal_warmup_diagnostic_only',matches_frozen_ordinary=True,
                total_ms=(98000,100000,98000,99000,102000)[ordinal],prefill_ms=50000,
                decode_tokens_per_second=(.41,.4,.42,.41,.39)[ordinal],
                six_demand=dict(batches=20,reads=120,logical_bytes=1000),
                checkpoint_capacity=dict(logical_payload_bytes=payload if adaptive else 0,
                    new_allocation_bytes=((payload+(2<<20)-1)//(2<<20))*(2<<20)if ordinal==0 else 0,same_original_context=True),
                speculation=dict(attempts=int(adaptive),accepted=int(adaptive),rejected=0,queued_bonus_samples=int(adaptive)))
            rows.append(row)
        return dict(requests=rows,matched_ABBA_request_ordinals=[1,2,3,4],active_cache_slots=128,
            six_demand_enabled=True,timing_Expert_cache_start='empty',known_control_drafts_used=False,
            causal_policy_maximum_actual_attempts=1,all_original_tokens_and_bytes_exact=True,
            causal_warmup_and_candidate_acceptance_passed=True),ordinary

    def test_only_complete_reverse_order_separated_win_passes(self):
        data,ordinary=self.fixture();self.assertTrue(speed_summary(data,ordinary)['passed'])
        data['requests'][3]['total_ms']=103000
        result=speed_summary(data,ordinary)
        self.assertFalse(result['passed']);self.assertFalse(result['both_reverse_pairs_win'][1])

    def test_oracle_snapshot_double_pricing_and_missing_source_proof_are_refused(self):
        for mutate in(lambda d:d['requests'][2].update(known_control_draft_used=True),
                      lambda d:d['requests'][2]['checkpoint_capacity'].update(new_allocation_bytes=2<<20),
                      lambda d:d['requests'][2]['six_demand'].update(reads=119)):
            data,ordinary=self.fixture();mutate(data)
            with self.assertRaises(ValueError):speed_summary(data,ordinary)

    def test_zero_causal_attempts_is_a_completed_negative_result(self):
        data,ordinary=self.fixture()
        for row in data['requests']:
            row['speculation']=dict(attempts=0,accepted=0,rejected=0,queued_bonus_samples=0)
            row['checkpoint_capacity'].update(logical_payload_bytes=0,new_allocation_bytes=0)
        data['causal_warmup_and_candidate_acceptance_passed']=False
        result=speed_summary(data,ordinary)
        self.assertFalse(result['passed']);self.assertFalse(result['one_additional_block_eligible'])

    def test_bounded_speed_entry_has_no_oracle_arm_and_prices_completed_real_capture(self):
        source=speed_loop()
        self.assertEqual(source.count('run_arm(0,'),5)
        self.assertNotIn('run_arm(group,',source)
        self.assertIn('state->used?1:state->planner.choose(pending,draft)',source)
        self.assertIn('checkpoint_capacity.completed(context,last_requested_snapshot,true)',source)
        self.assertIn('adaptive=(kind=="causal"||kind=="warmup"),reject=false,coverage=false',source)
        self.assertIn('delivery_reads!=6*delivery_batches',source)

class RetainedProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained=os.environ.get('QWEN_FROZEN_BUILD_DIR')
        if not retained:raise unittest.SkipTest('Set QWEN_FROZEN_BUILD_DIR to retained native build evidence')
        cls.case=Path(retained).parent/'hardware-first-generation-5720'
    def test_actual_same_width_rows_and_active_state_are_exact(self):
        data=json.loads((self.case/'native-arm1.same-batch.private.json').read_text())
        self.assertTrue(probe_summary(data)['passed'])
        changed=copy.deepcopy(data);changed['ordinary_reference_repeat_candidate_states'][2]['active_tensor_SHA256']='0'*64
        self.assertFalse(probe_summary(changed)['passed'])
    def test_actual_route_geometry_rejects_missing_work_and_duplicate_Experts(self):
        row=json.loads((self.case/'native-arm0.result.private.json').read_text())
        row['speculation']['queued_bonus_samples']=0
        route=json.loads((self.case/'native-arm0.routes.private.json').read_text())
        self.assertTrue(route_geometry(route,row)['all_original_layers_and_Experts_observed'])
        changed=copy.deepcopy(route);changed['records'][0]['ids'][1]=changed['records'][0]['ids'][0]
        with self.assertRaises(ValueError):route_geometry(changed,row)
        changed=copy.deepcopy(row);changed['completed_performance']['delta']['process_calls']+=1
        with self.assertRaises(ValueError):route_geometry(route,changed)

    def test_actual_all_row_distribution_is_complete_and_missing_columns_are_refused(self):
        case=self.case.parent/'hardware-first-generation-5760'
        if not (case/'restored-complete.private.json').exists():self.skipTest('Closed eight-input evidence not available')
        row=json.loads((case/'native-arm2.result.private.json').read_text())
        distribution=json.loads((case/'native-arm2.logit-distribution.private.json').read_text())
        reviewed=distribution_summary(distribution,row)
        self.assertEqual(reviewed['top1_equal_rows'],row['full_F32_rows_observed'])
        changed=copy.deepcopy(distribution);changed['rows'][0]['columns']-=1
        with self.assertRaises(ValueError):distribution_summary(changed,row)
        changed=copy.deepcopy(distribution);changed['rows'][0]['KL_reference_to_candidate']=float('nan')
        with self.assertRaises(ValueError):distribution_summary(changed,row)

if __name__=='__main__':unittest.main()
