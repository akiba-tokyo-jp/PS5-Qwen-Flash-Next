# SPDX-License-Identifier: MIT
import copy,json,sys,unittest
from unittest.mock import patch
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
    def mixed(self):
        root=Path(__file__).resolve().parents[1]
        report=json.loads((root/'docs/expert-q2-results-20261029.json').read_text())
        state,record=production()
        for key in ('original_rollback_full_readback_verified','arithmetic_smoke_passed','outputs_and_token_ids_equal_to_qualified_selected_case'):
            del record[key]
        record.update(previous_production_rollback_preserved=True,
            application_SELF=copy.deepcopy(report['production_placement']['application_SELF']),
            previous_production_SHA256=report['production_placement']['previous_production_SHA256'],
            precision=dict(Expert_weights='Gate/Up Q2_K; Down Q4_0',other_weights='original BF16/F32',
                KV_cache='F32',activation_inputs='F32',quantization='Expert weights only'),
            qualification_report='docs/expert-q2-results-20261029.json')
        state['production_SELF']=dict(path='preserved-mixed-control',**record['application_SELF'])
        state['Expert_format']='Gate_Up_Q2_K_Down_Q4_0'
        return state,record,report
    def test_exact_closed_mixed_control(self):
        s,p,r=self.mixed()
        with patch('prepare_first_case.read',return_value=r):
            self.assertEqual(qualified_control(s,True,p),s['production_SELF'])
    def test_mixed_refuses_missing_completion_quality_and_identity(self):
        s,p,r=self.mixed()
        for section,keys in {
            'fixed_quality_comparison':['completed','minimum_baseline_met','every_Q4_correct_answer_retained','quality_preserved'],
            'normal_application':['completed','precision_label_correct','all_sources_and_GPU_owners_positively_retired','same_format_full_F32_and_routes_exact'],
            'production_placement':['completed','exact_Q4_BF16_and_older_rollbacks_preserved','canonical_and_rollback_native_whole_SHA256_verified','all_five_settings_verified','fresh_idle_confirmed']}.items():
            for key in keys:
                bad=copy.deepcopy(r);bad[section].pop(key)
                with patch('prepare_first_case.read',return_value=bad),self.assertRaises(ValueError):qualified_control(s,True,p)
        for key,value in [('previous_production_SHA256','wrong'),('native_title_running',True),('gateway_running',None)]:
            bad=copy.deepcopy(r);bad['production_placement'][key]=value
            with patch('prepare_first_case.read',return_value=bad),self.assertRaises(ValueError):qualified_control(s,True,p)
        s['Expert_format']='Q4_0'
        with patch('prepare_first_case.read',return_value=r),self.assertRaises(ValueError):qualified_control(s,True,p)
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
