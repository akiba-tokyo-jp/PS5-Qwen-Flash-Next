#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record an exited GGML case without converting missing success logs into GPU completion."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load, need, save


def exact(row):
    need(record(row['path']) == row, 'A bound classification input changed')
    return load(row['path'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'case', 'archive', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    case = load(a.case / 'plan.private.json')
    first = load(a.case / 'observed-first.private.json')
    restored = load(a.case / 'process-exited-restoration/result.private.json')
    archive = load(a.archive)
    stages_path = a.case / 'observed-stages.private.log'
    stages = stages_path.read_text().splitlines()
    need(case['mode'] == 'GPU' and first['run_id'] == case['run_id'] and
         first['candidate_SELF_sha256'] == case['SELF']['sha256'] and restored['completed'] and
         restored['native_process_exit_observed'] and restored['exited_PID'] == first['pid'] and
         restored['exact_current_seven_restored_and_native_hashed'] and not restored['ordinary_exit_claimed'],
         'The exact accepted case, observed exit and selected-file restoration are required')
    need(archive['completed'] and archive['closed_owner_PID'] == first['pid'] and
         archive['whole_native_and_host_SHA256_equal'] and
         record(archive['archived_log']['path']) == archive['archived_log'], 'Complete closed driver journal required')
    journal = Path(archive['archived_log']['path']).read_text()
    need(journal.startswith('QWEN_NATIVE_LOG_READY pid=' + str(first['pid']) + ' ') and
         stages[-1] == 'IQ2_Down_GGML_graph_before_native_call' and
         'IQ2_Down_GGML_graph_positively_completed' not in stages and
         stages[-2] == 'native_driver_checkpoint_completed_producer_retained',
         'Only the observed first-call exit with its preceding positive checkpoint is classified')
    package = exact(case['package'])
    linked = exact(package['relink'])
    need(linked['GGML_carrier_ABI'] and linked['maximum_GGML_graphs'] == 12 and
         record(linked['artifact']['path']) == linked['artifact'], 'The actual failed GGML ELF must remain exact')
    executable = ELF(Path(linked['artifact']['path']))
    need(executable.symbol_data('ps5_ai_native_journal_debug_enabled') == bytes.fromhex('31c0c3'),
         'The actual executable must contain the observed disabled routine-success logging function')
    allocations = re.findall(r'RETURN perBO_AllocateDirect serial=(\d+) rc=0x00000000 physical=\d+ canary=1 known_owner=1', journal)
    mappings = re.findall(r'RETURN perBO_MapDirect serial=(\d+) rc=0x00000000 pointer=\w+ canary=1 known_mapping=1 placement_valid=1 GPU_readback_proven=0', journal)
    need(allocations == mappings == ['1', '2', '3'], 'Every observed allocation/map pair must have returned')
    state = load(a.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         state['unknown_completion'] and state['GPU_retirement_readmission_pending'] and
         state['active_successful_native_case']['run_id'] == case['run_id'],
         'Keep the restored console explicitly pending; classification does not grant readmission')
    save(a.out, dict(completed=True, case=record(a.case / 'plan.private.json'),
        restoration=record(a.case / 'process-exited-restoration/result.private.json'),
        archive=record(a.archive), stages=record(stages_path), actual_ELF=linked['artifact'],
        failed_scope='Q3 first actual GGML carrier graph', native_passed=False,
        submitted_GGML_graph_calls=1, positively_completed_GGML_graph_calls=0,
        previous_quiet_checkpoint_positively_observed=True, returned_allocation_map_pairs=3,
        routine_success_records_disabled_in_actual_ELF=True, submission_count_recoverable_from_journal=False,
        zero_submissions_claimed=False, post_call_GPU_completion_qualified=False,
        process_exit_cause_proved=False, ordinary_native_exit_claimed=False,
        selected_P1_seven_files_restored_and_native_hashed=True, unknown_completion=True,
        GPU_readmission_granted=False, repeat_launch_permitted=False, PS5_operations=0,
        full_model_quality_or_speed_qualified=False))
    print(json.dumps(dict(completed=True, native_passed=False, GPU_readmission_granted=False, PS5_operations=0)))


if __name__ == '__main__':
    main()
