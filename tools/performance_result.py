#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate completed aggregate wall intervals without claiming GPU timestamps."""
FIELDS = {
    'source_bytes', 'source_chunks', 'source_completed_windows', 'source_headroom_ns',
    'source_handle_ns', 'source_read_ns', 'source_consumer_ns', 'process_calls',
    'process_ns', 'synchronize_ns', 'checkpoint_ns', 'work_guard_ns', 'stage_observer_ns'}


def validate_performance(record, result):
    if (record.get('schema') != 'ps5-qwen-completed-performance-v1' or
        record.get('process_includes_source_and_backend_work') is not True or
        record.get('GPU_timestamp_queries') is not False or
        record.get('hot_path_logs_added') is not False or record.get('GPU_operations_added') is not False):
        raise ValueError('Performance measurement scope differs')
    delta = record.get('delta', {})
    if set(delta) != FIELDS or any(type(v) is not int or not 0 <= v < 2**63 for v in delta.values()):
        raise ValueError('Invalid completed performance counters')
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
