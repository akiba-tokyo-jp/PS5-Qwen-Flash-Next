#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the pre-allocation scheduler fixture without changing the active engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import record, write_json
from scoped_native_variant import link, seal

ROOT = Path(__file__).resolve().parents[1]

def scheduler_provider(cache, out):
    manifest = json.loads((cache / 'build/predictive-model-io-3201/manifest.private.json').read_text())
    row = next(row for row in manifest['objects'] if row['source'] == 'ggml/src/ggml-backend.cpp')
    assert record(row['object']['path']) == row['object']
    recipes = json.loads(Path(manifest['original_compile_recipes']['path']).read_text())
    recipe = next(row for row in recipes if Path(row['file']).name == 'ggml-backend.cpp')
    source = Path(recipe['file']).read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha256(source).hexdigest() == manifest['sources']['ggml/src/ggml-backend.cpp']['normalized_sha256']
    isolated = out / 'isolated'
    target = isolated / 'ggml/src/ggml-backend.cpp'
    target.parent.mkdir(parents=True)
    target.write_bytes(source)
    patch = manifest['patches'][-1]
    assert record(patch['path']) == patch
    result = subprocess.run(['git', 'apply', '--include=ggml/src/ggml-backend.cpp', patch['path']],
                            cwd=isolated, capture_output=True, timeout=30,
                            env=dict(os.environ, GIT_CEILING_DIRECTORIES=str(out)))
    (out / 'scheduler-reconstruction.private.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest['sources']['ggml/src/ggml-backend.cpp']['patched_sha256']
    text = '#include "scheduler_slot_maps.h"\n' + target.read_text()
    text = once(text, '                            tensor_id_copy(src_id, cur_backend_id, c) = tensor_copy;',
                '                            qwen_app::bind_scheduler_slot_map(backend, src, tensor_copy, c);\n'
                '                            tensor_id_copy(src_id, cur_backend_id, c) = tensor_copy;')
    command = [word.replace('"', '') for word in shlex.split(row['command'], posix=False)]
    command[command.index('-o') + 1] = row['object']['path']
    command += ['-I', str(ROOT / 'native/app'), '-I', str(Path(recipe['file']).parent)]
    return command, text

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('parent', 'workspace', 'cache', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    parent = json.loads(args.parent.read_text())
    assert 'resident_slot_maps' not in parent
    args.out.mkdir(parents=True, exist_ok=False)
    scheduler_command, scheduler_text = scheduler_provider(args.cache, args.out)
    scope = dict(schema='ps5-qwen-scheduler-slot-map-fixture-v1', model_loads=0, requests=0,
                 GPU_graphs=48, HTTP_requests=0, VideoOut_starts=0, maximum_seconds=180,
                 actual_CPU_Vulkan_scheduler=True, preallocation_input_binding=True,
                 copy_callback_changes_addresses=False, all_I32_bytes_and_canaries_exact=True,
                 original_driver_and_shader_objects=True, automatic_retries=0, CI_runs=0)
    command = parent['compile_commands'][0]
    entry = '#include "scheduler_slot_maps_fixture.h"\n' + Path(command[command.index('-c') + 1]).read_text()
    entry = once(entry, literal(parent['GDN_model_comparison']['scope']), literal(scope))
    branch = '''        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty scheduler fixture ledger required");
        qwen_service::mode=69;qwen_frontier::mode=7;qwen_load_tail_select(true);
        auto checked=qwen_app::scheduler_slot_maps_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto live=qwen_app::native_model_device_stats();if(live.live)throw std::runtime_error("Scheduler fixture ledger remains live");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-resident-slot-map-fixture-result-v1"},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},{"all_owners_positively_retired",true},
            {"device_ledger_live_bytes",live.live},{"device_ledger_peak_bytes",live.peak},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("scheduler_slot_map_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''
    entry = once(entry, '        screen.state="loading original BF16 model";', branch + '        screen.state="loading original BF16 model";')
    result, jobs, sources = link(args.parent, args.out,
        dict(entry=(command + ['-I', str(ROOT / 'native/app')], entry),
             scheduler=(scheduler_command, scheduler_text)),
        [Path(__file__), ROOT / 'native/app/scheduler_slot_maps.h', ROOT / 'native/app/scheduler_slot_maps_fixture.h'])
    result['GDN_model_comparison']['scope'] = scope
    result['next_five_comparison']['scope'] = scope
    result['resident_slot_map_fixture'] = dict(scope=scope, actual_sources=sources, commands=jobs)
    result['scheduler_slot_maps'] = dict(scope=scope, preallocation_contract=True,
                                        callback_rebinding=False, failed57500_implementation_used=False)
    seal(result, args.workspace, args.cache, args.out)
    write_json(args.out / 'core-safety.private.json', dict(completed=True, host_source_and_link_checks_only=True,
        native_qualification_claimed=False, actual_scheduler_fixture=True, PS5_operations=0, CI_runs=0))
    print(json.dumps(dict(completed=True, native_qualification_claimed=False, GPU_graphs=48)))

if __name__ == '__main__':
    main()
