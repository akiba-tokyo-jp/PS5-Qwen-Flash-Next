#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review a positive CPU-only exact-table reconstruction, never model speed."""
import re
from predictive_worker_result import fields
def validate(raw,nonce,manifest_sha,table_count,raw_bytes,packed_bytes):
    if not isinstance(raw,str)or len(raw.encode())>512<<10 or not re.fullmatch('[0-9a-f]{32}',nonce):
        raise ValueError('Bounded current-owner table evidence required')
    lines=raw.splitlines()
    def one(prefix):
        rows=[fields(s)for s in lines if s.startswith(prefix)]
        if len(rows)!=1:raise ValueError('Exactly one complete record required: '+prefix)
        return rows[0]
    begin,end=one('BEGIN '),one('END ')
    expected=dict(nonce=nonce,manifest_sha256=manifest_sha,tables=str(table_count),raw_bytes=str(raw_bytes),packed_bytes=str(packed_bytes),GPU_calls='0',title_launches='0')
    if begin!=expected or end.get('nonce')!=nonce or any(end.get(k)!=v for k,v in dict(GPU_calls='0',title_launches='0',no_retry='1').items()):
        raise ValueError('Native scope, exact data identity or owner differs')
    if end.get('success')=='0':return dict(completed=False,returned_known_refusal=True,GPU_calls=0,title_launches=0,production_adopted=False)
    if end.get('success')!='1':raise ValueError('Positive completion is required')
    for phase in range(1,4):
        c=one('context phase='+str(phase)+' ')
        if c.get('exact')!='1'or c.get('canaries')!='1':raise ValueError('Current boot and owner context required')
        processes=[fields(s)for s in lines if s.startswith('process phase='+str(phase)+' ')]
        if len(processes)!=8 or any(p.get('exact')!='1'or p.get('canaries')!='1'for p in processes):
            raise ValueError('All eight exact owner roles required')
    result=one('RESTORE_RETURNED ')
    if any(result.get(k)!='1'for k in('exact_hashes','codec_released','readonly_protection')):
        raise ValueError('Every original table and completed readonly restoration is required')
    elapsed,peak=int(result.get('elapsed_ns','0')),int(result.get('scratch_peak','0'))
    if not 0<elapsed<=10000000000 or not 0<peak<=1<<20:raise ValueError('Bounded codec accounting required')
    return dict(completed=True,returned_known_refusal=False,table_count=table_count,raw_bytes=raw_bytes,packed_bytes=packed_bytes,
        all_original_SHA256_exact=True,codec_released=True,readonly_protection=True,elapsed_ns=elapsed,scratch_peak=peak,
        CPU_data_fixture_only=True,compiler_or_model_qualified=False,measured_startup_savings=False,
        GPU_calls=0,title_launches=0,production_adopted=False)
