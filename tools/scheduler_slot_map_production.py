# SPDX-License-Identifier: MIT
"""Admit the measured scheduler contract and current-only installation."""
import json
from pathlib import Path
from throughput_production import DRIVER, PRECISION, MODEL_RECEIPT, SELECTED_SELF as CONTROL_SELF
ROOT = Path(__file__).resolve().parents[1]
REPORT = 'docs/scheduler-slot-map-adoption-20261101.json'
path = ROOT / 'config/scheduler-slot-map-selection.json'
SELECTION = json.loads(path.read_text()) if path.is_file() else {}
SELECTED_SELF = SELECTION.get('SELF', {}).get('sha256')

def need(value, message):
    if not value: raise ValueError(message)

def validate_scheduler_measurements(report):
    need(SELECTION and report.get('schema') == 'ps5-qwen-scheduler-slot-map-adoption-v1' and
         report.get('measured_qualification_completed') is True and report.get('selected') is True,
         'Complete measured selection required')
    need(report.get('application_SELF') == SELECTION['SELF'] and
         report.get('application_source_revision') == SELECTION['source_revision'] and
         report.get('previous_application_SELF', {}).get('sha256') == CONTROL_SELF,
         'Exact new program, source and actual previous9824 required')
    need(report.get('driver') == DRIVER and report.get('precision') == PRECISION and
         report.get('model_receipt_SHA256') == MODEL_RECEIPT and
         report.get('next_five_policy') == SELECTION['normal_scope'] and
         report.get('scheduler_slot_maps') == SELECTION['scheduler_slot_maps'],
         'Unchanged qualified driver, weights, execution and allocation contract required')
    fixture = report.get('scheduler_fixture', {})
    need(fixture.get('completed') is True and fixture.get('GPU_graphs') == 48 and
         fixture.get('actual_CPU_Vulkan_scheduler') is True and
         fixture.get('all_I32_bytes_and_canaries_exact') is True and fixture.get('live_address_changes') == 0,
         'Actual scheduler rebuild/reuse/view/canary proof required')
    model = report.get('model_comparison', {})
    need(model.get('completed') is True and model.get('requests') == 14 and
         all(model.get(k) is True for k in ('all_full_F32_routes_tokens_exact', 'identical_source_demand',
                                          'fixed_semantic_tasks_passed', 'ordinary_close_and_restore')) and
         min(model.get('paired_whole_time_savings_ms', [0])) > model.get('control_AA_whole_spread_ms', float('inf')),
         'Repeated exact model gain beyond control variation required')
    normal = report.get('normal', {})
    need(normal.get('completed') is True and normal.get('cases') == [59000, 59200, 59400, 59600] and
         normal.get('requests') == 12 and normal.get('actual_native_frames_viewed') == 8 and
         all(normal.get(k) is True for k in ('all_tokens_and_output_bytes_exact', 'all_actual_ordered_routes_exact',
            'identical_source_demand', 'all_counting_tasks_passed', 'all_full_F32_finite',
            'all_ordinary_closes_and_exact_restores', 'original_normal_generation_benefit_qualifies')),
         'Actual original-normal ABBA, exact work, viewed frames and ordinary retirement required')
    for group in normal.get('groups', [])[1:]:
        need(min(group['paired_whole_savings_ms']) > group['control_AA_whole_spread_ms'] and
             min(group['paired_decode_savings_ms']) > group['control_AA_decode_spread_ms'],
             'Both retained/prefix pairs must beat original-control variation')
    need(len(normal.get('groups', [])) == 3 and normal.get('initial_prefill_latency_regression_reported') is True and
         report.get('selection_priority') == 'Generation speed with explicit initial TTFT tradeoff',
         'Cold latency cost must be explicit; do not claim every metric improves')

def require_scheduler_slot_production(installation, context, report):
    validate_scheduler_measurements(report)
    need(report.get('completed') is True and report.get('pending_steps') == [], 'Placement and cleanup must be complete')
    need(installation.get('qualification_report') == REPORT and installation.get('application_SELF') == SELECTION['SELF'] and
         context.get('production_SELF', {}).get('sha256') == SELECTED_SELF and
         context.get('production_SELF', {}).get('bytes') == SELECTION['SELF']['bytes'] and
         installation.get('application_source_revision') == SELECTION['source_revision'], 'Exact installed program required')
    need(installation.get('driver') == DRIVER and installation.get('precision') == PRECISION and
         installation.get('model_receipt_SHA256') == context.get('selected_model_receipt_SHA256') == MODEL_RECEIPT and
         installation.get('next_five_policy') == context.get('next_five_policy') == SELECTION['normal_scope'] and
         installation.get('scheduler_slot_maps') == context.get('scheduler_slot_maps') == SELECTION['scheduler_slot_maps'],
         'Installed/runtime profile must match the physically qualified program')
    for ik, ck, value in (('active_expert_slots', 'active_cache_slots', 3712),
                         ('physical_cache_planes', 'physical_cache_planes', 3713),
                         ('expert_cache_bytes', 'expert_cache_bytes', 5703659520),
                         ('postload_device_budget_bytes', 'postload_device_budget_bytes', 6199160832),
                         ('postload_single_buffer_bytes', 'postload_single_buffer_bytes', 2147483648)):
        need(installation.get(ik) == context.get(ck) == value, 'Original cache and measured allocation budgets required')
    need(installation.get('CPU_heap_limit_bytes') == 536870912 and
         installation.get('previous_production_SHA256') == context.get('previous_production_SELF', {}).get('sha256') == CONTROL_SELF and
         installation.get('previous_production_rollback_preserved') is True, 'Exact host-preserved control and CPU limit required')
    placed = report.get('placement', {}); cleaned = report.get('cleanup', {})
    need(placed.get('completed') is True and placed.get('native_whole_SHA256_identity_EOF_verified') is True and
         placed.get('verified_programs') == 2 and placed.get('verified_settings') == 10 and
         placed.get('title_launches') == placed.get('GPU_calls') == 0,
         'Actual native installation/control/settings proof required')
    need(cleaned.get('completed') is True and cleaned.get('current_program_copies') == 1 and
         cleaned.get('current_settings') == 5 and cleaned.get('obsolete_backups_remaining') == 0 and
         cleaned.get('final_native_current_files_verified') is True and
         installation.get('console_retention') == cleaned.get('console_retention'),
         'Verified current-only console retention required')
    need(all(context.get(k) is False for k in ('native_running', 'gateway_running', 'model_loaded', 'unknown_completion')) and
         context.get('native_owners') == 0 and context.get('installed_control_complete_native_readback_verified') is True,
         'Actual positive idle and current program/settings integrity required')
