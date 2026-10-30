# SPDX-License-Identifier: MIT
"""Reject a future control with mismatched Q8 qualification or placement."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from performance_production import require_performance_production
from prepare_first_case import qualified_control

class PerformanceProductionTests(unittest.TestCase):
 def setUp(self):
  self.report=json.loads((ROOT/'docs/six-candidate-adoption-20261030.json').read_text())
  self.installation=json.loads((ROOT/'config/production-installation.json').read_text())
  r=self.report
  self.context=dict(prefill_tokens=16,selected_routing_policy=14,active_cache_slots=997,output_weight_type='Q8_0',
   graph_reuse_disabled_for_policy=False,Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',normal_performance_case=r['placement']['normal_case'],
   normal_performance_placement_case=r['placement']['case'],native_running=False,gateway_running=False,model_loaded=False,
   production_deployment_completed=True,original_restored=False,console_reserved=True,production_SELF=r['application_SELF'])

 def test_exact_completed_installation_is_accepted(self):
  require_performance_production(self.installation,self.context,self.report)
  self.assertEqual(qualified_control(self.context,True,self.installation),self.report['application_SELF'])

 def test_mismatched_or_incomplete_evidence_is_rejected(self):
  mutations=[('application_SELF','sha256','0'*64),('normal','same_policy_independent_full_F32_max_error',1),
   ('normal','all_counting_tokens_equal',False),('policy','active_cache_slots',867),('policy','output_weight_type','BF16'),
   ('policy','integer_activation_quantization',True),('policy','quota_transfer_bytes',199680001),
   ('placement','verified_programs',12),('placement','fresh_idle_confirmed',False),('placement','model_loaded',True),
   ('driver','persistent_shader_cache',True)]
  for section,key,value in mutations:
   with self.subTest(section=section,key=key):
    changed=copy.deepcopy(self.report);changed[section][key]=value
    with self.assertRaises(ValueError):require_performance_production(self.installation,self.context,changed)

 def test_other_active_capacity_is_rejected(self):
  with self.assertRaises(ValueError):require_performance_production(self.installation,dict(self.context,active_cache_slots=867),self.report)

 def test_pending_scope_is_rejected(self):
  changed=copy.deepcopy(self.report);changed['pending_steps']=['unknown']
  with self.assertRaises(ValueError):require_performance_production(self.installation,self.context,changed)

if __name__=='__main__':unittest.main()
