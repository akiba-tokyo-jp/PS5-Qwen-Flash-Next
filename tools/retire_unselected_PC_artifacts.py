#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire owned experiment binaries while preserving canonical inputs and logs."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import stat

from build_performance_quantizer import record
from start_success_route import load, need, save
from success_case_control import current_files

EXPECTED = Path('D:/PS5-AI/qwen-flash-next/performance-20261102')
SUFFIXES = {'.a', '.o', '.obj', '.elf', '.self', '.exe', '.dll', '.so', '.dylib', '.lib', '.pdb', '.spv', '.bc', '.pack', '.gguf', '.bin', '.npy', '.npz'}


def snapshot(path):
    value = path.stat()
    return dict(path=str(path.resolve()), bytes=value.st_size, inode=value.st_ino, device=value.st_dev,
                mtime_ns=value.st_mtime_ns, links=value.st_nlink, mode=value.st_mode)


def local_references(value, paths, content):
    if isinstance(value, dict):
        if isinstance(value.get('sha256'), str) and isinstance(value.get('bytes'), int):
            content.add((value['bytes'], value['sha256']))
        for item in value.values():
            local_references(item, paths, content)
    elif isinstance(value, list):
        for item in value:
            local_references(item, paths, content)
    elif isinstance(value, str):
        if len(value) > 2 and value[1:3] in (':/', ':\\'):
            path = Path(value)
            if path.is_file():
                paths.add(path.resolve())
        elif value.lstrip().startswith(('{', '[')):
            try:
                nested = json.loads(value)
            except (ValueError, TypeError):
                return
            local_references(nested, paths, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'base', 'final-review', 'original-receipt', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute-prepared', action='store_true')
    parser.add_argument('--protected-runtime-plan', type=Path, action='append', default=[])
    args = parser.parse_args()
    base = args.base.resolve()
    need(base == EXPECTED.resolve() and base.is_dir() and args.out.resolve().is_relative_to(base),
         'Resolve the exact explicitly owned experiment directory before any file retirement')
    review = load(args.final_review)
    need(review['completed'] and review['all_pending_profiles_resolved'] and review['production_current_verified'] and
         review['no_unknown_owners'], 'Finish every model/adoption decision before retiring experiment binaries')
    current = args.current.resolve()
    need(not current.is_relative_to(base), 'The canonical current directory must remain outside the retirement root')
    selected = current_files(current) + load(current / 'provenance/retained-relink-inputs.private.json')
    protected_paths, protected_content = set(), set()
    for path in current.rglob('*.json'):
        if path.name != 'active-console.private.json':
            local_references(load(path), protected_paths, protected_content)
    for path in args.protected_runtime_plan:
        local_references(load(path), protected_paths, protected_content)
    protected_paths.update(Path(row['path']).resolve() for row in selected)
    original = load(args.original_receipt)
    need(original['original_shards_verified'] and not original['learned_inference_performed'],
         'Preserve all already authenticated original BF16 sources without hashing them again')
    originals = []
    for row in original['files']:
        path = (args.original_receipt.parent / row['path']).resolve()
        need(path.is_file() and path.stat().st_size == row['bytes'], 'An authenticated original source is missing')
        protected_paths.add(path)
        originals.append(snapshot(path))
        if row.get('sha256'):
            protected_content.add((row['bytes'], row['sha256']))
    protected = [snapshot(path) for path in sorted(protected_paths)]
    protected_ids = {(row['device'], row['inode']) for row in protected}
    selected_records = {str(Path(row['path']).resolve()): {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in selected}
    canonical_content = {(row['bytes'], row['sha256']) for row in selected_records.values()}
    canonical_content.update((row['bytes'], row['sha256']) for row in original['files'] if row.get('sha256'))
    for row in selected_records.values():
        need(record(row['path']) == row, 'A selected canonical runtime/rebuild input changed')
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        targets, retained, groups = [], [], Counter()
        unmapped_content = protected_content - canonical_content
        sizes = {size for size, _ in unmapped_content}
        for directory, directories, names in os.walk(base, followlinks=False):
            directories[:] = [name for name in directories if not (Path(directory) / name).is_symlink() and
                not getattr(Path(directory) / name, 'is_junction', lambda: False)()]
            for name in names:
                path = Path(directory) / name
                if path.suffix.lower() not in SUFFIXES or path.is_symlink():
                    continue
                resolved = path.resolve()
                need(resolved.is_relative_to(base), 'A candidate escaped the exact retirement directory')
                info = snapshot(path)
                key = (info['device'], info['inode'])
                groups[key] += 1
                if resolved in protected_paths or key in protected_ids:
                    retained.append(dict(info, reason='canonical or authenticated source input'))
                    continue
                lower = name.lower()
                if lower.endswith('.private.bin') or lower.startswith(('native.', 'terminal.', 'console.', 'observations.')) or 'headless-observer' in path.parts:
                    retained.append(dict(info, reason='native log or evidence record'))
                    continue
                if path.suffix.lower() in ('.bin', '.gguf', '.pack', '.npy', '.npz') and info['bytes'] in sizes:
                    item = record(path)
                    if (item['bytes'], item['sha256']) in unmapped_content:
                        retained.append(dict(info, reason='exact selected/provenance content'))
                        continue
                targets.append(info)
        save(args.out / 'intent.private.json', dict(base=str(base), targets=targets, retained=retained,
            candidate_link_groups=[dict(device=key[0], inode=key[1], inside_candidates=count) for key, count in groups.items()],
            protected=protected, originals=originals, selected_records=list(selected_records.values()),
            final_review=record(args.final_review), original_receipt=record(args.original_receipt),
            source=record(Path(__file__)), recursive_deletion=False, source_text_and_logs_preserved=True))
        print(json.dumps(dict(prepared=True, candidate_binaries=len(targets), candidate_bytes=sum(row['bytes'] for row in targets),
                              protected_or_evidence_binaries=len(retained), PS5_operations=0)), flush=True)
        return
    intent = load(args.out / 'intent.private.json')
    need(intent['base'] == str(base) and intent['source'] == record(Path(__file__)) and
         intent['final_review'] == record(args.final_review) and intent['original_receipt'] == record(args.original_receipt) and
         intent['protected'] == protected and intent['originals'] == originals,
         'The exact protected current/original source selection changed')
    counts = {(row['device'], row['inode']): row['inside_candidates'] for row in intent['candidate_link_groups']}
    removed, skipped = [], []
    for row in intent['targets']:
        path = Path(row['path'])
        need(path.resolve().is_relative_to(base) and not path.is_symlink(), 'Never follow a target outside the owned root')
        actual = snapshot(path)
        need(all(actual[key] == row[key] for key in ('path', 'bytes', 'inode', 'device', 'mtime_ns')) and
             (actual['device'], actual['inode']) not in protected_ids, 'A planned trial file changed or became protected')
        try:
            path.unlink()
        except PermissionError:
            if row['links'] > counts[(actual['device'], actual['inode'])]:
                skipped.append(dict(row, reason='readonly hardlink has an external or noncandidate owner'))
                continue
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
            path.unlink()
        removed.append(row)
    for row in selected_records.values():
        need(record(row['path']) == row, 'A canonical input changed during trial retirement')
    need([snapshot(Path(row['path'])) for row in protected] == protected and
         [snapshot(Path(row['path'])) for row in originals] == originals,
         'Protected current and original source identities must remain unchanged')
    save(args.out / 'result.private.json', dict(completed=True, removed_files=len(removed),
        removed_bytes=sum(row['bytes'] for row in removed), removed=removed, retained_shared_inputs=skipped,
        retained_canonical_and_evidence=intent['retained'], selected_canonical_hashes_unchanged=True,
        all_original_BF16_source_metadata_unchanged=True, original_BF16_sources_rehashed=False,
        source_text_and_logs_preserved=True, recursive_deletion=False, PS5_operations=0))
    print(json.dumps(dict(completed=True, removed_files=len(removed), removed_bytes=sum(row['bytes'] for row in removed),
                          shared_inputs_retained=len(skipped), canonical_and_original_sources_preserved=True)), flush=True)


if __name__ == '__main__':
    main()
