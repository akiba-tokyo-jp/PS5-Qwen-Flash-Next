#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify returned real-layout CPU evidence without native operations."""
import re,statistics
def fields(line):return {k:int(v)for k,v in re.findall(r'(\w+)=(-?\d+)(?: |$)',line)}
def validate(raw,manifest):
    lines=raw.splitlines();nonce=manifest['nonce'];stride=3293184
    ends=[s for s in lines if s.startswith('END ')]
    if len(ends)!=1 or f'nonce={nonce} 'not in ends[0]or fields(ends[0])!=dict(success=1,all_workers_joined=1,Direct_released=1,pending_reads=0,GPU_calls=0,title_launches=0,no_retry=1):
        raise ValueError('Native layout completion is not positively returned')
    for marker in ('PACK_complete_SHA256_identity_EOF=1','ORIGINAL_selected_18_envelopes_SHA256_sealed_identity_EOF=1','DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0'):
        if lines.count(marker)!=1:raise ValueError('Missing exactness or retirement marker')
    eof=[fields(s)for s in lines if s.startswith('EOF_RETURNED ')]
    if len(eof)!=19 or any(s.get('bytes')!=0 for s in eof):raise ValueError('Incomplete sealed-source EOF checks')
    if len([s for s in lines if s.startswith('context ')and'exact=1'in s and'canaries=1'in s])!=3:raise ValueError('Missing original CPU context guards')
    rows=[s for s in lines if s.startswith(('BATCH_BEGIN ','LAYOUT_PLAN ','LAYOUT_RETURNED ','BATCH_DRAINED ','BATCH_EXACT '))]
    if len(rows)!=48*5:raise ValueError('Incomplete layout cohort')
    expected={(r,g,m)for r in range(8)for g in range(3)for m in range(2)};seen=set();ids=set();batches=[];physical=0
    for n in range(48):
        begin,plan,returned,drained,exact=rows[n*5:n*5+5];b=fields(begin);d=fields(drained);e=fields(exact)
        if not begin.startswith('BATCH_BEGIN ')or not drained.startswith('BATCH_DRAINED ')or not exact.startswith('BATCH_EXACT '):raise ValueError('Unordered positive batch')
        key=tuple(b.get(k)for k in ('round','group','mode'))
        if key not in expected or key in seen or any(d.get(k)!=b[k]or e.get(k)!=b[k]for k in b):raise ValueError('Wrong or repeated layout case')
        seen.add(key);mode=b['mode'];count=2 if mode else 6;size=(3 if mode else 1)*stride
        if d.get('copies')!=0 or d.get('physical_bytes')!=6*stride or not 0<d.get('source_ns',0)<=d.get('wall_ns',0):raise ValueError('Invalid delivered-byte or time accounting')
        if any(e.get(k)!=v for k,v in dict(original_SHA256=6,envelope_SHA256=6,tail_canary=1).items()):raise ValueError('Unverified original payload')
        p=re.fullmatch(r'LAYOUT_PLAN mode=(\d+) events=([0-9:,]+)',plan)
        r=re.fullmatch(r'LAYOUT_RETURNED count=(\d+) uncertain=0 events=([0-9:,]+)',returned)
        if p is None or r is None or int(p[1])!=mode or int(r[1])!=count:raise ValueError('Incomplete durable layout events')
        declared=[[int(v)for v in s.split(':')]for s in p[2].split(',')];events=[[int(v)for v in s.split(':')]for s in r[2].split(',')]
        if len(events)!=count or declared!=[v[:3]for v in events]or any(len(v)!=8 for v in events):raise ValueError('Durable plan and return differ')
        for i,event in enumerate(events):
            ident,offset,bytes_,begun,done,got,a,z=event
            sample=manifest['groups'][b['group']][i];expected_offset=sample['offset']if mode else sample['source_offset']
            if ident in ids or not 0<ident<=192 or offset!=expected_offset or bytes_!=size or got!=size or begun!=1 or done!=1 or not 0<a<=z or z-a>d['source_ns']:
                raise ValueError('Unowned I/O, wrong range, short read or invalid timing')
            ids.add(ident);physical+=size
        batches.append(d)
    if seen!=expected or ids!=set(range(1,193))or physical!=48*6*stride:raise ValueError('Layout ID/byte conservation failed')
    ratios={}
    for metric in ('wall_ns','source_ns'):
        paired=[]
        for round_ in range(8):
            sums=[sum(b[metric]for b in batches if b['round']==round_ and b['mode']==mode)for mode in (0,1)]
            paired.append(sums[0]/sums[1])
        ratios[metric]=dict(paired_round_ratios=paired,paired_median_ratio=statistics.median(paired),all_rounds_faster=min(paired)>1)
    return dict(completed=True,fixture_gate_passed=all(x['paired_median_ratio']>1 and x['all_rounds_faster']for x in ratios.values()),
        timings=ratios,batches=batches,exact_original_matrix_deliveries=288,actual_original_source_files=True,
        source_integrity_scope=manifest['source_integrity_scope'],physical_bytes=physical,compact_IO_events=192,
        original_descriptor_open_cost_outside_both_arms=True,source_descriptors_at_most=7,workers_joined=True,Direct_released=True,
        production_changed=False,full_model_speed_not_measured=True,GPU_calls=0,title_launches=0,unknown_completion=False)
