#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Require complete native read leases and original bytes before timing admission."""
import re,statistics

def fields(line):return {k:int(v)for k,v in re.findall(r'(\w+)=(-?\d+)',line)}

def parse_preallocation_refusal(raw,manifest):
    """A positive zero-work terminal is a refused test, never a speed result."""
    lines=raw.decode('ascii').splitlines()
    begin=[x for x in lines if x.startswith('BEGIN ')]
    end=[x for x in lines if x.startswith('END ')]
    observations=[fields(x)for x in lines if x.startswith('PREALLOC_HEADROOM ')]
    if len(begin)!=1 or len(end)!=1 or len(observations)!=1:
        raise ValueError('A unique positive refusal and capacity observation are required')
    for line in (begin[0],end[0]):
        if 'nonce='+manifest['nonce']not in line or 'GPU_calls=0'not in line or 'title_launches=0'not in line:
            raise ValueError('Refusal owner or scope differs')
    terminal=fields(end[0]);observation=observations[0];start=fields(begin[0])
    if any(terminal.get(k)!=v for k,v in dict(success=0,pending_reads=0,all_workers_joined=0,Direct_released=1,automatic_retry=0).items()):
        raise ValueError('The refusal is not a positively completed zero-work terminal')
    if any(x.startswith(('DIRECT_ALLOC_','DIRECT_MAP_','VERIFY_','IO_','BATCH_','RETAIN '))for x in lines):
        raise ValueError('The refused case started allocation or payload work')
    total=manifest.get('io_bytes',8<<20)+manifest['destination_bytes']
    required=observation['minimum']+max(observation['reserved'],256)+total//16384
    if (total%16384 or start['total_Direct_bytes']!=total or observation['additional_pages']!=total//16384 or
        observation['required']!=required or min(observation['free_first'],observation['free_last'])>=required or
        observation['rc']!=0 or observation['flexible_bytes']<(264<<20)):
        raise ValueError('The observed preallocation refusal does not match its unchanged floor')
    return dict(status='refused_before_allocation',completed=True,allocations=0,payload_reads=0,
        GPU_calls=0,title_launches=0,workers_started=0,unknown_completion=False,automatic_retries=0,
        observed_free_pages=[observation['free_first'],observation['free_last']],required_free_pages=required,
        total_Direct_bytes=total,whole_model_speed_qualified=False)
def parse(raw,manifest):
    lines=raw.decode('ascii').splitlines();nonce=manifest['nonce']
    for prefix in ('BEGIN ','END '):
        selected=[x for x in lines if x.startswith(prefix)]
        if len(selected)!=1 or 'nonce='+nonce not in selected[0] or 'GPU_calls=0'not in selected[0] or 'title_launches=0'not in selected[0]:
            raise ValueError('A unique same-owner CPU-only terminal is required')
    end=next(x for x in lines if x.startswith('END '))
    if not all(x in end for x in ('success=1 ','pending_reads=0 ','all_workers_joined=1 ','Direct_released=1 ','automatic_retry=0'))or any(x.startswith('RETAIN ')for x in lines):
        raise ValueError('Positive completion and backing retirement are required')
    begin=fields(next(x for x in lines if x.startswith('BEGIN ')))
    io_bytes=manifest.get('io_bytes',8<<20)
    if io_bytes not in (0,8<<20):raise ValueError('Unsupported source window budget')
    destination=manifest.get('destination_bytes',32<<20);total=io_bytes+destination
    count=manifest.get('samples',9);groups=manifest.get('groups',1);modes=len(manifest['variants'])
    if (begin['io_bytes'],begin['destination_bytes'],begin['total_Direct_bytes'],begin['maximum_outstanding_reads'])!=(io_bytes,destination,total,2):
        raise ValueError('Separate buffer budgets differ')
    for before,after in ((f'DIRECT_ALLOC_BEFORE bytes={total}','DIRECT_ALLOC_RETURNED rc=0'),
        (f'DIRECT_MAP_BEFORE bytes={total}','DIRECT_MAP_RETURNED rc=0'),('DIRECT_UNMAP_BEFORE','DIRECT_UNMAP_RETURNED rc=0'),
        ('DIRECT_RELEASE_BEFORE','DIRECT_RELEASE_RETURNED rc=0'),('EOF_BEFORE','EOF_RETURNED bytes=0')):
        if lines.count(before)!=1 or lines.count(after)!=1 or lines.index(before)>=lines.index(after):raise ValueError('Resource lifetime differs')
    for marker in ('PACK_complete_SHA256_identity_EOF=1','ALL_65536_BF16_patterns_exact=1'):
        if lines.count(marker)!=1:raise ValueError('Complete source and bit checks are required')
    verify=[x for x in lines if x.startswith('VERIFY_')]
    if not verify or len(verify)%2:raise ValueError('Pack verification reads are incomplete')
    verified=0
    for a,b in zip(verify[::2],verify[1::2]):
        if not a.startswith('VERIFY_BEFORE ')or not b.startswith('VERIFY_RETURNED ')or fields(a)['bytes']!=fields(b)['bytes']:
            raise ValueError('A verification read did not return exactly')
        verified+=fields(a)['bytes']
    if verified!=manifest['pack']['bytes']:raise ValueError('Full pack verification is incomplete')
    rows=[];seen=set();ids=set();active={};batch=None;reads=[];drained=None
    for line in lines:
        if line.startswith('BATCH_BEGIN '):
            if batch is not None or active:raise ValueError('A preceding batch is still owned')
            f=fields(line);batch=(f['round'],f.get('group',0),f['mode']);reads=[];drained=None
            if batch in seen or not 0<=batch[0]<manifest['rounds']or not 0<=batch[1]<groups or not 0<=batch[2]<modes:raise ValueError('Invalid batch identity')
        elif line.startswith('IO_BEFORE '):
            f=fields(line)
            if batch is None or drained or f['id']in ids or f['slot']in active or f['slot']not in (0,1):raise ValueError('A source lease was reused')
            ids.add(f['id']);active[f['slot']]=f
            if len(active)>2:raise ValueError('Source depth exceeded')
        elif line.startswith('IO_RETURNED '):
            f=fields(line);a=active.pop(f['slot'],None)
            if a is None or any(a[k]!=f[k]for k in ('id','offset','bytes'))or f['result']!=f['bytes']or f['start_ns']<=0 or f['end_ns']<f['start_ns']:
                raise ValueError('A Direct read did not return exactly')
            reads.append(f)
        elif line.startswith('BATCH_DRAINED '):
            f=fields(line)
            if batch!=(f['round'],f.get('group',0),f['mode'])or active or drained is not None or len(reads)!=count:raise ValueError('The batch was not drained')
            expected=(manifest['extents'][batch[1]]if groups>1 else manifest['extents'])[2<=batch[2]<4]
            if batch[2]>=4:
                if count!=3:raise ValueError('Packed cohort dimensions differ')
                expected=[dict(offset=expected[0]['offset']+i*(4<<20),requested=(4<<20)if i<2 else count*3276800-(8<<20))for i in range(3)]
            if sorted((x['offset'],x['bytes'])for x in reads)!=sorted((x['offset'],x['requested'])for x in expected):raise ValueError('Source extents differ')
            if f['wall_ns']<=0 or f['read_ns']!=sum(x['end_ns']-x['start_ns']for x in reads)or f['physical_bytes']!=sum(x['bytes']for x in reads):raise ValueError('Native timing/byte arithmetic differs')
            if (batch[2]<2 or batch[2]>=4)and f['restore_ns']!=0:raise ValueError('Raw mode reconstructed data')
            if batch[2]>=4 and f.get('copy_ns',0)<=0:raise ValueError('Packed output copy evidence is required')
            intervals=sorted((x['start_ns'],x['end_ns'])for x in reads);end_at=intervals[0][0];covered=0
            for a,b in intervals:
                covered+=max(0,b-max(end_at,a));end_at=max(end_at,b)
            f['no_read_active_inside_span_ns']=end_at-intervals[0][0]-covered
            drained=f
        elif line.startswith('BATCH_EXACT '):
            f=fields(line)
            if batch!=(f['round'],f.get('group',0),f['mode'])or not drained or f['complete_original_SHA256']!=count:raise ValueError('Original output digests are incomplete')
            rows.append(drained);seen.add(batch);batch=None;drained=None
    if batch is not None or active or len(rows)!=manifest['rounds']*groups*modes:raise ValueError('The native cohort is incomplete')
    summaries=[]
    for mode,name in enumerate(manifest['variants']):
        selected=[x for x in rows if x['mode']==mode]
        ratios=[sum(x['wall_ns']for x in rows if x['round']==r and x['mode']==0)/sum(x['wall_ns']for x in selected if x['round']==r)for r in range(manifest['rounds'])]
        same_read_control=1 if mode in (3,5)else 0
        matched=[sum(x['wall_ns']for x in rows if x['round']==r and x['mode']==same_read_control)/sum(x['wall_ns']for x in selected if x['round']==r)for r in range(manifest['rounds'])]
        summaries.append(dict(variant=name,median_batch_ms=statistics.median(x['wall_ns']for x in selected)/1e6,
            median_restore_ms=statistics.median(x['restore_ns']for x in selected)/1e6,
            median_copy_ms=statistics.median(x.get('copy_ns',0)for x in selected)/1e6,
            median_no_read_active_inside_span_ms=statistics.median(x['no_read_active_inside_span_ns']for x in selected)/1e6,
            paired_round_speedups=ratios,median_paired_speedup=statistics.median(ratios),
            matched_schedule_speedups=matched,median_matched_schedule_speedup=statistics.median(matched),
            clears_initial_delivery_gate=mode!=0 and statistics.median(ratios)>1.05 and all(x>1 for x in ratios) and
                (mode not in (3,5)or (statistics.median(matched)>1.05 and all(x>1 for x in matched)))))
    return dict(completed=True,complete_original_SHA256_exact=True,all_reads_returned=True,all_workers_joined=True,
        Direct_released=True,batches=len(rows),summary=summaries,rows=rows,
        io_bytes=io_bytes,destination_bytes=destination,whole_model_speed_qualified=False,production_adoption_qualified=False)
