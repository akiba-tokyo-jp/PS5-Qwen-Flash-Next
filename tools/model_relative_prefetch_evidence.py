# SPDX-License-Identifier: MIT
"""Review returned native source-prefetch counters without executing model work."""
from start_success_route import need


def review(terminal, enabled, allow_aggregate_only=False):
    audit=terminal['audit']
    need(audit['completed'] and audit['enabled'] is enabled and audit['requests']==3 and
         audit['worker_joined_and_actual_scratch_lease_retired'] and
         audit['original_source_FDs_held_until_same_pending_read_returned'] and
         audit['all_original_native_guards_unchanged'] and audit['additional_source_FDs']==0 and
         audit['maximum_pending_spans']==1 and audit['GPU_calls_added']==0,
         'Returned actual worker, scratch, source-fd and original guard ownership required')
    stats=audit['cumulative']
    need(all(type(value) is int and value>=0 for value in stats.values()) and
         stats['maximum_simultaneous_reads']<=4 and stats['worker_creations']<=1 and
         stats['predictions']==stats['completed_worker_jobs']==stats['hits']+stats['unused'] and
         stats['speculative_reads']==stats['speculative_returned_calls'] and
         stats['positive_worker_reads']+stats['invalid']==stats['completed_worker_jobs'] and
         stats['hits']<=stats['positive_worker_reads'] and stats['invalid']<=stats['unused'] and
         stats['hit_bytes']<=stats['predicted_bytes'] and (enabled or not any(stats.values())) and
         audit['final_worker_and_scratch_retirement_ns']>=0,
         'The final actual cumulative job/read/worker ownership counters must reconcile')
    missing=['relative_prefetch' not in row for row in terminal['requests']]
    if any(missing):
        need(allow_aggregate_only and len(missing)==3 and all(missing),
             'Every actual per-request receipt is required for timing; only the completed numerical run may use its final audit')
        return dict(enabled=enabled,cumulative=stats,all_actual_IO_and_worker_scratch_ownership_returned=True,
            no_actual_speculation_exercised=not bool(stats['speculative_reads']),per_request_counter_receipts_available=False,
            missing_request_receipts_not_reconstructed=True,
            final_worker_and_scratch_retirement_ns=audit['final_worker_and_scratch_retirement_ns'])
    previous=None
    for index,row in enumerate(terminal['requests']):
        receipt=row['relative_prefetch'];stats=receipt['cumulative']
        need(receipt['completed'] and receipt['enabled'] is enabled and receipt['ordinal']==index and
             receipt['all_original_and_speculative_IO_returned'] and receipt['additional_source_FDs']==0 and
             receipt['scratch_bytes']==(2<<20 if enabled else 0) and receipt['GPU_calls_added']==0 and
             receipt['final_source_drain_ns']>=0,
             'Each original request must positively drain its actual source reads')
        need(all(type(value) is int and value>=0 for value in stats.values()) and
             stats['maximum_simultaneous_reads']<=4 and stats['worker_creations']<=1 and
             stats['predictions']==stats['completed_worker_jobs']==stats['hits']+stats['unused'] and
             stats['speculative_reads']==stats['speculative_returned_calls'] and
             stats['positive_worker_reads']+stats['invalid']==stats['completed_worker_jobs'] and
             stats['hits']<=stats['positive_worker_reads'] and stats['invalid']<=stats['unused'] and
             stats['hit_bytes']<=stats['predicted_bytes'] and
             (enabled or not any(stats.values())),
             'Every actual speculative job/read and original four-read limit must reconcile')
        if previous is not None:
            need(stats.keys()==previous.keys() and all(stats[k]>=previous[k] for k in stats),
                 'Actual cumulative source counters must not regress')
        previous=stats
    need(previous==audit['cumulative'] and audit['final_worker_and_scratch_retirement_ns']>=0,
         'Final positive retirement must preserve the last returned request counters')
    return dict(enabled=enabled,cumulative=audit['cumulative'],
        all_actual_IO_and_worker_scratch_ownership_returned=True,
        per_request_counter_receipts_available=True,
        no_actual_speculation_exercised=not bool(audit['cumulative']['speculative_reads']),
        final_worker_and_scratch_retirement_ns=audit['final_worker_and_scratch_retirement_ns'])
