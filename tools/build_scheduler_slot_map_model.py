#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a matched model comparison only after actual scheduler qualification."""
import argparse
import copy
import json
from pathlib import Path
from build_throughput_current import command
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import record, write_json
from scoped_native_variant import link, seal

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('parent', 'fixture', 'fixture-case', 'workspace', 'cache', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    result = json.loads((args.fixture_case / 'native-model-terminal.private.json').read_text())
    closed = json.loads((args.fixture_case / 'restored-complete.private.json').read_text())
    assert result['completed'] and result['GPU_graphs'] == 48 and result['actual_CPU_Vulkan_scheduler']
    assert result['all_I32_bytes_and_canaries_exact'] and result['live_address_changes'] == 0
    assert result['device_ledger_live_bytes'] == 0 and result['all_model_source_device_owners_positively_retired']
    assert closed['completed'] and not closed['unknown_completion']
    assert fixture['scheduler_slot_maps']['preallocation_contract'] and not fixture['scheduler_slot_maps']['callback_rebinding']
    parent = copy.deepcopy(json.loads(args.parent.read_text()))
    assert 'resident_slot_maps' not in parent
    args.out.mkdir(parents=True, exist_ok=False)
    scheduler_command = fixture['resident_slot_map_fixture']['commands']['scheduler']
    scheduler_object = scheduler_command[scheduler_command.index('-o') + 1]
    old = next(x for x in parent['link_command'] if Path(x).name == 'ggml-backend.cpp.o')
    assert parent['link_command'].count(old) == 1
    parent['link_command'] = [scheduler_object if x == old else x for x in parent['link_command']]
    proof_inputs = [record(args.fixture), record(args.fixture_case / 'native-model-terminal.private.json'),
                    record(args.fixture_case / 'restored-complete.private.json'), record(scheduler_object),
                    record(ROOT / 'native/app/scheduler_slot_maps.h')]
    for row in fixture['inputs_before']:
        if Path(row['path']).name == 'scheduler_slot_maps.h': assert record(row['path']) == row
    parent['inputs_before'] += proof_inputs
    parent['scheduler_slot_map_backend'] = dict(command=scheduler_command, original_backend=record(old),
                                               qualified_fixture=proof_inputs[:3])
    parent_path = args.out / 'qualified-scheduler-parent.private.json'; write_json(parent_path, parent)
    cache_command = command(parent, next(x for x in parent['link_command'] if Path(x).name == 'cache.o'))
    cache = '#include "scheduler_slot_maps.h"\n' + Path(cache_command[cache_command.index('-c') + 1]).read_text()
    cache = once(cache, '    std::vector<int32_t> ids;',
                 '    std::unique_ptr<qwen_app::SchedulerSlotMaps> scheduler_slot_maps;\n    std::vector<int32_t> ids;')
    cache = once(cache, '        if(resident_reuse_enabled){', '''        if(groups.size()==1&&groups[0].id>=0&&std::strncmp(ggml_backend_name(devices[groups[0].id].backend),"Vulkan",6)==0){
            std::vector<const ggml_tensor*> sources;for(const auto&layer:layers)sources.push_back(layer.slot_map);
            scheduler_slot_maps=std::make_unique<qwen_app::SchedulerSlotMaps>(devices[groups[0].id].backend,std::move(sources),groups[0].n_slots);
        }
        if(resident_reuse_enabled){''')
    cache = once(cache, '        ggml_backend_tensor_set_async(backend, dst, src->data, 0, ggml_nbytes(src));',
                 '        if(scheduler_slot_maps&&scheduler_slot_maps->publish(backend,unsigned(il),src,dst))return true;\n'
                 '        ggml_backend_tensor_set_async(backend, dst, src->data, 0, ggml_nbytes(src));')
    entry_command = parent['compile_commands'][0]
    entry = '#include "scheduler_slot_maps.h"\n' + Path(entry_command[entry_command.index('-c') + 1]).read_text()
    entry = once(entry, 'qwen_throughput::mode=arm?5:0;',
                 'qwen_throughput::mode=5;qwen_app::scheduler_slot_map_reuse=bool(arm);')
    entry = once(entry, '            const auto cpu_before=qwen_load::snapshot();',
                 '            const auto map_before=qwen_app::scheduler_slot_map_counts;\n            const auto cpu_before=qwen_load::snapshot();')
    entry = once(entry, '            row["phase"]=phase;',
                 '            const auto map_after=qwen_app::scheduler_slot_map_counts;Json map_delta=Json::array();for(unsigned j=0;j<10;++j)map_delta.push_back(map_after[j]-map_before[j]);row["scheduler_slot_map_delta"]=map_delta;row["scheduler_slot_map_reuse_enabled"]=bool(arm);\n            row["phase"]=phase;')
    old_scope = parent['GDN_model_comparison']['scope']
    scope = dict(old_scope, control_throughput_mode=5, candidate_throughput_mode=5,
                 scheduler_slot_map_comparison=True, both_arms_preallocated_maps=True,
                 no_live_address_rebinding=True, original_ID_download_and_cache_planning_preserved=True,
                 original_normal_external_qualification_required=True)
    entry = once(entry, literal(old_scope), literal(scope))
    result, jobs, sources = link(parent_path, args.out,
        dict(entry=(entry_command + ['-I', str(ROOT / 'native/app')], entry),
             cache=(cache_command + ['-I', str(ROOT / 'native/app')], cache)),
        [Path(__file__), ROOT / 'native/app/scheduler_slot_maps.h'])
    result['GDN_model_comparison']['scope'] = scope
    result['next_five_comparison']['scope'] = scope
    result['scheduler_slot_maps'] = dict(scope=scope, actual_sources=sources, commands=jobs,
        fixture_proof=proof_inputs[:3], preallocation_contract=True, callback_rebinding=False)
    seal(result, args.workspace, args.cache, args.out)
    write_json(args.out / 'core-safety.private.json', dict(completed=True, host_source_and_link_checks_only=True,
        actual_CPU_Vulkan_scheduler_fixture_passed=True, model_qualification_claimed=False,
        original_ID_sync_and_cache_planning_preserved=True, live_address_rebinding=False, PS5_operations=0, CI_runs=0))
    print(json.dumps(dict(completed=True, model_qualification_claimed=False)))

if __name__ == '__main__': main()
