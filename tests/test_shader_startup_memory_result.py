# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from shader_startup_memory_result import validate
def good():
    phases=['shader_CPU_admission_begin','shader_file_initialization_before','shader_file_initialization_returned',
        'shader_registry_initialization_before','shader_registry_initialization_returned','shader_prior_proof_before',
        'shader_prior_proof_returned','shader_CPU_admission_returned']
    return dict(schema='ps5-qwen-shader-startup-memory-result-v1',pid=7,run_id='a'*32,
        all_shader_input_calls_returned=True,CPU_only=True,ordinary_OS_close_required=True,GPU_calls=0,source_workers=0,
        model_metadata_files=0,model_loaded=False,matched_idle_ns=2000000,shader_read_calls=1,shader_returned_bytes=16384,
        shader_file_bytes=16384,shader_input_window_bytes=16384,samples=[dict(phase=p,valid=True,idle_before_ns=i*10000000+1,
            before_ns=i*10000000+2000001,write_after_ns=i*10000000+3000001,after_ns=i*10000000+4000001,
            free_idle_before=5000-i*4,free_before=5000-i*4,free_after_write=4999-i*4,free_after=4998-i*4)
            for i,p in enumerate(('shader_asset_read_before_native_call','shader_asset_read_native_call_returned'))],
        operation_boundaries=dict(enabled=True,invalid_observation=False,total_observations=len(phases),
            rows=[dict(phase=p,sequence=i+1,valid=True,kernel_free_pages=5000-i,monotonic_ns=i+1)for i,p in enumerate(phases)]))
class Controls(unittest.TestCase):
    def test_signed_intervals_keep_negative_results(self):
        r=validate(good(),7,'a'*32);self.assertEqual(r['signed_page_changes']['journal_write_pages'],-2)
        self.assertEqual(r['signed_page_changes']['journal_fsync_pages'],-2)
        self.assertEqual(r['signed_page_changes']['read_marker_gap_pages'],-2)
        self.assertFalse(r['proprietary_cause_identified']);self.assertFalse(r['GPU_execution_qualified'])
    def test_owner_and_scope(self):
        for key,value in [('pid',True),('pid',8),('run_id','b'*32),('GPU_calls',1),('source_workers',1),('model_metadata_files',1),
            ('CPU_only',False),('model_loaded',True),('all_shader_input_calls_returned',False),('matched_idle_ns',2000000.0)]:
            r=good();r[key]=value
            with self.assertRaises(ValueError):validate(r,7,'a'*32)
    def test_counts_and_window(self):
        for key,value in [('shader_read_calls',2),('shader_read_calls',True),('shader_returned_bytes',0),('shader_input_window_bytes',1)]:
            r=good();r[key]=value
            with self.assertRaises(ValueError):validate(r,7,'a'*32)
    def test_pair_order_and_observations(self):
        for change in(lambda r:r['samples'].reverse(),lambda r:r['samples'].pop(),lambda r:r['samples'][0].update(valid=False),
            lambda r:r['samples'][1].update(idle_before_ns=1),lambda r:r['samples'][0].update(before_ns=1)):
            r=good();change(r)
            with self.assertRaises(ValueError):validate(r,7,'a'*32)
    def test_ring_wrap_or_missing_phase_is_not_complete(self):
        for change in(lambda r:r['operation_boundaries'].update(total_observations=65),
            lambda r:r['operation_boundaries'].update(invalid_observation=True),lambda r:r['operation_boundaries']['rows'][0].update(phase='missing'),
            lambda r:r['operation_boundaries']['rows'][0].update(sequence=True)):
            r=good();change(r)
            with self.assertRaises(ValueError):validate(r,7,'a'*32)
if __name__=='__main__':unittest.main()
