#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export a positively closed model trace and screen bounded stride coverage."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import PHYSICAL,lan_module

ROW=struct.Struct('<6Q3q24Q2i4I')


def decode(raw,audit,binding):
    need(len(raw)==audit['bytes'] and hashlib.sha256(raw).hexdigest()==audit['sha256'] and raw[:8]==b'QWENIO1\0',
         'Whole exported bytes must match the native generated stream SHA256')
    version,header,row_size,json_size=struct.unpack_from('<4I',raw,8);count=struct.unpack_from('<Q',raw,24)[0]
    need(version==1 and header==16384 and row_size==ROW.size==288 and 0<json_size<=header-128 and
         0<count<=32768 and len(raw)==header+count*row_size and count==audit['records'],
         'Exact bounded native observation stream geometry required')
    need(json.loads(raw[128:128+json_size])==binding,'Exact native run/SELF/model binding required')
    rows=[]
    for index in range(count):
        value=ROW.unpack_from(raw,header+index*row_size)
        ordinal,begin,end,thread,offset,requested,returned,flags_before,flags_after=value[:9]
        before,after=value[9:21],value[21:33];fd,error,valid_before,valid_after,equal,candidate=value[33:]
        need(ordinal==index and 0<begin<=end and requested>0 and candidate in (0,1) and
             equal in (0,1) and valid_before in (0,1) and valid_after in (0,1),
             'All original call ordinals and monotonic intervals must complete')
        need(bool(equal)==bool(valid_before and valid_after and before==after and flags_before==flags_after),
             'Independently recomputed complete descriptor equality differs')
        rows.append(dict(ordinal=ordinal,begin=begin,end=end,thread=thread,offset=offset,bytes=requested,returned=returned,
            flags=flags_before,identity=before,identity_equal=bool(equal),candidate=bool(candidate),descriptor=fd,error=error))
    need(sum(row['candidate'] for row in rows)==audit['candidate_calls'] and
         audit['observed_calls']==audit['forwarded_original_calls']==count and audit['overflow_records']==0,
         'Every original call must be retained without overflow or diagnostic retries')
    return rows


def stride_screen(rows):
    groups=defaultdict(list)
    for row in rows:groups[row['thread']].append(row)
    summaries=[]
    for thread,events in groups.items():
        previous=None;pending=None;submitted=hits=unused=hit_bytes=predicted_bytes=hit_read_wall=0
        for row in sorted(events,key=lambda item:item['begin']):
            valid=(row['candidate'] and row['identity_equal'] and row['returned']==row['bytes'] and
                row['identity'][2]>=64<<20 and row['offset']+row['bytes']<=row['identity'][2])
            key=(tuple(row['identity']),row['flags'],row['bytes'],row['offset'])
            if pending:
                if valid and pending==key:hits+=1;hit_bytes+=row['bytes'];hit_read_wall+=row['end']-row['begin']
                else:unused+=1
                pending=None
            if not valid:previous=None;continue
            if previous and submitted<6 and key[:3]==previous[:3] and row['offset']>previous[3]:
                predicted=row['offset']+(row['offset']-previous[3])
                if predicted+row['bytes']<=row['identity'][2]:
                    pending=(*key[:3],predicted);submitted+=1;predicted_bytes+=row['bytes']
            previous=key
        if pending:unused+=1
        summaries.append(dict(thread=thread,original_calls=len(events),hypothetical_predictions=submitted,
            hypothetical_hits=hits,hypothetical_unused=unused,hypothetical_hit_bytes=hit_bytes,
            hypothetical_predicted_bytes=predicted_bytes,
            sum_matching_overlapped_read_wall_ns_not_application_wait=hit_read_wall))
    return summaries


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','reference-case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=load(a.case/'result.private.json');plan=load(a.case/'case/plan.private.json')
    for key in ('terminal','audit','closure'):need(record(result[key]['path'])==result[key],'Completed observation evidence changed')
    terminal=load(result['terminal']['path']);audit=load(result['audit']['path']);closed=load(result['closure']['path'])
    need(result['completed'] and result['kind']=='I1-model-pread-observation' and terminal['audit']==audit and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['ordinary_OS_closes']==1 and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         audit['completed'] and audit['diagnostic_owners_positively_retired'] and audit['exported_after_all_original_owners_retired'] and
         audit['original_reads_retried']==audit['source_payload_bytes_inspected']==audit['additional_workers']==audit['GPU_calls_added']==0,
         'Positive original and diagnostic retirement, ordinary exit and restoration required before export')
    expected_path=plan['report']+'.pread-trace';need(audit['path']==expected_path and audit['pid']==terminal['pid'] and
         audit['run_id']==plan['run_id'] and audit['candidate_SELF_sha256']==plan['SELF']['sha256'],'Exact completed native trace binding required')
    a.out.mkdir(parents=True,exist_ok=False);lan=lan_module()
    raw=lan.web('/fs'+urllib.parse.quote(PHYSICAL+expected_path[5:],safe='/'),16<<20)
    destination=a.out/'model-pread-trace.private.bin';destination.write_bytes(raw)
    binding={key:terminal[key] for key in ('run_id','pid','candidate_SELF_sha256','model_receipt_sha256')}
    rows=decode(raw,audit,binding)
    pattern=re.compile(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})')
    stages=a.case/'case/native-stages.private.log';reference_stages=a.reference_case/'native-stages.private.log'
    actual=[row[1:] for row in pattern.findall(stages.read_bytes()) if row[0]==b'1']
    expected=[row[1:] for row in pattern.findall(reference_stages.read_bytes()) if row[0]==b'1']
    need(len(actual)==23 and actual==expected,'All23 full248320-column F32 rows must remain byte-exact')
    routes=a.case/'case/headless-observer/native.arm0.routes.private.json';reference_routes=a.reference_case/'native-arm0.routes.private.bin'
    need(load(routes)['records']==load(reference_routes)['records'],'Actual target routes must remain exact')
    summaries=stride_screen(rows)
    report=dict(completed=True,case=record(a.case/'result.private.json'),native_audit=result['audit'],closure=result['closure'],
        raw=record(destination),stages=record(stages),reference_stages=record(reference_stages),
        original_calls=len(rows),large_aligned_candidates=audit['candidate_calls'],original_producers=len(summaries),
        full_requested_bytes=sum(row['bytes'] for row in rows),returned_bytes=sum(max(0,row['returned']) for row in rows),
        short_or_failed_reads=sum(row['returned']!=row['bytes'] for row in rows),
        candidates_with_full_stable_identity=sum(row['candidate'] and row['identity_equal'] for row in rows),
        all23_full_F32_rows_and_actual_routes_exact=True,all_original_calls_preserved_without_retries=True,
        original_CPU_peak_bytes=terminal['CPU_heap_peak_bytes'],original_device_peak_bytes=terminal['device_ledger_peak_bytes'],
        per_original_producer_stride_screen=summaries,maximum_hypothetical_predictions_per_producer=6,
        hypothetical_predictions_were_not_submitted=True,independent_source_admission_and_contention_costs_not_simulated=True,
        overlapping_read_wall_sums_are_not_application_wait_or_speedup=True,model_prefetch_integration_or_speed_qualified=False,
        native_owners=0,production_adopted=False,initializer_requests=0,automatic_retries=0)
    save(a.out/'result.private.json',report)
    print(json.dumps(dict(completed=True,original_calls=len(rows),original_producers=len(summaries),
        hypothetical_hits=sum(row['hypothetical_hits'] for row in summaries),F32_rows_exact=23,production_adopted=False)))


if __name__=='__main__':main()
