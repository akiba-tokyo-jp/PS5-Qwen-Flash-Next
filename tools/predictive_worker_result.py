#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review completed original-role CPU worker evidence, without a model claim."""
import re
def fields(line):return dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^ ]+)',line))
def validate(raw,nonce,plan_sha):
    if not isinstance(raw,str)or len(raw.encode())>512<<10 or not re.fullmatch('[0-9a-f]{32}',nonce):
        raise ValueError('Bounded native CPU worker evidence required')
    lines=raw.splitlines()
    def one(prefix):
        rows=[fields(s)for s in lines if s.startswith(prefix)]
        if len(rows)!=1:raise ValueError('One complete native record required: '+prefix)
        return rows[0]
    begin,end=one('BEGIN '),one('END ')
    if(begin.get('nonce')!=nonce or end.get('nonce')!=nonce or begin.get('plan_sha256')!=plan_sha or
       begin.get('Direct_bytes')!='9912320'or begin.get('rounds')!='4'or begin.get('roles')!='3'):
        raise ValueError('CPU worker owner, original source plan or extent differs')
    if any(row.get(k)!='0'for row in(begin,end)for k in('GPU_calls','title_launches')):
        raise ValueError('CPU-only scope differs')
    if(any(end.get(k)!='1'for k in('worker_joined','Direct_released','no_retry'))or
       any(s.startswith('RETAIN ')for s in lines)):
        raise ValueError('Unretired or uncertain CPU worker resources')
    if end.get('success')=='0':
        return dict(completed=False,returned_known_refusal=True,all_source_owners_retired=True,
            GPU_calls=0,title_launches=0,native_model_speed_qualified=False,production_adopted=False)
    if end.get('success')!='1':raise ValueError('Positive native completion required')
    if sum(s.startswith('context ')and'exact=1'in s and'canaries=1'in s for s in lines)!=3:
        raise ValueError('All three complete owner/boot boundaries required')
    if one('WORKER_START_RETURNED ').get('persistent')!='1'or one('WORKER_JOINED ')!={'persistent_lifetimes':'1','jobs':'4'}:
        raise ValueError('Exactly one persistent worker must retire all four jobs')
    for prefix in('DIRECT_ALLOC_RETURNED ','DIRECT_MAP_RETURNED ','DIRECT_UNMAP_RETURNED ','DIRECT_RELEASE_RETURNED '):
        if one(prefix).get('rc')!='0':raise ValueError('Direct lifetime did not positively complete')
    starts=[fields(s)for s in lines if s.startswith('JOB_BEFORE ')]
    jobs=[fields(s)for s in lines if s.startswith('JOB_RETURNED ')]
    roles=[fields(s)for s in lines if s.startswith('ROLE_RETURNED ')]
    if len(starts)!=4 or len(jobs)!=4 or len(roles)!=12:raise ValueError('Every original role and complete job is required')
    for n,(start,job)in enumerate(zip(starts,jobs)):
        if(start!={'round':str(n),'roles':'3','expected_bytes':'9879552'}or job.get('round')!=str(n)or
           any(job.get(k)!='1'for k in('exact_hashes_and_canaries','foreground_cost_control'))or job.get('pending')!='0'):
            raise ValueError('Worker geometry, exact originals or completion differs')
        elapsed=int(job.get('elapsed_ns','0'));foreground=int(job.get('foreground_ns','-1'));wait=int(job.get('wait_ns','-1'))
        if not 0<elapsed<=10000000000 or foreground<0 or wait<0 or foreground+wait!=elapsed:
            raise ValueError('Complete CPU foreground and join intervals required')
        previous=0
        for i,row in enumerate(roles[n*3:n*3+3]):
            if any(row.get(k)!=v for k,v in dict(round=str(n),role=str(i),bytes='3293184',errno='0').items()):
                raise ValueError('All three original roles must return their exact bytes')
            a,b=int(row.get('begin_ns','0')),int(row.get('end_ns','0'))
            if a<=0 or b<a or b-a>elapsed or a<previous:raise ValueError('Worker role order or positive timing differs')
            previous=b
    return dict(completed=True,returned_known_refusal=False,jobs=4,original_role_deliveries=12,
        physical_bytes=39518208,original_BF16_bytes=39321600,all_original_hashes_and_canaries_exact=True,
        persistent_worker_lifetimes=1,all_source_owners_retired=True,
        foreground_cost_metadata_control_passed=True,maximum_outstanding_reads=1,
        elapsed_ns=[int(r['elapsed_ns'])for r in jobs],foreground_ns=[int(r['foreground_ns'])for r in jobs],
        wait_ns=[int(r['wait_ns'])for r in jobs],GPU_calls=0,title_launches=0,
        native_model_speed_qualified=False,GPU_overlap_qualified=False,production_adopted=False)
