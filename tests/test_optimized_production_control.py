# SPDX-License-Identifier: MIT
"""Require positive optimized-Q2 evidence before preserving it as a control."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_first_case as subject

class OptimizedControlTests(unittest.TestCase):
    def setUp(self):
        self.installation=json.loads((ROOT/'config/production-installation.json').read_text())
        self.report=json.loads((ROOT/self.installation['qualification_report']).read_text())
        self.context=dict(native_running=False,gateway_running=False,model_loaded=False,
            production_deployment_completed=True,original_restored=False,console_reserved=True,
            production_SELF=dict(self.installation['application_SELF'],path='preserved-local-control'),
            Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE')
    def qualify(self,report=None,context=None,installation=None):
        with patch.object(subject,'read',return_value=self.report if report is None else report):
            return subject.qualified_control(self.context if context is None else context,True,
                self.installation if installation is None else installation)
    def test_current_complete_evidence(self):
        self.assertEqual(self.qualify(),self.context['production_SELF'])
    def test_previous_optimized_control_remains_admissible(self):
        installation=json.loads((ROOT/'config/production-installation-Q2-optimized-20261030.json').read_text())
        report=json.loads((ROOT/installation['qualification_report']).read_text())
        context=copy.deepcopy(self.context);context['production_SELF']=dict(installation['application_SELF'],path='preserved-local-control')
        self.assertEqual(self.qualify(report,context,installation),context['production_SELF'])
    def test_new_IO_control_requires_actual_selected_paths_and_all_decisions(self):
        for group,key,value in [(None,'all_four_proposals_disposed',False),
            ('normal_application','all_selected_IO_paths_exercised',False),
            ('normal_application','io_winner_flags',1),
            ('production_placement','verified_native_programs',9)]:
            report=copy.deepcopy(self.report)
            (report if group is None else report[group])[key]=value
            with self.subTest(group=group,key=key),self.assertRaises(ValueError):self.qualify(report)
    def test_resource_completion_integrity_and_quality_cannot_be_dropped(self):
        for group,key in [('normal_application','ordinary_same_width_full_F32_and_routes_exact'),
            ('normal_application','final_unlike_width_full_vocab_top1_and_tokens_equal'),
            ('normal_application','all_model_source_and_GPU_owners_positively_retired'),
            ('normal_application','ordinary_close_and_exact_restoration_passed'),
            ('production_placement','all_canonical_and_rollback_whole_SHA256_identity_EOF_passed'),
            ('production_placement','fresh_idle_confirmed'),('quality','owner_expected_Expert_Q2_loss_accepted')]:
            report=copy.deepcopy(self.report);report[group][key]=False
            with self.subTest(group=group,key=key),self.assertRaises(ValueError):self.qualify(report)
    def test_unknown_completion_and_wrong_source_are_rejected(self):
        for mutate in (lambda r:r.update(unknown_completion=True),
            lambda r:r['production_placement']['application_SELF'].update(sha256='0'*64),
            lambda r:r['production_placement'].update(native_title_running=True),
            lambda r:r['quality'].update(output_normalization=True)):
            report=copy.deepcopy(self.report);mutate(report)
            with self.assertRaises(ValueError):self.qualify(report)
    def test_live_or_unowned_context_is_rejected(self):
        for key,value in [('native_running',True),('gateway_running',True),('model_loaded',True),('console_reserved',False)]:
            context=copy.deepcopy(self.context);context[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.qualify(context=context)

if __name__=='__main__':unittest.main()
