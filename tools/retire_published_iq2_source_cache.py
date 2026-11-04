#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the qualified cache-retirement body on newly sealed IQ2 source files."""
import argparse
import ast
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, build, current_files, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'publication', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--completed-scope', type=Path, action='append', default=[])
    p.add_argument('--target-free-pages', type=int, default=7374)
    p.add_argument('--Up-prefix', action='store_true', help='Select the distinct sealed forty-three-file Up prefix instead of the last four')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    need(7374 <= a.target_free_pages <= 16384, 'Preserve the original model screen and bounded source scope')
    publication = load(a.publication)
    plan_path = a.publication.parent / 'plan.private.json'
    plan = load(plan_path)
    need(publication['completed'] and publication['whole_new_bytes_and_all_parent_identities_qualified'] and
         record(publication['source_integrity']['path']) == publication['source_integrity'],
         'Only the positively sealed new publication is eligible')
    seal = load(publication['source_integrity']['path'])
    known = {r['path']: r for r in seal['parts']}
    candidates = [r for r in plan['files'] if r['local']['bytes'] == 216268800]
    need(len(candidates) == (43 if a.Up_prefix else 4),
         'Only the exact sealed Up prefix or distinct final four source files are eligible')
    files, windows = [], []
    for row in reversed(candidates):
        source = known[row['application']]
        need(source['bytes'] == row['local']['bytes'] and source['sha256'] == row['local']['sha256'] and
             source['path'].startswith(plan['application_directory'] + '/') and
             source['identity'][5] == source['bytes'], 'Each owned sealed file and native identity must be exact')
        index = len(files)
        files.append(dict(source, mounted_path=ALIAS + source['path'][5:]))
        for offset in range(0, source['bytes'], 64 << 20):
            size = min(64 << 20, source['bytes'] - offset)
            need(not (offset % 16384 or size % 16384), 'Only complete aligned source windows are eligible')
            windows.append(dict(file=index, offset=offset, bytes=size))
    state = load(a.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('source_publication_owner') and
         not state.get('CPU_source_seal_owner'), 'The current application must be positively idle')
    selected, first = current_files(a.current), 0
    for path in a.completed_scope:
        done, intent = load(path), load(path.parent / 'intent.private.json')
        need(done['completed'] and done['all_mappings_and_FDs_positively_retired'] and
             intent['files'] == files and intent['windows'] == windows and
             intent['boot'] == state['current_boot'] and done['starting_window'] == first,
             'Only an exact positively retired prefix may be skipped')
        first += done['observations']['scanned']
    need(first < len(windows), 'Never repeat a completed source window')
    template = Path(__file__).with_name('observe_source_cache_complement.py')
    literals = [n.value for n in ast.walk(ast.parse(template.read_text(encoding='utf-8')))
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and
                n.value.startswith('#include <sys/mman.h>') and 'struct CacheSource' in n.value]
    need(len(literals) == 1, 'Reuse the exact existing native cache-retirement body')
    context = literals[0].replace('FIRST_WINDOW', str(first)).replace('TARGET_FREE_PAGES', str(a.target_free_pages) + 'u')
    file_rows = ','.join('{' + json.dumps(r['mounted_path']) + ',{' + ','.join(str(v) + 'ULL' for v in r['identity']) + '}}' for r in files)
    window_rows = ','.join('{' + str(r['file']) + ',' + str(r['offset']) + 'ULL,' + str(r['bytes']) + 'ULL}' for r in windows)
    context = context.replace('FILES', file_rows).replace('WINDOWS', window_rows)
    a.out.mkdir(parents=True, exist_ok=False)
    native_plan = build(a.workspace, a.mount_plan, selected, selected, [], 'retire-completed-images',
                        a.out / 'native', completed_images_context=context)
    save(a.out / 'intent.private.json', dict(publication=record(a.publication), plan=record(plan_path),
        template=record(template), files=files, windows=windows, starting_window=first,
        boot=state['current_boot'], selected=selected, target_free_pages=a.target_free_pages,
        publication_scope='Up-prefix43' if a.Up_prefix else 'Up-final4',
        maximum_live_readonly_mapping_bytes=64 << 20, maximum_sync_extent_bytes=8 << 20,
        maximum_sync_calls=128, maximum_scope_seconds=20, native_API_body_unchanged=True,
        old_original_source_windows_replayed=0, source_writes=0, global_cache_purge=False))
    if not a.execute:
        return
    native = completed_operation(lan_module(), native_plan, a.out / 'native')
    need(native['completed'] and native['helper_exited'] and native['helper_files_removed'] and
         native['operation_calls'] <= 128, 'All readonly mappings, descriptors and the helper must retire')
    rows = re.findall(rb'COMPLEMENT_COMPLETE (.*)', Path(native['raw']['path']).read_bytes())
    need(len(rows) == 1, 'One exact returned source-cache receipt is required')
    observations = {k.decode(): int(v) for k, v in re.findall(rb'\b([A-Za-z_]+)=(-?\d+)', rows[0])}
    need(observations['returned_error'] == 0, 'A returned API refusal stops without replay')
    save(a.out / 'result.private.json', dict(completed=True, native=native, observations=observations,
        starting_window=first, all_mappings_and_FDs_positively_retired=True,
        remaining_windows=len(windows) - first - observations['scanned'],
        source_writes=0, old_original_source_windows_replayed=0, global_cache_purge=False,
        model_launch_admission=False, exclusive_global_RAM_gain_claimed=False))
    print(json.dumps(dict(completed=True, observations=observations)), flush=True)


if __name__ == '__main__':
    main()
