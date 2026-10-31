# SPDX-License-Identifier: MIT
"""Admit the measured retained-weight and parallel small-row normal program."""
import math
from resident_all_q8_production import DRIVER, MODEL_RECEIPT, PRECISION
from cold_request_production import POLICY as CONTROL_POLICY

REPORT = 'docs/weight-followup-adoption-20261031.json'
SELECTED_SELF = '3066dfe45c32d0586e3bdddb9e9ab31b200b3185a20aa0206e2418f326b2002f'
CONTROL_SELF = 'bd390b921eaf6cfee9057cfd01ab1b03ecc48b171c0501a2807b999375dcca49'
POLICY = dict(CONTROL_POLICY, active_cache_slots=3072, physical_cache_planes=3073,
    cache_bytes=4720619520, quota_transfer_bytes=3207049216,
    postload_device_budget_bytes=5086097408, postload_single_buffer_bytes=1677721600,
    retained_Expert_weights=True, request_and_KV_state_retained=False,
    parallel_small_rows=True, maximum_small_rows=8)


def require_weight_followup_production(installation, context, report):
    def need(ok, message):
        if not ok:
            raise ValueError(message)

    need(report.get('schema') == 'ps5-qwen-weight-followup-adoption-v1' and
         report.get('completed') is True and report.get('pending_steps') == [] and
         report.get('all_five_candidate_dispositions_completed') is True,
         'Completed candidate dispositions and native placement required')
    need(report.get('application_SELF') == installation.get('application_SELF') ==
         dict(bytes=20081383, sha256=SELECTED_SELF) and
         report.get('previous_application_SELF', {}).get('sha256') ==
         installation.get('previous_production_SHA256') == CONTROL_SELF and
         context.get('production_SELF', {}).get('sha256') == SELECTED_SELF,
         'Exact qualified normal program and immediate control required')
    need(report.get('driver') == installation.get('driver') == DRIVER and
         report.get('precision') == installation.get('precision') == PRECISION and
         report.get('model_receipt_SHA256') == installation.get('model_receipt_SHA256') ==
         context.get('selected_model_receipt_SHA256') == MODEL_RECEIPT,
         'Pinned driver, unchanged weights and explicit precision required')
    need(report.get('policy') == POLICY and
         installation.get('active_expert_slots') == context.get('active_cache_slots') == 3072 and
         installation.get('physical_cache_planes') == 3073 and
         installation.get('expert_cache_bytes') == 4720619520 and
         installation.get('postload_quota_transfer_bytes') == 3207049216 and
         installation.get('postload_device_budget_bytes') == 5086097408 and
         installation.get('postload_single_buffer_bytes') == 1677721600 and
         installation.get('workspace_reservation_bytes') == 50331648 and
         installation.get('CPU_heap_limit_bytes') == 536870912 and
         installation.get('physical_Direct_reserve_bytes') == 536870912 and
         installation.get('retain_Expert_weights_between_requests') is True and
         context.get('retain_Expert_weights_between_requests') is True and
         installation.get('parallel_small_rows') is True and
         context.get('parallel_small_rows') is True and
         installation.get('request_and_KV_state_retained') is False and
         context.get('prefill_tokens') == installation.get('prefill_tokens') == 32,
         'Measured cache, independent request reset and original reserves required')
    evidence = report.get('candidate_evidence', {})
    need(evidence.get('retention_case') == 11660 and
         evidence.get('retention_total_time_reduction_percent', 0) > 0 and
         evidence.get('row_cases') == [11720, 11760, 12120] and
         evidence.get('same_cache_opposite_order_row_reduction_percent', 0) > 0 and
         evidence.get('all_row_full_F32_routes_tokens_bytes_exact') is True and
         evidence.get('all_retention_task_contents_correct') is True and
         evidence.get('PLE_BF16_and_all_weight_payloads_unchanged') is True,
         'Completed measured winners and exact arithmetic-preserving controls required')
    normal, placement = (report.get(k, {}) for k in ('normal', 'placement'))
    need(normal.get('case') == installation.get('normal_validation_case') ==
         context.get('normal_performance_case') == 12220 and
         normal.get('completed') is True and normal.get('POSTs') == 3 and
         normal.get('actual_native_frames_viewed') == 2 and
         all(normal.get(k) is True for k in ('all_full_vocabulary_rows_finite',
             'all_counting_tokens_and_bytes_equal', 'complete_actual_routes_verified',
             'retained_weights_and_empty_request_memory_verified',
             'source_model_GPU_owners_positively_retired', 'ordinary_close_exact_restore')),
         'Completed normal API, display, numerical and resource qualification required')
    for key, cap in (('CPU_heap_peak_bytes', 536870912),
                     ('device_ledger_peak_bytes', 5086097408),
                     ('actual_workspace_capacity_peak_bytes', 50331648)):
        need(type(normal.get(key)) is int and 0 < normal[key] <= cap, 'Native memory quota exceeded')
    for kind in ('cold_start', 'request_reset_weights_retained', 'exact_prefix_repeat'):
        metrics = normal.get(kind, {})
        need(all(type(metrics.get(k)) in (float, int) and math.isfinite(metrics[k]) and metrics[k] > 0
                 for k in ('total_ms', 'TTFT_ms', 'decode_tokens_per_second')),
             'Actual native timing required')
    need(placement.get('completed') is True and placement.get('case') ==
         installation.get('production_placement_case') == context.get('normal_performance_placement_case') and
         placement.get('normal_case') == 12220 and placement.get('verification_files') == 12 and
         placement.get('verified_programs') == 2 and placement.get('verified_settings') == 5 and
         placement.get('verified_control_settings') == 5 and
         all(placement.get(k) is True for k in ('native_whole_SHA256_identity_EOF_verified',
             'immediate_control_preserved', 'fresh_idle_confirmed', 'runtime_ownership_restored')) and
         all(placement.get(k) is False for k in ('native_title_running', 'gateway_running', 'model_loaded')),
         'Two programs, both settings sets and positive idle required')
    need(context.get('Expert_format') == 'Gate_Up_Q2_K_Down_Q2_0_MSE' and
         context.get('PLE_convolution_weight_type') == 'BF16' and
         context.get('remaining_resident_matrix_weight_type') == 'Q8_0' and
         context.get('selected_routing_policy') == 14 and
         context.get('graph_reuse_disabled_for_policy') is False and
         all(context.get(k) is False for k in ('native_running', 'gateway_running', 'model_loaded')),
         'Installed precision, routing and idle state differ')
