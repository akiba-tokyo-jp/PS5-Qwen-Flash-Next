#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from price_ple_admission import price,CPU_PHASES,GPU_PHASES

def case(gpu=False):
    digest='a'*64
    scope=dict(driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',profile='cumulative-idle',
        native_archive_sha256='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925',persistent_caches_enabled=False)
    sample=dict(free_first=8137 if gpu else 8175,free_last=8137 if gpu else 8174,
        minimum=898,reserved=206,page_bytes=16384,native_startup_target=2974,full_prelaunch_required=10142)
    free=[3165,4581,3177,3177,3177,3145]if gpu else[1884,3296,3300,3296]
    rows=[dict(phase=phase,kernel_free_pages=value,kernel_startup_target_pages=2974,
        VM=dict(free=value),CPU_heap_mapped_bytes=16<<20,CPU_heap_peak_bytes=16<<20,CPU_heap_libc_fallbacks=0,
        Flexible_available_bytes=440401920)for phase,value in zip(CPU_PHASES+(GPU_PHASES if gpu else()),free)]
    result=dict(pid=17,model_loaded=False)
    if gpu:result.update(schema='ps5-qwen-PLE-slice-smoke-v1',isolated_title_memory_observations=rows,
        positive_device_idle_and_epoch_retirement=True,all_F32_outputs_bit_exact=True,F64_reference_passed=True)
    else:result.update(schema='ps5-qwen-isolated-PLE-CPU-calibration-v2',observations=rows,
        all_started_CPU_operations_returned=True,GPU_graphs=0,GPU_initializations=0,source_owner_prepared=True)
    return dict(label='synthetic_gpu'if gpu else'synthetic_cpu',SELF_sha256=digest,
        policy=dict(native_PLE_slice_validation=scope,native_isolated_PLE_title=dict(candidate_SELF_sha256=digest,
            model_loading_enabled=False,CPU_only_startup_calibration=not gpu)),
        admission=dict(completed=True,observations=[copy.deepcopy(sample)for _ in range(10)]),
        result=result,owner=dict(pid=17),completion=dict(completed=True),
        restoration=dict(completed=True,unknown_completion=False,native_owners=0))

class PricingTests(unittest.TestCase):
    def test_different_phase_peaks_are_not_added(self):
        result=price([case(),case(True)])
        self.assertEqual(result['CPU_phase_requirement_pages'],7701)
        self.assertEqual(result['GPU_startup_requirement_pages'],8190)
        self.assertEqual(result['proposed_future_prelaunch_pages'],8190)
        self.assertFalse(result['fresh_admission_granted'])
        self.assertFalse(result['physical_hardware_minimum_established'])

    def test_control_cannot_hide_a_more_expensive_completed_gpu_interval(self):
        self.assertEqual(price([case()])['proposed_future_prelaunch_pages'],8109)
        self.assertGreater(price([case(),case(True)])['proposed_future_prelaunch_pages'],8109)

    def test_incomplete_or_unknown_cases_do_not_price_a_launch(self):
        for edit in (lambda c:c['completion'].update(completed=False),
            lambda c:c['restoration'].update(unknown_completion=True),
            lambda c:c['owner'].update(pid=18),lambda c:c['admission']['observations'].pop(),
            lambda c:c['result']['observations'].pop(),lambda c:c['result'].update(model_loaded=True)):
            value=case();edit(value)
            with self.assertRaises(ValueError):price([value])

    def test_other_images_and_floors_cannot_borrow_an_admission(self):
        a=case();b=case(True);b['SELF_sha256']='b'*64
        with self.assertRaises(ValueError):price([a,b])
        for field in('minimum','reserved','page_bytes','native_startup_target','full_prelaunch_required'):
            value=case();value['admission']['observations'][0][field]+=1
            with self.assertRaises(ValueError):price([value])

    def test_heap_and_pool_changes_are_outside_this_calibration(self):
        for field,value in(('CPU_heap_libc_fallbacks',1),('CPU_heap_mapped_bytes',32<<20),
            ('CPU_heap_peak_bytes',32<<20),('Flexible_available_bytes',(64<<20)-1),('kernel_free_pages',1153)):
            c=case();c['result']['observations'][0][field]=value
            if field=='kernel_free_pages':c['result']['observations'][0]['VM']['free']=value
            with self.assertRaises(ValueError):price([c])

    def test_variation_and_gpu_startup_are_retained(self):
        with self.assertRaises(ValueError):price([case()],255)
        c=case(True);c['result']['isolated_title_memory_observations'][-2].update(kernel_free_pages=2973,VM=dict(free=2973))
        with self.assertRaises(ValueError):price([c])

if __name__=='__main__':unittest.main()
