# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from device_state_result import validate
def good():
    r=dict(schema='ps5-qwen-device-state-fixture-result-v1',pid=7,state_bytes=136<<20,CPU_transfer_window_bytes=2<<20,device_ledger_live_bytes=0,
        device_ledger_peak_bytes=530<<20,shader_CPU_verified_assets=1527,shader_module_inputs_after_CPU_verification=0,
        model_loaded=False,model_state_completeness_qualified=False,host_full_state_payload_allocated=False,
        cases=[dict(case=n,capture_pieces=2 if n%2==0 else 1,restore_pieces=1+n%3,discard=n==7,F32_bits_exact=True,canaries_intact=True)for n in range(8)])
    for key in ('all_F32_bits_exact','canaries_intact','all_copy_owners_retired','source_IO_completed_and_worker_stopped','positive_device_idle_and_epoch_retirement',
        'all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned','queue_submission_count_not_inferred'):r[key]=True
    stages=['device_state_shared_shader_CPU_admission_completed GPU_not_started=1']
    for n in range(8):stages+=['device_state_before_capture owners_pinned=1','device_state_capture_copies_completed owners_pinned=1',
        'device_state_before_restore owners_pinned=1','device_state_restore_discarded_without_copy'if n==7 else'device_state_restore_copies_completed owners_pinned=1',
        'device_state_case_exact_and_positive_completion']
    return r,'\n'.join(stages+['device_state_validation_completed_waiting_for_ordinary_close model_loaded=0'])
class Controls(unittest.TestCase):
    def test_complete(self):
        r,s=good();v=validate(r,s,7);self.assertTrue(v['completed']);self.assertFalse(v['complete_model_checkpoint_qualified'])
    def test_missing(self):
        for key in good()[0]:
            r,s=good();del r[key]
            with self.assertRaises(ValueError):validate(r,s,7)
    def test_bad_owners_or_scope(self):
        for key,value in [('all_copy_owners_retired',False),('model_loaded',True),('device_ledger_live_bytes',1),('state_bytes',136.0),
            ('host_full_state_payload_allocated',True),('device_ledger_peak_bytes',769<<20),('shader_CPU_verified_assets',0)]:
            r,s=good();r[key]=value
            with self.assertRaises(ValueError):validate(r,s,7)
    def test_wrong_durable_order(self):
        r,s=good()
        for bad in (s.replace('device_state_capture_copies_completed owners_pinned=1','',1),s.replace('device_state_before_capture owners_pinned=1','device_state_before_restore owners_pinned=1',1)):
            with self.assertRaises(ValueError):validate(r,bad,7)
        with self.assertRaises(ValueError):validate(r,s,8)
if __name__=='__main__':unittest.main()
