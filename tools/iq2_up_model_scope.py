#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject partial IQ2 layouts before an unchanged single-group cache can launch."""
from build_performance_quantizer import record
from start_success_route import load, need


def require_arithmetic_qualification(row):
    need(record(row['path']) == row, 'The native arithmetic qualification changed')
    proof = load(row['path'])
    need(proof['completed'] and proof['native_operator_numerics_qualified'] and
         not proof['full_model_quality_or_speed_qualified'], 'Completed native arithmetic qualification required')
    for name in ('component', 'closure', 'case'):
        need(record(proof[name]['path']) == proof[name], 'An arithmetic qualification input changed')
    component, closure = load(proof['component']['path']), load(proof['closure']['path'])
    need(component['completed'] and component.get('F16_storage_FP32_accumulation') is True and
         component['GPU_graphs'] == 12 and len(component['cases']) == 6 and
         component['all_outputs_reference_valid'] and component['all_backends_positively_retired'] and
         component['source_descriptor_and_scratch_retired'] and closure['completed'] and
         closure['ordinary_exit_observed'] and closure['current_seven_restored_and_native_hashed'] and
         not closure['unknown_completion'], 'The twelve qualified graphs and positive ordinary retirement are required')


def require_cache_layout(profile):
    if profile.get('headless_audit_kind') != 'Q2-IQ2-Up-model':
        return
    scope = profile['overrides']['native_headless_model_audit']
    need(scope['arm'] in ('control', 'candidate') and scope['selected_cache_slots'] == 3712,
         'The exact original slot count and arm are required')
    if scope.get('IQ2_only_FP32_accumulation') is True:
        need(scope['backend_environment'] == dict(GGML_VK_DISABLE_MMVQ='1') and
             scope.get('normal_F16_enabled') is True,
             'Normal F16 storage with only MMVQ disabled is required')
        require_arithmetic_qualification(scope['arithmetic_qualification'])
    else:
        need(scope['explicit_F32_profile'] == dict(GGML_VK_DISABLE_MMVQ='1', GGML_VK_DISABLE_F16='1'),
             'The legacy explicit F32 backend profile is required')
    expected = [] if scope['arm'] == 'control' else list(range(48))
    need(scope['IQ2_Up_layers'] == expected,
         'Partial IQ2 Up layouts create multiple cache groups and cannot use the unchanged single-group reset; '
         'require the full48-layer uniform layout before any publication or launch')
