#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate complete isolated padded-bank evidence; never access the console."""
import math

RESIDUES=(32,160,256,640,832,1120,1152,1184,1632,1696,1728,1760,1792,1824,
          2080,2208,2240,2304,2336,2784,3232,6688,6720,8320,11360,11424,12768,12832,12864,12928)
SOURCE_SHA='16fffd6b293d7d218adff19ba8a4f2d5176341b43b15fda3c9d63aa3f0677b1a'

def validate_layout(r,stages,pid,run_id):
    assert r['schema']=='ps5-qwen-padded-bank-layout-result-v1' and r['pid']==pid and r['run_id']==run_id
    assert r['source_SHA256']==SOURCE_SHA and r['eligible'] is True
    assert r['all_started_IO_closed'] is True and r['Direct_reads']==1 and r['GPU_graphs']==360
    assert r['model_loaded'] is False and r['VideoOut_started'] is False and r['automatic_retries']==0
    assert r['positive_resource_retirement'] is True and r['source_workers_stopped'] is True
    assert r['device_ledger_live_bytes']==0 and r['device_ledger_allocations']>=4
    assert 0<r['device_ledger_peak_bytes']<=(1792<<20)
    alignment=r['descriptor_alignment']
    assert isinstance(alignment,int) and 0<alignment<=16384 and alignment&(alignment-1)==0
    assert all(offset%alignment==0 for offset in RESIDUES) and r['memory_flags']&7==7
    assert r['active_slots']==53 and r['physical_planes']==54 and r['bank_stride']==3293184
    assert r['maximum_absolute_error_limit']==1e-6 and r['reference_accumulation']=='F64'
    expected={(k,n,v,offset)for k,n in ((2560,640),(640,2560))for v in (1,10)for offset in RESIDUES}
    actual=set()
    assert len(r['cases'])==120
    for row in r['cases']:
        key=tuple(row[name]for name in ('columns','rows','input_vectors','residue'))
        assert key not in actual;actual.add(key)
        assert all(row[name] is True for name in ('matrix_passed','vector_passed','non_dyadic_vector_passed','padding_intact'))
        error=row['maximum_absolute_error']
        assert math.isfinite(error) and 0<=error<=1e-6 and row['non_BF16_exact_F32_inputs']>0
    assert actual==expected
    lines=stages.splitlines()
    assert 'native_exception_admission_failed' not in stages
    assert stages.endswith('padded_layout_completed_model_not_loaded_waiting_for_ordinary_close\n')
    for marker in ('complete_SELF_and_receipt_direct_SHA256_passed GPU_not_started=1',
                   'padded_layout_empty_device_ledger_admitted_before_allocation',
                   'native_driver_producer_completed_resources_owned'):
        assert marker in lines
    assert not any(marker in stages for marker in ('model_load_started_after_memory_admission',
        'inference_before_decode_call','model_resident_native_first_frame_completed'))
    for before,after,count in (
        ('padded_layout_open_before_native_call','padded_layout_open_native_call_returned',1),
        ('padded_layout_read_before_native_call','padded_layout_read_native_call_returned',1),
        ('padded_layout_close_before_native_call','padded_layout_close_native_call_returned',1),
        ('padded_layout_before_synchronous_owned_lease','padded_layout_synchronous_owned_lease_returned',4),
        ('padded_layout_before_finite_graph','padded_layout_numerics_and_positive_completion_passed',360)):
        assert lines.count(before)==lines.count(after)==count
    assert lines.count('padded_layout_shape_resources_positively_retired')==4
    assert lines.count('native_driver_before_positive_device_idle')==lines.count('native_driver_device_idle_completed')>=360
    return dict(eligible=True,all_started_calls_returned=True,positive_GPU_and_source_retirement=True,
                model_inference=False,full_model_speed_qualified=False)
