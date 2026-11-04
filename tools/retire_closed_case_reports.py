#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove exact console report copies after positive close and whole PC archival."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re

from build_performance_quantizer import record
from compact_case_integrity_markers import compact
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, current_files, lan_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'closures', 'compact-marker-control', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute-prepared', action='store_true')
    args = parser.parse_args()
    state_path = args.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('CPU_source_seal_owner'),
         'Only positively idle ownership may retire archived console reports')
    boot = state['current_boot']
    targets, proofs = {}, []
    for closure_record in load(args.closures):
        path = Path(closure_record['path'])
        need(record(path) == closure_record, 'A positive close receipt changed')
        closed, plan = load(path), load(path.parent / 'ordinary-close/plan.private.json')
        need(closed['completed'] and closed['ordinary_exit_observed'] and
             closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'] and
             closed['all_model_source_device_owners_positively_retired'] and closed['native_owners'] == 0 and
             plan['operation'] == 'close' and plan['close_admission']['completed'],
             'Every report cohort must have positive owner retirement and ordinary exit')
        proof = load(path.parent / 'ordinary-close/result.private.json')
        need(proof['completed'] and proof['helper_exited'] and proof['helper_files_removed'] and
             proof['operation_calls'] == 1, 'The exact close helper must have retired')
        proofs += [closure_record, record(path.parent / 'ordinary-close/plan.private.json'),
                   record(path.parent / 'ordinary-close/result.private.json')]
        for row in plan['close_admission']['reports']:
            remote = row['remote']
            name = PurePosixPath(remote).name
            need(str(PurePosixPath(remote).parent) == PHYSICAL + '/qwen-runtime' and
                 (re.fullmatch(r'plan-[0-9a-f]{32}\.json(?:\.arm[0-9]+\.(?:routes|result))?', name) or
                  re.fullmatch(r'entry-b' + str(boot[0]) + '-' + str(boot[1]) + r'-[0-9]+\.stages', name)) and
                 0 < row['bytes'] <= 8 << 20 and
                 record(row['path']) == {key: row[key] for key in ('path', 'bytes', 'sha256')},
                 'Only whole archived terminal/result/route/stage files may be removed')
            if remote in targets:
                need(targets[remote]['sha256'] == row['sha256'], 'Ambiguous archived report identity')
            targets[remote] = dict(row, alias=ALIAS + remote[len(PHYSICAL):])
    targets = list(targets.values())
    need(1 <= len(targets) <= 256, 'One finite unique archived report batch is required')
    selected = current_files(args.current)
    need(not {row['remote'] for row in selected}.intersection(row['remote'] for row in targets),
         'A current application file must never be a retirement target')
    facts = dict(targets=targets, proofs=proofs, closures=record(args.closures), selected=selected,
                 boot=boot, source_owner=state.get('source_publication_owner'),
                 PC_archives_preserved=True, recursive_operations=0, source_data_files_removed=0)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        context = 'struct ArchivedReport{const char*path;const char*alias;unsigned long long bytes;const char*sha256;};\n'
        context += 'static const struct ArchivedReport archived[]={' + ','.join(
            '{' + ','.join((json.dumps(row['remote']), json.dumps(row['alias']), str(row['bytes']) + 'ULL',
                            json.dumps(row['sha256']))) + '}' for row in targets) + '};\nstatic unsigned archive_index;\n'
        context += '#define CASE_COMPLETED_FILE_KIND "archived_report"\n#define CASE_COMPLETED_FILE_LABEL "ARCHIVED_REPORT"\n'
        for key, field in (('PATH', 'path'), ('ALIAS', 'alias'), ('BYTES', 'bytes'), ('SHA256', 'sha256')):
            context += '#define CASE_ACTIVATION_' + key + ' archived[archive_index].' + field + '\n'
        context += 'static int case_completed_activation_reports_valid(void){return 1;}\n'
        context += '#include "activation_capture_retire.h"\n'
        context += 'static int case_retire_completed_images(int*calls){for(archive_index=0;archive_index<sizeof(archived)/sizeof(archived[0]);++archive_index)if(!case_retire_activation(calls))return 0;return 1;}\n'
        plan = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images',
                     args.out / 'native', completed_images_context=context)
        compact(plan, args.out / 'native', args.compact_marker_control)
        save(args.out / 'intent.private.json', dict(facts, source=record(Path(__file__)),
             native_plan=record(args.out / 'native/plan.private.json')))
        print(json.dumps(dict(prepared=True, reports=len(targets), archived_bytes=sum(r['bytes'] for r in targets), PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    need(all(intent[key] == value for key, value in facts.items()) and intent['source'] == record(Path(__file__)) and
         intent['native_plan'] == record(args.out / 'native/plan.private.json'), 'The exact archived report admission changed')
    state['CPU_source_seal_owner'] = dict(plan=intent['native_plan'], phase='retire-archived-console-reports',
        ordinary_helper_completion_pending=True, GPU_calls=0, title_launches=0)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    result = completed_operation(lan_module(), load(args.out / 'native/plan.private.json'), args.out / 'native')
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and
         result['operation_calls'] == len(targets) and
         Path(result['raw']['path']).read_bytes().count(b'ARCHIVED_REPORT_RETIRED both_namespaces_absent=1') == len(targets),
         'Every archive deletion, directory owner restoration, positive close and current-file hash must finish')
    save(args.out / 'result.private.json', dict(completed=True, native=result, retired_files=len(targets),
        archived_bytes=sum(row['bytes'] for row in targets), PC_archives_preserved=True,
        current_seven_native_hashes_unchanged=True, runtime_directory_owner_restored=True, RAM_gain_claimed=False))
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == intent['native_plan'], 'Never clear another CPU helper owner')
    state.pop('CPU_source_seal_owner')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, retired_files=len(targets), PC_archives_preserved=True, RAM_gain_claimed=False)))


if __name__ == '__main__':
    main()
