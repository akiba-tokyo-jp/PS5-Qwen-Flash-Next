#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify only the source-bound shader barrier after a positive pre-graph backend synchronization.

This does not recover a submission count from suppressed logs. The first graph
has no usable compute pipeline: CPU shader admission is mandatory and its flag
is permanently false in this exact image. The preceding backend synchronize
drains transfers; no backend operation intervenes before the first graph.
"""
import argparse
import json
from pathlib import Path
import re
import struct

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load, need, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'failure', 'audit', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--record-known-barrier',action='store_true',help='Record known prior completion while retaining the independent capacity gate')
    a = p.parse_args()
    failure = load(a.failure)
    audit = load(a.audit)
    need(failure['completed'] and not failure['native_passed'] and
         failure['positively_completed_GGML_graph_calls'] == 0 and
         failure['submitted_GGML_graph_calls'] == 1 and
         failure['previous_quiet_checkpoint_positively_observed'] and
         failure['returned_allocation_map_pairs'] == 3 and
         audit['completed'] and audit['actual_ELF'] == failure['actual_ELF'],
         'Only the exact first-call exit and complete actual-image review are admitted')
    image = failure['actual_ELF']
    need(record(image['path']) == image, 'The actual exited image changed')
    e = ELF(Path(image['path']))
    prepare=e.symbol_data('qwen_app_prepare_shader_code')
    start=e.symbols['qwen_app_prepare_shader_code']['value']
    need(prepare[20:23]==bytes.fromhex('0fb605') and prepare[27:31]==bytes.fromhex('3c010f85') and
         start+27+struct.unpack_from('<i',prepare,23)[0]==audit['flag_address'],
         'The exact mandatory admission must reject a flag other than one before any decoding or shader-module creation')
    refs = audit['all_text_flag_references']
    need(audit['initially_zero_PT_LOAD_tail'] and len(refs) == 2 and
         all('movzbl' in r['instruction'] for r in refs) and
         {r['function'].split('<', 1)[1].split('>', 1)[0] for r in refs} ==
             {'qwen_app_register_additional_shader', 'qwen_app_prepare_shader_code'} and
         not any('initialize_native_shader_assets' in n or 'initialize_native_shader_file' in n for n in e.symbols),
         'The actual shader-admitted flag must have only the two observed readers and no initialization implementation')
    raw = Path(image['path']).read_bytes()
    offset = struct.unpack_from('<Q', raw, 40)[0]
    stride, count = struct.unpack_from('<HH', raw, 58)
    need(stride == 64, 'Complete ELF64 sections required')
    for i in range(count):
        section = struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * stride)
        if section[1] != 4:
            continue
        need(section[9] == 24, 'Exact RELA entries required')
        for at in range(section[4], section[4] + section[5], 24):
            destination, info, addend = struct.unpack_from('<QQq', raw, at)
            need(destination != audit['flag_address'] and addend != audit['flag_address'],
                 'The uninitialized flag may not escape through a relocated address or loader write')
    need(record(audit['pipeline']['path']) == audit['pipeline'] and
         len(audit['early_pipeline_calls_to_wrapped_admission']) == 1 and
         audit['early_pipeline_calls_to_wrapped_admission'][0]['resolved_target'] ==
             e.symbols['__wrap_qwen_app_prepare_shader_code']['value'],
         'Every fresh compute pipeline must enter the actual mandatory CPU admission before shader-module creation')
    case = load(failure['case']['path'])
    package = load(case['package']['path'])
    linked = load(package['relink']['path'])
    source = linked['source']
    support=Path(source['path']).parent/'paired_down_native_support.h'
    need(record(source['path']) == source, 'The exact linked first-graph source changed')
    text = Path(source['path']).read_text()
    barrier = ('ggml_backend_synchronize(fixture_backend);qwen_native_driver_checkpoint();\n'
        '    native_guard(31);qwen_native_stage("IQ2_Down_GGML_graph_before_native_call");\n'
        '    native_require(ggml_backend_graph_compute(fixture_backend,graph)==GGML_STATUS_SUCCESS,')
    need(barrier in text and text.count('ggml_backend_graph_compute(') == 1 and
         'auto*y=ggml_mul_mat_id(ctx,view,x,indices);' in text and
         'ggml_build_forward_expand(graph,y);' in text and
         not any(s in text for s in ('vkQueueSubmit', 'vkCmdDispatch', 'vkCmdCopy', 'std::thread')),
         'Only the first view/matmul graph after a drained backend may use this shader barrier')
    stages = Path(failure['stages']['path']).read_text().splitlines()
    need(stages[-4:] == ['native_driver_before_positive_device_idle', 'native_driver_device_idle_completed',
        'native_driver_checkpoint_completed_producer_retained', 'IQ2_Down_GGML_graph_before_native_call'],
        'The exact preceding backend synchronization and driver quiet checkpoint must have positively returned')
    state = load(a.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         state['unknown_completion'] and state['GPU_retirement_readmission_pending'] and
         state['active_successful_native_case']['run_id'] == case['run_id'],
         'The selected files must be restored while capacity readmission is still pending')
    save(a.out, dict(completed=True, failure=record(a.failure), audit=record(a.audit),
        actual_ELF=image, source=source, support=record(support), package=case['package'], stages=failure['stages'],
        current_boot=state['current_boot'], run_id=case['run_id'],
        prior_backend_synchronization_and_driver_checkpoint_positive=True,
        mandatory_shader_admission_flag_permanently_false=True,
        fresh_compute_pipeline_creation_blocked_before_shader_module=True,
        first_graph_source_ops=['VIEW', 'MUL_MAT_ID'], graph_ops_observed_natively=False,
        no_intervening_backend_operation_after_positive_synchronization=True,
        post_checkpoint_queue_submissions=0, source_bound_pre_dispatch_barrier=True,
        submission_count_recovered_from_journal=False, overall_zero_submissions_claimed=False,
        all_preexisting_submitted_work_completed_at_prior_checkpoint=True,
        process_exit_cause_proved=False, ordinary_exit_claimed=False, BO_retirement_claimed=False,
        only_capacity_CPU_readmission_permitted=True, GPU_execution_permitted=False, PS5_operations=0))
    if a.record_known_barrier:
        state.update(state='source_bound_shader_barrier_current_restored_capacity_pending',unknown_completion=False)
        state['source_classified_shader_barrier']=record(a.out)
        need(state['GPU_retirement_readmission_pending'], 'Recording the known barrier must not grant GPU capacity readmission')
        (a.current/'active-console.private.json').write_text(json.dumps(state,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(completed=True, source_bound_pre_dispatch_barrier=True,
        capacity_CPU_readmission_only=True, PS5_operations=0)))


if __name__ == '__main__':
    main()
