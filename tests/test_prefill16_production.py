#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject mismatched or incomplete normal-prefill production evidence."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from prepare_first_case import require_prefill16_production
class Prefill16ProductionTests(unittest.TestCase):
 def setUp(self):
  self.report=json.loads((ROOT/'docs/prefill16-adoption-20261030.json').read_text());r=self.report
  self.installation=dict(application_SELF=r['application_SELF'],previous_production_SHA256=r['previous_application_SELF']['sha256'],precision=r['precision'],driver=r['driver'],
   prefill_tokens=16,selected_routing_policy=14,normal_validation_case=r['placement']['normal_case'],production_placement_case=r['placement']['case'],owner_expected_quantization_loss_accepted=True)
  self.context=dict(prefill_tokens=16,selected_routing_policy=14,prefill16_normal_case=r['placement']['normal_case'],prefill16_placement_case=r['placement']['case'],Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE')
 def test_completed_exact_evidence_is_accepted(self):
  require_prefill16_production(self.installation,self.context,self.report)
 def test_incomplete_or_mismatched_report_is_refused(self):
  for section,key,value in [('application_SELF','sha256','0'*64),('normal','all_declared_adoption_criteria_passed',False),
   ('normal','same_policy_independent_full_F32_max_error',1),('normal','all_counting_tokens_equal',False),('normal','prefill_tokens',4),
   ('placement','verified_programs',11),('placement','verified_settings',4),('placement','fresh_idle_confirmed',False),('placement','model_loaded',True),('driver','persistent_pipeline_cache',True)]:
   with self.subTest(section=section,key=key):
    r=copy.deepcopy(self.report);r[section][key]=value
    with self.assertRaises(ValueError):require_prefill16_production(self.installation,self.context,r)
 def test_other_context_width_is_refused(self):
  with self.assertRaises(ValueError):require_prefill16_production(self.installation,dict(self.context,prefill_tokens=4),self.report)
if __name__=='__main__':unittest.main()
