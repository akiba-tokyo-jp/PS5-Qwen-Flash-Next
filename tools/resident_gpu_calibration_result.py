#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate one completed empty-backend measurement; never admit model work."""
import re


PHASES = (
    'GPU_initializer_before', 'GPU_initializer_frontend_returned',
    'GPU_initializer_registry_returned', 'GPU_initializer_device_returned',
    'GPU_initializer_backend_returned', 'GPU_initializer_empty_queue_completed',
    'GPU_initializer_backend_retired_no_model_sources_started',
)


def review(report, trace, binding):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(report.get('schema') == 'ps5-qwen-resident-GPU-initialization-calibration-result-v1', 'Wrong terminal schema')
    require(type(binding.get('pid')) is int and binding['pid'] > 0 and
            isinstance(binding.get('run_id'), str) and re.fullmatch('[0-9a-f]{32}', binding['run_id']), 'Exact owner binding required')
    require(type(report.get('pid')) is int and report['pid'] == binding['pid'] and
            type(report.get('run_id')) is str and report['run_id'] == binding['run_id'], 'Terminal owner differs')
    for key in ('completed', 'backend_instance_positively_synchronized_and_retired',
                'source_workers_stopped', 'ordinary_OS_close_required',
                'global_device_lifetime_retained_until_ordinary_OS_close'):
        require(report.get(key) is True, 'Missing positive completion: ' + key)
    for key in ('model_loaded', 'unknown_completion', 'postload_model_device_ledger_enabled',
                'whole_model_CPU_preflight_repeated'):
        require(report.get(key) is False, 'Unexpected scope: ' + key)
    for key in ('model_loads', 'model_requests', 'graph_computes', 'tensor_payload_allocations',
                'model_tensor_API_calls', 'source_workers_started', 'whole_model_metadata_files',
                'source_chunks', 'source_completed_windows'):
        require(type(report.get(key)) is int and report[key] == 0, 'Unexpected work: ' + key)
    for key, value in (('backend_instances', 1), ('selected_required_pages', 1410),
                       ('selected_total_above_kernel_minimum_pages', 512),
                       ('ordinary_operational_floor_pages', 1154), ('sampled_phase_component_pages', 245)):
        require(type(report.get(key)) is int and report[key] == value, 'Unexpected policy component: ' + key)
    require(trace.get('schema') == 'ps5-qwen-resident-startup-memory-v1' and
            trace.get('global_snapshots_not_exclusive_attribution') is True, 'Complete sampled trace required')
    samples = trace['samples']
    require(isinstance(samples, list) and 7 <= len(samples) <= 64, 'Finite complete samples required')
    previous = -1
    for row in samples:
        require(type(row.get('ns')) is int and row['ns'] >= previous, 'Trace time moved backwards')
        previous = row['ns']
        require(type(row.get('kernel_minimum_pages')) is int and row['kernel_minimum_pages'] == 898 and
                type(row.get('kernel_reserved_pages')) is int and row['kernel_reserved_pages'] == 206 and
                type(row.get('kernel_free_pages')) is int and row['kernel_free_pages'] >= 1154,
                'Ordinary operational formula was not retained')
    gpu = [row for row in samples if row['phase'].startswith('GPU_initializer_')]
    require(tuple(row['phase'] for row in gpu) == PHASES, 'Missing, duplicate or reordered completed GPU boundary')
    require(report['entry_free_pages'] == gpu[0]['kernel_free_pages'] >= 1410, 'Entry price did not pass')
    return dict(completed_empty_backend_lifetime=True,
                sampled_global_GPU_interval_decline_pages=gpu[0]['kernel_free_pages'] - gpu[-1]['kernel_free_pages'],
                maximum_sampled_global_decline_pages=max(0, gpu[0]['kernel_free_pages'] - min(row['kernel_free_pages'] for row in gpu)),
                elapsed_ns=gpu[-1]['ns'] - gpu[0]['ns'],
                samples=gpu, model_execution_admitted=False,
                full_model_VM_bound_established=False, speedup_qualified=False)
