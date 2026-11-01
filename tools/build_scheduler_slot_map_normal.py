#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the actual normal app only after a positive matched model comparison."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from expert_q4 import record, write_json
from scoped_native_variant import link, seal

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('normal', 'model', 'analysis', 'workspace', 'cache', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean implementation revision required'
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    analysis = json.loads(args.analysis.read_text())
    assert analysis['completed'] and analysis['internal_comparison_qualifies']
    assert analysis['all_full_F32_routes_tokens_exact'] and analysis['identical_source_demand'] and analysis['fixed_semantic_tasks_passed']
    for row in analysis['evidence']: assert record(row['path']) == row
    model = json.loads(args.model.read_text())
    normal = copy.deepcopy(json.loads(args.normal.read_text()))
    parent = json.loads(Path(model['source_parent']['path']).read_text())
    old_cache = next(x for x in normal['link_command'] if Path(x).name == 'cache.o')
    assert old_cache in parent['link_command'], 'Actual installed cache provider must match the compared model control'
    cache_command = model['scheduler_slot_maps']['commands']['cache']
    cache_object = cache_command[cache_command.index('-o') + 1]
    scheduler_command = model['scheduler_slot_map_backend']['command']
    scheduler_object = scheduler_command[scheduler_command.index('-o') + 1]
    old_scheduler = next(x for x in normal['link_command'] if Path(x).name == 'ggml-backend.cpp.o')
    normal['link_command'] = [cache_object if x == old_cache else scheduler_object if x == old_scheduler else x
                              for x in normal['link_command']]
    normal['inputs_before'] += active_link_inputs(model) + [record(args.normal), record(args.model), record(args.analysis)]
    normal['expert_q2_model']['actual_cache'] = model['scheduler_slot_maps']['actual_sources']['cache']
    normal['routing_sharing']['commands'][1] = cache_command
    normal['routing_sharing']['actual_sources']['cache'] = model['scheduler_slot_maps']['actual_sources']['cache']
    args.out.mkdir(parents=True, exist_ok=False)
    parent_path = args.out / 'normal-provider-parent.private.json'; write_json(parent_path, normal)
    command = normal['compile_commands'][0]
    entry = '#include "scheduler_slot_maps.h"\n' + Path(command[command.index('-c') + 1]).read_text()
    entry = once(entry, 'int main(int argc, char ** argv) {',
                 'int main(int argc, char ** argv) {\n    qwen_app::scheduler_slot_map_reuse=true;')
    entry = once(entry, '            std::uint64_t io_before[4]{};',
                 '            const auto scheduler_maps_before=qwen_app::scheduler_slot_map_counts;\n            std::uint64_t io_before[4]{};')
    entry = once(entry, '            row["bundled_Experts"]=',
                 '            {Json delta=Json::array();for(unsigned j=0;j<10;++j)delta.push_back(qwen_app::scheduler_slot_map_counts[j]-scheduler_maps_before[j]);row["scheduler_slot_map_delta"]=delta;row["scheduler_slot_map_reuse_enabled"]=qwen_app::scheduler_slot_map_reuse.load();}\n            row["bundled_Experts"]=')
    entry = once(entry, '        write_fresh_report(startup.admission_report,{{"four_next",four_next_report()}',
                 '        write_fresh_report(startup.admission_report,{{"scheduler_slot_map_counts",qwen_app::scheduler_slot_map_counts},{"scheduler_slot_map_reuse_enabled",qwen_app::scheduler_slot_map_reuse.load()},{"four_next",four_next_report()}')
    result, jobs, sources = link(parent_path, args.out,
        dict(entry=(command + ['-I', str(ROOT / 'native/app')], entry)),
        [Path(__file__), ROOT / 'native/app/scheduler_slot_maps.h'])
    result['scheduler_slot_map_normal'] = dict(actual_sources=sources, commands=jobs,
        application_source_revision=revision, model_analysis=record(args.analysis),
        exact_original_normal_parent=record(args.normal), same_original_driver_and_GPU_provider=True,
        selected_path_counters=True, no_live_address_rebinding=True,
        original_normal_external_qualification_required=True, production_adopted=False)
    seal(result, args.workspace, args.cache, args.out)
    write_json(args.out / 'core-safety.private.json', dict(completed=True, host_source_and_link_checks_only=True,
        actual_model_comparison_passed=True, normal_qualification_claimed=False, PS5_operations=0, CI_runs=0))
    print(json.dumps(dict(completed=True, source_revision=revision, normal_qualification_claimed=False)))

if __name__ == '__main__': main()
