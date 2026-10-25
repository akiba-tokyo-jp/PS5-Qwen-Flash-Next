#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit finite same-owner CPU memory traces without inferring reclaimability."""
import re

def fields(line):
    return {k:int(v)for k,v in re.findall(r'(\w+)=(-?\d+)',line)}

def parse(raw,manifest):
    lines=raw.decode('ascii').splitlines()
    selected={p:[x for x in lines if x.startswith(p)]for p in ('BEGIN ','END ','DIRECT_EXACT ','FILE_CLOSED ')}
    if any(len(selected[p])!=1 for p in selected):
        raise ValueError('Unique positive terminal and completed Direct input are required')
    for prefix in ('BEGIN ','END '):
        line=selected[prefix][0]
        if ('nonce='+manifest['nonce'])not in line:
            raise ValueError('Trace owner differs')
        f=fields(line)
        if any(f.get(k)!=0 for k in ('explicit_allocations','title_launches','GPU_calls')):
            raise ValueError('Trace scope differs')
    end=fields(selected['END '][0]);start=fields(selected['BEGIN '][0])
    capacity=manifest.get('trace_capacity',64)
    if capacity not in (64,128) or end.get('success')!=1 or end.get('automatic_retry')!=0 or start.get('direct_mode')!=1 or start.get('trace_capacity')!=capacity or start.get('window')!=1<<20:
        raise ValueError('Trace did not positively complete its fixed scope')
    if any(x.startswith(('RETAIN ','DIRECT_REFUSED '))for x in lines):
        raise ValueError('Refused or unknown work is not an admitted comparison')
    contexts=[fields(x)for x in lines if x.startswith('context ')]
    if [x.get('phase')for x in contexts]!=[1,2,3] or any(x.get('exact')!=1 or x.get('canaries')!=1 for x in contexts):
        raise ValueError('Same-boot context checks are incomplete')
    if any(fields(x).get('exact')!=1 for x in lines if x.startswith('process ')):
        raise ValueError('A service identity changed')
    samples=[fields(x)for x in lines if x.startswith('SAMPLE ')]
    if not 10<=len(samples)<=capacity or len(samples)!=end.get('samples'):
        raise ValueError('Bounded sample count differs')
    required=('seq','phase','ns','free_first','free_last','total','minimum','reserved','target','active','inactive','wired','cache','page_bytes')
    for i,s in enumerate(samples):
        if any(k not in s for k in required) or s['seq']!=i or s['ns']<=0 or (i and s['ns']<=samples[i-1]['ns']):
            raise ValueError('Trace ordering differs')
        if (s['page_bytes']!=16384 or not 0<s['reserved']<=s['minimum']<s['target']<=s['total'] or
            any(not 0<=s[k]<=s['total']for k in ('free_first','free_last','active','inactive','wired','cache'))):
            raise ValueError('Invalid memory counters')
        if i and any(s[k]!=samples[0][k]for k in ('total','minimum','reserved','target','page_bytes')):
            raise ValueError('Memory domain or safety thresholds changed')
    logical=manifest['canonical_SELF']['bytes'];offset=0;expected=[]
    while offset<logical:
        n=min(1<<20,logical-offset)
        expected.append((offset,(n+16383)//16384*16384,n));offset+=n
    eof=logical//16384*16384
    expected.append((eof,16384,logical-eof))
    reads=[x for x in lines if x.startswith(('READ_BEFORE','READ_RETURNED '))]
    if len(reads)!=2*len(expected):raise ValueError('Incomplete read journal')
    for i,(offset,requested,returned)in enumerate(expected):
        a,b=reads[2*i:2*i+2];f=fields(b)
        if a!='READ_BEFORE' or not b.startswith('READ_RETURNED ') or any(f.get(k)!=v for k,v in dict(offset=offset,requested=requested,bytes=returned).items()):
            raise ValueError('Direct read or final EOF differs')
    exact=fields(selected['DIRECT_EXACT '][0])
    if any(exact.get(k)!=v for k,v in dict(bytes=logical,calls=len(expected),returned=len(expected),complete_SHA256_identity_EOF=1).items()) or fields(selected['FILE_CLOSED '][0]).get('success')!=1:
        raise ValueError('Full canonical integrity and positive close are required')
    phases=[s['phase']for s in samples]
    network=bool(manifest.get('network_control',False))
    if phases!=[0]*5+([5]*17 if network else [])+[1]+[2]*len(expected)+[4]*5:
        raise ValueError('Matched idle and Direct boundaries differ')
    for s in samples[5:-5]:
        additional=64 if s['phase']==1 else 0
        if min(s['free_first'],s['free_last'])<s['minimum']+max(s['reserved'],256)+additional:
            raise ValueError('A Direct read ran below its unchanged admission floor')
    def delta(a,b):
        return {k:b[k]-a[k]for k in ('free_first','free_last','active','inactive','wired','cache')}
    result=dict(completed=True,canonical_Direct_SHA256_identity_EOF_exact=True,all_reads_returned=True,
        file_closed=True,source_bytes=logical,reads=len(expected),samples=len(samples),
        idle_before_delta_pages=delta(samples[0],samples[4]),
        direct_interval_delta_pages=delta(next(s for s in samples if s['phase']==1),samples[-5]),
        idle_after_delta_pages=delta(samples[-5],samples[-1]),
        lowest_free_pages=min(min(s['free_first'],s['free_last'])for s in samples),
        final_free_pages=min(samples[-1]['free_first'],samples[-1]['free_last']),
        page_bytes=16384,inactive_pages_counted_as_available=False,
        proprietary_cause_identified=False,full_model_admitted=False,
        source_role=manifest.get('source_role','production_SELF'),
        title_launches=0,GPU_calls=0,unknown_completion=False,automatic_retries=0)
    if network:
        control=[s for s in samples if s['phase']==5]
        first=control[0]
        needed=first['minimum']+max(first['reserved'],256)+(logical+16383)//16384+64
        if min(first['free_first'],first['free_last'])<needed or lines.count('NETWORK_WINDOW_ENDED')!=1:
            raise ValueError('Network control did not retain its conservative pre-admission')
        result['network_interval_delta_pages']=delta(control[0],control[-1])
    return result
