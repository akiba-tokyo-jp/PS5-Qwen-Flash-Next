#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen reinvesting rejected shared-Q4 savings on its actual captured routes."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from screen_cached_layer_runs import CPP
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'planner-proof', 'case', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    prior = load(a.planner_proof)
    need(prior['completed'] and prior['actual_three_request_native_cache_counters_reproduced'],
         'The qualified indexed-policy replay is required')
    # Authenticate the reused planner and policy sources, without rerunning its
    # old model trace, compiler controls, or the original native experiment.
    reused = [item for item in prior['inputs'] if Path(item['path']).name in
              ('planner.h', 'screen_cached_layer_runs.py', 'indexed_probation_policy.h',
               'decode_prefill_protection.h', 'expert_temporal_probation.h', 'expert_policy.h')]
    need(len(reused) == 6 and all(record(item['path']) == item for item in reused),
         'The exact planner implementation changed')
    terminal_path = a.case / 'native.result.private.json'
    terminal = load(terminal_path)
    sequence_path = a.case.parent / 'result.private.json'
    sequence = load(sequence_path)
    need(sequence['completed'] and sequence['scope'] == 'Q1' and
         sequence['all_ordinary_closes_and_exact_restores'], 'A completed Q1 ABBA is required')
    bindings = [item for item in sequence['cases']
                if item['case'] in (64281, 64282) and a.case.name == 'case-' + str(item['case'])]
    need(len(bindings) == 1 and bindings[0]['scope_events'] == [[1, 144, 22, 1]] * 3,
         'Exactly one actual144-tensor Q4 candidate case is required')
    authenticated = bindings[0]['native_terminal']
    need(record(authenticated['path']) == authenticated and
         record(terminal_path)['sha256'] == authenticated['sha256'],
         'The selected actual Q4 terminal must match its authenticated sequence record')
    need(terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and
         terminal['device_ledger_live_bytes'] == 0 and terminal['shared_Expert_weight_type'] == 'Q8_0',
         'The complete rejected-Q4 case and its legacy metadata require explicit binding')
    # The old entry carries Q8_0 in its metadata; source/layer geometry, not this
    # legacy field, authenticates the actual Q4 test in the completed ABBA proof.
    campaign = load(ROOT / 'docs/native-performance-comparisons-20261102.json')
    need(campaign['Q1']['tested_legacy_type_metadata_incorrect'] and
         campaign['Q1']['saved_device_weight_bytes'] == 117964800,
         'The independently recorded Q4 saving and metadata correction are required')
    traces, inputs = [], [record(a.planner_proof), record(sequence_path), authenticated, record(terminal_path), *reused,
                          record(Path(__file__)), record(ROOT / 'docs/native-performance-comparisons-20261102.json')]
    for ordinal in range(3):
        path = a.case / ('native-arm' + str(ordinal) + '.routes.private.bin')
        trace = load(path)
        need(trace['complete'] and not trace['capture_failed'] and trace['cache_slots'] == 3712 and
             trace['ordinal'] == ordinal and trace['pid'] == terminal['pid'] and trace['run_id'] == terminal['run_id'],
             'All three actual Q4 route traces are required')
        traces.append(trace)
        inputs.append(record(path))
    a.out.mkdir(parents=True, exist_ok=False)
    # Add64 slots, keep the existing global spare plane, and conservatively
    # reserve up to2MiB extra rounding for each of the three weight banks.
    raw_extra = 64 * (537600 + 537600 + 460800)
    conservative_extra = raw_extra + 3 * (2 << 20)
    saving = campaign['Q1']['saved_device_weight_bytes']
    need(conservative_extra < saving, 'New cache payload and rounding must fit the independently measured saving')
    header = next(item for item in reused if Path(item['path']).name == 'planner.h')
    source = CPP
    source = once(source, 'if(argc!=3)', 'if(argc!=4)')
    source = once(source, 'Json input;std::ifstream(argv[1])>>input;Json result=Json::array();',
                  'const int slots=std::stoi(argv[3]);if(slots!=3712&&slots!=3776)throw std::runtime_error("Exact cache scope required");'
                  'Json input;std::ifstream(argv[1])>>input;Json result=Json::array();')
    source = once(source, 'p.init(49,512,3712,48)', 'p.init(49,512,slots,48)')
    source = once(source, 'if(hits!=t["cache_hits"]||misses!=t["cache_misses"])',
                  'if(slots==3712&&(hits!=t["cache_hits"]||misses!=t["cache_misses"]))')
    cpp = a.out / 'reinvest.cpp'
    cpp.write_text(source, encoding='utf-8', newline='\n')
    data = a.out / 'Q4-routes.private.json'
    save(data, traces)
    exe = a.out / 'reinvest.exe'
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    command = [str(host / 'clang++.exe'), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
               '-I', str(Path(header['path']).parent), '-I', str(ROOT / 'native/app')]
    # Bind the same pinned vendor include used by the qualified compiler job.
    old_command = prior['commands'][0]
    vendor = next(Path(old_command[i + 1]) for i, value in enumerate(old_command[:-1])
                  if value == '-I' and Path(old_command[i + 1]).name == 'vendor')
    command += ['-I', str(vendor), str(cpp), '-o', str(exe)]
    commands = [command]
    for slots in (3712, 3776):
        commands.append([str(exe), str(data), str(a.out / (str(slots) + '.private.json')), str(slots)])
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''),
               TMP=str(a.out), TEMP=str(a.out))
    for index, job in enumerate(commands):
        run = subprocess.run(job, capture_output=True, timeout=60, env=env)
        (a.out / (str(index) + '.private.log')).write_bytes(run.stdout + run.stderr)
        need(run.returncode == 0, run.stderr.decode(errors='replace')[-3000:])
    before, after = (load(a.out / (str(slots) + '.private.json')) for slots in (3712, 3776))
    changes = [dict(ordinal=old['ordinal'], control_hits=old['hits'], control_misses=old['misses'],
                    additional_slots_hits=new['hits'], additional_slots_misses=new['misses'],
                    avoided_Expert_fills=old['misses'] - new['misses']) for old, new in zip(before, after)]
    need(len(changes) == 3 and all(old['ordinal'] == new['ordinal'] for old, new in zip(before, after)),
         'All ordinary cache conditions must remain aligned')
    result = dict(completed=True, source_inputs=inputs, commands=commands, actual_Q4_baseline_counters_exact=True,
                  original_cache_slots=3712, proposed_cache_slots=3776, shared_Q4_saved_bytes=saving,
                  additional_cache_payload_bytes=raw_extra, explicit_three_bank_rounding_allowance_bytes=3 * (2 << 20),
                  conservative_additional_cache_bytes=conservative_extra,
                  remaining_saved_bytes_before_other_geometry_changes=saving-conservative_extra,
                  conditions=changes, original_R1_trace_not_replayed=True,
                  fixed_captured_routes_only=True, cache_dependent_ranking_not_recomputed=True,
                  actual_expanded_buffer_layout_or_peak_allocation_not_qualified=True,
                  new_Q4_quality_or_model_decode_tok_s_measured=False, native_integration=False,
                  source_scope=prior['source_scope'], PS5_operations=0, production_adopted=False)
    save(a.out / 'result.private.json', result)
    print(json.dumps(dict(completed=True, actual_Q4_baseline_counters_exact=True, conditions=changes,
                          conservative_extra_bytes=conservative_extra, saving_bytes=saving, PS5_operations=0)))


if __name__ == '__main__':
    main()
