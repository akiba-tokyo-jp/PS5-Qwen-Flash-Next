#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review a bounded CPU shader I/O control without inferring title/GPU costs."""
import re

def validate(raw,manifest):
    lines=raw.decode('ascii').splitlines()
    def one(prefix):
        rows=[line for line in lines if line.startswith(prefix)]
        if len(rows)!=1:raise ValueError('Expected one '+prefix)
        return dict(re.findall(r'(\w+)=(\S+)',rows[0]))
    def expected(row,fields):
        if any(row.get(k)!=str(v)for k,v in fields.items()):raise ValueError('Control scope differs')
    begin,end=one('BEGIN '),one('END ')
    expected(begin,dict(nonce=manifest['nonce'],CPU_only=1,title_launches=0,GPU_calls=0,maximum_reads=169,
        bytes=8258588,input_window=49152,matched_idle_ns=2000000,additional_floor_pages=256))
    expected(end,dict(success=1,nonce=manifest['nonce'],reads=169,returned=169,bytes=8258588,
        stages=338,pending=0,whole_SHA256=1,title_launches=0,GPU_calls=0,automatic_retry=0))
    direct=manifest.get('owned_Direct_window',False)
    expected(one('READ_SCOPE '),dict(direct_flag_set=1,static_aligned_window=int(not direct),tracked_Direct_heap=0,
        registry_initialized=0,codec_initialized=0))
    if direct:
        expected(one('READ_SCOPE '),dict(owned_Direct_window=1))
        expected(one('DIRECT_OWNERSHIP '),dict(released=1,pending=0))
        for phase in ('ALLOC','MAP','UNMAP','RELEASE'):expected(one('DIRECT_'+phase+'_RETURNED '),dict(rc=0))
    if not lines or not lines[-1].startswith('END '):raise ValueError('Terminal control record required')
    if lines.count('shader_asset_read_before_native_call')!=169 or lines.count('shader_asset_read_native_call_returned')!=169:
        raise ValueError('All durable read markers are required')
    markers=[line for line in lines if line.startswith('shader_asset_read_')]
    if markers!=['shader_asset_read_before_native_call','shader_asset_read_native_call_returned']*169:
        raise ValueError('Read marker order differs')
    samples={};keys={'kind','index','part','ns','free_first','free_last','active','inactive','wired','cache'}
    for line in lines:
        if not line.startswith('SAMPLE '):continue
        row=dict(re.findall(r'(\w+)=(\S+)',line))
        if set(row)!=keys:raise ValueError('Sample fields differ')
        kind=row.pop('kind')
        if any(not re.fullmatch(r'[0-9]+',v)for v in row.values()):raise ValueError('Unsigned observation required')
        row={k:int(v)for k,v in row.items()};key=(kind,row.pop('index'),row.pop('part'))
        if key in samples or row['ns']==0 or min(row['free_first'],row['free_last'])<1410:
            raise ValueError('Duplicate, invalid or below-floor observation')
        row['free']=min(row['free_first'],row['free_last']);samples[key]=row
    required={('stage',i,j)for i in range(338)for j in range(4)}|{('read',i,j)for i in range(169)for j in range(3)}
    required|={('quiet',i,0)for i in range(6)}|{('initial',0,0),('final',0,0)}
    if direct:required.add(('allocation',0,0))
    if set(samples)!=required:raise ValueError('Complete fixed observation set required')
    totals={name:dict(signed_free_page_decline=0,elapsed_ns=0,intervals=0)for name in ('matched_idle','write','fsync','pread','SHA256','quiet')}
    def interval(name,a,b,minimum=0):
        elapsed=b['ns']-a['ns']
        if elapsed<minimum:raise ValueError('Non-monotonic or truncated interval')
        r=totals[name];r['signed_free_page_decline']+=a['free']-b['free'];r['elapsed_ns']+=elapsed;r['intervals']+=1
    ordered=[samples['initial',0,0]]
    if direct:ordered.append(samples['allocation',0,0])
    for i in range(169):
        for k in (2*i,2*i+1):
            s=[samples['stage',k,j]for j in range(4)]
            interval('matched_idle',s[0],s[1],2000000);interval('write',s[1],s[2]);interval('fsync',s[2],s[3])
        before=[samples['stage',2*i,j]for j in range(4)]
        after=[samples['stage',2*i+1,j]for j in range(4)]
        r=[samples['read',i,j]for j in range(3)]
        interval('pread',r[0],r[1]);interval('SHA256',r[1],r[2]);ordered+=before+r+after
    quiet=[samples['quiet',i,0]for i in range(6)]
    for i in range(5):interval('quiet',quiet[i],quiet[i+1],200000000)
    ordered+=quiet+[samples['final',0,0]]
    if any(a['ns']>b['ns']for a,b in zip(ordered,ordered[1:])):raise ValueError('Operation sequence differs')
    first,last=ordered[0],ordered[-1];total=first['free']-last['free']
    return dict(schema='ps5-qwen-shader-io-memory-review-v1',completed=True,CPU_only=True,
        reads=169,returned_bytes=8258588,durable_stage_records=338,observations=len(samples),intervals=totals,
        initial_free_pages=first['free'],final_free_pages=last['free'],minimum_observed_free_pages=min(r['free']for r in samples.values()),
        signed_total_free_page_decline=total,unclassified_signed_page_decline=total-sum(r['signed_free_page_decline']for r in totals.values()),
        initial_categories={k:first[k]for k in ('active','inactive','wired','cache')},
        final_categories={k:last[k]for k in ('active','inactive','wired','cache')},
        title_launches=0,GPU_calls=0,unknown_completion=False,tracked_Direct_heap=False,owned_Direct_window=direct,
        owned_Direct_bytes=manifest.get('owned_Direct_bytes',0),positive_Direct_release=direct,registry_initialized=False,
        codec_initialized=False,title_startup_or_GPU_qualification=False,automatic_causal_attribution=False,
        note='Signed global page changes include observer and background work; the input uses the declared isolated window, not the title heap arena.')
