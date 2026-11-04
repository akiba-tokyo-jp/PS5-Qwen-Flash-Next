#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check canonical identity receipt retention and reject altered evidence offline."""
import argparse
import copy
from pathlib import Path
import tempfile

from build_performance_quantizer import record
from retained_identity_proof import require_same_provider
from start_success_route import load, need, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'package', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    state = load(args.current / 'active-console.private.json')
    original = load(state['required_bundle_inputs']['path'])['identity_provider']
    selected = load(args.package)['required_bundle_identity_audit']['provider']
    require_same_provider(original, original, args.current)
    require_same_provider(original, selected, args.current)
    receipt = load(selected['path'])
    rejected = []
    with tempfile.TemporaryDirectory(prefix='qwen-retained-identity-') as directory:
        root = Path(directory)
        changes = {
            'input-identity': lambda x: x['inputs'][0]['identity'].__setitem__(0, x['inputs'][0]['identity'][0] + 1),
            'owner-policy': lambda x: x.__setitem__('original_owner_unchanged', False),
            'recompiled': lambda x: x.__setitem__('recompilations', 1),
            'artifact-bytes': lambda x: x['artifact'].__setitem__('bytes', x['artifact']['bytes'] + 1),
            'artifact-digest': lambda x: x['artifact'].__setitem__('sha256', '0' * 64),
            'noncanonical-path': lambda x: x['artifact'].__setitem__('path', str(root / 'other.o')),
            'unrelated-original': lambda x: x['canonical_path_rebind_of'].__setitem__('sha256', '0' * 64),
            'extra-field': lambda x: x.__setitem__('unqualified_exception', True),
        }
        for name, change in changes.items():
            value = copy.deepcopy(receipt)
            change(value)
            path = root / (name + '.json')
            save(path, value)
            try:
                require_same_provider(original, record(path), args.current)
            except RuntimeError:
                rejected.append(name)
            else:
                raise AssertionError('Altered identity receipt accepted: ' + name)
        altered = dict(selected, sha256='0' * 64)
        try:
            require_same_provider(original, altered, args.current)
        except RuntimeError:
            rejected.append('receipt-digest')
        else:
            raise AssertionError('Altered receipt digest accepted')
    need(len(rejected) == 9, 'Every altered receipt must be rejected')
    save(args.out, dict(completed=True, original_provider=original, selected_provider=selected,
        positive_cases=2, rejected_controls=rejected, PS5_operations=0))
    print('Canonical identity receipt: 2 positive and 9 rejection controls passed; PS5 operations: 0')


if __name__ == '__main__':
    main()
