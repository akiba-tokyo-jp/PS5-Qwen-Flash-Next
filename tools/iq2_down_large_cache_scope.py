#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind corrected Down indexing and all changed graphs to full-cache admission."""
from build_performance_quantizer import record
from iq2_down_ggml_completion import validate_terminal as validate_original_terminal
from start_success_route import load, need


def validate_terminal(terminal):
    need(terminal.get('large_cache_index_safe') is True and
         terminal.get('F16_storage_FP32_accumulation') is True and
         type(terminal.get('completed_GGML_case_prefix')) is int and
         terminal['completed_GGML_case_prefix'] == 0 and
         type(terminal.get('reused_decode_cases')) is int and
         terminal['reused_decode_cases'] == 0,
         'Corrected indexing changes all twelve graphs; no prior decode graph may be reused')
    # Reuse the original all-graph ownership, fence and negative-stop rules.
    normalized = dict(terminal, F16_storage_FP32_accumulation=False)
    return validate_original_terminal(normalized)


def require_provider(row):
    need(record(row['path']) == row, 'The corrected Down provider changed')
    provider = load(row['path'])
    need(provider['completed'] and provider.get('large_cache_index_safe') is True and
         provider['F16_arithmetic_only'] and provider['redirected_resource_pairs'] == 17 and
         provider['changed_decode_addressing'] and provider['required_new_native_graphs'] == 12 and
         provider['GPU_executable_sections_byte_exact'] and
         provider['original_shader_registry_unchanged'] and provider['new_global_initializers'] == 0,
         'A full-cache model requires the corrected seventeen-resource F16 provider')
    proof_row, shaders_row = provider['large_cache_index_proof'], provider['shaders']
    need(record(proof_row['path']) == proof_row and record(shaders_row['path']) == shaders_row,
         'The exact all-plane index proof and compiled resource family are required')
    proof, shaders = load(proof_row['path']), load(shaders_row['path'])
    need(proof['completed'] and proof['shaders'] == shaders_row and
         proof['decoder'] == shaders['carrier_decoder'] and
         record(proof['decoder']['path']) == proof['decoder'] and
         proof['actual_GLSL_helper_extracted'] and proof['independent_uint64_reference'] and
         proof['planes'] == shaders['cache_planes'] == 3713 and
         proof['logical_elements'] == shaders['logical_elements'] == 6083379200 and
         proof['carrier_bytes'] == 1710950400 and proof['cases'] >= 20000000 and
         proof['old_overflow_negatives'] > 0 and proof['all3713_planes_checked'] and
         proof['Euclidean_quotient_remainder_domain_bounds_checked'] and
         proof['all_physical_addresses_below_2GiB'] and proof['packed_units'] == [4, 64] and
         shaders['completed'] and shaders['large_cache_index_safe'] and
         shaders['all_seventeen_resources_recompiled'] and len(shaders['shaders']) == 17 and
         shaders['original_float_decoder_expression_preserved'] and
         shaders['new_64_bit_shader_operations'] is False and
         shaders['previous_native_decode_cases_reusable'] is False,
         'The actual compiled helper must cover the complete logical and physical cache domains')
    for name in ('tested_header', 'harness'):
        need(record(proof[name]['path']) == proof[name], 'An independent index-control input changed')
    return provider


def require_model_qualification(native_row, provider_row):
    provider = require_provider(provider_row)
    need(record(native_row['path']) == native_row, 'The corrected native qualification changed')
    proof = load(native_row['path'])
    need(proof['completed'] and proof['native_passed'] and proof['GGML_carrier_ABI'] and
         proof['ordinary_exit_observed'] and proof['current_seven_restored_and_native_hashed'] and
         record(proof['native']['path']) == proof['native'] and
         record(proof['package']['path']) == proof['package'],
         'A full model requires positive native graphs and ordinary selected restoration')
    package = load(proof['package']['path'])
    need(record(package['relink']['path']) == package['relink'], 'The native fixture link changed')
    link, terminal = load(package['relink']['path']), load(proof['native']['path'])
    need(link['model_resource_provider'] == provider_row and link['large_cache_index_safe'] and
         link['large_cache_index_proof'] == provider['large_cache_index_proof'] and
         link['maximum_GGML_graphs'] == 12 and link['unchanged_native_decode_cases_reused'] == 0,
         'The exact native twelve-graph fixture must bind this provider and index proof')
    validate_terminal(terminal)
    need(terminal['all_outputs_passed'] and len(terminal['cases']) == 12,
         'Every changed decode and prefill graph must pass before full-cache model admission')
    return provider
