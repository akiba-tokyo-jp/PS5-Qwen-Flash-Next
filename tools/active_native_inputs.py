#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Select the current sealed link, not every unused historical ancestor ELF."""
from pathlib import Path

def active_link_inputs(receipt):
    """Build-time qualification still verifies the complete source ancestry.

    Runtime stages bind the exact native/package receipts, SELF, current image,
    every explicit linked object/archive and this image's generated source view.
    Historical images that are not inputs to this link cannot change its bits.
    Controller/observer source guards are retained separately by the operator.
    """
    rows={}
    for row in receipt['inputs_before']+[receipt['artifact']]:
        key=str(Path(row['path']))
        previous=rows.setdefault(key,row)
        if previous!=row:raise ValueError('Ambiguous captured native input')
    artifact=Path(receipt['artifact']['path']);wanted={str(artifact)}
    for argument in receipt['link_command']:
        if not argument.startswith('-')and Path(argument).suffix.lower()in('.o','.obj','.a'):
            key=str(Path(argument))
            if key not in rows:raise ValueError('Every explicit linked object/archive must have a captured digest: '+key)
            wanted.add(key)
    wanted.update(key for key in rows if Path(key).parent==artifact.parent)
    result=[rows[key]for key in sorted(wanted)]
    if not any(Path(row['path']).suffix=='.a'for row in result):raise ValueError('The current linked archives are required')
    return result
