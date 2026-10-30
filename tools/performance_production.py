# SPDX-License-Identifier: MIT
"""Bind future controls to the exact qualified output-Q8 normal installation."""
OUTPUT_Q8_PRECISION=dict(Expert_weights='Gate/Up Q2_K; Down Q2_0 MSE',
 other_weights='original BF16/F32 except output Q8_0',output_weight='Q8_0',KV_cache='F32',
 activation_inputs='F32',quantization='Expert and resident output weights')

def require_performance_production(installation,context,report):
 normal=report.get('normal',{});placed=report.get('placement',{});policy=report.get('policy',{})
 if(report.get('schema')!='ps5-qwen-six-candidate-adoption-v1' or report.get('completed')is not True or
    report.get('all_six_candidates_disposed')is not True or report.get('pending_steps')!=[] or
    report.get('application_SELF')!=installation.get('application_SELF') or
    report.get('previous_application_SELF',{}).get('sha256')!=installation.get('previous_production_SHA256') or
    report.get('precision')!=OUTPUT_Q8_PRECISION or installation.get('precision')!=OUTPUT_Q8_PRECISION or
    report.get('driver')!=installation.get('driver') or
    any(report.get('driver',{}).get(k)is not False for k in ('persistent_shader_cache','persistent_pipeline_cache')) or
    normal.get('schema')!='ps5-qwen-six-candidate-normal-qualification-v1' or
    normal.get('completed')is not True or normal.get('all_declared_adoption_criteria_passed')is not True or
    normal.get('same_policy_independent_full_F32_max_error')!=0 or normal.get('all_counting_tokens_equal')is not True or
    any(v!=16 for v in (policy.get('prefill_tokens'),installation.get('prefill_tokens'),context.get('prefill_tokens'))) or
    any(v!=14 for v in (policy.get('bits'),installation.get('selected_routing_policy'),context.get('selected_routing_policy'))) or
    policy.get('prefill_Experts')!=6 or policy.get('decode_Experts')!=6 or policy.get('active_cache_slots')!=997 or
    policy.get('cache_bytes')!=1533419520 or policy.get('output_weight_type')!='Q8_0' or
    policy.get('graph_reuse_enabled')is not True or policy.get('integer_activation_quantization')is not False or
    policy.get('quota_transfer_bytes')!=199680000 or policy.get('saved_output_payload_bytes')!=595968000 or
    context.get('active_cache_slots')!=997 or context.get('output_weight_type')!='Q8_0' or
    context.get('graph_reuse_disabled_for_policy')is not False or context.get('Expert_format')!='Gate_Up_Q2_K_Down_Q2_0_MSE' or
    placed.get('completed')is not True or placed.get('all_programs_and_settings_native_whole_SHA256_identity_EOF_verified')is not True or
    placed.get('verified_programs')!=13 or placed.get('verified_settings')!=5 or placed.get('verification_files')!=18 or
    placed.get('prior_programs_and_settings_preserved')is not True or placed.get('fresh_idle_confirmed')is not True or
    placed.get('normal_case')!=installation.get('normal_validation_case') or placed.get('normal_case')!=context.get('normal_performance_case') or
    placed.get('case')!=installation.get('production_placement_case') or placed.get('case')!=context.get('normal_performance_placement_case') or
    any(placed.get(k)is not False for k in ('native_title_running','gateway_running','model_loaded')) or
    installation.get('owner_expected_quantization_loss_accepted')is not True):
  raise ValueError('Exact output-Q8 normal qualification, quota coupling, idle placement and every preserved rollback are required')
