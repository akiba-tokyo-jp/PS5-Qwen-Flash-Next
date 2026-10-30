# SPDX-License-Identifier: MIT
"""Refuse inconsistent memory, precision and owner evidence for the actual winner."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from memory_graph_production import require_memory_graph_production
from prepare_first_case import qualified_control

class MemoryProductionTests(unittest.TestCase):
 def setUp(self):
  self.r=json.loads((ROOT/'docs/memory-delivery-graph-adoption-20261030.json').read_text());self.i=json.loads((ROOT/'config/production-installation.json').read_text())
  self.c=dict(active_cache_slots=1381,Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',output_weight_type='Q8_0',shared_Expert_weight_type='Q8_0',graph_reuse_disabled_for_policy=False,prefill_tokens=16,selected_routing_policy=14,normal_performance_case=10760,normal_performance_placement_case=10820,selected_model_receipt_SHA256=self.r['model_receipt_SHA256'],native_running=False,gateway_running=False,model_loaded=False,production_deployment_completed=True,original_restored=False,console_reserved=True,production_SELF=self.r['application_SELF'])
 def test_selected_installed_control(self):
  require_memory_graph_production(self.i,self.c,self.r);self.assertEqual(qualified_control(self.c,True,self.i),self.r['application_SELF'])
 def test_wrong_or_incomplete_native_evidence(self):
  changes=[('policy','active_cache_slots',1253),('policy','quota_transfer_bytes',601284609),('policy','physical_Direct_reserve_bytes',0),('policy','integer_activation_quantization',True),('driver','persistent_shader_cache',True),('normal','same_policy_independent_full_F32_max_error',1),('normal','device_ledger_peak_bytes',2480332801),('normal','actual_workspace_capacity_peak_bytes',67108865),('normal','CPU_heap_peak_bytes',536870913),('normal','source_model_GPU_owners_positively_retired',False),('placement','native_whole_SHA256_identity_EOF_verified',False),('placement','model_loaded',True),('placement','immediate_control_preserved',False),('fixed_quality','compared_requests',7),('fixed_quality','application_output_normalization',True)]
  for section,key,value in changes:
   with self.subTest(section=section,key=key):
    r=copy.deepcopy(self.r);r[section][key]=value
    with self.assertRaises(ValueError):require_memory_graph_production(self.i,self.c,r)
 def test_binding_and_pending_work(self):
  for key,value in [('model_receipt_SHA256','0'*64),('pending_steps',['unfinished']),('all_six_candidates_disposed',False)]:
   r=copy.deepcopy(self.r);r[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):require_memory_graph_production(self.i,self.c,r)
  with self.assertRaises(ValueError):qualified_control(dict(self.c,native_running=True),True,self.i)
 def test_stale_installed_quota_descriptor(self):
  for key,value in [('postload_quota_transfer_bytes',199680000),('output_only_Q8_exception',True),('shared_Expert_Q8_exception',False),('workspace_reservation_bytes',248<<20)]:
   i=copy.deepcopy(self.i);i[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):require_memory_graph_production(i,self.c,self.r)
if __name__=='__main__':unittest.main()
