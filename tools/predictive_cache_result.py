#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review a retired native predictive cache report without inferring speed."""
def validate_predictive_cache(record,owner):
    if(type(owner.get('pid'))is not int or owner['pid']<=0 or type(owner.get('run_id'))is not str or
       len(owner['run_id'])!=32 or any(c not in '0123456789abcdef'for c in owner['run_id'])):
        raise ValueError('Exact native predictive owner required')
    expected=dict(schema='ps5-qwen-predictive-cache-result-v1',pid=owner['pid'],run_id=owner['run_id'],
        all_read_jobs_completed=True,actual_bank_leases_retired=True,all_model_owners_retired=True,
        device_ledger_live_bytes=0,speedup_qualified=False)
    if any(type(record.get(k))is not type(v)or record[k]!=v for k,v in expected.items()):
        raise ValueError('Predictive owner or positive resource retirement differs')
    for k in ('proposals','loads','useful_next_layer','unused_next_layer','ineligible','logical_bytes',
              'foreground_wait_ns','worker_read_ns'):
        if type(record.get(k))is not int or not 0<=record[k]<2**63:
            raise ValueError('Finite complete predictive counters required')
    if(record['proposals']!=record['loads']+record['ineligible']or
       record['loads']!=record['useful_next_layer']+record['unused_next_layer']or
       record['logical_bytes']!=record['loads']*9830400 or
       (record['loads']and not record['worker_read_ns'])):
        raise ValueError('Every predictive delivery, useful or unused, must be counted')
    return dict(native_predictions_exercised=record['loads']>0,loads=record['loads'],
        logical_bytes=record['logical_bytes'],speedup_qualified=False)
