#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject partial IQ2 layouts before an unchanged single-group cache can launch."""
from build_performance_quantizer import record
from start_success_route import load, need


def require_gate_input_qualification(row):
    need(row is not None and record(row['path'])==row,'The native Gate/Up identity proof changed')
    proof=load(row['path'])
    need(proof['completed'] and proof['native_input_identity_qualified'] and proof['all48_layers_per_width'] and
         proof['calls']==1200 and set(proof['graph_construction_widths'])=={1,2,30,32} and
         proof['original_GGML_operations_preserved'] and record(proof['audit']['path'])==proof['audit'] and
         record(proof['closure']['path'])==proof['closure'] and load(proof['closure']['path'])['ordinary_exit_observed'],
         'The complete native1200-pair Gate/Up input/ID audit and ordinary retirement are required')


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


def require_down_qualification(row, provider_row):
    need(record(row['path'])==row and record(provider_row['path'])==provider_row,
         'The native Down qualification or selected resource provider changed')
    proof=load(row['path']);provider=load(provider_row['path'])
    need(proof['completed'] and proof['native_passed'] and proof['GGML_carrier_ABI'] and
         proof['ordinary_exit_observed'] and proof['current_seven_restored_and_native_hashed'] and
         record(proof['native']['path'])==proof['native'] and record(proof['package']['path'])==proof['package'],
         'Positive native Down arithmetic and ordinary selected restoration are required')
    terminal=load(proof['native']['path']);package=load(proof['package']['path'])
    need(record(package['relink']['path'])==package['relink'] and
         load(package['relink']['path'])['model_resource_provider']==provider_row and
         terminal['all_outputs_passed'] and provider['completed'] and provider['GPU_executable_sections_byte_exact'] and
         provider['original_shader_registry_unchanged'] and provider['new_global_initializers']==0,
         'The completed native cases and exact resource provider must remain bound')
    from iq2_down_ggml_completion import validate_terminal
    validate_terminal(terminal)
    if provider.get('F16_arithmetic_only'):
        need(provider['redirected_resource_pairs']==17 and terminal.get('F16_storage_FP32_accumulation') is True and
             terminal['completed_GGML_case_prefix']==0 and terminal['reused_decode_cases']==6 and len(terminal['cases'])==6 and
             record(provider['F16_operands']['path'])==provider['F16_operands'],
             'All six changed F16 cases and the separate original decode qualification are required')
        operands=load(provider['F16_operands']['path']);ancestor=operands['native_F32_proof']
        need(record(ancestor['path'])==ancestor and ancestor!=row,'A distinct completed original F32 qualification is required')
        parent=load(ancestor['path']);parent_package=load(parent['package']['path'])
        need(record(parent['package']['path'])==parent['package'] and
             record(parent_package['relink']['path'])==parent_package['relink'], 'The original resource lineage changed')
        parent_provider=load(parent_package['relink']['path'])['model_resource_provider']
        need(not load(parent_provider['path']).get('F16_arithmetic_only'),'The original qualification must precede F16 refinement')
        require_down_qualification(ancestor,parent_provider)
        require_arithmetic_qualification(provider['F16_Up_prerequisite'])
    else:
        need(terminal['completed_GGML_case_prefix']==2 and len(terminal['cases'])==10 and
             provider['generic_indexed_refinement'] and provider['redirected_resource_pairs']==15,
             'The ten changed native F32 cases and exact fifteen-resource provider must remain bound')


def require_cache_layout(profile):
    if profile.get('headless_audit_kind')=='Q3-IQ2-Down-model':
        scope=profile['overrides']['native_headless_model_audit']
        F16=scope.get('Down_only_FP32_accumulation') is True
        environment={} if scope['arm']=='control' else (
            dict(GGML_VK_DISABLE_MMVQ='1') if F16 else dict(GGML_VK_DISABLE_MMVQ='1',GGML_VK_DISABLE_F16='1'))
        need(scope['arm'] in ('control','candidate') and scope['selected_cache_slots']==3712 and
             scope['IQ2_Down_layers']==([] if scope['arm']=='control' else list(range(48))) and
             scope['global_F32_candidate_only']==(not F16) and scope['normal_F16_enabled']==(F16 or scope['arm']=='control') and
             scope['backend_environment']==environment and
             load(scope['Down_resource_provider']['path']).get('F16_arithmetic_only',False)==F16,
             'Only a uniform48-layer Down carrier model and original slot count may launch')
        require_down_qualification(scope['arithmetic_qualification'],scope['Down_resource_provider'])
        return
    if profile.get('headless_audit_kind') not in ('Q2-IQ2-Up-model','Q2-IQ2-Gate-Up-model'):
        return
    scope = profile['overrides']['native_headless_model_audit']
    need(scope['arm'] in ('control', 'candidate') and scope['selected_cache_slots'] == 3712,
         'The exact original slot count and arm are required')
    if scope.get('IQ2_only_FP32_accumulation') is True:
        need(scope['backend_environment'] == ({} if scope['arm']=='control' else dict(GGML_VK_DISABLE_MMVQ='1')) and
             scope.get('normal_F16_enabled') is True,
             'The control uses normal P1; only the candidate disables MMVQ and keeps normal F16 storage')
        require_arithmetic_qualification(scope['arithmetic_qualification'])
    else:
        need(scope['explicit_F32_profile'] == dict(GGML_VK_DISABLE_MMVQ='1', GGML_VK_DISABLE_F16='1'),
             'The legacy explicit F32 backend profile is required')
    expected = [] if scope['arm'] == 'control' else list(range(48))
    need(scope['IQ2_Up_layers'] == expected,
         'Partial IQ2 Up layouts create multiple cache groups and cannot use the unchanged single-group reset; '
         'require the full48-layer uniform layout before any publication or launch')
    if profile['headless_audit_kind']=='Q2-IQ2-Gate-Up-model':
        need(scope.get('IQ2_Gate_layers')==expected and scope.get('IQ2_only_FP32_accumulation') is True,
             'Gate and Up must each be uniform across all48 layers with qualified scoped arithmetic')
        require_gate_input_qualification(scope.get('Gate_input_identity'))
    else:
        need(not scope.get('IQ2_Gate_layers'),'A Gate conversion requires its explicit combined model scope')


def require_IQ2_comparison(profiles, scope, numerical_proof):
    need(scope in ('Q2','Q3') and len(profiles) in (2,4),'One explicit IQ2 pair or ABBA is required')
    kinds={'Q2':('Q2-IQ2-Up-model','Q2-IQ2-Gate-Up-model'),'Q3':('Q3-IQ2-Down-model',)}
    expected=['control','candidate'] if len(profiles)==2 else ['control','candidate','candidate','control']
    need(len({p['headless_audit_kind'] for p in profiles})==1 and profiles[0]['headless_audit_kind'] in kinds[scope],
         'A single uniform IQ2 model scope must match the original proposal')
    for profile,arm in zip(profiles,expected):
        require_cache_layout(profile)
        compiled=profile['overrides']['native_headless_model_audit']
        need(compiled['arm']==arm and compiled['arithmetic_qualification']==numerical_proof and
             profile['performance_timings_usable'] and not profile.get('qualification_observer') and
             profile['headless_requests']==3 and compiled['original_cold_retained_exact_prefix_sequence'],
             'Exact timed original-cohort arms and the same completed native arithmetic proof are required')
        if arm=='control':
            need(compiled['backend_environment']=={} and 'model_layer' not in profile,
                 'The control must use normal adopted P1 without additional quantized layers')
        else:
            layer=profile['model_layer'];publication=load(layer['publication']['path'])
            need(record(layer['publication']['path'])==layer['publication'] and publication['completed'] and
                 publication['whole_new_bytes_and_all_parent_identities_qualified'] and
                 record(layer['model_receipt']['path'])==layer['model_receipt'],
                 'The complete candidate must retain its positive whole-source seal')
