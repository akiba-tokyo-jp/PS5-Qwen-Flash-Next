# SPDX-License-Identifier: MIT
"""A performance fragment must not manufacture a wider runtime admission."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qualified_performance import apply_profile


class QualifiedProfileTests(unittest.TestCase):
    def fixture(self):
        profile=dict(schema='ps5-qwen-qualified-performance-profile-v1',application_SELF=dict(sha256='a'*64,bytes=123),
            driver=dict(archive_sha256='b'*64,persistent_shader_cache=False,persistent_pipeline_cache=False),
            precision=dict(weights='original BF16/F32',KV_cache='F32',quantization=False),
            selected_native_policy=dict(native_bf16_indexed_vector=dict(enabled=True),native_indexed_vector_fixture=dict(enabled=True),
                native_padded_expert_cache=dict(active_slots=128,layout_qualification_SELF_SHA256='c'*64,layout_qualification_result_SHA256='d'*64)),
            disabled_native_policy=['native_mapped_streaming_copy'],required_runtime_scope={k:dict(enabled=True,case=5520)for k in
                ('native_matched_cache_production','native_resident_OS_reserve','native_resident_CPU_table_pricing','native_prefix_delivery_combination')})
        policy=dict(allowed_modes=['first-generation-validation'],deployment_enabled=False,native_first_generation_validation=dict(run='unchanged'),
            native_prefill=dict(tokens=4),native_source_schedule=dict(source_window_bytes=8388608,maximum_outstanding_reads=2),
            native_large_cache_scope=dict(stage='model',active_slots=128,physical_planes=129,cache_request_bytes=1274462208,
                layout_qualification=dict(SELF_sha256='c'*64,report_sha256='d'*64)),**copy.deepcopy(profile['required_runtime_scope']))
        package=dict(integrity_verified=True,roundtrip_segments_verified=6,real_module_import_audit=dict(missing=[]),
            SELF=copy.deepcopy(profile['application_SELF']),linked_driver=dict(archive_sha256='b'*64))
        return policy,profile,package

    def test_exact_prepared_runtime_and_existing_bindings_are_preserved(self):
        policy,profile,package=self.fixture();original=copy.deepcopy(policy)
        result=apply_profile(policy,profile,package)
        self.assertEqual(policy,original)
        self.assertEqual(result['native_first_generation_validation'],original['native_first_generation_validation'])
        self.assertEqual(result['native_large_cache_scope'],original['native_large_cache_scope'])
        self.assertEqual(result['native_padded_expert_cache']['active_slots'],128)

    def test_wrong_or_missing_runtime_and_layout_are_refused(self):
        policy,profile,package=self.fixture()
        for key in profile['required_runtime_scope']:
            for missing in (False,True):
                bad=copy.deepcopy(policy)
                if missing:bad.pop(key)
                else:bad[key]['enabled']=1
                with self.subTest(key=key,missing=missing),self.assertRaises(ValueError):apply_profile(bad,profile,package)
        for key,value in (('active_slots',53),('physical_planes',128),('cache_request_bytes',512<<20),('stage','layout')):
            bad=copy.deepcopy(policy);bad['native_large_cache_scope'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):apply_profile(bad,profile,package)
        bad=copy.deepcopy(policy);bad['native_large_cache_scope']['layout_qualification']['report_sha256']='e'*64
        with self.assertRaises(ValueError):apply_profile(bad,profile,package)

    def test_historical_53_slot_package_remains_explicitly_usable(self):
        policy,profile,package=self.fixture();profile.pop('required_runtime_scope')
        profile['selected_native_policy']['native_padded_expert_cache']['active_slots']=53
        policy.pop('native_large_cache_scope')
        self.assertEqual(apply_profile(policy,profile,package)['native_padded_expert_cache']['active_slots'],53)


if __name__=='__main__':unittest.main()
