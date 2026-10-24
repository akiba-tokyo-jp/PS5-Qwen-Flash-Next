#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate completed aggregate wall intervals without claiming GPU timestamps."""
FIELDS = {
    'source_bytes', 'source_chunks', 'source_completed_windows', 'source_headroom_ns',
    'source_handle_ns', 'source_read_ns', 'source_consumer_ns', 'process_calls',
    'process_ns', 'synchronize_ns', 'checkpoint_ns', 'work_guard_ns', 'stage_observer_ns'}


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


def validate_performance(record, result):
    schema = record.get('schema')
    if (schema not in ('ps5-qwen-completed-performance-v1', 'ps5-qwen-completed-performance-v2', 'ps5-qwen-completed-performance-v3', 'ps5-qwen-completed-performance-v4') or
        record.get('process_includes_source_and_backend_work') is not True or
        record.get('GPU_timestamp_queries') is not False or
        record.get('hot_path_logs_added') is not False or record.get('GPU_operations_added') is not False):
        raise ValueError('Performance measurement scope differs')
    delta = record.get('delta', {})
    fields = FIELDS | ({'source_parallel_batches'} if schema.endswith('v2') else
        {'source_pipeline_batches', 'source_worker_read_ns', 'source_worker_dispatch_ns'} if schema.endswith(('v3','v4')) else set())
    if schema.endswith('v4'):
        fields |= {'source_parallel_batches','source_coalesced_batches','source_selected_serial_batches',
                   'source_physical_read_bytes','source_physical_read_calls'}
    if set(delta) != fields or any(type(v) is not int or not 0 <= v < 2**63 for v in delta.values()):
        raise ValueError('Invalid completed performance counters')
    if schema.endswith('v2') and (record.get('source_read_ns_is_batch_wall_time') is not True or
        record.get('maximum_parallel_source_reads') != 2 or
        not 0 < delta['source_parallel_batches'] <= delta['source_chunks'] // 2):
        raise ValueError('Parallel reads lack bounded completed batch evidence')
    if schema.endswith('v3') and (record.get('source_read_ns_is_producer_wait_time') is not True or
        record.get('maximum_parallel_source_reads') != 1 or record.get('worker_times_overlap_consumers') is not True or
        not 0 < delta['source_pipeline_batches'] <= delta['source_chunks'] // 2 or delta['source_worker_read_ns'] <= 0):
        raise ValueError('Source pipelining lacks single-read completion evidence')
    if schema.endswith('v4') and (record.get('source_read_ns_is_producer_wait_time') is not True or
        record.get('maximum_parallel_source_reads') != 2 or record.get('file_range_schedule_enabled') is not True or
        record.get('physical_read_bytes_include_alignment') is not True or
        delta['source_physical_read_bytes'] < delta['source_bytes'] or
        delta['source_physical_read_calls'] != delta['source_chunks']-delta['source_coalesced_batches'] or
        delta['source_selected_serial_batches'] != delta['source_pipeline_batches'] or
        delta['source_parallel_batches']+delta['source_coalesced_batches']+delta['source_pipeline_batches'] > delta['source_chunks']//2):
        raise ValueError('Selected source scheduling lacks exact bounded completion evidence')
    metrics = result['metrics']
    reason = result['stop_reason']
    if reason not in ('end_of_generation', 'output_token_limit'):
        raise ValueError('Performance requires completed generation')
    expected = metrics['prompt_tokens'] + metrics['generated_tokens'] - (reason == 'output_token_limit')
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
                GPU_compute_time_qualified=False)
