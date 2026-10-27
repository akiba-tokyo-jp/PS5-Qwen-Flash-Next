#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently review one bounded CPU AIO/source comparison."""
import re
import statistics


def fields(line):
    return dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^ ]+)',line))


def validate(raw,nonce,plan_sha):
    if not isinstance(raw,str)or len(raw.encode())>512<<10 or not re.fullmatch('[0-9a-f]{32}',nonce):
        raise ValueError('Bounded actual AIO evidence and fresh nonce required')
    lines=raw.splitlines()
    def one(prefix):
        found=[fields(s)for s in lines if s.startswith(prefix)]
        if len(found)!=1:raise ValueError('One actual terminal record required: '+prefix)
        return found[0]
    begin,end=one('BEGIN '),one('END ')
    if begin.get('nonce')!=nonce or begin.get('plan_sha256')!=plan_sha or end.get('nonce')!=nonce:
        raise ValueError('Source plan or CPU owner nonce differs')
    for name in ('GPU_calls','title_launches'):
        if begin.get(name)!='0'or end.get(name)!='0':raise ValueError('CPU-only scope differs')
    if any(end.get(k)!='1'for k in ('all_workers_joined','all_AIO_IDs_retired','Direct_released','no_retry'))or any('RETAIN 'in s for s in lines):
        raise ValueError('Unknown or unretired CPU source owner')
    if end.get('success')=='0':
        return dict(completed=False,returned_known_refusal=True,all_source_owners_retired=True,
            native_speed_qualified=False,production_adopted=False,GPU_calls=0,title_launches=0)
    if end.get('success')!='1':raise ValueError('Missing positive completion')
    contexts=[s for s in lines if s.startswith('context ')and 'exact=1'in s and 'canaries=1'in s]
    if len(contexts)!=3:raise ValueError('All three exact CPU context boundaries are required')
    init,invalid=one('AIO_INITIALIZE_RETURNED '),one('AIO_INVALID_FD_COMPLETED ')
    if init.get('rc')!='0'or init.get('canaries')!='1'or int(invalid.get('value','0'))>=0 or invalid.get('retired_once')!='1':
        raise ValueError('AIO ABI prerequisite did not positively complete')
    if int(invalid.get('terminal','0'))&0xffff not in(3,4):raise ValueError('Invalid-descriptor request remains pending')
    rows=[fields(s)for s in lines if s.startswith('PAIR_RETURNED ')]
    modes=[0,1,1,0,0,1,1,0]
    if len(rows)!=8:raise ValueError('All eight original-source pairs are required')
    elapsed=[]
    for index,(row,mode) in enumerate(zip(rows,modes)):
        if row.get('round')!=str(index)or row.get('mode')!=str(mode)or row.get('bytes')!='6586368':
            raise ValueError('Actual read geometry or reverse order differs')
        if any(row.get(k)!='1'for k in ('original_hashes','identities','all_requests_retired')):
            raise ValueError('Source exactness or completion differs')
        ns=int(row.get('elapsed_ns','0'))
        if not 0<ns<=10000000000:raise ValueError('Invalid bounded I/O interval')
        elapsed.append(ns)
    for prefix in ('DIRECT_UNMAP_RETURNED ','DIRECT_RELEASE_RETURNED '):
        if one(prefix).get('rc')!='0':raise ValueError('Direct allocation did not retire')
    control=[elapsed[n]for n in (0,3,4,7)]
    candidate=[elapsed[n]for n in (1,2,5,6)]
    ratios=[elapsed[a]/elapsed[b]for a,b in ((0,1),(3,2),(4,5),(7,6))]
    drift=(max(control)-min(control))/statistics.mean(control)
    winner=all(r>1+drift for r in ratios)
    decision='source_fixture_winner'if winner else ('source_fixture_loser'if all(r<1 for r in ratios)else'inconclusive')
    return dict(completed=True,returned_known_refusal=False,rounds=8,original_matrix_deliveries=16,
        physical_bytes=8*6586368,round_modes=modes,elapsed_ns=elapsed,
        control_mean_ns=statistics.mean(control),AIO_mean_ns=statistics.mean(candidate),
        paired_ratios=ratios,mean_source_ratio=statistics.mean(control)/statistics.mean(candidate),
        control_spread_fraction=drift,decision=decision,all_source_owners_retired=True,
        initialization_and_allocation_outside_both_timed_arms=True,
        wait_and_completed_ID_retirement_inside_AIO_interval=True,
        native_model_speed_qualified=False,production_adopted=False,GPU_calls=0,title_launches=0)
