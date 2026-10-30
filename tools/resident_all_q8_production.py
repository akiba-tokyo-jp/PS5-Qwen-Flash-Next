# SPDX-License-Identifier: MIT
"""Admit only the measured resident-Q8 program with the original BF16 PLE kernel."""
import math
from cold_request_production import DRIVER, POLICY

REPORT = 'docs/resident-all-Q8-adoption-20261031.json'
SELECTED_SELF = 'bd390b921eaf6cfee9057cfd01ab1b03ecc48b171c0501a2807b999375dcca49'
CONTROL_SELF = '57043cbe809362e0910e69279caca1a4985c92f93114f0f06dd81ebe81bd2bbf'
MODEL_RECEIPT = '8b67b85e6cb2f3fd910e900b0299c3325d8717814f0ffab9ef505cab1dfc686b'
PRECISION = dict(Expert_weights='Gate/Up Q2_K; Down Q2_0 MSE',
    other_weights='resident Q8_0 except original BF16 PLE convolution and F32 tensors; nonresident tensors unchanged',
    output_weight='Q8_0', shared_Expert_weight='Q8_0 (144 active projections)',
    PLE_convolution='BF16 [4,10240], 81920 bytes', KV_cache='F32',
    activation_inputs='F32', quantization='Expert Q2 and resident matrix Q8_0')


def require_resident_all_q8_production(installation, context, report):
    def need(ok, message):
        if not ok:
            raise ValueError(message)

    need(report.get('schema') == 'ps5-qwen-all-resident-Q8-adoption-v1' and
         report.get('completed') is True and report.get('pending_steps') == [],
         'Completed native resident-Q8 qualification and placement required')
    need(report.get('application_SELF') == installation.get('application_SELF') ==
         dict(bytes=20065607, sha256=SELECTED_SELF) and
         report.get('previous_application_SELF', {}).get('sha256') ==
         installation.get('previous_production_SHA256') == CONTROL_SELF,
         'Exact qualified resident-Q8 program and immediate control required')
    need(report.get('driver') == installation.get('driver') == DRIVER and
         report.get('precision') == installation.get('precision') == PRECISION,
         'Pinned driver and explicit PLE, Expert, resident and input precision required')
    need(report.get('model_receipt_SHA256') == installation.get('model_receipt_SHA256') ==
         context.get('selected_model_receipt_SHA256') == MODEL_RECEIPT,
         'Exact native-published resident-Q8 model required')
    need(report.get('policy') == POLICY and installation.get('active_expert_slots') ==
         context.get('active_cache_slots') == 1381 and
         installation.get('physical_cache_planes') == 1382 and
         installation.get('expert_cache_bytes') == 2123243520 and
         installation.get('workspace_reservation_bytes') == 50331648 and
         context.get('prefill_tokens') == installation.get('prefill_tokens') == 32,
         'Original measured cache, workspace and prefill policy required')
    precision = report.get('weight_conversion', {})
    need(precision.get('converted_tensors') == 544 and
         precision.get('saved_resident_payload_bytes') == 3163852800 and
         precision.get('resident_payload_bytes') == 4774100480 and
         all(precision.get(k) is True for k in
             ('PLE_convolution_BF16_preserved', 'Expert_Q2_payloads_unchanged',
              'other_F32_and_nonresident_tensors_unchanged', 'native_whole_source_seal_completed')),
         'Complete544-tensor conversion with exact original PLE and Expert payloads required')
    normal, quality, placement = (report.get(k, {}) for k in ('normal', 'fixed_quality', 'placement'))
    need(normal.get('case') == installation.get('normal_validation_case') ==
         context.get('normal_performance_case') == 11480 and
         normal.get('completed') is True and normal.get('POSTs') == 3 and
         normal.get('actual_native_frames_viewed') == 2 and
         all(normal.get(k) is True for k in ('same_profile_F32_and_routes_passed',
             'all_counting_answers_correct', 'source_model_GPU_owners_positively_retired',
             'ordinary_close_exact_restore')),
         'Completed normal API, display, numerical and resource qualification required')
    for key, cap in (('CPU_heap_peak_bytes', 536870912), ('device_ledger_peak_bytes', 2480332800),
                     ('actual_workspace_capacity_peak_bytes', 50331648)):
        need(type(normal.get(key)) is int and 0 < normal[key] <= cap, 'Native memory quota exceeded')
    for kind in ('independent', 'retained'):
        metrics = normal.get(kind, {})
        need(all(type(metrics.get(k)) in (float, int) and math.isfinite(metrics[k]) and metrics[k] > 0
                 for k in ('total_ms', 'TTFT_ms', 'decode_tokens_per_second')),
             'Actual native timing is required')
    need(quality.get('case') == 11520 and quality.get('compared_requests') ==
         quality.get('semantic_correct_requests') == 8 and
         all(quality.get(k) is True for k in ('all_ordered_routes_equal',
             'all_application_caches_empty', 'same_profile_full_F32_passed',
             'ordinary_close_exact_restore')) and quality.get('application_output_normalization') is False,
         'Eight completed independent fixed-task comparisons required')
    need(placement.get('completed') is True and placement.get('case') ==
         installation.get('production_placement_case') == context.get('normal_performance_placement_case') and
         placement.get('normal_case') == 11480 and placement.get('verification_files') == 12 and
         all(placement.get(k) is True for k in ('native_whole_SHA256_identity_EOF_verified',
             'immediate_control_preserved', 'fresh_idle_confirmed', 'runtime_ownership_restored')) and
         all(placement.get(k) is False for k in ('native_title_running', 'gateway_running', 'model_loaded')),
         'Exact two-program/two-settings-set placement and positive idle required')
    need(context.get('Expert_format') == 'Gate_Up_Q2_K_Down_Q2_0_MSE' and
         context.get('PLE_convolution_weight_type') == 'BF16' and
         context.get('remaining_resident_matrix_weight_type') == 'Q8_0' and
         context.get('selected_routing_policy') == 14 and
         context.get('graph_reuse_disabled_for_policy') is False,
         'Installed precision and routing descriptors differ')
