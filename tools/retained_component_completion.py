#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit ordinary close of the exact positively idle retained component owner."""
from pathlib import Path
from build_performance_quantizer import record
from start_success_route import load, need

STAGE = b'paired_Down_native_GPU_completed_idle_device_retained_waiting_for_ordinary_close'


def validate_terminal(terminal):
    if terminal.get('GGML_carrier_ABI') is True:
        from iq2_down_ggml_completion import validate_terminal as validate_GGML
        return validate_GGML(terminal)
    need(terminal['completed'] and terminal['all_outputs_passed'] and not terminal['unknown_completion'] and
         terminal['native_PS5'] and terminal['model_loads'] == 0 and
         not terminal['all_GPU_resources_positively_retired'] and terminal['all_case_resources_positively_retired'] and
         terminal['all_source_IO_completed'] and terminal['IO_journal_closed'],
         'All component work and I/O must return before retaining the idle device')
    cases = terminal['cases']
    need(len(cases) == 24 and {(x['layer'], x['width'], x['workgroup']) for x in cases} ==
         {(l, w, g) for l in (0, 23, 47) for w in (1, 2, 30, 32) for g in (64, 128)} and
         all(x['positive_fence'] and x['all_case_resources_retired'] and x['all_outputs_passed'] and
             x['canaries_exact'] and x['mismatches'] == 0 and x['Vulkan_dispatches'] == 1 for x in cases),
         'All twenty-four distinct native reference cases must positively retire')
    owner = terminal['retained_completed_device']
    need(owner['held'] and owner['device'] and owner['instance'] and owner['epoch'] > 0 and
         owner['driver_used_bytes'] <= owner['driver_reserved_bytes'] and not owner['global_capacity_measured'] and
         owner['device_destroy_calls'] == owner['driver_retire_calls'] == owner['post_completion_GPU_operations'] == 0 and
         owner['ordinary_process_close_required'], 'The completed device and actual backing remain owned until ordinary close')
    return owner


def validate_close(close, selected):
    package = load(close['retained_component_package']['path'])
    need(record(close['retained_component_package']['path']) == close['retained_component_package'] and
         package['SELF']['sha256'] == selected[0]['sha256'], 'The exact installed component SELF is required')
    relink = load(package['relink']['path'])
    need(record(package['relink']['path']) == package['relink'] and relink['completed'] and
         relink['paired_down_carrier'] and relink['retained_idle_device_until_ordinary_close'] and
         relink['retained_device_controls'] == 19, 'The qualified source-bound retained-device adapter is required')
    if relink.get('GGML_carrier_ABI'):
        need(relink['GGML_operator_linked'] and relink['maximum_GGML_graphs']==12 and relink['backend_free_calls']==0 and
             Path(relink['source']['path']).name=='iq2_down_ggml_fixture.private.cpp',
             'The finite GGML adapter and retained live backend must be source bound')
    for row in (relink['source'], *[x for x in relink['inputs_before'] if Path(x['path']).name in
                ('paired_down_native_support.h', 'retained_completed_device.h', 'native_paired_carrier_adapter.py')]):
        need(record(row['path']) == row, 'A qualified lifetime source changed')
    reports = close['reports']
    for row in reports:
        need(record(row['path']) == {k: row[k] for k in ('path', 'bytes', 'sha256')}, 'A captured completion report changed')
    first, terminal = load(reports[0]['path']), load(reports[1]['path'])
    need(bool(terminal.get('GGML_carrier_ABI'))==bool(relink.get('GGML_carrier_ABI')),
         'The actual terminal topology must match the compiled component')
    validate_terminal(terminal)
    need(first['pid'] == terminal['pid'] == close['pid'] and first['run_id'] == terminal['run_id'] and
         first['candidate_SELF_sha256'] == terminal['candidate_SELF_sha256'] == selected[0]['sha256'] and
         Path(reports[2]['path']).read_bytes().splitlines()[-1] == STAGE,
         'The exact same owner, SELF, run and final CPU-only stage are required')
    return True
