#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price cache candidates against completed native allocator observations only."""
import argparse
import hashlib
import json
from pathlib import Path

MIB=1<<20
STRIDE=3293184
BASE_SLOTS=53


def rounded_banks(slots):
    if type(slots)is not int or not 53<=slots<=1024:
        raise ValueError('The completed bounded capacity screen is required')
    return 3*((STRIDE*(slots+1)+2*MIB-1)//(2*MIB))*(2*MIB)


def price(sweep,before,after,system,result):
    if (result.get('driver_revision')!='872cc1264ad8ba5d6b888b092968fa5858a38c58'or
        result.get('profile')!='cumulative-idle'or
        result.get('native_archive_sha256')!='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925'or
        result.get('candidate_SELF_sha256')!='ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d'):
        raise ValueError('The exact completed original-precision production control is required')
    if (sweep.get('baseline_53_native_counters_exact')is not True or
        sweep.get('actual_ExpertPolicy_matches_Python_at_all_capacities')is not True or
        sweep.get('native_speed_qualified')is not False or sweep.get('PS5_operations')!=0):
        raise ValueError('An independently matched metadata screen is required')
    if (result.get('full_model_inference_executed')is not True or
        result.get('GPU_completion_and_retirement_passed')is not True or
        result.get('model_resources_released_after_completion')is not True or
        result.get('untracked_libc_heap_fallbacks')!=0 or
        result.get('postload_device_live_bytes')!=0 or
        before.get('pid')!=result.get('pid') or system.get('pid')!=result.get('pid') or
        after.get('model_loaded')is not True or system.get('model_loaded')is not True or
        system.get('CPU_heap_uses_Direct_pool')is not True or
        system.get('CPU_heap_libc_fallbacks')!=0):
        raise ValueError('The completed matching native control is required')
    def positive(value):
        if type(value)is not int or value<=0:raise ValueError('Positive byte counters required')
        return value
    cpu_cap=positive(before['CPU_budget_bytes'])
    cpu_already=positive(system['CPU_heap_mapped_bytes'])
    cpu_peak=positive(result['CPU_heap_peak_bytes'])
    if not cpu_already<=cpu_peak<=cpu_cap:raise ValueError('Tracked CPU scope differs')
    peak=positive(result['postload_device_peak_bytes'])
    base_banks=rounded_banks(BASE_SLOTS)
    if peak<base_banks:raise ValueError('Persistent baseline banks exceed the device peak')
    available=positive(after['native_Direct_available_bytes'])
    pool=positive(after['native_Direct_pool_bytes'])
    owned=positive(after['native_Direct_owned_bytes'])
    if available+owned>pool:raise ValueError('Allocator domains cannot be added or duplicated')
    if before['Flexible_available_bytes']<before['Flexible_reserve_bytes']:
        raise ValueError('The historical control failed its Flexible reserve')
    # These independent allowances remain explicit. The CPU source window is
    # inside the CPU cap; the ledger peak already includes workspace/context.
    allowances=dict(CPU_growth_to_existing_cap=cpu_cap-cpu_already,
        transfer_staging=128*MIB,Direct_reserve=512*MIB,
        platform_margin=positive(before['additional_Direct_platform_margin_bytes']),
        display_allowance=32*MIB)
    other=sum(allowances.values())
    rows=[]
    for candidate in sweep['policies']:
        slots=candidate['slots'];bank=rounded_banks(slots)
        priced_peak=peak-base_banks+bank
        required=priced_peak+other
        rows.append(dict(slots=slots,rounded_bank_bytes=bank,
            historical_device_peak_with_bank_delta_bytes=priced_peak,
            required_after_load_with_existing_CPU_cap_bytes=required,
            historical_after_load_slack_bytes=available-required,
            fits_historical_after_load_envelope=required<=available,
            banks_plus_already_owned_exceed_historical_pool=bank+owned>pool,
            fits_last_reported_buffer_batch_limit=bank//3<=before['device_buffer_batch_limit_bytes'],
            external_upload_reduction_fraction=candidate['external_byte_reduction_fraction'],
            one_token_upload_reduction_fraction=candidate['external_one_token_uploaded_bytes_reduction_fraction']))
    return dict(schema='ps5-qwen-historical-cache-envelope-v1',
        SELF_sha256=result['candidate_SELF_sha256'],pid=result['pid'],
        driver_revision=result['driver_revision'],profile=result['profile'],
        native_archive_sha256=result['native_archive_sha256'],
        historical_pool_bytes=pool,historical_after_load_available_bytes=available,
        baseline_rounded_bank_bytes=base_banks,baseline_device_peak_bytes=peak,
        CPU_already_in_available_query_bytes=cpu_already,
        separately_preserved_allowances=allowances,candidates=rows,
        workspace_and_context_not_charged_twice=True,CPU_source_window_not_charged_twice=True,
        historical_envelope_assumes_unchanged_other_lifetimes=True,
        changed_geometry_native_allocation_qualified=False,
        current_physical_admission_granted=False,PS5_operations=0,CI_runs=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_text())
    keys={'sweep','before','after','system','result'}
    if set(manifest)!={'schema',*keys}or manifest['schema']!='ps5-qwen-cache-envelope-inputs-v1':
        raise ValueError('An exact bound native-evidence manifest is required')
    values={};inputs=[]
    for key in sorted(keys):
        row=manifest[key];raw=Path(row['path']).read_bytes()
        if len(raw)!=row['bytes']or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Native capacity evidence changed')
        values[key]=json.loads(raw);inputs.append(row)
    report=price(**values);report['inputs']=inputs
    with args.out.open('x',encoding='utf-8',newline='\n')as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({k:report[k]for k in('schema','current_physical_admission_granted','PS5_operations')}))


if __name__=='__main__':main()
