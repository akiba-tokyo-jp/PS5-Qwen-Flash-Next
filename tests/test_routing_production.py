#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ensure fresh experiments bind the installed routing winner and its rollback."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from prepare_first_case import require_routing_production

class RoutingProductionTests(unittest.TestCase):
 def setUp(self):
  self.report=json.loads((ROOT/'docs/routing-winners-adoption-20261030.json').read_text())
  r=self.report
  self.installation=dict(precision=r['precision'],application_SELF=r['application_SELF'],previous_production_SHA256=r['previous_application_SELF']['sha256'],
   selected_routing_policy=r['policy']['bits'],normal_validation_case=r['placement']['normal_case'],production_placement_case=r['placement']['case'],owner_expected_quantization_loss_accepted=True)
  self.context=dict(selected_routing_policy=14,routing_winners_normal_case=9550,
   routing_winners_placement_case=9560,Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE')
 def test_completed_routing_evidence_is_accepted(self):
  require_routing_production(self.installation,self.context,self.report)
 def test_changed_or_incomplete_evidence_is_refused(self):
  for section,key,value in [('application_SELF','sha256','0'*64),
    ('normal','all_declared_adoption_criteria_passed',False),('normal','same_policy_independent_full_F32_max_error',1),
    ('placement','fresh_idle_confirmed',False),('placement','verification_files',15),
    ('placement','native_title_running',True),('precision','KV_cache','Q4')]:
   with self.subTest(section=section,key=key):
    changed=copy.deepcopy(self.report);changed[section][key]=value
    with self.assertRaises(ValueError):require_routing_production(self.installation,self.context,changed)
 def test_different_live_control_is_refused(self):
  changed=dict(self.context,selected_routing_policy=6)
  with self.assertRaises(ValueError):require_routing_production(self.installation,changed,self.report)
if __name__=='__main__':unittest.main()
