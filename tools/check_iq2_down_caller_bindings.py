#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check separate replacement arrays and unchanged original startup references in the actual linked ELF."""
import argparse
import json
from pathlib import Path
import struct

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load, need, save


def exact(row):
    need(record(row['path']) == row, 'A bound caller-array input changed')
    return load(row['path'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'fixture', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    fixture = load(a.fixture)
    linked = exact(fixture['relink'])
    provider = exact(linked['model_resource_provider'])
    build = exact(provider['shaders'])
    need(linked['CPU_shader_resource_admission_before_GPU'] and linked['fresh_changed_CPU_startup_required'] and
         provider['original_shader_registry_unchanged'] and provider['original_startup_lookup_expectations_preserved'] and
         provider['separate_GPU_caller_arrays'] == 3 and provider['new_global_initializers'] == 0,
         'The corrected provider and mandatory fresh CPU startup are required')
    image = linked['artifact']
    need(record(image['path']) == image, 'The corrected actual ELF changed')
    e = ELF(Path(image['path']))
    native_receipt = a.current / 'provenance/native-link.receipt.private.json'
    tables = load(native_receipt)['lossless_shader_storage']['lookup_tables']
    selected = [t for t in tables if t['name'] in
        ('arr_dmmv_q2_0_f32_f32', 'arr_dmmv_q2_0_f16_f32', 'arr_dmmv_id_q2_0_f32_f32')]
    shaders = {r['name']: r for r in build['shaders']}
    checked = []
    for t in selected:
        name = t['name']
        new = 'qwen_iq2_down_' + name
        old_lengths = struct.unpack('<3Q', e.symbol_data(name + '_len'))
        new_lengths = struct.unpack('<3Q', e.symbol_data(new + '_len'))
        for index, target in enumerate(t['targets']):
            expected = 'qwen_iq2_down_' + target
            old_at = e.symbols[name + '_data']['value'] + 8 * index
            new_at = e.symbols[new + '_data']['value'] + 8 * index
            need(e.pointer(old_at) == e.symbols[target + '_data']['value'] and
                 old_lengths[index] == struct.unpack('<Q', e.symbol_data(target + '_len'))[0],
                 'Every original observed startup lookup must retain its original pointer and length')
            need(e.pointer(new_at) == e.symbols[expected + '_data']['value'] and
                 new_lengths[index] == shaders[target]['artifact']['bytes'],
                 'Every separate caller array must contain the actual replacement pointer and full byte length')
            checked.append(dict(array=name, index=index, original_startup_reference_exact=True,
                replacement_reference_exact=True, replacement_bytes=new_lengths[index]))
    need(len(selected) == 3 and len(checked) == 9, 'All three arrays and nine elements must be checked')
    for name, shader in shaders.items():
        need(record(shader['artifact']['path']) == shader['artifact'] and
             e.symbol_data('qwen_iq2_down_' + name + '_data') == Path(shader['artifact']['path']).read_bytes(),
             'All thirteen actual embedded resources must be byte-identical to the validated SPIR-V')
    need(any('initialize_native_shader_assets' in name for name in e.symbols) and
         any('initialize_native_shader_file' in name for name in e.symbols),
         'The actual corrected ELF must retain both required CPU initialization implementations')
    support = a.fixture.parent / 'paired_down_native_support.h'
    text = support.read_text()
    need(text.index('const auto shader_CPU_admission=qwen_paired_down_prepare_CPU();') <
         text.index('if(native_binding.at("CPU_only").get<bool>())'),
         'The changed CPU proof must execute resource admission before its early return')
    save(a.out, dict(completed=True, fixture=record(a.fixture), actual_ELF=image,
        provider=linked['model_resource_provider'], original_receipt=record(native_receipt),
        support=record(support), arrays=checked, original_startup_registry_unchanged=True,
        replacement_SPIRV_resources_byte_exact=13, actual_CPU_initialization_functions_retained=True,
        fresh_changed_CPU_startup_required=True, native_CPU_or_GPU_qualified=False, PS5_operations=0))
    print(json.dumps(dict(completed=True, original_and_replacement_array_elements=9,
        replacement_resources=13, PS5_operations=0)))


if __name__ == '__main__':
    main()
