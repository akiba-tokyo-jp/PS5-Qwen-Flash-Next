#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire an archived fixture input after its positive ordinary process exit."""
import argparse
import json
from pathlib import Path, PurePosixPath

from build_performance_quantizer import record
from compact_case_integrity_markers import compact
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, current_files, digest_expression, lan_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'completion', 'linked', 'compact-marker-control', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--protected-plan', type=Path, action='append', required=True)
    parser.add_argument('--execute-prepared', action='store_true')
    args = parser.parse_args()
    done, linked = load(args.completion), load(args.linked)
    native = load(done['native']['path'])
    package = load(done['package']['path'])
    need(done['completed'] and done['ordinary_exit_observed'] and
         done['current_seven_restored_and_native_hashed'] and not done['unknown_completion'] and
         package['relink'] == record(args.linked) and record(done['native']['path']) == done['native'] and
         native['completed'] and native['all_source_IO_completed'] and
         native['all_case_resources_positively_retired'] and not native['unknown_completion'] and
         native['model_loads'] == 0, 'Bind an exact archived fixture to its positive ordinary exit')
    pack = linked['component_pack']
    local, application = pack['local'], pack['application_path']
    need(record(local['path']) == local and 0 < local['bytes'] <= 128 << 20 and
         application == '/app0/qwen-runtime/paired-Down-' + local['sha256'][:24] + '.bin',
         'Only an exact archived Down fixture input is eligible')
    state_path = args.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('CPU_source_seal_owner'),
         'Require positive idle ownership before this new cleanup scope')
    references = [args.current / name for name in ('deployment.private.json', 'qwen-runtime/app.json',
        'qwen-runtime/development.json', 'provenance/model-source-plan.private.json',
        'provenance/protected-model-source-plan.private.json', 'provenance/required-bundle-inputs.private.json')]
    references += args.protected_plan
    basename = PurePosixPath(application).name
    need(all(basename not in path.read_text(encoding='utf-8') for path in references),
         'A selected or pending model references this component; retain it')
    selected = current_files(args.current)
    report = dict(done['native'], remote=PHYSICAL + '/qwen-runtime/plan-' + native['run_id'] + '.json')
    target = dict(local, remote=PHYSICAL + application[5:], alias=ALIAS + application[5:])
    facts = dict(target=target, report=report, completion=record(args.completion), linked=record(args.linked),
                 protected_plans=[record(path) for path in references], selected=selected, boot=state['current_boot'],
                 source_owner=state.get('source_publication_owner'), PC_original_preserved=True,
                 recursive_operations=0, source_model_files_removed=0)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        context = '#define CASE_COMPLETED_FILE_KIND "component_input"\n#define CASE_COMPLETED_FILE_LABEL "COMPONENT_INPUT"\n'
        for key, value in (('PATH', target['remote']), ('ALIAS', target['alias']), ('SHA256', target['sha256'])):
            context += '#define CASE_ACTIVATION_' + key + ' ' + json.dumps(value) + '\n'
        context += '#define CASE_ACTIVATION_BYTES ' + str(target['bytes']) + 'ULL\n'
        context += 'static int case_completed_activation_reports_valid(void){return ' + digest_expression(report) + ';}\n'
        context += '#include "activation_capture_retire.h"\n'
        context += 'static int case_retire_completed_images(int*calls){return case_retire_activation(calls);}\n'
        plan = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images',
                     args.out / 'native', completed_images_context=context)
        plan = compact(plan, args.out / 'native', args.compact_marker_control)
        save(args.out / 'intent.private.json', dict(facts, native_plan=record(args.out / 'native/plan.private.json'),
                                                  source=record(Path(__file__))))
        print(json.dumps(dict(prepared=True, files=1, bytes=local['bytes'], PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    need(all(intent[key] == value for key, value in facts.items()) and intent['source'] == record(Path(__file__)) and
         intent['native_plan'] == record(args.out / 'native/plan.private.json'), 'The exact cleanup admission changed')
    plan = load(args.out / 'native/plan.private.json')
    state['CPU_source_seal_owner'] = dict(plan=intent['native_plan'], phase='retire-closed-component-input',
                                         ordinary_helper_completion_pending=True, GPU_calls=0, title_launches=0)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    result = completed_operation(lan_module(), plan, args.out / 'native')
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and
         result['operation_calls'] == 1 and
         b'COMPONENT_INPUT_RETIRED both_namespaces_absent=1' in Path(result['raw']['path']).read_bytes(),
         'Require exact unlink, restored directory owner, both aliases absent and positive current-file hashes')
    save(args.out / 'result.private.json', dict(completed=True, native=result, retired_files=1,
         retired_bytes=local['bytes'], PC_original_preserved=True, current_seven_native_hashes_unchanged=True,
         runtime_directory_owner_restored=True, RAM_gain_claimed=False))
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == intent['native_plan'], 'Never clear another helper owner')
    state.pop('CPU_source_seal_owner')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, retired_files=1, retired_bytes=local['bytes'], RAM_gain_claimed=False)))


if __name__ == '__main__':
    main()
