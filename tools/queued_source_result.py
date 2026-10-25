#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Strict completed CPU replay result; never infer model speed from I/O alone."""
import re,statistics

def parse(raw,nonce):
    text=raw.decode('ascii');lines=text.splitlines()
    begin=[x for x in lines if x.startswith('BEGIN ')];end=[x for x in lines if x.startswith('END ')]
    if begin!=[f'BEGIN nonce={nonce} exact_trace=1 scratch_bytes=8388608 maximum_fds=8 source_quads=32 sample_quads=8 GPU_calls=0 title_launches=0']:
        raise ValueError('Queue replay start scope differs')
    if end!=[f'END success=1 nonce={nonce} pending_reads=0 all_workers_joined=1 Direct_released=1 GPU_calls=0 title_launches=0 automatic_retry=0'] or any(x.startswith('RETAIN ')for x in lines):
        raise ValueError('Queue replay completion or ownership differs')
    for operation in ('ALLOC','MAP','UNMAP','RELEASE'):
        before=[x for x in lines if x.startswith('DIRECT_'+operation+'_BEFORE')]
        after=[x for x in lines if x.startswith('DIRECT_'+operation+'_RETURNED')]
        if len(before)!=1 or after!=['DIRECT_'+operation+'_RETURNED rc=0']:
            raise ValueError('Direct operation lacks positive completion')
    reads=[x for x in lines if x.startswith('READ_BEFORE ')];returned=[x for x in lines if x.startswith('READ_RETURNED ')]
    if len(reads)!=192 or len(returned)!=192:raise ValueError('A read batch lacks completion')
    for a,b in zip(reads,returned):
        m=re.fullmatch(r'READ_BEFORE lanes=(2|4) bytes=(\d+)',a)
        if not m:raise ValueError('Unknown read batch')
        lanes,n=map(int,m.groups())
        if not 0<n<=8388608//lanes or n%16384 or b!=f'READ_RETURNED lanes={lanes} pending=0':
            raise ValueError('Read extent or return differs')
    rows=[]
    for line in lines:
        if not line.startswith('QUAD '):continue
        m=re.fullmatch(r'QUAD round=(\d+) mode=(\d+) index=(\d+) wall_ns=(\d+) logical_bytes=13107200 calls=(\d+) exact_SHA256=1',line)
        if not m:raise ValueError('Queue replay bytes/hash report differs')
        r,mode,index,ns,calls=map(int,m.groups())
        if not 0<ns<45000000000 or calls!=(4 if mode==0 else 8):raise ValueError('Queue replay interval differs')
        rows.append(dict(round=r,mode=mode,index=index,wall_ns=ns))
    expected=[(r,(r+order)%2,i)for r in range(6)for order in range(2)for i in range(8)]
    if [(x['round'],x['mode'],x['index'])for x in rows]!=expected:raise ValueError('Missing, repeated or unrotated replay samples')
    samples={mode:[sum(x['wall_ns']for x in rows if x['round']==r and x['mode']==mode)for r in range(6)]for mode in (0,1)}
    medians={m:statistics.median(v)for m,v in samples.items()}
    return dict(schema='ps5-qwen-queued-source-CPU-result-v1',completed=True,
        all_returned_payload_SHA256_exact=True,all_workers_joined=True,Direct_released=True,
        scratch_bytes=8388608,maximum_FDs=8,prepared_quads=32,sampled_quads=8,rounds=6,
        source_bytes_per_mode_per_round=104857600,round_wall_ns=samples,
        median_GB_s={m:104857600/medians[m]for m in medians},
        four_read_median_speedup=medians[0]/medians[1],
        whole_model_speed_qualified=False,production_adopted=False,GPU_calls=0,title_launches=0)
