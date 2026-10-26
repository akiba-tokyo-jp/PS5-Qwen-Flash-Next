#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate completed aggregate wall intervals without claiming GPU timestamps."""
FIELDS = {
    'source_bytes', 'source_chunks', 'source_completed_windows', 'source_headroom_ns',
    'source_handle_ns', 'source_read_ns', 'source_consumer_ns', 'process_calls',
    'process_ns', 'synchronize_ns', 'checkpoint_ns', 'work_guard_ns', 'stage_observer_ns'}


def validate_first_performance(record, aggregate, first, *, split_sources=False):
    # The first terminal owns request-specific batching metadata. Its numerical
    # result must still agree exactly with the complete lifecycle aggregate.
    for key in ('metrics','token_ids','output_bytes','stop_reason'):
        if key not in first or first[key] != aggregate.get(key):
            raise ValueError('First performance terminal differs from the aggregate')
    if ('prefill_batch_tokens' in aggregate and
            aggregate['prefill_batch_tokens'] != first.get('prefill_batch_tokens')):
        raise ValueError('Aggregate and first-terminal prefill widths differ')
    return validate_performance(record, first, split_sources=split_sources)


def validate_backpressure(record):
    schema=record.get('schema')
    limits={'ps5-qwen-memory-backpressure-v1':(2000,10000),'ps5-qwen-memory-backpressure-v2':(20000,60000)}
    if schema not in limits:raise ValueError('Unknown memory backpressure policy')
    boundary,total=limits[schema]
    required=dict(schema=schema,enabled=True,
        maximum_boundary_wait_ms=boundary,maximum_total_wait_ms=total,poll_interval_ms=100,
        memory_reserves_unchanged=True,IO_or_GPU_operations_retried=False,last_qualified=True,
        kernel_page_size=16384,kernel_extra_margin_bytes=4 << 20)
    if any(type(record.get(k)) is not type(v) or record[k]!=v for k,v in required.items()):
        raise ValueError('Memory backpressure scope differs')
    counters=['observations','pressure_events','recovered_admissions','cumulative_wait_ns',
        'pause_calls','kernel_free_pages','kernel_minimum_pages','kernel_reserved_pages']
    if any(type(record.get(k)) is not int or not 0<=record[k]<2**63 for k in counters):
        raise ValueError('Memory backpressure counters differ')
    if (not record['observations'] or record['pressure_events']!=record['recovered_admissions'] or
        not 0<record['kernel_reserved_pages']<=record['kernel_minimum_pages'] or
        record['pressure_events']>record['pause_calls'] or
        record['cumulative_wait_ns']>total*1_000_000 or record['pause_calls']>total//100 or
        (record['pause_calls']==0)!=(record['cumulative_wait_ns']==0) or
        record['kernel_free_pages']<record['kernel_minimum_pages']+max(record['kernel_reserved_pages'],256)):
        raise ValueError('A pressure admission lacks bounded recovery')
    return record


def validate_performance(record, result, *, split_sources=False, checkpoint_validation=None):
    schema = record.get('schema')
    if type(split_sources) is not bool or (split_sources and schema not in (
            'ps5-qwen-completed-performance-v4', 'ps5-qwen-completed-performance-v5')):
        raise ValueError('Split source accounting requires an admitted selected schedule')
    if (schema not in tuple('ps5-qwen-completed-performance-v'+str(v) for v in range(1,6)) or
        record.get('process_includes_source_and_backend_work') is not True or
        record.get('GPU_timestamp_queries') is not False or
        record.get('hot_path_logs_added') is not False or record.get('GPU_operations_added') is not False):
        raise ValueError('Performance measurement scope differs')
    delta = record.get('delta', {})
    fields = FIELDS | ({'source_parallel_batches'} if schema.endswith('v2') else
        {'source_pipeline_batches', 'source_worker_read_ns', 'source_worker_dispatch_ns'} if schema.endswith(('v3','v4','v5')) else set())
    if schema.endswith(('v4','v5')):
        fields |= {'source_parallel_batches','source_coalesced_batches','source_selected_serial_batches',
                   'source_physical_read_bytes','source_physical_read_calls'}
    padded=record.get('owned_padded_bank_IO',False)
    if type(padded) is not bool or (padded and not schema.endswith(('v4','v5'))):
        raise ValueError('Owned bank I/O requires selected source accounting')
    if padded:
        fields |= {'source_direct_bank_bytes','source_direct_bank_reads','source_padded_scatter_bytes'}
    if set(delta) != fields or any(type(v) is not int or not 0 <= v < 2**63 for v in delta.values()):
        raise ValueError('Invalid completed performance counters')
    if padded and (delta['source_direct_bank_bytes']!=3276800*delta['source_direct_bank_reads'] or
            delta['source_direct_bank_bytes']+delta['source_padded_scatter_bytes']>delta['source_bytes'] or
            delta['source_direct_bank_reads']>delta['source_physical_read_calls'] or
            delta['source_direct_bank_reads']>delta['source_chunks']):
        raise ValueError('Direct bank payload/read/scatter accounting differs')
    if schema.endswith('v2') and (record.get('source_read_ns_is_batch_wall_time') is not True or
        record.get('maximum_parallel_source_reads') != 2 or
        not 0 < delta['source_parallel_batches'] <= delta['source_chunks'] // 2):
        raise ValueError('Parallel reads lack bounded completed batch evidence')
    if schema.endswith('v3') and (record.get('source_read_ns_is_producer_wait_time') is not True or
        record.get('maximum_parallel_source_reads') != 1 or record.get('worker_times_overlap_consumers') is not True or
        not 0 < delta['source_pipeline_batches'] <= delta['source_chunks'] // 2 or delta['source_worker_read_ns'] <= 0):
        raise ValueError('Source pipelining lacks single-read completion evidence')
    if schema.endswith(('v4','v5')) and (record.get('source_read_ns_is_producer_wait_time') is not True or
        record.get('maximum_parallel_source_reads') != 2 or record.get('file_range_schedule_enabled') is not True or
        record.get('physical_read_bytes_include_alignment') is not True or
        delta['source_physical_read_bytes'] < delta['source_bytes'] or
        delta['source_parallel_batches']+delta['source_coalesced_batches']+delta['source_selected_serial_batches'] > delta['source_chunks']//2):
        raise ValueError('Selected source scheduling lacks exact bounded completion evidence')
    if schema.endswith(('v4','v5')):
        joined = delta['source_selected_serial_batches'] - delta['source_pipeline_batches']
        extra = delta['source_physical_read_calls'] - (delta['source_chunks'] - delta['source_coalesced_batches'])
        # A split fallback pair completes two logical windows without the worker.
        # Each window is smaller than a part and can add at most one read.
        if split_sources:
            if (not 0 <= joined <= delta['source_chunks']//2 or not joined <= extra <= 2*joined or
                    delta['source_physical_read_bytes'] > delta['source_bytes'] +
                    32768*delta['source_physical_read_calls']):
                raise ValueError('Split fragments exceed bounded physical read accounting')
        elif joined != 0 or extra != 0:
            raise ValueError('Unsplit source physical read accounting differs')
    metrics = result['metrics']
    reason = result['stop_reason']
    if reason not in ('end_of_generation', 'output_token_limit'):
        raise ValueError('Performance requires completed generation')
    width = 1
    if schema.endswith('v5'):
        width = record.get('prefill_batch_tokens')
        if (type(width) is not int or width not in (2,4) or
            type(result.get('prefill_batch_tokens')) is not int or result['prefill_batch_tokens'] != width or
            type(record.get('generated_token_batch_tokens')) is not int or record['generated_token_batch_tokens'] != 1 or
            record.get('all_prompt_outputs_requested') is not True):
            raise ValueError('Batched prefill scope differs')
    expected = (metrics['prompt_tokens'] + width - 1)//width + metrics['generated_tokens'] - (reason == 'output_token_limit')
    if checkpoint_validation is not None:
        from model_checkpoint_result import checkpoint_process_geometry
        if width!=4:raise ValueError('Checkpoint replay accounting requires the qualified four-token path')
        expected=len(checkpoint_process_geometry(result,checkpoint_validation))
    if delta['process_calls'] != expected or delta['process_ns'] <= 0:
        raise ValueError('Completed decode call count differs')
    if not delta['source_chunks'] or delta['source_chunks'] != delta['source_completed_windows']:
        raise ValueError('A measured source window lacks completion')
    source_ns = sum(delta[k] for k in ('source_headroom_ns', 'source_handle_ns',
                                     'source_read_ns', 'source_consumer_ns'))
    decode_ns = delta['process_ns'] + delta['synchronize_ns']
    if delta['source_read_ns'] <= 0 or source_ns > decode_ns:
        raise ValueError('Source intervals exceed their enclosing decode interval')
    return dict(delta=delta, measured_source_wall_fraction=source_ns / decode_ns,
                GPU_compute_time_qualified=False,
                deliberate_state_validation_replays_included=checkpoint_validation is not None)
