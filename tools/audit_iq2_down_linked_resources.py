#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check actual linked Down resources and preserve original startup references."""
import argparse
from pathlib import Path
import struct

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load, need, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'fixture', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    fixture = load(a.fixture)
    link_row = fixture['relink']
    need(record(link_row['path']) == link_row, 'The completed fixture link changed')
    link = load(link_row['path'])
    provider_row = link['model_resource_provider']
    need(record(provider_row['path']) == provider_row, 'The selected resource provider changed')
    provider = load(provider_row['path'])
    shader_row = provider['shaders']
    need(record(shader_row['path']) == shader_row, 'The selected shader build changed')
    shaders = load(shader_row['path'])['shaders']
    linked = ELF(Path(link['artifact']['path']))
    original = ELF(a.current / 'provenance/qwen-native.pie.elf')
    receipt_path = a.current / 'provenance/native-link.receipt.private.json'
    receipt = load(receipt_path)
    resources = []
    replacement_lengths = {}
    for row in shaders:
        name = row['name']
        artifact = row['artifact']
        need(record(artifact['path']) == artifact, 'The exact resource bytes changed')
        replacement_lengths[name] = artifact['bytes']
        length_symbol = 'qwen_iq2_down_' + name + '_len'
        need(linked.symbol_data('qwen_iq2_down_' + name + '_data') == Path(artifact['path']).read_bytes() and
             (length_symbol not in linked.symbols or
              struct.unpack('<Q', linked.symbol_data(length_symbol))[0] == artifact['bytes']) and
             all(linked.symbol_data(name + suffix) == original.symbol_data(name + suffix)
                 for suffix in ('_data', '_len')), 'Actual replacement bytes and original codec tokens must remain exact')
        resources.append(dict(name=name, bytes=artifact['bytes'], replacement_exact=True, original_token_exact=True))
    arrays = []
    for table in receipt['lossless_shader_storage']['lookup_tables']:
        name = table['name']
        if name not in ('arr_dmmv_q2_0_f32_f32', 'arr_dmmv_q2_0_f16_f32', 'arr_dmmv_id_q2_0_f32_f32'):
            continue
        for prefix in ('', 'qwen_iq2_down_'):
            base = linked.symbols[prefix + name + '_data']['value']
            lengths = struct.unpack('<3Q', linked.symbol_data(prefix + name + '_len'))
            for i, target in enumerate(table['targets']):
                symbol = prefix + target + '_data'
                need(linked.pointer(base + 8 * i) == linked.symbols[symbol]['value'],
                     'Each actual caller/startup pointer must select its exact declared resource')
                expected_length = replacement_lengths[target] if prefix else struct.unpack('<Q', linked.symbol_data(target + '_len'))[0]
                need(lengths[i] == expected_length,
                     'The selected actual resource length must remain exact')
        arrays.append(dict(name=name, original_startup_pairs=3, replacement_caller_pairs=3))
    need(len(resources) == provider['redirected_resource_pairs'] == 17 and len(arrays) == 3 and
         provider['original_shader_registry_unchanged'] and
         Path(provider['shader_registry']['path']).read_bytes() == Path(provider['selected_shader_registry']['path']).read_bytes() and
         linked.symbols['__cxx_global_var_init.2']['size'] > 0,
         'All seventeen resources, nine caller pairs and the original startup registry must be present')
    save(a.out, dict(completed=True, fixture=record(a.fixture), actual_ELF=record(link['artifact']['path']),
        provider=provider_row, original_receipt=record(receipt_path), resources=resources, arrays=arrays,
        original_startup_registry_unchanged=True, actual_CPU_initialization_functions_retained=True,
        fresh_changed_CPU_startup_required=True, native_CPU_or_GPU_qualified=False, PS5_operations=0))
    print(dict(completed=True, exact_resources=17, exact_caller_pairs=9, PS5_operations=0))


if __name__ == '__main__':
    main()
