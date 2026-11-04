#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify actual native immutable-span prefetch delivery and positive retirement."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','run','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();built=load(a.build);run=load(a.run/'result.private.json')
    terminal=load(run['terminal']['path']);audit=load(run['audit']['path']);closed=load(run['closure']['path'])
    for row in (run['terminal'],run['audit'],run['closure'],built['entry'],built['provider'],*built['inputs']):
        need(record(row['path'])==row,'A native span input or completed output changed')
    need(run['completed'] and run['kind']=='I1-span-fixture' and run['native_requests']==0 and not run['unknown_completion'] and
         closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         terminal['completed'] and terminal['model_loads']==terminal['GPU_calls']==terminal['device_ledger_live_bytes']==0 and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['audit']==audit,'Exact positive CPU fixture retirement required')
    need(audit['completed'] and audit['all_bytes_and_canaries_passed'] and audit['source_descriptor_worker_and_scratch_retired'] and
         audit['source_device_equals_same_launch_title_directory'] and audit['fresh_full_descriptor_identity_preserved'] and
         audit['source_lease_opens']==audit['source_lease_closes']==24 and audit['last_lease_open_errno']==0,
         'Actual separately owned source leases and stable full identity required')
    cases=audit['cases'];need(len(cases)==8,'All four paired byte geometries required')
    total_hits=0;total_hit_bytes=0;logical_bytes=0
    for index,size in enumerate((540672,557056,475136,491520)):
        for enabled,row in enumerate(cases[index*2:index*2+2]):
            stats=row['source_calls']
            need(row['span_bytes']==size and row['prefetch_enabled']==bool(enabled) and row['passed'] and
                 row['read_calls_returned'] and row['all_bytes_equal_independent_Direct_reads'] and row['canaries_equal'] and
                 row['independent_reference_reads']==8 and row['independent_reference_bytes']==8*size and
                 stats['foreground_calls']==(2 if enabled else 8) and stats['foreground_bytes']==(2 if enabled else 8)*size and
                 stats['prefetch_calls']==stats['hits']==(6 if enabled else 0) and
                 stats['prefetch_bytes']==stats['hit_bytes']==(6 if enabled else 0)*size and
                 all(stats[k]==0 for k in ('unused','declined','invalid','admission_declines','descriptor_declines')),
                 'Each actual speculative read must serve the exact expected foreground bytes without waste or refusal')
            total_hits+=stats['hits'];total_hit_bytes+=stats['hit_bytes'];logical_bytes+=8*size
    journal=(a.run/'closed/completed-native-stages.private.log').read_bytes().splitlines()
    need(journal.count(b'immutable_span_prefetch_before_worker_submit')==24 and
         journal.count(b'I1_fixture_before_foreground_span_read')==journal.count(b'I1_fixture_foreground_span_read_returned')==64 and
         journal.count(b'I1_fixture_before_independent_Direct_reference_read')==journal.count(b'I1_fixture_independent_Direct_reference_read_returned')==64 and
         journal.count(b'I1_fixture_request_worker_drain_completed')==8 and
         journal.count(b'I1_fixture_worker_join_and_scratch_lease_completed')==1,'Exact positive finite I/O and worker journal required')
    a.out.mkdir(parents=True,exist_ok=False)
    result=dict(completed=True,native_byte_delivery_and_prefetch_qualified=True,geometry_bytes=[540672,557056,475136,491520],
        logical_reads=64,independent_reference_reads=64,logical_bytes_equal=logical_bytes,prefetch_calls=total_hits,
        useful_prefetch_bytes=total_hit_bytes,source_lease_opens=24,source_lease_closes=24,all_canaries_equal=True,
        all_source_worker_and_scratch_owners_retired=True,closure=run['closure'],build=record(a.build),run=record(a.run/'result.private.json'),
        actual_model_demand_trace_qualified=False,model_integration_qualified=False,native_model_speed_qualified=False,
        production_adopted=False,PS5_operations=0)
    save(a.out/'result.private.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('closure','build','run')}))


if __name__=='__main__':main()
