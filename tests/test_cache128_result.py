# SPDX-License-Identifier: MIT
"""Fault injection of model-capacity bindings; synthetic records are not GPU evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from cache128_result import CACHE_BYTES,MODEL_REQUIREMENT,validate_binding
from first_generation_result import validate
from padded_bank_result import RESIDUES,SOURCE_SHA
import test_first_generation_result as baseline


class Cache128Records(unittest.TestCase):
    def setUp(self):
        baseline.FirstGenerationRecords.setUp(self)
        self.layout=dict(schema='ps5-qwen-padded-bank-layout-result-v2',pid=900,run_id='d'*32,
            candidate_SELF_sha256='e'*64,source_SHA256=SOURCE_SHA,eligible=True,all_started_IO_closed=True,
            Direct_reads=1,GPU_graphs=360,model_loaded=False,VideoOut_started=False,automatic_retries=0,
            positive_resource_retirement=True,source_workers_stopped=True,device_ledger_live_bytes=0,
            device_ledger_allocations=4,device_ledger_peak_bytes=698351616,descriptor_alignment=32,memory_flags=7,
            active_slots=128,physical_planes=129,bank_stride=3293184,driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',
            profile='cumulative-idle',native_archive_sha256='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925',
            maximum_absolute_error_limit=1e-6,reference_accumulation='F64',cases=[dict(columns=k,rows=n,
                input_vectors=v,residue=r,matrix_passed=True,vector_passed=True,non_dyadic_vector_passed=True,
                padding_intact=True,maximum_absolute_error=1e-9,non_BF16_exact_F32_inputs=1)
                for k,n in ((2560,640),(640,2560))for v in (1,10)for r in RESIDUES])

    def save(self):
        baseline.FirstGenerationRecords.save(self)

    def expanded(self):
        raw=json.dumps(self.layout).encode()
        self.binding['cache128']=dict(schema='ps5-qwen-cache128-model-binding-v1',active_slots=128,physical_planes=129,
            cache_request_bytes=CACHE_BYTES,context_allowance_bytes=256<<20,layout_qualification=dict(pid=900,run_id='d'*32,
                SELF_sha256='e'*64,report_bytes=len(raw),report_sha256=hashlib.sha256(raw).hexdigest(),
                report_path='/app0/qwen-runtime/plan-'+('d'*32)+'.json.padded-layout'))
        Path(str(self.result)+'.cache128.layout-qualification').write_bytes(raw)
        self.records['.memory']['planned_resident_headroom_bytes']=MODEL_REQUIREMENT
        self.records['.memory.after-load']=dict(model_loaded=True,expert_cache_requested_bytes=CACHE_BYTES,
            remaining_context_workspace_staging_reserve_bytes=1152<<20,device_budget_source='canary-validated native Direct allocator',
            native_Direct_available_bytes=3401433088,native_Direct_owned_bytes=8772485120,native_Direct_pool_bytes=12280922112)
        for ordinal,suffix in enumerate(('.first','.demo1','.demo2')):
            request=self.records['']if ordinal==0 else self.records[suffix+'.result']
            prompt=request['metrics']['prompt_tokens'];generated=request['metrics']['generated_tokens']
            tokens=[min(4,prompt-n)for n in range(0,prompt,4)]+[1]*(generated-(request['stop_reason']=='output_token_limit'))
            rows=[dict(layer=il,tokens=t,ids=list(range(10))*t)for t in tokens for il in range(48)]
            unique=10*len(rows)
            self.records[suffix+'.expert-routes']=dict(schema='ps5-qwen-completed-expert-routes-v1',complete=True,capture_failed=False,
                pid=1234,run_id='a'*32,ordinal=ordinal,cache_reset_before_request=ordinal<2,layers_per_process=48,experts=512,
                experts_per_token=10,cache_slots=128,maximum_records=4608,all_existing_downloads_and_synchronizations_returned=True,
                additional_GPU_downloads=0,routing_and_cache_policy_unchanged=True,process_calls=len(tokens),records=rows,
                selected_indices=sum(10*t for t in tokens)*48,unique_selected_experts=unique,cache_hits=0,cache_misses=unique,
                uploaded_bytes=unique*9830400,prefetch_advice_bytes=0,sidecar_written_after_model_and_source_retirement=True,
                JSON_created_after_model_and_source_retirement=True)

    def test_bound_layout_actual_request_and_all_three_routes(self):
        self.expanded();self.save();validate(self.result,self.binding)

    def test_scope_cannot_be_inferred_from_native_claims(self):
        self.expanded();self.save();self.binding.pop('cache128')
        with self.assertRaises(ValueError):validate(self.result,self.binding)

    def test_unsupported_or_incomplete_independent_geometry_is_rejected(self):
        self.expanded();original=copy.deepcopy(self.binding['cache128'])
        for key,value in (('active_slots',53),('physical_planes',128),('cache_request_bytes',512<<20),
            ('context_allowance_bytes',1024<<20),('layout_qualification',{}),('active_slots',True)):
            bad=copy.deepcopy(original);bad[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate_binding(bad)
        for key in original:
            bad=copy.deepcopy(original);bad.pop(key)
            with self.subTest(missing=key),self.assertRaises(ValueError):validate_binding(bad)

    def test_proof_hash_and_complete_layout_are_required(self):
        self.expanded();self.save()
        Path(str(self.result)+'.cache128.layout-qualification').write_bytes(b'{}')
        with self.assertRaises(ValueError):validate(self.result,self.binding)
        self.layout['cases'].pop();self.expanded();self.save()
        with self.assertRaises(ValueError):validate(self.result,self.binding)

    def test_postload_and_route_capacity_cannot_fall_back_to_53(self):
        self.expanded();original=copy.deepcopy(self.records)
        for suffix,key,value in (('.memory.after-load','expert_cache_requested_bytes',512<<20),
            ('.memory.after-load','native_Direct_available_bytes',1),
            ('.memory.after-load','remaining_context_workspace_staging_reserve_bytes',1),
            ('.memory.after-load','native_Direct_pool_bytes',1),
            ('.first.expert-routes','cache_slots',53),('.demo1.expert-routes','cache_slots',53),
            ('.demo2.expert-routes','cache_slots',53),('.demo2.expert-routes','cache_reset_before_request',True),
            ('.demo2.expert-routes','sidecar_written_after_model_and_source_retirement',False),
            ('.demo2.expert-routes','ordinal',True)):
            self.records=copy.deepcopy(original);self.records[suffix][key]=value;self.save()
            with self.subTest(suffix=suffix,key=key),self.assertRaises(ValueError):validate(self.result,self.binding)


if __name__=='__main__':unittest.main()
