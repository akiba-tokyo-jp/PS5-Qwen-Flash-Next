#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify a completed bounded bank fixture; this never closes or launches a title."""
import math,re,statistics

def validate_compact_stages(result,stages):
    """Bind each durable batch plan/return to the completed in-memory events."""
    if result.get('schema')!='ps5-qwen-vector-bank-result-compact-v2':raise ValueError('Compact evidence required')
    if 'vector_bank_IO_before id='in stages or 'vector_bank_IO_returned id='in stages:raise ValueError('Mixed recording modes')
    rows=[s for s in stages.splitlines()if s.startswith(('vector_bank_IO_batch_plan ','vector_bank_IO_batch_returned ','vector_bank_batch_exact_GPU_fences_completed'))]
    if len(rows)!=3*68:raise ValueError('Incomplete durable batch history')
    for n,batch in enumerate(result['batches']):
        plan,returned,fenced=rows[n*3:n*3+3]
        p=re.fullmatch(r'vector_bank_IO_batch_plan group=(\d+) mode=(\d+) events=([0-9:,]+)',plan)
        r=re.fullmatch(r'vector_bank_IO_batch_returned count=(\d+) uncertain=0 events=([0-9:,]+)',returned)
        if p is None or r is None or fenced!='vector_bank_batch_exact_GPU_fences_completed':raise ValueError('Unordered or uncertain durable batch')
        declared=[[int(v)for v in item.split(':')]for item in p[3].split(',')]
        events=[[int(v)for v in item.split(':')]for item in r[2].split(',')]
        expected=[[int(v)for v in event]for event in batch['io_events']]
        if(int(p[1]),int(p[2]))!=(batch['group'],batch['mode'])or int(r[1])!=len(expected)or events!=expected or declared!=[e[:3]for e in expected]:
            raise ValueError('Durable events disagree with completed batch')
    return dict(durable_batch_plans=68,durable_batch_returns=68,durable_IO_events=272,all_durable_plans_and_returns_match=True)

def validate(result,pid):
    if not isinstance(result,dict)or result.get('schema')not in ('ps5-qwen-vector-bank-result-v1','ps5-qwen-vector-bank-result-compact-v2')or result.get('pid')!=pid:
        raise ValueError('Exact owned vector-bank result required')
    compact=result['schema']=='ps5-qwen-vector-bank-result-compact-v2'
    for key in ('F64_reference_passed','F32_inputs_non_BF16_exact','same_F32_outputs_bit_exact',
                'all_30_residues_passed','canaries_intact','all_IO_returned_and_closed','all_workers_joined',
                'all_three_strong_bank_leases_returned','positive_device_idle_and_epoch_retirement',
                'all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned'):
        if result.get(key)is not True:raise ValueError('Unpassed completion or exactness: '+key)
    for key,expected in dict(original_matrix_deliveries=408,GPU_graphs=204,scalar_read_calls=204,vector_read_calls=68,
                             device_ledger_live_bytes=0,copy_bytes=0,shader_CPU_verified_assets=1527).items():
        if type(result.get(key))is not int or result[key]!=expected:raise ValueError('Wrong finite counter: '+key)
    if result.get('model_loaded')is not False or result.get('real_bank_slots')!=[0,52]or result.get('selected_IDs')!=[52,0,26,0,50,2,52,13,25,42]:
        raise ValueError('Wrong bank geometry or model state')
    if type(result.get('non_BF16_exact_input_values'))is not int or result['non_BF16_exact_input_values']<=0:
        raise ValueError('Missing original F32 input coverage')
    if type(result.get('shader_module_inputs_after_CPU_verification'))is not int or result['shader_module_inputs_after_CPU_verification']<=0:
        raise ValueError('Missing checked GPU shader inputs')
    error=result.get('maximum_absolute_error');peak=result.get('device_ledger_peak_bytes')
    if type(error)not in (float,int)or not math.isfinite(error)or error<0 or type(peak)is not int or not 0<peak<=1792<<20:
        raise ValueError('Invalid numerical or live-allocation observation')
    batches=result.get('batches')
    if not isinstance(batches,list)or len(batches)!=68:raise ValueError('Incomplete cohort')
    expected={(r,g,m,True)for r in range(8)for g in range(3)for m in range(2)}|{(0,g,m,False)for g in range(3,13)for m in range(2)}
    actual=set();event_ids=set();event_bytes=0
    for row in batches:
        keys={'round','group','mode','timed','delivery_wall_ns','physical_bytes','copies'}
        if compact:keys|={'source_critical_ns','source_begin_ns','source_end_ns','batch_safety_records','io_events'}
        if not isinstance(row,dict)or set(row)!=keys:
            raise ValueError('Invalid batch fields')
        if type(row['timed'])is not bool or any(type(row[k])is not int for k in ('round','group','mode','delivery_wall_ns','physical_bytes','copies')):
            raise ValueError('Invalid batch types')
        key=(row['round'],row['group'],row['mode'],row['timed'])
        if key in actual or row['delivery_wall_ns']<=0 or row['physical_bytes']!=6*3293184 or row['copies']!=0:
            raise ValueError('Invalid or duplicate delivery')
        actual.add(key)
        if compact:
            for field in ('source_critical_ns','source_begin_ns','source_end_ns','batch_safety_records'):
                if type(row[field])is not int:raise ValueError('Invalid compact timing type')
            if not 0<row['source_critical_ns']<=row['delivery_wall_ns'] or row['batch_safety_records']!=2 or not 0<row['source_begin_ns']<row['source_end_ns'] or row['source_end_ns']-row['source_begin_ns']!=row['source_critical_ns']:
                raise ValueError('Invalid compact source interval or safety records')
            events=row['io_events'];count=2 if row['mode']else 6
            if not isinstance(events,list)or len(events)!=count:raise ValueError('Incomplete compact I/O events')
            for event in events:
                if not isinstance(event,list)or len(event)!=8:raise ValueError('Invalid compact I/O event shape')
                ident,offset,size,begun,returned,got,begin,end=event
                if any(type(event[i])is not int for i in (0,1,2,5,6,7))or begun is not True or returned is not True:
                    raise ValueError('Incomplete compact I/O return')
                expected_size=(3 if row['mode']else 1)*3293184
                if ident in event_ids or not 0<ident<=272 or size!=expected_size or got!=size or offset<4194304 or offset%16384 or offset+size>128<<20:
                    raise ValueError('Invalid compact I/O identity, bounds or byte count')
                if not row['source_begin_ns']<=begin<=end<=row['source_end_ns']:raise ValueError('I/O interval escapes source interval')
                event_ids.add(ident);event_bytes+=size
    if actual!=expected:raise ValueError('Missing paired deliveries')
    if compact and(event_ids!=set(range(1,273))or event_bytes!=68*6*3293184):raise ValueError('Compact I/O conservation failed')
    ratios=[]
    for r in range(8):
        sums=[sum(x['delivery_wall_ns']for x in batches if x['timed']and x['round']==r and x['mode']==mode)for mode in (0,1)]
        ratios.append(sums[0]/sums[1])
    review=dict(completed=True,paired_round_ratios=ratios,paired_median_ratio=statistics.median(ratios),
        all_rounds_faster=min(ratios)>1,fixture_gate_passed=statistics.median(ratios)>1 and min(ratios)>1,
        GPU_graphs=204,original_matrix_deliveries=408,all_reads_fences_and_workers_completed=True,
        no_model_inference=True,production_adopted=False)
    if compact:
        source_ratios=[]
        for r in range(8):
            sums=[sum(x['source_critical_ns']for x in batches if x['timed']and x['round']==r and x['mode']==mode)for mode in (0,1)]
            source_ratios.append(sums[0]/sums[1])
        review.update(source_paired_round_ratios=source_ratios,source_paired_median_ratio=statistics.median(source_ratios),
            all_source_rounds_faster=min(source_ratios)>1,compact_IO_events=272,compact_durable_batch_records=136)
        review['fixture_gate_passed']=review['fixture_gate_passed']and statistics.median(source_ratios)>1 and min(source_ratios)>1
    return review
