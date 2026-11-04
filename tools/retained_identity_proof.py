#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify an immutable identity receipt after byte-identical artifact retention."""
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load, need


def require_same_provider(original_record, selected_record, current):
    """Allow only a canonical path change; retain every original identity field."""
    need(record(original_record['path']) == original_record, 'Original identity receipt changed')
    need(record(selected_record['path']) == selected_record, 'Selected identity receipt changed')
    if selected_record == original_record:
        return True
    original, selected = load(original_record['path']), load(selected_record['path'])
    need(selected.get('canonical_path_rebind_of') == original_record and
         type(selected.get('recompilations')) is int and selected['recompilations'] == 0,
         'Retained identity receipt must authenticate its unchanged original')
    artifact = selected['artifact']
    need(all(artifact[key] == original['artifact'][key] for key in ('bytes', 'sha256')),
         'Retained identity artifact differs from the physically observed provider')
    retained = load(Path(current) / 'provenance/retained-relink-inputs.private.json')
    need(sum(all(row[key] == artifact[key] for key in ('path', 'bytes', 'sha256'))
             for row in retained) == 1 and record(artifact['path']) == artifact,
         'Identity artifact must be an unchanged unique canonical relink input')
    expected = dict(original, artifact=artifact, canonical_path_rebind_of=original_record, recompilations=0)
    need(selected == expected, 'Retention must preserve every original identity receipt field')
    return True
