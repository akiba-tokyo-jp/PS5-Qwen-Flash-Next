# SPDX-License-Identifier: MIT
"""Exercise the actual transformed terminal guard without network or model work."""
import ast,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from observe_routing_winners_monitor import observer_source

class TerminalScopeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  tree=ast.parse(observer_source())
  checks=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='require'and
    len(n.args)>1 and isinstance(n.args[1],ast.Constant)and n.args[1].value=='Exact positive Q2 application completion required']
  assert len(checks)==1
  cls.guard=compile(ast.Expression(checks[0].args[0]),'<actual-normal-terminal-guard>','eval')

 def valid(self,slots=997,disabled=False):
  owner=dict(pid=123,run_id='finite',candidate_SELF_sha256='candidate',model_receipt_sha256='model')
  result=dict(owner,completed=True,active_cache_slots=slots,Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',HTTP_requests=2,VideoOut_starts=1,
   passive_monitor_and_API_completed=True,all_model_source_device_owners_positively_retired=True,device_ledger_live_bytes=0,
   full_F32_continuation_and_routes_passed=True,source_windows=1234,source_completed_windows=1234,routing_winners_policy=14,graph_reuse_disabled_for_policy=disabled)
  return dict(result=result,owner=owner,run=owner['run_id'],ROUTING_SCOPE=dict(active_cache_slots=slots,selected_routing_policy=14,graph_reuse_disabled_for_policy=disabled))

 def test_current_and_historical_capacities(self):
  for slots,disabled in ((997,False),(867,True)):
   self.assertTrue(eval(self.guard,{},self.valid(slots,disabled)))

 def test_mismatched_capacity_is_rejected(self):
  env=self.valid();env['result']['active_cache_slots']=867
  self.assertFalse(eval(self.guard,{},env))

 def test_graph_scope_is_enforced(self):
  env=self.valid();env['result']['graph_reuse_disabled_for_policy']=True
  self.assertFalse(eval(self.guard,{},env))

 def test_positive_retirement_is_still_required(self):
  for key,value in (('all_model_source_device_owners_positively_retired',False),('device_ledger_live_bytes',1),('source_completed_windows',1233)):
   env=self.valid();env['result'][key]=value
   self.assertFalse(eval(self.guard,{},env))

if __name__=='__main__':unittest.main()
