#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the read-only capacity ABI to compare the two actual storage paths."""
from pathlib import Path
if __name__=='__main__':
    p=Path(__file__).with_name('build_filesystem_capacity.py');s=p.read_text()
    assert s.count('filesystem_capacity.cpp')==2
    s=s.replace('filesystem_capacity.cpp','filesystem_scope_capacity.cpp')
    exec(compile(s,str(p)+'#two-actual-filesystems','exec'),dict(__file__=__file__,__name__='__main__'))
