#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check aggregate-only numerical evidence and strict per-request timing evidence."""
import copy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from model_relative_prefetch_evidence import review


def completed():
    stats=dict(original_reads=4798,original_bytes=5570695280,predictions=6,predicted_bytes=8781824,hits=0,hit_bytes=0,
        unused=6,invalid=0,declines=0,maximum_simultaneous_reads=4,worker_creations=1,positive_worker_reads=6,
        speculative_reads=6,speculative_returned_calls=6,speculative_bytes=8781824,completed_worker_jobs=6)
    audit=dict(completed=True,enabled=True,requests=3,worker_joined_and_actual_scratch_lease_retired=True,
        original_source_FDs_held_until_same_pending_read_returned=True,all_original_native_guards_unchanged=True,
        additional_source_FDs=0,maximum_pending_spans=1,GPU_calls_added=0,cumulative=stats,
        final_worker_and_scratch_retirement_ns=47469)
    requests=[dict(relative_prefetch=dict(completed=True,enabled=True,ordinal=i,cumulative=copy.deepcopy(stats),
        final_source_drain_ns=1,additional_source_FDs=0,scratch_bytes=2<<20,
        all_original_and_speculative_IO_returned=True,GPU_calls_added=0)) for i in range(3)]
    return dict(audit=audit,requests=requests)


def main():
    full=completed()
    assert review(full,True)['per_request_counter_receipts_available']
    aggregate=completed();aggregate['requests']=[{}, {}, {}]
    result=review(aggregate,True,allow_aggregate_only=True)
    assert not result['per_request_counter_receipts_available'] and result['missing_request_receipts_not_reconstructed']
    cases=[(aggregate,False)]
    for key,value in (('completed_worker_jobs',5),('maximum_simultaneous_reads',5),('worker_creations',2),
                      ('speculative_returned_calls',5),('positive_worker_reads',5),('hit_bytes',8781825)):
        bad=copy.deepcopy(aggregate);bad['audit']['cumulative'][key]=value;cases.append((bad,True))
    bad=completed();bad['requests'][1].pop('relative_prefetch');cases.append((bad,True))
    bad=completed();bad['requests'][0]['relative_prefetch']['scratch_bytes']=4<<20;cases.append((bad,False))
    for case,allow in cases:
        try:review(case,True,allow_aggregate_only=allow)
        except RuntimeError:continue
        raise AssertionError('Incomplete or inconsistent actual ownership evidence was admitted')
    print(dict(completed=True,positive_controls=2,negative_controls=len(cases),PS5_operations=0))


if __name__=='__main__':main()
