# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_first_case import qualified_control
def production():
    record=dict(schema='ps5-qwen-production-installation-v1',application_SELF=dict(bytes=17,sha256='abc'))
    for key in ('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified','original_rollback_full_readback_verified',
        'arithmetic_smoke_passed','outputs_and_token_ids_equal_to_qualified_selected_case','source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified'):record[key]=True
    state=dict(native_running=False,gateway_running=False,model_loaded=False,console_reserved=True,production_deployment_completed=True,
        original_restored=False,production_SELF=dict(path='preserved-control',bytes=17,sha256='abc'),original_SELF=dict(path='rollback'))
    return state,record
class Controls(unittest.TestCase):
    def test_production(self):
        s,p=production();self.assertEqual(qualified_control(s,True,p),s['production_SELF'])
    def test_every_missing_proof(self):
        for key in production()[1]:
            s,p=production();del p[key]
            with self.assertRaises(ValueError):qualified_control(s,True,p)
        for key in production()[0]:
            if key=='original_SELF':continue
            s,p=production();del s[key]
            with self.assertRaises(ValueError):qualified_control(s,True,p)
    def test_running_unknown_or_misbound(self):
        for key,value in [('native_running',True),('gateway_running',None),('model_loaded',True),('original_restored',True)]:
            s,p=production();s[key]=value
            with self.assertRaises(ValueError):qualified_control(s,True,p)
        s,p=production();s['production_SELF']['sha256']='different'
        with self.assertRaises(ValueError):qualified_control(s,True,p)
    def test_legacy_unchanged(self):
        s,p=production();s.update(original_restored=True,original_numerical_re_admission='passed',complete_original_SELF_readback_after_shutdown=True,original_moe_admitted=True)
        self.assertEqual(qualified_control(s),s['original_SELF'])
        s['original_moe_admitted']=False
        with self.assertRaises(ValueError):qualified_control(s)
if __name__=='__main__':unittest.main()
