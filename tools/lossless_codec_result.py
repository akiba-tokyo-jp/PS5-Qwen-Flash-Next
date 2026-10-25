#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate complete native CPU delivery evidence; never infer whole-model speed."""
import json,re,statistics
def parse(raw,manifest):
    text=raw.decode('ascii');lines=text.splitlines()
    begin=[x for x in lines if x.startswith('BEGIN ')];end=[x for x in lines if x.startswith('END ')]
    if len(begin)!=1 or len(end)!=1:raise ValueError('Exactly one positive native terminal is required')
    for line in (begin[0],end[0]):
        if 'nonce='+manifest['nonce']not in line or 'GPU_calls=0'not in line or 'title_launches=0'not in line:
            raise ValueError('Wrong owner scope or GPU/title work')
    if not all(x in end[0]for x in ('success=1 ','pending_reads=0 ','Direct_released=1 ','automatic_retry=0')):
        raise ValueError('Native completion and positive backing release are required')
    if any(x.startswith('RETAIN ')for x in lines):raise ValueError('Uncertain backing is not a benchmark result')
    if sum(x.startswith('READ_BEFORE ')for x in lines)!=sum(x.startswith('READ_RETURNED ')for x in lines):
        raise ValueError('Not every Direct read returned')
    if lines.count('PACK_complete_SHA256_identity_EOF=1')!=1 or lines.count('ALL_65536_BF16_patterns_exact=1')!=1:
        raise ValueError('Complete source integrity and bit-preservation evidence are required')
    for before,after in (('DIRECT_ALLOC_BEFORE bytes=8388608','DIRECT_ALLOC_RETURNED rc=0'),
        ('DIRECT_MAP_BEFORE bytes=8388608','DIRECT_MAP_RETURNED rc=0'),
        ('DIRECT_UNMAP_BEFORE','DIRECT_UNMAP_RETURNED rc=0'),('DIRECT_RELEASE_BEFORE','DIRECT_RELEASE_RETURNED rc=0'),
        ('EOF_BEFORE','EOF_RETURNED bytes=0')):
        if lines.count(before)!=1 or lines.count(after)!=1 or lines.index(before)>=lines.index(after):
            raise ValueError('Native resource lifecycle evidence differs')
    rows=[];keys=set()
    for line in lines:
        if not line.startswith('SAMPLE '):continue
        row={k:int(v)for k,v in re.findall(r'(\w+)=(\d+)',line)}
        key=(row['round'],row['mode'],row['index'])
        if key in keys or not 0<=key[0]<manifest['rounds'] or not 0<=key[1]<len(manifest['variants']) or not 0<=key[2]<manifest['samples']:
            raise ValueError('Native sample identity is duplicated or outside scope')
        keys.add(key)
        expected=manifest['extents'][row['index']][row['mode']]['requested']
        if (row['exact_SHA256']!=1 or row['physical_bytes']!=expected or row['read_ns']<=0 or
            row['restore_ns']<0 or row['delivery_ns']!=row['read_ns']+row['restore_ns'] or
            row['delivery_ns']<=0 or (row['mode']==0 and row['restore_ns']!=0)):
            raise ValueError('Native sample byte or timing arithmetic differs')
        rows.append(row)
    if len(rows)!=manifest['rounds']*manifest['samples']*len(manifest['variants']):raise ValueError('Native cohort is incomplete')
    summaries=[]
    for mode,name in enumerate(manifest['variants']):
        selected=[r for r in rows if r['mode']==mode];ratios=[]
        for round_index in range(manifest['rounds']):
            baseline=sum(r['delivery_ns']for r in rows if r['mode']==0 and r['round']==round_index)
            candidate=sum(r['delivery_ns']for r in selected if r['round']==round_index)
            ratios.append(baseline/candidate)
        summaries.append(dict(variant=name,median_read_ms=statistics.median(r['read_ns']for r in selected)/1e6,
            median_restore_ms=statistics.median(r['restore_ns']for r in selected)/1e6,
            median_delivery_ms=statistics.median(r['delivery_ns']for r in selected)/1e6,
            paired_round_speedups=ratios,median_paired_speedup=statistics.median(ratios),
            every_round_faster=all(x>1 for x in ratios),
            clears_initial_delivery_gate=mode!=0 and statistics.median(ratios)>1.05 and all(x>1 for x in ratios),
            physical_bytes=sum(r['physical_bytes']for r in selected)))
    return dict(completed=True,all_original_SHA256_exact=True,all_reads_returned=True,Direct_released=True,
        samples=len(rows),summary=summaries,whole_model_speed_qualified=False,production_adoption_qualified=False)
