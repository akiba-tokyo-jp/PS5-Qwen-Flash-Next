#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire unscanned owned staging pages after a returned source-seal memory refusal."""
import argparse
import ast
import json
from pathlib import Path, PurePosixPath
import re

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, current_files, lan_module

ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT = r'''
static int staged_capture(struct CacheSource*f,uint64_t mounted,unsigned index,const uint64_t*expected){
 struct stat s;
 if(lstat(f->path,&s)||!S_ISREG(s.st_mode)||(s.st_mode&07777)!=0777||s.st_uid||s.st_gid||s.st_nlink!=1||
    (uint64_t)s.st_dev!=mounted||s.st_size!=UINT64_C(235929600))return 0;
 uint64_t values[10]={(uint64_t)s.st_dev,(uint64_t)s.st_ino,(uint64_t)s.st_mode,
  (uint64_t)s.st_uid,(uint64_t)s.st_gid,(uint64_t)s.st_size,
  (uint64_t)s.st_mtim.tv_sec,(uint64_t)s.st_mtim.tv_nsec,
  (uint64_t)s.st_ctim.tv_sec,(uint64_t)s.st_ctim.tv_nsec};
 for(unsigned i=0;i<10;++i)if(values[i]!=expected[i])return 0;
 for(unsigned i=0;i<10;++i)f->identity[i]=values[i];
 return report("STAGED_CACHE_ID index=%u values=%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu",index,
  (unsigned long long)values[0],(unsigned long long)values[1],(unsigned long long)values[2],
  (unsigned long long)values[3],(unsigned long long)values[4],(unsigned long long)values[5],
  (unsigned long long)values[6],(unsigned long long)values[7],(unsigned long long)values[8],(unsigned long long)values[9]);
}
'''
CAPTURE = ' for(unsigned i=0;i<sizeof(sources)/sizeof(sources[0]);++i)if(!staged_capture(sources+i,(uint64_t)root.st_dev,i,staged_expected[i]))return 0;\n'


def context_for(files, windows, first, identities):
    template = ROOT / 'tools/observe_source_cache_complement.py'
    literals = [node.value for node in ast.walk(ast.parse(template.read_text(encoding='utf-8')))
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and
                node.value.startswith('#include <sys/mman.h>') and 'struct CacheSource' in node.value]
    need(len(literals) == 1, 'Reuse one exact qualified cache-retirement body')
    original = literals[0]
    context = original.replace('static const struct CacheSource sources[]', 'static struct CacheSource sources[]', 1)
    predicate = '!(s->st_mode&0022)'
    need(context.count(predicate) == 1, 'One sealed-source mode predicate must adapt to observed staging metadata')
    context = context.replace(predicate, '(s->st_mode&07777)==0777', 1)
    marker = 'static uint32_t complement_free(void)'
    need(context.count(marker) == 1, 'One metadata adapter insertion point required')
    expected = 'static const uint64_t staged_expected[][10]={' + ','.join(
        '{' + ','.join(str(value) + 'ULL' for value in row) + '}' for row in identities) + '};\n'
    context = context.replace(marker, expected + SNAPSHOT + '\n' + marker, 1)
    marker = ' if(lstat(MOUNT,&root)||!S_ISDIR(root.st_mode))return 0;\n'
    need(context.count(marker) == 1, 'Capture all owned metadata before the first cache operation')
    context = context.replace(marker, marker + CAPTURE, 1)
    restored = context.replace(expected + SNAPSHOT + '\n', '', 1).replace(CAPTURE, '', 1)
    restored = restored.replace('static struct CacheSource sources[]', 'static const struct CacheSource sources[]', 1)
    restored = restored.replace('(s->st_mode&07777)==0777', predicate, 1)
    need(restored == original, 'The qualified range, canary, IO, identity and close body must stay exact')
    context = context.replace('FIRST_WINDOW', str(first)).replace('TARGET_FREE_PAGES', '16384u')
    context = context.replace('FILES', ','.join('{' + json.dumps(row['alias']) + ',{0}}' for row in files))
    context = context.replace('WINDOWS', ','.join('{' + str(row['file']) + ',' + str(row['offset']) + 'ULL,' +
                                               str(row['bytes']) + 'ULL}' for row in windows))
    return context, record(template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'publication', 'transfer-proof', 'memory-refusal', 'staged-metadata-proof', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--completed-scope', type=Path, action='append', default=[])
    parser.add_argument('--execute-prepared', action='store_true')
    parser.add_argument('--compact-marker-control', type=Path)
    args = parser.parse_args()
    publication_path = args.publication / 'plan.private.json'
    publication, transfer, refusal = load(publication_path), load(args.transfer_proof), load(args.memory_refusal)
    old_plan = load(args.memory_refusal.parent / 'plan.private.json')
    raw = Path(refusal['raw']['path']).read_text()
    need(not refusal['completed'] and refusal['operation_calls'] == 0 and refusal['helper_exited'] and
         refusal['helper_files_removed'] and refusal['GPU_calls'] == refusal['initializer_requests'] == 0 and
         record(refusal['raw']['path']) == refusal['raw'] and
         'CPU_METADATA_PRESSURE free_before=1196 free_after=1196 ' in raw and 'required=1201' in raw and
         raw.endswith('END success=0 operation_calls=0 app_id=-1 log_healthy=1 GPU_calls=0 initializer_requests=0 mount_calls=0\n') and
         publication['native_plan'] == record(args.memory_refusal.parent / 'plan.private.json') and
         old_plan['whole_integrity_window_bytes'] == 262144 and old_plan['CPU_metadata_margin_pages'] == 97,
         'Only the exact positively retired zero-operation source memory refusal is eligible')
    need(transfer['complete'] and transfer['exit_code'] == 0 and transfer['publication'] == record(publication_path) and
         transfer['native_submissions'] == transfer['completed_payload_retransmissions'] == 0 and
         len(transfer['rows']) == len(publication['files']) and
         all(row == dict(uploaded_file=i + 1, total=len(publication['files']), bytes=file['local']['bytes'])
             for i, (row, file) in enumerate(zip(transfer['rows'], publication['files']))),
         'All exact whole stores must finish before any staged cache maintenance')
    state_path = args.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and state['source_publication_owner']['plan'] == record(publication_path),
         'The exact idle staged source owner must remain reserved')
    references = json.dumps([load(args.current / name) for name in (
        'qwen-runtime/app.json', 'qwen-runtime/development.json',
        'provenance/model-source-plan.private.json', 'provenance/protected-model-source-plan.private.json',
        'provenance/required-bundle-inputs.private.json')])
    root = publication['directory']
    need(root.startswith(PHYSICAL + '/expert-q2-') and publication['application_directory'] not in references and
         root not in references, 'The staged namespace must not be a selected model input')
    files = [row for row in reversed(publication['files']) if row['local']['bytes'] == 235929600]
    need(len(files) == 48 and len({row['physical'] for row in files}) == 48 and
         all(str(PurePosixPath(row['physical']).parent) == root and '..' not in PurePosixPath(row['physical']).parts and
             row['alias'] == ALIAS + row['physical'][len(PHYSICAL):] for row in files),
         'Only the exact48 fully transferred Down carrier files are eligible')
    metadata = load(args.staged_metadata_proof)
    metadata_intent = load(args.staged_metadata_proof.parent / 'intent.private.json')
    need(metadata['completed'] and metadata['source_data_reads'] == metadata['source_data_writes'] == metadata['cache_operations'] == 0 and
         metadata['native']['completed'] and metadata['native']['helper_exited'] and metadata['native']['helper_files_removed'] and
         metadata_intent['publication'] == record(publication_path), 'Fresh completed readonly metadata must bind this staged publication')
    observed = {int(row['index']): row for row in metadata['observations'] if row['kind'] == 'alias'}
    observed_paths = {int(index): path for kind, index, path in metadata_intent['paths'] if kind == 'alias'}
    need(set(observed) == set(range(48)) and
         all(observed_paths.get(i) == files[i]['alias'] for i in range(48)),
         'Every exact staged alias and its index must be observed')
    identities = [observed[i]['identity'] for i in range(48)]
    need(all(row['rc'] == '0' and row['nlink'] == '1' and len(row['identity']) == 10 and
             row['identity'][2] == 0o100777 and row['identity'][3:6] == [0, 0, 235929600]
             for row in observed.values()), 'Only the exact observed root-owned0777 staging files may be admitted')
    windows = [dict(file=i, offset=offset, bytes=min(64 << 20, row['local']['bytes'] - offset))
               for i, row in enumerate(files) for offset in range(0, row['local']['bytes'], 64 << 20)]
    first = 0
    for path in args.completed_scope:
        previous, intent = load(path), load(path.parent / 'intent.private.json')
        need(previous['completed'] and previous['all_mappings_and_FDs_positively_retired'] and
             previous['starting_window'] == first and intent['files'] == files and intent['windows'] == windows and
             intent['boot'] == state['current_boot'], 'Never repeat a completed staged cache window')
        first += previous['observations']['scanned']
    need(first < len(windows), 'The staged cache scope is exhausted')
    selected = current_files(args.current)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        context, template = context_for(files, windows, first, identities)
        native = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images',
                       args.out / 'native', completed_images_context=context)
        if args.compact_marker_control:
            from compact_case_integrity_markers import compact
            native = compact(native, args.out / 'native', args.compact_marker_control)
        need(native['whole_integrity_window_bytes'] == 16384 and native['CPU_metadata_margin_pages'] == 21,
             'Preserve the qualified cache-helper defaults and all model/source-sealer guards')
        save(args.out / 'intent.private.json', dict(publication=record(publication_path), transfer=record(args.transfer_proof),
            memory_refusal=record(args.memory_refusal), files=files, windows=windows, starting_window=first,
            staged_metadata=record(args.staged_metadata_proof), expected_staged_identities=identities,
            boot=state['current_boot'], selected=selected, template=template, source=record(Path(__file__)),
            native_plan=record(args.out / 'native/plan.private.json'), original_cache_operations_exact=True,
            staging_metadata_admission_changed=True,
            compact_marker_control=record(args.compact_marker_control) if args.compact_marker_control else None,
            source_writes=0, model_readiness_pages_unchanged=7374, source_sealer_minimum_pages_unchanged=1201))
        print(json.dumps(dict(prepared=True, files=48, windows=len(windows), starting_window=first, PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    need(intent['selected'] == selected and intent['files'] == files and intent['windows'] == windows and
         intent['starting_window'] == first and intent['source'] == record(Path(__file__)) and
         intent['publication'] == record(publication_path) and intent['transfer'] == record(args.transfer_proof) and
         intent['memory_refusal'] == record(args.memory_refusal) and
         intent.get('compact_marker_control') == (record(args.compact_marker_control) if args.compact_marker_control else None) and
         intent['staged_metadata'] == record(args.staged_metadata_proof) and intent['expected_staged_identities'] == identities,
         'The exact prepared source-cache scope must remain unchanged')
    cpu = state.get('CPU_source_seal_owner')
    need(not cpu, 'The fresh metadata helper must positively retire before staged cache work')
    native = load(args.out / 'native/plan.private.json')
    need(record(args.out / 'native/plan.private.json') == intent['native_plan'], 'The prepared cache helper changed')
    state['CPU_source_seal_owner'] = dict(plan=intent['native_plan'], publication=str(args.publication),
        phase='staged-source-cache-retirement', GPU_calls=0, title_launches=0, ordinary_helper_completion_pending=True)
    state['source_publication_owner']['phase'] = 'staged-source-cache-retirement'
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    result = completed_operation(lan_module(), native, args.out / 'native')
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'], 'The exact helper must retire positively')
    raw = Path(result['raw']['path']).read_bytes()
    found = re.findall(rb'COMPLEMENT_COMPLETE (.*)', raw)
    need(len(found) == 1, 'One complete cache-retirement receipt required')
    observed = {key.decode(): int(value) for key, value in re.findall(rb'\b([A-Za-z_]+)=(-?\d+)', found[0])}
    identities = {int(index): list(map(int, values.split(b','))) for index, values in
                  re.findall(rb'STAGED_CACHE_ID index=(\d+) values=([0-9,]+)', raw)}
    need(set(identities) == set(range(48)) and all(len(row) == 10 for row in identities.values()) and
         observed['returned_error'] == 0 and observed['scanned'] > 0 and observed['total'] == len(windows),
         'All48 metadata guards and each readonly mapping/fd must finish positively')
    save(args.out / 'result.private.json', dict(completed=True, native=result, observations=observed,
        starting_window=first, remaining_windows=len(windows) - first - observed['scanned'],
        staged_identities=identities, all_mappings_and_FDs_positively_retired=True,
        source_writes=0, original_cache_operations_exact=True, staging_metadata_admission_changed=True,
        source_content_not_yet_qualified=True,
        model_launch_admission=False, sufficient_for_changed_sealer=observed['free_after'] >= 7374))
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == intent['native_plan'], 'Never clear another CPU owner')
    state.pop('CPU_source_seal_owner')
    state['source_publication_owner'].update(phase='after-positive-staged-cache-retirement',
        staged_cache_results=[record(path) for path in [*args.completed_scope, args.out / 'result.private.json']])
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, observations=observed, source_writes=0, original_sealer_floor=1201,
                         model_floor=7374, mappings_and_FDs_retired=True)))


if __name__ == '__main__':
    main()
