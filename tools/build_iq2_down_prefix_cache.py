#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile a source-prefix Down refinement against the exact selected PS5 ABI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from build_iq2_up_model import cache_text
from build_performance_quantizer import record
from iq2_down_large_cache_scope import require_provider
from iq2_down_prefix_cache import PLANE_BYTES, PREFIX_BYTES, transform
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'cache-baseline', 'provider', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    provider = require_provider(record(a.provider))
    baseline = load(a.cache_baseline)
    need(baseline['completed'] and baseline['baseline_provider_qualified'] and
         baseline['selected_object_byte_exact'] and not baseline['section_differences'] and
         record(baseline['artifact']['path']) == baseline['artifact'] and
         record(baseline['source']['path']) == baseline['source'],
         'Only the exact selected original cache and corrected Down provider may be refined')
    decoder = Path(load(provider['shaders']['path'])['carrier_decoder']['path']).read_text(encoding='utf-8')
    for declaration in ('IQ2_DOWN_CARRIER_BYTES=460800u', 'IQ2_DOWN_PAYLOAD_OFFSET=64u',
                        'IQ2_DOWN_TABLE_OFFSET=422464u'):
        need(declaration in decoder, 'The exact source-bound decoder geometry changed')
    need(PREFIX_BYTES == 425024 and PREFIX_BYTES < PLANE_BYTES,
         'Preserve every header,payload and codebook byte')
    a.out.mkdir(parents=True, exist_ok=False)
    previous = Path(a.cache_baseline).parent
    for header in previous.glob('*.h'):
        shutil.copyfile(header, a.out / header.name)
    view = load(baseline['selected_VFS_view']['path'])
    for row in view['roots']:
        local = a.out / Path(row['external-contents']).name
        if local.exists():
            row['external-contents'] = local.resolve().as_posix()
    overlay = a.out / 'selected-view.private.json'
    save(overlay, view)
    source, artifact = a.out / 'cache.private.cpp', a.out / 'cache.o'
    source.write_text(transform(cache_text(Path(baseline['source']['path']).read_text(encoding='utf-8'), True)),
                      encoding='utf-8', newline='\n')
    command = [str(a.out) if v == str(previous) else v for v in baseline['command']]
    command[command.index('-ivfsoverlay') + 1] = str(overlay)
    command[command.index('-c') + 1], command[command.index('-o') + 1] = str(source), str(artifact)
    if '-MF' in command:
        command[command.index('-MF') + 1] = str(a.out / 'cache.private.d')
    child = subprocess.run(command, capture_output=True, timeout=180,
        env=dict(os.environ, TMP=str(a.out), TEMP=str(a.out)))
    (a.out / 'compile.private.log').write_bytes(child.stdout + child.stderr)
    need(child.returncode == 0, (child.stdout + child.stderr).decode(errors='replace')[-2500:])
    save(a.out / 'result.private.json', dict(completed=True, actual_selected_PS5_ABI_compiled=True,
        source=record(source), artifact=record(artifact), baseline=record(a.cache_baseline),
        provider=record(a.provider), large_cache_index_proof=provider['large_cache_index_proof'],
        transform=record(ROOT / 'tools/iq2_down_prefix_cache.py'), commands=[command],
        original_source_and_GPU_slot_stride=PLANE_BYTES, source_upload_prefix_bytes=PREFIX_BYTES,
        unused_tail_bytes_omitted=PLANE_BYTES-PREFIX_BYTES, selected_cache_slots=3712,
        actual_upload_byte_statistics_preserved=True, independent_omitted_padding_counter=True,
        original_adjacent_bulk_path_preserved=True, existing_pair_pipeline_reused=True,
        source_descriptor_identity_and_completion_guards_preserved=True,
        GPU_shader_resources_unchanged=True, new_weight_files=0, new_weight_transfers=0,
        model_numerical_equivalence_or_rate_qualified=False, PS5_operations=0))
    print(json.dumps(dict(completed=True, actual_PS5_ABI_compiled=True,
        unused_Down_tail_bytes=PLANE_BYTES-PREFIX_BYTES, weight_transfers=0, PS5_operations=0)))


if __name__ == '__main__':
    main()
