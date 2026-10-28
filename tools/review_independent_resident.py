#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review independently retired prediction, prefix and delivery cohorts."""
import argparse
import json
import os
from pathlib import Path
from resident_route_review import require_same_tokens
from review_resident_results import arms, capture, closed_case, load, metric, paired, review_refill


def review(cache, number, kind):
    if kind == 'refill':
        result = review_refill(cache, number)
        case = cache / f'hardware-first-generation-{number}'
    else:
        count = 10 if kind == 'predictive' else 9
        case, report = closed_case(cache, number, count)
        rows = report['requests']
        if any(row['full_F32_logit_rows_compared'] != 23 for row in rows[1:]):
            raise ValueError('All original full-vocabulary F32 rows must match')
        original = load(case / 'native-arm0.routes.private.json')
        route_checks = [require_same_tokens(original,
            load(case / f'native-arm{i}.routes.private.json'),
            30 if kind == 'prefix' and i in (4, 6) else 0)
            for i in range(9)]
        result = dict(case=number, native_requests=count, original_route_checks=route_checks,
            maximum_absolute_F32_error=max(row['maximum_absolute_logit_error'] for row in rows[1:]),
            full_F32_rows_compared=23 * (count - 1), native_evidence=capture(case / 'native-model-terminal.private.json'))
        if kind == 'predictive':
            rejection = rows[9]
            stats = rejection['speculation']
            if not (report['forced_rejection_and_full_F32_restore_passed'] and
                    stats['attempts'] == stats['rejected'] == 1 and stats['accepted'] == 0):
                raise ValueError('Forced-rejection restoration did not positively finish')
            result.update(prediction=arms(rows, (1, 4), (2, 3)),
                speculation=arms(rows, (5, 8), (6, 7)),
                prediction_counters=[rows[i]['predictive'] for i in (2, 3)],
                speculation_counters=[rows[i]['speculation'] for i in (6, 7)],
                forced_rejection=stats)
        else:
            if report['kind'] != 'prefix' or not report['full_F32_continuation_and_routes_passed']:
                raise ValueError('Independent native prefix result required')
            result.update(prefix_pair_total=paired(
                [sum(metric(rows[i], 'total_ms') for i in pair) for pair in ((1, 2), (7, 8))],
                [sum(metric(rows[i], 'total_ms') for i in pair) for pair in ((3, 4), (5, 6))], False),
                prefix_second=arms(rows, (2, 8), (4, 6)),
                prefix_counters=[row['prefix'] for row in rows])
    retirement = load(case / 'native.resident.upload-retirement.private.json')
    if not (retirement['completed'] and retirement['producer_epoch_completed'] and
            retirement['original_upload_fences_and_command_cleanup_returned'] and
            retirement['exclusive_staging_destructor_completed'] and
            0 < retirement['released_requested_bytes'] <= 64 << 20 and
            retirement['owned_before'] - retirement['owned_after'] >= retirement['released_requested_bytes'] and
            retirement['GPU_or_ordinary_floor_changes'] == 0):
        raise ValueError('Complete original allocator and upload retirement required')
    result.update(schema='ps5-qwen-independent-resident-review-v1', kind=kind,
        only_closed_completed_native_evidence_used=True, upload_retirement=retirement,
        original_BF16_and_all_experts_retained=True, original_GPU_floor_unchanged=True,
        console_calls=0, production_adopted=False)
    package=load(case/'candidate-package.private.json')
    native=load(package['native_link_receipt']['path'])
    result['native_build_receipt']=capture(package['native_link_receipt']['path'])
    reserve_path=case/'native.resident.OS-reserve.private.json'
    if native.get('post_context_OS_reserve') and not reserve_path.exists():
        raise ValueError('The actual compiled phase-pricing sidecar must be preserved')
    if reserve_path.exists():
        selected=load(reserve_path)
        postload=selected.get('activated_after_model_and_upload_retirement',False)
        if not((selected['activated_after_original_context'] or postload) and selected['original_setup_GPU_floor']==1154 and
               selected['context_allowance_pages']==43 and selected['selected_kernel_minimum_pages']==898 and
               selected['selected_operational_floor_pages'] in (962,1104) and
               selected['free_pages_at_activation']>=selected['selected_operational_floor_pages'] and
               selected['original_wait_and_retirement_guards'] and not selected['universal_peak_bound_established']):
            raise ValueError('Explicit post-context reserve qualification differs')
        if postload and (selected.get('selected_context_entry_pages')!=1005 or selected['free_pages_at_activation']<1005):
            raise ValueError('The separately measured next-context price differs')
        result.update(original_GPU_floor_unchanged=False,original_GPU_setup_floor_unchanged=not postload,
            original_GPU_initialization_and_model_load_floors_unchanged=True,context_price_revised=postload,
            post_context_reserve_policy_changed=True,post_context_reserve=selected)
    tables_path=case/'native.resident.tables-attempt.private.json'
    if tables_path.exists():
        tables=load(tables_path)
        if not(tables['attempted'] and tables['completed'] and not tables['memory_refused'] and not tables['scratch_fault'] and
               tables['scratch_live_bytes']==0 and tables['tables_completed']==673 and tables['bytes_completed']==9471408 and
               tables['protection_attempted'] and tables['protection_return_code']==0 and
               tables['Direct_allocated'] and tables['Direct_mapped'] and tables['Direct_zeroed'] and
               tables['CPU_metadata_scope_active'] and tables['CPU_selected_base_extra_pages']==21 and tables['GPU_calls']==0):
            raise ValueError('Exact original table restoration, CPU scope and readonly protection must complete')
        result['CPU_table_restoration']=tables
    combination=native.get('prefix_cache128_combination')
    if combination:
        report=load(case/'native-model-terminal.private.json');scope=combination['scope']
        if kind!='prefix' or report['active_cache_slots']!=128 or scope['active_cache_slots']!=128:
            raise ValueError('The independently bound 128-slot prefix combination differs')
        for row in report['requests']:
            stats=row['six_demand'];enabled=scope['six_demand_enabled']
            if not(stats['enabled']==enabled and (stats['batches']>0)==enabled and
                   stats['reads']==6*stats['batches'] and stats['logical_bytes']==3276800*stats['reads']):
                raise ValueError('Actual prefix/delivery batch, read and byte conservation differs')
        result.update(active_cache_slots=128,prefix_delivery_combination=scope,
            six_demand=[row['six_demand']for row in report['requests']])
        if native.get('checkpoint_capacity_reuse'):
            capacities=[row['checkpoint_capacity']for row in report['requests']]
            payload=capacities[3]['requested_payload_bytes']
            rounded=(payload+(2<<20)-1)&~((2<<20)-1)
            if not(type(payload)is int and 118038528<=payload<=142606336 and
                   capacities[3]['new_allocation_bytes']==rounded and capacities[5]['new_allocation_bytes']==0 and
                   payload==capacities[5]['requested_payload_bytes'] and
                   all(row['same_context_qualified']and row['original_device_Direct_and_Flexible_caps_unchanged']for row in capacities)):
                raise ValueError('Only actual completed same-context storage may be credited')
            result['checkpoint_capacity_reuse']=dict(first_completed_capture=capacities[3],
                second_completed_capture=capacities[5],same_original_context=True,
                restored_request_rows_retain_latest_capture_admission_not_new_transfer=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--case', type=int, required=True)
    p.add_argument('--kind', choices=('predictive', 'prefix', 'refill'), required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = review(a.cache, a.case, a.kind)
    temporary=a.out.with_name(a.out.name+'.writing')
    if a.out.exists():raise FileExistsError(a.out)
    with temporary.open('x', encoding='utf-8', newline='\n') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
        file.flush();os.fsync(file.fileno())
    if a.out.exists():raise FileExistsError(a.out)
    temporary.rename(a.out)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
