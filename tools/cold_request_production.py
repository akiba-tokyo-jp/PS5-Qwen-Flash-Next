# SPDX-License-Identifier: MIT
"""Bind the closed cold-request campaign to its exact installed program."""
from memory_graph_production import DRIVER, PRECISION

SELECTED_SELF = '57043cbe809362e0910e69279caca1a4985c92f93114f0f06dd81ebe81bd2bbf'
CONTROL_SELF = '5c5d70347f25d2fe0905da3325519c056038475254fbf90af745af61c7b126ea'
MODEL_RECEIPT = '7ba7bbf919eba43a365f570930558b9405b60ad66f9e3cdeea104ce5557377fb'
POLICY = dict(active_cache_slots=1381, physical_cache_planes=1382,
              cache_bytes=2123243520, quota_transfer_bytes=601284608,
              postload_device_budget_bytes=2480332800,
              postload_single_buffer_bytes=750780416,
              workspace_reservation_bytes=50331648,
              CPU_heap_limit_bytes=536870912, physical_Direct_reserve_bytes=536870912,
              prefill_tokens=32, prefill_Experts=6, decode_Experts=6, bits=14,
              total_bundled_Experts=448, maximum_parallel_source_reads=4,
              graph_reuse_enabled=True, integer_activation_quantization=False,
              indexed_window0_probation=True, cross_projection_demand_streaming=True,
              source_scratch_bytes=8388608, speculative_source_reads=False,
              additional_GPU_forecast=False)


def require_cold_request_production(installation, context, report):
    def need(value, message):
        if not value:
            raise ValueError(message)

    need(report.get('schema') == 'ps5-qwen-cold-request-adoption-v1' and
         report.get('completed') is True and report.get('all_five_candidates_disposed') is True and
         report.get('pending_steps') == [], 'Closed five-candidate cold-request campaign required')
    app = report.get('application_SELF', {})
    previous = report.get('previous_application_SELF', {})
    need(app == installation.get('application_SELF') and app == dict(bytes=19140135, sha256=SELECTED_SELF) and
         previous.get('sha256') == installation.get('previous_production_SHA256') == CONTROL_SELF,
         'Exact qualified program and immediate control required')
    need(report.get('driver') == installation.get('driver') == DRIVER and
         report.get('precision') == installation.get('precision') == PRECISION,
         'Pinned driver, disabled persistent caches and explicit precision required')
    policy = report.get('policy', {})
    need(report.get('dispositions') == dict(prefill32='adopted', indexed_probation='adopted',
         continuous_four_lanes='adopted', layer_quota='tested_worse_not_adopted',
         deadline_prefetch='observer_tested_no_gain_physical_prefetch_screened_out'),
         'Every selected candidate must have an explicit measured disposition')
    diagnostic = report.get('timing_diagnostic', {})
    need(diagnostic.get('case') == 11030 and diagnostic.get('completed') is True and
         diagnostic.get('ordinary_close_exact_restore') is True and
         diagnostic.get('ordinary_speed_comparison_valid') is False,
         'Completed diagnostic timing must remain separate from ordinary performance')
    need(all(type(policy.get(k)) is type(v) and policy[k] == v for k, v in POLICY.items()),
         'Exact measured demand-streaming and tightened workspace policy required')
    need(installation.get('active_expert_slots') == context.get('active_cache_slots') == 1381 and
         installation.get('physical_cache_planes') == 1382 and installation.get('expert_cache_bytes') == 2123243520 and
         installation.get('postload_quota_transfer_bytes') == 601284608 and
         installation.get('workspace_reservation_bytes') == 50331648 and
         installation.get('prefill_tokens') == context.get('prefill_tokens') == 32,
         'Actual installed cache, quota and width descriptors must match')
    need(installation.get('output_only_Q8_exception') is False and installation.get('shared_Expert_Q8_exception') is True and
         context.get('Expert_format') == 'Gate_Up_Q2_K_Down_Q2_0_MSE' and
         context.get('output_weight_type') == context.get('shared_Expert_weight_type') == 'Q8_0' and
         context.get('selected_routing_policy') == 14 and context.get('graph_reuse_disabled_for_policy') is False,
         'Exact native precision and routing policy required')
    normal = report.get('normal', {})
    quality = report.get('fixed_quality', {})
    placed = report.get('placement', {})
    need(normal.get('case') == installation.get('normal_validation_case') == context.get('normal_performance_case') == 10970 and
         normal.get('completed') is True and normal.get('all_declared_adoption_criteria_passed') is True,
         'Completed selected normal cohort required')
    need(normal.get('same_policy_independent_full_F32_max_error') == 0 and
         all(normal.get(k) is True for k in ('all_counting_tokens_equal', 'source_model_GPU_owners_positively_retired', 'ordinary_close_exact_restore')) and
         normal.get('actual_native_frames_viewed') == 2,
         'Full-vocabulary, positive retirement, restoration and actual display evidence required')
    for key, cap in (('CPU_heap_peak_bytes', 536870912), ('device_ledger_peak_bytes', 2480332800),
                     ('actual_workspace_capacity_peak_bytes', 50331648)):
        need(type(normal.get(key)) is int and 0 < normal[key] <= cap, 'Measured memory peak exceeds its distinct quota')
    need(quality.get('case') == 11010 and quality.get('all_four_fixed_tasks_compared') is True and
         quality.get('semantic_correct_requests') == quality.get('compared_requests') == 8 and
         quality.get('cross_delivery_full_F32_max_error') == 0 and quality.get('all_ordered_routes_equal') is True and
         quality.get('all_application_caches_empty') is True and quality.get('reversed_delivery_order') is True and
         quality.get('raw_JSON_fences_disclosed') is True and quality.get('application_output_normalization') is False and
         quality.get('ordinary_close_exact_restore') is True,
         'Eight independent fixed-input delivery comparisons with exact F32/routes required')
    need(placed.get('case') == installation.get('production_placement_case') == context.get('normal_performance_placement_case') and
         placed.get('normal_case') == 10970 and placed.get('completed') is True and
         all(placed.get(k) is True for k in ('native_whole_SHA256_identity_EOF_verified', 'immediate_control_preserved',
                                            'fresh_idle_confirmed', 'runtime_ownership_restored')) and
         placed.get('verified_programs') == 2 and placed.get('verified_settings') == placed.get('verified_control_settings') == 5 and
         placed.get('verification_files') == 12,
         'Exact program/settings placement and immediate control preservation required')
    need(all(placed.get(k) is False for k in ('native_title_running', 'gateway_running', 'model_loaded')),
         'Placed owners must be positively inactive')
    need(report.get('model_receipt_SHA256') == installation.get('model_receipt_SHA256') == context.get('selected_model_receipt_SHA256') == MODEL_RECEIPT and
         installation.get('previous_production_rollback_preserved') is True and
         installation.get('preserved_programs_verified') == 2 and installation.get('owner_expected_quantization_loss_accepted') is True,
         'Exact model receipt, immediate control and accepted precision scope required')
