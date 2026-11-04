#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove reviewed trial copies whose content matches a separately retained input."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from retire_unselected_PC_artifacts import EXPECTED, local_references, snapshot
from start_success_route import load, need, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    intent_path, result_path = args.prior / 'intent.private.json', args.prior / 'result.private.json'
    intent, result = load(intent_path), load(result_path)
    base = Path(intent['base']).resolve()
    need(base == EXPECTED.resolve() and args.out.resolve().is_relative_to(base), 'Use only the exact owned experiment directory')
    need(result['completed'] and result['selected_canonical_hashes_unchanged'] and
         result['all_original_BF16_source_metadata_unchanged'] and not result['retained_shared_inputs'],
         'Require the completed canonical full-hash guard from the preceding cleanup')
    protected = intent['protected']
    need([snapshot(Path(row['path'])) for row in protected] == protected, 'Canonical inputs changed after their positive hash guard')
    protected_ids = {(row['device'], row['inode']) for row in protected}
    targets = [row for row in intent['retained'] if row['reason'] == 'exact selected/provenance content']
    content, paths = set(), set()
    current = Path('D:/PS5-AI/qwen-flash-next/current')
    for path in current.rglob('*.json'):
        if path.name != 'active-console.private.json':
            local_references(load(path), paths, content)
    verified = []
    for row in targets:
        path = Path(row['path'])
        actual = snapshot(path)
        need(path.resolve().is_relative_to(base) and not path.is_symlink() and
             (row['device'], row['inode']) not in protected_ids and
             all(actual[key] == row[key] for key in ('path', 'bytes', 'inode', 'device', 'mtime_ns', 'links', 'mode')),
             'Delete only the exact reviewed duplicate path, never a canonical file or hardlink')
        full = record(path)
        need((full['bytes'], full['sha256']) in content and path.resolve() not in paths,
             'The complete current bytes must match recorded provenance and have no selected path dependency')
        verified.append(full)
    if args.check_only:
        print(json.dumps(dict(checked=True, target_files=len(verified), full_current_content_hashes=verified,
            all_have_no_current_path_or_file_identity_dependency=True,
            protected_current_metadata_unchanged=True, deletions=0, PS5_operations=0)), flush=True)
        return
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / 'intent.private.json', dict(prior_intent=record(intent_path), prior_result=record(result_path),
        targets=targets, current_full_content_hashes=verified, protected=protected, source=record(Path(__file__)), recursive_deletion=False,
        protected_inputs_rehashed=False, PS5_operations=0))
    for index, row in enumerate(targets):
        Path(row['path']).unlink()
        save(args.out / ('removed-' + str(index) + '.private.json'), dict(path=row['path'], removed=True))
    need([snapshot(Path(row['path'])) for row in protected] == protected, 'Canonical identities must remain unchanged')
    save(args.out / 'result.private.json', dict(completed=True, removed_files=len(targets),
        removed_bytes=sum(row['bytes'] for row in targets), canonical_identity_metadata_unchanged=True,
        prior_full_canonical_hash_guard=record(result_path), recursive_deletion=False, PS5_operations=0))
    print(json.dumps(dict(completed=True, removed_duplicate_files=len(targets),
                         removed_bytes=sum(row['bytes'] for row in targets), canonical_inputs_preserved=True)), flush=True)


if __name__ == '__main__':
    main()
