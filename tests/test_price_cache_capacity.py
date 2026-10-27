# SPDX-License-Identifier: MIT
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('price',Path(__file__).resolve().parents[1]/'tools/price_cache_capacity.py')
price=importlib.util.module_from_spec(spec);spec.loader.exec_module(price)
M=1<<20
class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.values=dict(sweep=dict(baseline_53_native_counters_exact=True,
            actual_ExpertPolicy_matches_Python_at_all_capacities=True,native_speed_qualified=False,PS5_operations=0,
            policies=[dict(slots=n,external_byte_reduction_fraction=0,
                external_one_token_uploaded_bytes_reduction_fraction=0)for n in (53,128,160,384)]),
            before=dict(pid=123,CPU_budget_bytes=512*M,Flexible_available_bytes=415*M,
                Flexible_reserve_bytes=256*M,additional_Direct_platform_margin_bytes=256*M,
                device_buffer_batch_limit_bytes=2048*M),
            after=dict(model_loaded=True,native_Direct_available_bytes=3243*M,
                native_Direct_owned_bytes=8366*M,native_Direct_pool_bytes=11712*M),
            system=dict(pid=123,model_loaded=True,CPU_heap_uses_Direct_pool=True,CPU_heap_libc_fallbacks=0,
                CPU_heap_mapped_bytes=96*M),
            result=dict(pid=123,full_model_inference_executed=True,GPU_completion_and_retirement_passed=True,
                model_resources_released_after_completion=True,untracked_libc_heap_fallbacks=0,
                postload_device_live_bytes=0,CPU_heap_peak_bytes=432*M,postload_device_peak_bytes=904*M,
                driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',profile='cumulative-idle',
                native_archive_sha256='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925',
                candidate_SELF_sha256='ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d'))
    def test_each_actual_bank_is_rounded(self):
        self.assertEqual(price.rounded_banks(53),510*M)
        self.assertEqual(price.rounded_banks(128),1218*M)
        for bad in (True,52,1025,128.0):
            with self.assertRaises(ValueError):price.rounded_banks(bad)
    def test_context_workspace_and_CPU_are_not_double_charged(self):
        r=price.price(**self.values);row=r['candidates'][1]
        self.assertEqual(row['historical_device_peak_with_bank_delta_bytes'],1612*M)
        self.assertEqual(r['separately_preserved_allowances']['CPU_growth_to_existing_cap'],416*M)
        self.assertEqual(row['required_after_load_with_existing_CPU_cap_bytes'],2956*M)
        self.assertTrue(row['fits_historical_after_load_envelope'])
        self.assertFalse(r['current_physical_admission_granted'])
    def test_policy_gap_and_real_historical_pool_bound_are_separate(self):
        rows=price.price(**self.values)['candidates']
        self.assertFalse(rows[2]['fits_historical_after_load_envelope'])
        self.assertFalse(rows[2]['banks_plus_already_owned_exceed_historical_pool'])
        self.assertTrue(rows[3]['banks_plus_already_owned_exceed_historical_pool'])
    def test_changed_identity_lifecycle_and_domains_are_rejected(self):
        for group,key,value in (('result','GPU_completion_and_retirement_passed',False),
            ('result','postload_device_live_bytes',1),('system','pid',124),
            ('system','CPU_heap_libc_fallbacks',1),('system','CPU_heap_uses_Direct_pool',False),
            ('result','profile','control'),('result','CPU_heap_peak_bytes',513*M),
            ('after','native_Direct_pool_bytes',1),('sweep','native_speed_qualified',True)):
            bad=copy.deepcopy(self.values);bad[group][key]=value
            with self.subTest(group=group,key=key),self.assertRaises(ValueError):price.price(**bad)
if __name__=='__main__':unittest.main()
