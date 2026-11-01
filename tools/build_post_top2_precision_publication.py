#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the existing new-only CPU publisher to the audited109-tensor overlay."""
from pathlib import Path
if __name__=='__main__':
    path=Path(__file__).with_name('build_precision_publication.py');source=path.read_text()
    old="prep['selected_tensors']in(48,96,108)";assert source.count(old)==1
    source=source.replace(old,"prep['selected_tensors']==109")
    exec(compile(source,str(path)+'#exact109-tensors','exec'),dict(__file__=__file__,__name__='__main__'))
