#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove only fully reviewed, unselected IQ2 namespaces after all cases retire."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from build_performance_quantizer import record
from compact_case_integrity_markers import compact
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, current_files, lan_module


def publication_files(path):
    published, plan = load(path), load(path.parent / 'plan.private.json')
    seal = load(published['source_integrity']['path'])
    native = load(published['native_result']['path'])
    root, files = plan['directory'], plan['files']
    need(published['completed'] and published['whole_new_bytes_and_all_parent_identities_qualified'] and
         record(published['source_integrity']['path']) == published['source_integrity'] and
         record(published['native_result']['path']) == published['native_result'] and
         native['completed'] and native['helper_exited'] and native['helper_files_removed'] and
         native['operation_calls'] == 2 * len(files) + 2 and
         seal['CPU_owners_positively_closed'] and seal['all_new_parts_complete_Direct_SHA256_readback'] and
         root == seal['canonical_source_directory'] and
         re.fullmatch(re.escape(PHYSICAL) + r'/expert-q2-[0-9a-f]{32}', root) and 1 <= len(files) <= 256,
         'Only a fully sealed exact new-only source namespace may be retired')
    known = {row['path']: row for row in seal['parts'] + seal['headers']}
    for row in files:
        need(str(PurePosixPath(row['physical']).parent) == root and
             '..' not in PurePosixPath(row['physical']).parts and
             row['alias'] == ALIAS + row['physical'][len(PHYSICAL):] and
             row['application'] == '/app0' + row['physical'][len(PHYSICAL):], 'Every target must be a direct owned child')
        if PurePosixPath(row['physical']).name == 'model-receipt.json':
            need(row['local']['sha256'] == seal['model_receipt_sha256'] and
                 row['local']['bytes'] == seal['receipt_identity'][5], 'The exact sealed receipt must remain bound')
        else:
            source = known[row['application']]
            need(source['bytes'] == row['local']['bytes'] and source['sha256'] == row['local']['sha256'],
                 'Every exact part/header must retain its whole-file sealing evidence')
    need(len({row['physical'] for row in files}) == len(files), 'No target may occur twice')
    return root, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'final-review', 'compact-marker-control', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--publication', type=Path, action='append', required=True)
    parser.add_argument('--component-manifest', type=Path)
    parser.add_argument('--staging-manifest', type=Path)
    parser.add_argument('--protected-runtime-plan', type=Path, action='append', default=[])
    parser.add_argument('--execute-prepared', action='store_true')
    parser.add_argument('--continue-prepared', action='store_true')
    args = parser.parse_args()
    need(not (args.execute_prepared and args.continue_prepared), 'Execute once or continue the exact returned cleanup prefix')
    reviewed = load(args.final_review)
    need(reviewed['completed'] and reviewed['all_pending_profiles_resolved'] and
         reviewed['production_current_verified'] and reviewed['no_unknown_owners'],
         'Finish all speed/quality/adoption decisions before removing any candidate source')
    state_path = args.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('CPU_source_seal_owner') and
         (not state.get('source_publication_owner') or args.continue_prepared and
          state['source_publication_owner']['plan'] == record(args.out / 'intent.private.json')) and
         not state.get('GPU_retirement_readmission_pending'),
         'Every actual model and helper must positively retire before final source cleanup')
    reference_paths = [args.current / name for name in ('deployment.private.json', 'qwen-runtime/app.json',
        'qwen-runtime/development.json', 'provenance/model-source-plan.private.json',
        'provenance/protected-model-source-plan.private.json', 'provenance/required-bundle-inputs.private.json',
        'provenance/retained-relink-inputs.private.json', 'provenance/current-package.private.json')]
    reference_paths += args.protected_runtime_plan
    references = '\n'.join(path.read_text(encoding='utf-8') for path in reference_paths)
    retired, retained = [], []
    for path in args.publication:
        root, files = publication_files(path)
        item = dict(publication=record(path), plan=record(path.parent / 'plan.private.json'), root=root, files=files)
        if PurePosixPath(root).name in references:
            retained.append(dict(root=root, reason='The selected runtime or canonical rebuild provenance references this namespace'))
        else:
            retired.append(item)
    need(len({row['root'] for row in retired + retained}) == len(retired) + len(retained), 'A namespace cannot appear twice')
    components, protected_components = [], []
    for row in load(args.component_manifest) if args.component_manifest else []:
        name = PurePosixPath(row['remote']).name
        need(str(PurePosixPath(row['remote']).parent) == PHYSICAL + '/qwen-runtime' and
             re.fullmatch(r'(?:iq2-Up|paired-Down|cold-rodata)-[0-9a-f]{24}\.bin', name) and
             name.endswith(row['sha256'][:24] + '.bin') and 0 < row['bytes'] <= 128 << 20,
             'Only exact named closed prototype/fixture inputs are eligible')
        if row.get('local'):
            need(record(row['local']['path']) == row['local'] and
                 all(row[key] == row['local'][key] for key in ('bytes', 'sha256')), 'The complete PC fixture input changed')
        else:
            need(row['bytes'] == 8388608 and name.startswith('cold-rodata-') and
                 hashlib.sha256(bytes(range(256)) * 32768).hexdigest() == row['sha256'],
                 'Only the exact deterministic driver-free8MiB prototype may omit a PC input file')
        if name in references:
            protected_components.append(row)
        else:
            components.append(dict(row, alias=ALIAS + row['remote'][len(PHYSICAL):]))
    staging, protected_staging = [], []
    for row in load(args.staging_manifest) if args.staging_manifest else []:
        match = re.fullmatch(r'/data/ai/moss-qwen-case-([0-9a-f]{32})(?:\.(?:elf|log)|-(?:candidate-SELF|restore-SELF)\.bin|-(?:restore-)?[0-9]+\.json|-[A-Za-z0-9-]+\.once)', row['remote'])
        need(match and row['uid'] in (0, 1) and row['gid'] == 0 and row['nlink'] == 1 and
             row['mode'].startswith('-') and 0 <= row['bytes'] <= 128 << 20,
             'Only exact inactive ordinary Qwen case files may be removed outside the title namespace')
        if match[1] in references:
            protected_staging.append(row)
        else:
            staging.append(row)
    selected = current_files(args.current)
    facts = dict(final_review=record(args.final_review), retired=retired, retained=retained, selected=selected,
        protected_references=[record(path) for path in reference_paths], boot=state['current_boot'],
        components=components, protected_components=protected_components,
        component_manifest=record(args.component_manifest) if args.component_manifest else None,
        staging=staging, protected_staging=protected_staging,
        staging_manifest=record(args.staging_manifest) if args.staging_manifest else None,
        source=record(Path(__file__)), recursive_deletion=False, selected_namespace_children_never_pruned=True)
    if not args.execute_prepared and not args.continue_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        save(args.out / 'intent.private.json', facts)
        print(json.dumps(dict(prepared=True, unselected_namespaces=len(retired), protected_namespaces=len(retained),
                              files=sum(len(row['files']) for row in retired), component_inputs=len(components),
                              inactive_case_files=len(staging), PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    if args.continue_prepared:
        old_source = record(args.out / 'pre-resume-source.private.py')
        need(all(old_source[key] == intent['source'][key] for key in ('bytes', 'sha256')) and
             {key: value for key, value in intent.items() if key != 'source'} ==
             {key: value for key, value in facts.items() if key != 'source'},
             'Continue only the immutable original targets; retain the original source and every positive deletion')
        before = load(args.out / 'current-before/result.private.json')
        before_plan = load(args.out / 'current-before/plan.private.json')
        need(before['completed'] and before['operation_calls'] == len(components) and before['helper_exited'] and
             before['helper_files_removed'] and before_plan['old_files'] == before_plan['new_files'] == selected,
             'Never replay the successful current-file guard or component retirements')
        save(args.out / 'continued-check-scope.private.json', dict(original_source=old_source,
            corrected_source=facts['source'], current_before=record(args.out / 'current-before/result.private.json'),
            changes='Check alias absence natively after cleanup; preserve all positively deleted targets',
            completed_component_deletions_replayed=0, completed_source_deletions_replayed=0))
    else:
        need(intent == facts, 'The exact final source selection changed')
    state['source_publication_owner'] = dict(plan=record(args.out / 'intent.private.json'), phase='retire-reviewed-unselected-sources',
                                            GPU_calls=0, title_launches=0, recursive_deletion=False)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    lan = lan_module()

    def idle():
        with lan.OPENER.open('http://' + lan.HOST + ':8084/processes_list', timeout=8) as response:
            rows = json.loads(response.read())['processes']
        need(not any(row['name'] == 'eboot.bin' or row['name'] == 'payload' and int(row['pid']) != 154 for row in rows),
             'An application or extra helper owner appeared during cleanup')

    def guard(label):
        out = args.out / label
        active = components if label == 'current-before' else []
        context = 'static int case_retire_completed_images(int*calls){(void)calls;return 1;}\n'
        if active:
            context = 'struct Fixture{const char*path;const char*alias;unsigned long long bytes;const char*sha;};\n'
            context += 'static const struct Fixture fixtures[]={' + ','.join('{' + ','.join((json.dumps(row['remote']),
                json.dumps(row['alias']), str(row['bytes']) + 'ULL', json.dumps(row['sha256']))) + '}' for row in active) + '};\nstatic unsigned fixture_index;\n'
            context += '#define CASE_COMPLETED_FILE_KIND "reviewed_fixture"\n#define CASE_COMPLETED_FILE_LABEL "REVIEWED_FIXTURE"\n'
            for key, field in (('PATH', 'path'), ('ALIAS', 'alias'), ('BYTES', 'bytes'), ('SHA256', 'sha')):
                context += '#define CASE_ACTIVATION_' + key + ' fixtures[fixture_index].' + field + '\n'
            context += 'static int case_completed_activation_reports_valid(void){return live_context()&&idle();}\n'
            context += '#include "activation_capture_retire.h"\n'
            context += 'static int case_retire_completed_images(int*calls){for(fixture_index=0;fixture_index<sizeof(fixtures)/sizeof(fixtures[0]);++fixture_index)if(!case_retire_activation(calls))return 0;return 1;}\n'
        elif label == 'current-after' and retired:
            paths = [path for row in retired for path in (row['root'], ALIAS + row['root'][len(PHYSICAL):])]
            context = 'static const char*retired_roots[]={' + ','.join(map(json.dumps, paths)) + '};\n'
            context += 'static int case_retire_completed_images(int*calls){(void)calls;for(unsigned i=0;i<sizeof(retired_roots)/sizeof(retired_roots[0]);++i){struct stat value;errno=0;int rc=lstat(retired_roots[i],&value),saved=errno;if(!report("RETIRED_NAMESPACE_ABSENCE index=%u rc=%d error=%d",i,rc,saved)||rc!=-1||saved!=ENOENT)return 0;}return 1;}\n'
        plan = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images', out,
                     completed_images_context=context)
        plan = compact(plan, out, args.compact_marker_control)
        result = completed_operation(lan, plan, out)
        need(result['completed'] and result['operation_calls'] == len(active) and result['helper_exited'] and result['helper_files_removed'],
             'Exact current-seven full native hashes, boot/services and idle guards must finish')

    idle()
    if not args.continue_prepared:
        guard('current-before')
    removed = 0
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST, 2121, timeout=20)
        ftp.login()
        need(ftp.sendcmd('SELF') == '226 SELF transfer mode disabled', 'Raw FTP mode is required')
        for index, item in enumerate(retired):
            root = item['root']
            receipts = [args.out / ('removed-' + str(index) + '-' + str(ordinal) + '.private.json')
                        for ordinal in range(len(item['files']))]
            if args.continue_prepared and all(path.exists() for path in receipts):
                need(all(load(path)['path'] == row['physical'] and load(path)['reply'].startswith(('226 ', '250 '))
                         for path, row in zip(receipts, item['files'])), 'Every collected source deletion must bind its exact original target')
                lan.absent(root)
                removed += len(item['files'])
                save(args.out / ('collected-removed-namespace-' + str(index) + '.private.json'),
                     dict(root=root, positive_file_deletions=len(item['files']), physical_absence_confirmed=True,
                          alias_absence_deferred_to_current_after_native_guard=True, deletions_replayed=0))
                print(json.dumps(dict(namespace_collected=index + 1, files=len(item['files']), deletions_replayed=0)), flush=True)
                continue
            need(not any(path.exists() for path in receipts), 'A partially deleted namespace requires its exact prefix collection before continuing')
            lines = []
            ftp.retrlines('LIST ' + root, lines.append)
            actual = {line.split(maxsplit=8)[8]: line.split(maxsplit=8) for line in lines
                      if len(line.split(maxsplit=8)) == 9 and line.split(maxsplit=8)[8] not in ('.', '..')}
            expected = {PurePosixPath(row['physical']).name: row for row in item['files']}
            need(set(actual) == set(expected) and all(values[:5] == ['-rw-r--r--', '1', '0', '0', str(expected[name]['local']['bytes'])]
                 for name, values in actual.items()), 'The exact sealed namespace manifest changed; do not remove it')
            idle()
            for ordinal, row in enumerate(item['files']):
                reply = ftp.sendcmd('DELE ' + row['physical'])
                need(reply.startswith(('226 ', '250 ')), 'One exact returned source deletion must finish')
                save(args.out / ('removed-' + str(index) + '-' + str(ordinal) + '.private.json'), dict(path=row['physical'], reply=reply))
                removed += 1
            lines = []
            ftp.retrlines('LIST ' + root, lines.append)
            need(all(line.split(maxsplit=8)[-1] in ('.', '..') for line in lines), 'Only an empty exact owned directory may be removed')
            reply = ftp.rmd(root)
            need(reply.startswith(('226 ', '250 ')), 'The empty owned directory must retire')
            lan.absent(root)
            save(args.out / ('removed-namespace-' + str(index) + '.private.json'), dict(root=root,
                positive_directory_reply=reply, physical_absence_confirmed=True,
                alias_absence_deferred_to_current_after_native_guard=True))
            print(json.dumps(dict(namespace_retired=index + 1, total=len(retired), removed_files=removed)), flush=True)
        if staging:
            idle()
            lines = []
            ftp.retrlines('LIST /data/ai', lines.append)
            actual = {line.split(maxsplit=8)[8]: line.split(maxsplit=8) for line in lines if len(line.split(maxsplit=8)) == 9}
            for row in staging:
                values = actual.get(PurePosixPath(row['remote']).name)
                need(values and values[:5] == [row['mode'], str(row['nlink']), str(row['uid']), str(row['gid']), str(row['bytes'])],
                     'An exact inactive-case file changed; retain it')
            for index, row in enumerate(staging):
                reply = ftp.sendcmd('DELE ' + row['remote'])
                need(reply.startswith(('226 ', '250 ')), 'One exact inactive case file deletion must return positively')
                save(args.out / ('staging-removed-' + str(index) + '.private.json'), dict(path=row['remote'], reply=reply))
                lan.absent(row['remote'])
    idle()
    guard('current-after')
    save(args.out / 'result.private.json', dict(completed=True, retired_files=removed, retired_namespaces=len(retired),
        protected_namespaces=retained, protected_current_seven_full_native_hashes_pass=True,
        retired_component_inputs=len(components), protected_component_inputs=protected_components,
        retired_inactive_case_files=len(staging), protected_active_runtime_files=protected_staging,
        selected_namespace_children_never_pruned=True, recursive_deletion=False, GPU_calls=0, title_launches=0,
        original_PC_BF16_sources_preserved=True, all_canonical_rebuild_inputs_preserved=True))
    state = load(state_path)
    need(state['source_publication_owner']['plan'] == record(args.out / 'intent.private.json'), 'Never clear another source owner')
    state.pop('source_publication_owner')
    prior = state.pop('active_successful_native_case', None)
    if prior:
        state['archived_last_trial_case_after_source_retirement'] = prior
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, retired_namespaces=len(retired), retired_files=removed,
                          current_seven_native_hashes_pass=True)), flush=True)


if __name__ == '__main__':
    main()
