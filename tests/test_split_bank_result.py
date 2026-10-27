#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from split_bank_result import HASHES,PACK_SHA,PHASES,validate_report

def fixture():
    binding=dict(schema='ps5-qwen-isolated-split-bank-title-v1',run_id='b'*32,candidate_SELF_sha256='a'*64,
        candidate_SELF_bytes=23000000,model_loading_enabled=False,source_workers=0)
    r=dict(schema='ps5-qwen-split-bank-result-v1',run_id=binding['run_id'],candidate_SELF_sha256=binding['candidate_SELF_sha256'],pid=123,
        mapped_Direct_read_calls=6,GPU_graphs=12,independent_actual_VkDeviceMemory_groups=2,contiguous_roles_per_actual_group=3,
        nested_strong_backing_leases=6,conservative_cache_charge_bytes=512<<20,device_ledger_live_bytes=0,source_workers=0,automatic_retries=0,
        original_pack_SHA256_checked=True,all_original_raw_and_envelope_SHA256_checked=True,positive_resource_retirement=True,all_started_IO_closed=True,
        positive_device_idle_and_epoch_retirement=True,current_complete_shader_file_SHA256_checked=True,all_used_shader_inputs_SHA256_checked=True,
        all_shader_input_leases_returned=True,model_loaded=False,GPU_IO_overlap_tested=False,generation_speed_measured=False,
        source_pack_sha256=PACK_SHA,non_BF16_exact_F32_input_values=100,device_ledger_peak_bytes=800<<20,shader_module_inputs=5,
        Direct_available_before_GPU=10<<30,Flexible_available_before_GPU=128<<20,kernel_startup_target_pages=2974,
        kernel_free_after_CPU_source_before_GPU=3000,maximum_absolute_error=0.0,maximum_normalized_error=0.0,cases=[],memory_observations=[])
    for group in range(2):
        for role in range(3):
            raw,envelope=HASHES[role*2+group]
            r['cases'].append(dict(group=group,role=role,global_slot=52 if group else 0,local_slot=26 if group else 0,
                columns=640 if role==2 else 2560,rows=2560 if role==2 else 640,residue=1632 if role==2 else 2784,GPU_graphs=2,
                original_raw_sha256=raw,original_envelope_sha256=envelope,F64_reference_passed=True,same_F32_outputs_bit_exact=True,
                whole_envelope_unchanged_after_GPU=True,preceding_canary_checked=bool(group),following_canary_checked=not bool(group),
                reference_absolute_tolerance=1e-5,reference_relative_tolerance=1e-5,maximum_absolute_error=0.0,maximum_normalized_error=0.0))
    for phase in PHASES:r['memory_observations'].append(dict(phase=phase,CPU_heap_mapped_bytes=32<<20,CPU_heap_peak_bytes=32<<20,
        CPU_heap_libc_fallbacks=0,kernel_free_pages=4000,kernel_startup_target_pages=2974))
    return r,binding

class Review(unittest.TestCase):
    def setUp(self):self.r,self.b=fixture()
    def reject(self,changed):
        with self.assertRaises((ValueError,KeyError,TypeError)):validate_report(changed,self.b,123)
    def test_positive_is_only_fixture(self):
        result=validate_report(self.r,self.b,123)
        self.assertTrue(result['native_report_scope_passed']);self.assertFalse(result['model_speed_qualified']);self.assertFalse(result['production_adopted'])
    def test_independent_owner_and_scope(self):
        for key,value in(('pid',124),('run_id','f'*32),('candidate_SELF_sha256','f'*64),('model_loaded',True),('GPU_IO_overlap_tested',True),('generation_speed_measured',True)):
            with self.subTest(key=key):r=copy.deepcopy(self.r);r[key]=value;self.reject(r)
    def test_each_finite_count_and_completion(self):
        for key,value in self.r.items():
            if type(value)is bool:
                r=copy.deepcopy(self.r);r[key]=not value;self.reject(r)
            elif key in('mapped_Direct_read_calls','GPU_graphs','independent_actual_VkDeviceMemory_groups','contiguous_roles_per_actual_group',
                'nested_strong_backing_leases','conservative_cache_charge_bytes','device_ledger_live_bytes','source_workers','automatic_retries'):
                for altered in(value+1,True):r=copy.deepcopy(self.r);r[key]=altered;self.reject(r)
    def test_shapes_hashes_and_boundary_canaries(self):
        for i in range(6):
            for key,value in(('group',9),('local_slot',52),('residue',0),('original_raw_sha256','0'*64),('original_envelope_sha256','0'*64),
                ('preceding_canary_checked',not self.r['cases'][i]['preceding_canary_checked']),('following_canary_checked',not self.r['cases'][i]['following_canary_checked'])):
                r=copy.deepcopy(self.r);r['cases'][i][key]=value;self.reject(r)
        r=copy.deepcopy(self.r);r['cases'].reverse();self.reject(r)
    def test_numerical_error_controls(self):
        for key,value in(('maximum_normalized_error',1.01),('maximum_normalized_error',float('nan')),('maximum_absolute_error',float('inf')),
            ('reference_absolute_tolerance',1e-3),('same_F32_outputs_bit_exact',False)):
            r=copy.deepcopy(self.r);r['cases'][0][key]=value;self.reject(r)
        r=copy.deepcopy(self.r);r['maximum_absolute_error']=1.0;self.reject(r)
    def test_memory_and_retirement_bounds(self):
        for key,value in(('device_ledger_peak_bytes',1792<<20|1),('kernel_free_after_CPU_source_before_GPU',2973),('Direct_available_before_GPU',1024),('Flexible_available_before_GPU',0)):
            r=copy.deepcopy(self.r);r[key]=value;self.reject(r)
        for key,value in(('CPU_heap_libc_fallbacks',1),('CPU_heap_peak_bytes',513<<20),('CPU_heap_mapped_bytes',True)):
            r=copy.deepcopy(self.r);r['memory_observations'][0][key]=value;self.reject(r)
        r=copy.deepcopy(self.r);r['memory_observations'].pop();self.reject(r)
    def test_all_case_fields_required(self):
        for key in self.r['cases'][0]:
            r=copy.deepcopy(self.r);del r['cases'][0][key];self.reject(r)
if __name__=='__main__':unittest.main()
