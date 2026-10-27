#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check a finite raw-buffer capacity result; no inference or launch permission."""
from resident_gpu_calibration_result import review as review_initializer

SIZES = (2147483648, 2147483648, 2147483648, 2147483648, 165170688)


def review(report, trace, binding):
    def require(ok, message):
        if not ok:
            raise ValueError(message)

    capacity = report.get('buffer_capacity_measurement')
    require(isinstance(capacity, dict) and capacity.get('completed') is True, 'Complete allocation record required')
    terminal = dict(report); terminal.pop('buffer_capacity_measurement')
    initializer = review_initializer(terminal, trace, binding)
    allocated = capacity.get('allocated_buffers')
    require(type(allocated) is int and 0 <= allocated <= 5, 'Finite allocation count required')
    require(capacity.get('all_five_allocated') is (allocated == 5), 'Full prefix count differs')
    require(capacity.get('requested_live_peak_bytes') == sum(SIZES[:allocated]), 'Exact original-resident payload prefix required')
    require(capacity.get('buffer_free_callbacks_returned') == allocated and
            capacity.get('live_calibration_buffer_objects') == 0 and
            capacity.get('queue_submissions') == capacity.get('model_tensors_created') == 0 and
            capacity.get('physical_backing_retained_for_ordinary_OS_close') is True,
            'Positive metadata retirement and retained physical ownership required')
    rows = capacity['observations']
    require(len(rows) in (allocated, allocated + 1) and len(rows) <= 5, 'Allocation return conservation differs')
    for i, row in enumerate(rows):
        require(type(row.get('ordinal')) is int and row['ordinal'] == i and
                row.get('requested_bytes') == SIZES[i] and row.get('allocation_returned') is True and
                row.get('allocation_succeeded') is (i < allocated), 'Actual allocation result differs')
        require(type(row.get('free_before')) is int and row['free_before'] >= 1666 and
                type(row.get('free_after')) is int and row['free_after'] >= 1154,
                'Scoped before-call allowance or original operational formula failed')
    require(capacity['driver_owned_bytes_at_peak'] >= capacity['driver_owned_bytes_before'] + sum(SIZES[:allocated]) and
            capacity['driver_owned_bytes_after_callbacks'] == capacity['driver_owned_bytes_at_peak'],
            'Physical backing must remain accounted until ordinary OS close')
    require(capacity.get('terminal') == 'completed' if allocated == 5 else capacity.get('terminal') in
            ('selected_per_buffer_VM_allowance_refused', 'fresh_Direct_or_Flexible_capacity_refused', 'allocation_returned_null'),
            'Finite terminal reason differs')
    all_samples = [s for s in trace['samples'] if s['phase'].startswith(('GPU_initializer_', 'GPU_capacity_'))]
    initial = all_samples[0]['kernel_free_pages']
    return dict(completed_capacity_measurement=True, all_five_allocated=allocated == 5,
                allocated_buffers=allocated, requested_bytes=sum(SIZES[:allocated]),
                sampled_global_peak_decline_pages=max(0, initial - min(s['kernel_free_pages'] for s in all_samples)),
                initializer_and_allocation_interval_ns=initializer['elapsed_ns'],
                physical_backing_still_owned_before_normal_OS_close=True,
                exact_model_layout_qualified=False, model_load_context_budget_established=False,
                model_execution_admitted=False, speedup_qualified=False)
