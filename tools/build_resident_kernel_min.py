#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the explicit kernel-minimum experiment using the coherent app builder."""
import json
import os
from pathlib import Path
import sys
import build_resident_OS_reserve as builder
import resident_kernel_min_scope as scope
from shader_storage import record


def main():
    out = Path(sys.argv[sys.argv.index('--out') + 1])
    for name in ('SCOPE', 'entry', 'implementation', 'source_header', 'system_header'):
        setattr(builder, name, getattr(scope, name))
    builder.main()
    path = out / 'receipt.private.json'
    receipt = json.loads(path.read_text())
    receipt['post_context_OS_reserve'].update(selected_post_context_floor_pages=962,
        OS_threshold_counters_unchanged=True, application_margin_revised=True,
        kernel_minimum_experiment=True, native_qualification_pending=True)
    receipt['inputs_before'] += [record(x) for x in (Path(__file__), Path(scope.__file__), Path(builder.__file__))]
    temporary = out / 'kernel-minimum-receipt.next.private.json'
    temporary.write_text(json.dumps(receipt, indent=2) + '\n')
    os.replace(temporary, path)
    print(json.dumps(dict(kernel_minimum_experiment_built=True, selected_post_context_pages=962,
        GPU_initialization_and_context_prices_unchanged=True, OS_counter_writes=0, PS5_operations=0)), flush=True)


if __name__ == '__main__':
    main()
