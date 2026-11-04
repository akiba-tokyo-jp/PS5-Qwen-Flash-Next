#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire source residency introduced by one positively completed model owner."""
import argparse
import ast
import json
from pathlib import Path, PurePosixPath
import re

from build_performance_quantizer import record
from compact_case_integrity_markers import compact
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, build, current_files, lan_module

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'completed_model_source_cache_cohorts'


def cohort_entry(entries, case_record, completed_records):
    matches = [entry for entry in entries if entry['case_result'] == case_record]
    need(len(matches) <= 1, 'One completed model may own only one source-residency cohort')
    previous = matches[0] if matches else None
    need((not previous and not completed_records) or
         (previous and not previous.get('pending_helper') and previous['completed_scopes'] == completed_records),
         'Never reset a completed model cohort or repeat its already processed windows')
    return previous


def validate_owner(state, plan, native, closed, selected):
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('source_publication_owner') and
         not state.get('CPU_source_seal_owner') and not state.get('GPU_retirement_readmission_pending'),
         'Only a positively idle restored console may retire its last completed model source cohort')
    need(native['completed'] and native['model_loads'] == 1 and
         native['all_model_source_device_owners_positively_retired'] and native['device_ledger_live_bytes'] == 0 and
         native['source_windows'] > 0 and native['source_windows'] == native['source_completed_windows'] and
         native['candidate_SELF_sha256'] == plan['SELF']['sha256'] and native['run_id'] == plan['run_id'] and
         closed['completed'] and closed['ordinary_exit_observed'] and closed['native_owners'] == 0 and
         closed['all_model_source_device_owners_positively_retired'] and not closed['unknown_completion'] and
         closed['current_seven_restored_and_native_hashed'] and plan['old_files'] == selected and
         state['active_successful_native_case']['run_id'] == native['run_id'] and
         state['active_successful_native_case']['phase'] == 'model-complete-ordinary-close-original-restored',
         'A new cohort requires actual completed source reads and the exact latest ordinary model exit; low free pages alone never qualify')


def sources(current, case):
    plan_path = case / 'case/plan.private.json'
    plan, closed = load(plan_path), load(case / 'closed/result.private.json')
    need(record(closed['native_terminal']['path']) == closed['native_terminal'] and
         record(plan['package']['path']) == plan['package'], 'Exact archived native and compiled package evidence is required')
    native = load(closed['native_terminal']['path'])
    package = load(plan['package']['path'])
    profile_row = package['effective_application_policy']['profile']
    need(record(profile_row['path']) == profile_row, 'The compiled model profile changed')
    profile = load(profile_row['path'])
    need(profile['headless_audit_kind'] in ('Q2-IQ2-Up-model', 'Q2-IQ2-Gate-Up-model', 'Q3-IQ2-Down-model') and
         profile['model_and_GPU_guards_preserved'], 'Only the explicit remaining original-model cohorts are eligible')
    parent = current / 'provenance/model-source-plan.private.json'
    required = current / 'provenance/required-bundle-inputs.private.json'
    original = load(parent)
    rows = original['physical'] + original['backing'] + load(required)['rows']
    evidence = [record(plan_path), record(case / 'result.private.json'), record(case / 'closed/result.private.json'),
                closed['native_terminal'], plan['package'], profile_row, record(parent), record(required)]
    layer = profile.get('model_layer')
    if layer:
        publication = load(layer['publication']['path'])
        need(record(layer['publication']['path']) == layer['publication'] and publication['completed'] and
             publication['whole_new_bytes_and_all_parent_identities_qualified'] and
             layer['source_policy'] == publication['policy'] and
             record(publication['source_integrity']['path']) == publication['source_integrity'] and
             native['model_receipt_sha256'] == layer['model_receipt']['sha256'],
             'Only the exact sealed source set used by this completed model may extend the parent inputs')
        seal = load(publication['source_integrity']['path'])
        rows += seal['parts'] + seal['headers']
        evidence += [layer['publication'], publication['source_integrity']]
    else:
        need(profile['overrides']['native_headless_model_audit']['arm'] == 'control',
             'An original-source cohort must be the exact compiled control')
    unique = {}
    for row in rows:
        path, identity = row['path'], row['identity']
        need(path.startswith('/app0/') and '..' not in PurePosixPath(path).parts and len(identity) == 10 and
             row['bytes'] == identity[5] and identity[2] & 0o170000 == 0o100000 and not identity[2] & 0o22,
             'Every eligible source must have a complete immutable native identity')
        key = tuple(identity[1:])
        if key in unique:
            need(unique[key]['bytes'] == row['bytes'], 'Aliased source identities must agree')
        unique[key] = dict(row, mounted_path=ALIAS + path[5:])
    files = [row for row in reversed(list(unique.values())) if row['bytes'] >= 16384]
    windows = [dict(file=i, offset=offset, bytes=min(64 << 20, (row['bytes'] // 16384 * 16384) - offset))
               for i, row in enumerate(files) for offset in range(0, row['bytes'] // 16384 * 16384, 64 << 20)]
    need(files and windows, 'A completed read owner must retain explicit bounded source extents')
    return plan, native, closed, files, windows, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'case', 'compact-marker-control', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--completed-scope', type=Path, action='append', default=[])
    parser.add_argument('--execute-prepared', action='store_true')
    args = parser.parse_args()
    state_path = args.current / 'active-console.private.json'
    state, selected = load(state_path), current_files(args.current)
    plan, native, closed, files, windows, evidence = sources(args.current, args.case)
    validate_owner(state, plan, native, closed, selected)
    case_record = record(args.case / 'result.private.json')
    entries = state.get(LEDGER, [])
    previous = cohort_entry(entries, case_record, [record(path) for path in args.completed_scope])
    first = 0
    for path in args.completed_scope:
        result, intent = load(path), load(path.parent / 'intent.private.json')
        need(result['completed'] and result['all_mappings_and_FDs_positively_retired'] and
             result['starting_window'] == first and intent['case_result'] == case_record and
             intent['files'] == files and intent['windows'] == windows and intent['boot'] == state['current_boot'],
             'Continue only the exact positive prefix within the same actual model read cohort')
        first += result['observations']['scanned']
    need(first < len(windows), 'This completed model cohort is exhausted; only a different actual completed model may qualify again')
    facts = dict(case_result=case_record, run_id=native['run_id'], evidence=evidence, files=files, windows=windows,
        selected=selected, boot=state['current_boot'], starting_window=first, source=record(Path(__file__)),
        actual_completed_source_windows=native['source_completed_windows'], earlier_pool_ledgers_unchanged=True,
        physical_ranges_may_appear_in_earlier_completed_model_cohorts=True,
        new_cohort_requires_a_different_positive_model_owner=True, aligned_tails_excluded=True,
        model_readiness_pages_unchanged=7374, native_cache_floor_unchanged=1154, source_writes=0)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        template = ROOT / 'tools/observe_source_cache_complement.py'
        literals = [node.value for node in ast.walk(ast.parse(template.read_text(encoding='utf-8')))
                    if isinstance(node, ast.Constant) and isinstance(node.value, str) and
                    node.value.startswith('#include <sys/mman.h>') and 'struct CacheSource' in node.value]
        need(len(literals) == 1, 'Reuse the exact qualified readonly cache body')
        context = literals[0].replace('FIRST_WINDOW', str(first)).replace('TARGET_FREE_PAGES', '16384u')
        context = context.replace('FILES', ','.join('{' + json.dumps(row['mounted_path']) + ',{' +
            ','.join(str(value) + 'ULL' for value in row['identity']) + '}}' for row in files))
        context = context.replace('WINDOWS', ','.join('{' + str(row['file']) + ',' + str(row['offset']) + 'ULL,' +
            str(row['bytes']) + 'ULL}' for row in windows))
        built = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images',
                      args.out / 'native', completed_images_context=context)
        compact(built, args.out / 'native', args.compact_marker_control)
        save(args.out / 'intent.private.json', dict(facts, template=record(template), native_API_body_unchanged=True,
             native_plan=record(args.out / 'native/plan.private.json')))
        print(json.dumps(dict(prepared=True, actual_model_read_cohort=native['run_id'], files=len(files), windows=len(windows), PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    need(all(intent[key] == value for key, value in facts.items()) and
         intent['native_plan'] == record(args.out / 'native/plan.private.json'), 'The exact read-owner cache scope changed')
    if previous is None:
        previous = dict(case_result=case_record, run_id=native['run_id'], completed_scopes=[])
        state.setdefault(LEDGER, []).append(previous)
    previous['pending_helper'] = intent['native_plan']
    state['CPU_source_seal_owner'] = dict(plan=intent['native_plan'], phase='completed-model-source-residency',
        run_id=native['run_id'], GPU_calls=0, title_launches=0, ordinary_helper_completion_pending=True)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    result = completed_operation(lan_module(), load(args.out / 'native/plan.private.json'), args.out / 'native')
    raw = Path(result['raw']['path']).read_bytes()
    found = re.findall(rb'COMPLEMENT_COMPLETE (.*)', raw)
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and len(found) == 1,
         'The same helper and each readonly mapping/descriptor must positively retire')
    observed = {key.decode(): int(value) for key, value in re.findall(rb'\b([A-Za-z_]+)=(-?\d+)', found[0])}
    need(observed['returned_error'] == 0 and observed['scanned'] > 0 and observed['total'] == len(windows) and
         result['operation_calls'] <= 128, 'Preserve the original finite cache admission, operation bound and positive prefix')
    save(args.out / 'result.private.json', dict(completed=True, native=result, observations=observed,
        starting_window=first, remaining_windows=len(windows) - first - observed['scanned'],
        case_result=case_record, run_id=native['run_id'], all_mappings_and_FDs_positively_retired=True,
        earlier_pool_ledgers_unchanged=True, source_writes=0, model_launch_admission=False,
        exclusive_global_RAM_gain_claimed=False))
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == intent['native_plan'], 'Never clear another CPU owner')
    entry = next(entry for entry in state[LEDGER] if entry['case_result'] == case_record)
    need(entry['pending_helper'] == intent['native_plan'], 'The exact completed-model cache claim changed')
    entry.pop('pending_helper')
    entry['completed_scopes'].append(record(args.out / 'result.private.json'))
    state.pop('CPU_source_seal_owner')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, actual_model_read_cohort=native['run_id'], observations=observed,
                          previous_ledgers_unchanged=True, model_floor=7374)), flush=True)


if __name__ == '__main__':
    main()
