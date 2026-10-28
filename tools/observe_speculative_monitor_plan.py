#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the original boot-bound observer with isolated combined-mode validators."""
import json
from pathlib import Path
import sys
from speculative_monitor_result import install
from observe_boot_bound_plan import main as boot_bound_main

def main():
    require='--binding'
    if sys.argv.count(require)!=1:raise ValueError('One exact observer binding required')
    path=Path(sys.argv[sys.argv.index(require)+1])
    state=install(json.loads(path.read_text()))
    boot_bound_main()
    if state['quality_review']is None:raise ValueError('No complete actual combined-mode quality result')
    print(json.dumps(dict(combined_native_monitor_review=state['quality_review'],legacy_validator_files_changed=False)),flush=True)

if __name__=='__main__':main()
