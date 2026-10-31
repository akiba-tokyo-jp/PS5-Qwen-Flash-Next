#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a private full-plan case after packaging and positive data transfer.

This performs offline input checks, emits the exact native admission scope and
preserves restoration inputs. It has no network client or console operations.
Fresh CPU/session/clock observations and ordinary launch remain separate gates.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

from driver_inputs import sha
from qwen_flash_next import ROOT


def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def bound(row):
    if record(row["path"]) != row: raise ValueError("A private input binding changed")
    return Path(row["path"])


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, indent=2) + "\n"); output.flush(); os.fsync(output.fileno())


def require_routing_production(installation, context, report):
    """Admit the qualified routing app without inventing cross-policy F32 equality."""
    normal=report.get('normal',{});placed=report.get('placement',{});policy=report.get('policy',{})
    if (report.get('schema')!='ps5-qwen-routing-winners-adoption-v1' or
        report.get('completed')is not True or
        report.get('all_requested_integration_and_qualification_and_placement_completed')is not True or
        report.get('pending_steps')!=[] or report.get('precision')!=installation.get('precision') or
        report.get('application_SELF')!=installation.get('application_SELF') or
        report.get('previous_application_SELF',{}).get('sha256')!=installation.get('previous_production_SHA256') or
        normal.get('schema')!='ps5-qwen-routing-winners-normal-qualification-v1' or
        normal.get('completed')is not True or normal.get('all_declared_adoption_criteria_passed')is not True or
        normal.get('same_policy_independent_full_F32_max_error')!=0 or normal.get('all_counting_tokens_equal')is not True or
        normal.get('selected_policy')!=installation.get('selected_routing_policy') or
        policy.get('bits')!=installation.get('selected_routing_policy') or
        context.get('selected_routing_policy')!=installation.get('selected_routing_policy') or
        placed.get('completed')is not True or
        placed.get('all_11_programs_and_five_settings_native_whole_SHA256_identity_EOF_verified')is not True or
        placed.get('prior_programs_and_settings_preserved')is not True or placed.get('fresh_idle_confirmed')is not True or
        placed.get('verification_files')!=16 or
        placed.get('normal_case')!=installation.get('normal_validation_case') or
        placed.get('normal_case')!=context.get('routing_winners_normal_case') or
        placed.get('case')!=installation.get('production_placement_case') or
        placed.get('case')!=context.get('routing_winners_placement_case') or
        any(placed.get(k)is not False for k in ('native_title_running','gateway_running','model_loaded')) or
        installation.get('owner_expected_quantization_loss_accepted')is not True or
        context.get('Expert_format')!='Gate_Up_Q2_K_Down_Q2_0_MSE'):
        raise ValueError('Qualified routing normal app, exact placement and preserved rollbacks are required')


def require_prefill16_production(installation, context, report):
    """Bind the normal width16 qualification to its exact installed program."""
    normal=report.get('normal',{});placed=report.get('placement',{});policy=report.get('policy',{})
    if (report.get('schema')!='ps5-qwen-prefill16-adoption-v1' or
        report.get('completed')is not True or report.get('pending_steps')!=[] or
        report.get('application_SELF')!=installation.get('application_SELF') or
        report.get('previous_application_SELF',{}).get('sha256')!=installation.get('previous_production_SHA256') or
        report.get('precision')!=installation.get('precision') or report.get('driver')!=installation.get('driver') or
        normal.get('schema')!='ps5-qwen-prefill16-normal-qualification-v1' or
        normal.get('completed')is not True or normal.get('all_declared_adoption_criteria_passed')is not True or
        normal.get('same_policy_independent_full_F32_max_error')!=0 or normal.get('all_counting_tokens_equal')is not True or
        normal.get('prefill_tokens')!=16 or normal.get('all_prompt_outputs_requested')is not True or
        any(v!=16 for v in (policy.get('prefill_tokens'),installation.get('prefill_tokens'),context.get('prefill_tokens'))) or
        any(v!=14 for v in (normal.get('selected_policy'),policy.get('bits'),installation.get('selected_routing_policy'),context.get('selected_routing_policy'))) or
        placed.get('completed')is not True or placed.get('all_programs_and_settings_native_whole_SHA256_identity_EOF_verified')is not True or
        placed.get('verified_programs')!=12 or placed.get('verified_settings')!=5 or placed.get('verification_files')!=17 or
        placed.get('prior_programs_and_settings_preserved')is not True or placed.get('fresh_idle_confirmed')is not True or
        placed.get('normal_case')!=installation.get('normal_validation_case') or placed.get('normal_case')!=context.get('prefill16_normal_case') or
        placed.get('case')!=installation.get('production_placement_case') or placed.get('case')!=context.get('prefill16_placement_case') or
        any(placed.get(k)is not False for k in ('native_title_running','gateway_running','model_loaded')) or
        installation.get('owner_expected_quantization_loss_accepted')is not True or context.get('Expert_format')!='Gate_Up_Q2_K_Down_Q2_0_MSE'):
        raise ValueError('Qualified normal width16 app, exact placement and preserved rollbacks are required')


def qualified_control(context, production=False, installation=None):
    if any(context.get(k)is not False for k in ('native_running','gateway_running','model_loaded')):
        raise ValueError('A positively idle preserved control is required')
    if production:
        required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
            'original_rollback_full_readback_verified','arithmetic_smoke_passed','outputs_and_token_ids_equal_to_qualified_selected_case',
            'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified')
        q4_precision=dict(Expert_weights='Q4_0',other_weights='original BF16/F32',KV_cache='F32',
            activation_inputs='F32',quantization='Expert weights only')
        mixed_precision=dict(q4_precision,Expert_weights='Gate/Up Q2_K; Down Q4_0')
        all_q2_precision=dict(q4_precision,Expert_weights='Gate/Up Q2_K; Down Q2_0 MSE')
        from performance_production import OUTPUT_Q8_PRECISION,require_performance_production
        if(isinstance(installation,dict)and installation.get('qualification_report')=='docs/limit-winners-adoption-20261031.json'):
            from limit_winners_production import require_limit_winners_production
            require_limit_winners_production(installation,context,read(ROOT/installation['qualification_report']))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        elif(isinstance(installation,dict)and installation.get('qualification_report')=='docs/speed-followup-adoption-20261031.json'):
            from speed_followup_production import require_speed_followup_production
            require_speed_followup_production(installation,context,read(ROOT/installation['qualification_report']))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        elif(isinstance(installation,dict)and installation.get('qualification_report')=='docs/weight-followup-adoption-20261031.json'):
            from weight_followup_production import require_weight_followup_production
            require_weight_followup_production(installation,context,read(ROOT/installation['qualification_report']))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        elif(isinstance(installation,dict)and installation.get('qualification_report')=='docs/resident-all-Q8-adoption-20261031.json'):
            from resident_all_q8_production import require_resident_all_q8_production
            require_resident_all_q8_production(installation,context,read(ROOT/installation['qualification_report']))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        elif(isinstance(installation,dict)and installation.get('qualification_report')=='docs/cold-request-adoption-20261030.json'):
            from cold_request_production import require_cold_request_production
            require_cold_request_production(installation,context,read(ROOT/'docs/cold-request-adoption-20261030.json'))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        elif(isinstance(installation,dict)and installation.get('qualification_report')=='docs/memory-delivery-graph-adoption-20261030.json'):
            from memory_graph_production import require_memory_graph_production
            require_memory_graph_production(installation,context,read(ROOT/'docs/memory-delivery-graph-adoption-20261030.json'))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        elif(isinstance(installation,dict)and(installation.get('precision')==OUTPUT_Q8_PRECISION or
                installation.get('qualification_report')=='docs/six-candidate-adoption-20261030.json')):
            require_performance_production(installation,context,read(ROOT/'docs/six-candidate-adoption-20261030.json'))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified')
            if installation.get('console_retention')is None:
                required+=('previous_production_rollback_preserved',)
        optimized_reports={
            'docs/expert-q2-optimization-results-20261030.json':('ps5-qwen-Q2-eight-optimization-dispositions-v1',9),
            'docs/expert-q2-io-reduction-results-20261030.json':('ps5-qwen-Q2-IO-reduction-adoption-v1',10)}
        routing_Q2=(isinstance(installation,dict) and installation.get('precision')==all_q2_precision and
            installation.get('selected_routing_policy')in (2,6,14))
        if routing_Q2:
            if installation.get('prefill_tokens')==16:
                require_prefill16_production(installation,context,read(ROOT/'docs/prefill16-adoption-20261030.json'))
            else:
                require_routing_production(installation,context,read(ROOT/'docs/routing-winners-adoption-20261030.json'))
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
        optimized_Q2=(isinstance(installation,dict) and installation.get('precision')==all_q2_precision and
            installation.get('qualification_report')in optimized_reports and not routing_Q2)
        if optimized_Q2:
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
            report=read(ROOT/installation['qualification_report']);normal=report.get('normal_application',{})
            placed=report.get('production_placement',{});quality=report.get('quality',{})
            expected_schema,programs=optimized_reports[installation['qualification_report']]
            if programs==10 and (report.get('all_four_proposals_disposed')is not True or
                normal.get('all_selected_IO_paths_exercised')is not True or
                normal.get('io_winner_flags')!=5 or installation.get('io_winner_flags')!=5):
                raise ValueError('The actual selected I/O paths and all four proposal dispositions are required')
            if (report.get('schema')!=expected_schema or
                report.get('precision')!=all_q2_precision or report.get('unknown_completion')is not False or
                any(normal.get(k)is not True for k in ('completed','ordinary_same_width_full_F32_and_routes_exact',
                    'final_unlike_width_full_vocab_top1_and_tokens_equal','all_model_source_and_GPU_owners_positively_retired',
                    'ordinary_close_and_exact_restoration_passed')) or
                normal.get('case')!=installation.get('normal_application_case') or
                any(placed.get(k)is not True for k in ('completed','all_canonical_and_rollback_whole_SHA256_identity_EOF_passed','fresh_idle_confirmed')) or
                placed.get('verified_settings')!=5 or placed.get('verified_native_programs')!=programs or
                any(placed.get(k)is not False for k in ('native_title_running','gateway_running','model_loaded')) or
                placed.get('application_SELF')!=installation.get('application_SELF') or
                placed.get('previous_production_SELF',{}).get('sha256')!=installation.get('previous_production_SHA256') or
                quality.get('owner_expected_Expert_Q2_loss_accepted')is not True or quality.get('output_normalization')is not False or
                (quality.get('strict_format'),quality.get('answer_contents'),quality.get('total_requests'))!=(6,9,9) or
                context.get('Expert_format')!='Gate_Up_Q2_K_Down_Q2_0_MSE'):
                raise ValueError('Completed optimized Q2 arithmetic, scoped width validation, exact placement and owner quality acceptance required')
        if isinstance(installation,dict) and installation.get('precision')==all_q2_precision and not optimized_Q2 and not routing_Q2:
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
            if installation.get('qualification_report')!='docs/expert-q2-results-20261029.json':
                raise ValueError('The exact closed all-Expert Q2 adoption report is required')
            report=read(ROOT/installation['qualification_report'])
            candidate=report.get('conditional_all_Expert_2bit',{})
            accepted=candidate.get('owner_quality_acceptance',{})
            normal=candidate.get('normal_application',{});placed=candidate.get('production_placement',{})
            if (report.get('schema')!='ps5-qwen-expert-q2-results-v1' or
                candidate.get('Expert_format')!='Gate_Up_Q2_K_Down_Q2_0_MSE' or
                any(candidate.get(k)is not True for k in ('completed','production_adopted',
                    'actual_all_Q2_model_converted','actual_all_Q2_model_quality_measured','actual_all_Q2_model_throughput_measured')) or
                candidate.get('pending_validation')is not False or
                candidate.get('actual_fixed_quality',{}).get('every_previous_correct_answer_retained')is not False or
                any(accepted.get(k)is not True for k in ('expected_loss_accepted','strict_quality_report_unchanged')) or
                accepted.get('strict_correct_requests')!=6 or accepted.get('semantic_correct_requests')!=9 or
                accepted.get('total_requests')!=9 or accepted.get('output_normalization_in_application')is not False or
                any(normal.get(k)is not True for k in ('completed','both_rates_faster','precision_label_correct',
                    'all_sources_and_GPU_owners_positively_retired','same_format_full_F32_and_routes_exact')) or
                any(placed.get(k)is not True for k in ('completed','exact_mixed_Q4_BF16_and_older_rollbacks_preserved',
                    'canonical_and_rollback_native_whole_SHA256_verified','all_five_settings_verified','fresh_idle_confirmed')) or
                any(placed.get(k)is not False for k in ('native_title_running','gateway_running','model_loaded')) or
                placed.get('application_SELF')!=installation.get('application_SELF') or
                normal.get('native_whole_SELF_SHA256')!=installation.get('application_SELF',{}).get('sha256') or
                candidate.get('actual_model_receipt_SHA256')!=installation.get('model_receipt_SHA256') or
                placed.get('previous_production_SHA256')!=installation.get('previous_production_SHA256') or
                context.get('Expert_format')!='Gate_Up_Q2_K_Down_Q2_0_MSE'):
                raise ValueError('Completed all-Q2 arithmetic, owner quality acceptance, normal speed and exact placement required')
        if isinstance(installation,dict) and installation.get('precision')==mixed_precision:
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
            if installation.get('qualification_report')!='docs/expert-q2-results-20261029.json':
                raise ValueError('The exact closed mixed Expert adoption report is required')
            mixed=read(ROOT/installation['qualification_report'])
            quality=mixed.get('fixed_quality_comparison',{});normal=mixed.get('normal_application',{});placed=mixed.get('production_placement',{})
            if (mixed.get('schema')!='ps5-qwen-expert-q2-results-v1' or
                mixed.get('selected_mixed_format')!='Gate_Up_Q2_K_Down_Q4_0' or
                any(quality.get(k)is not True for k in ('completed','minimum_baseline_met','every_Q4_correct_answer_retained','quality_preserved')) or
                any(normal.get(k)is not True for k in ('completed','precision_label_correct','all_sources_and_GPU_owners_positively_retired','same_format_full_F32_and_routes_exact')) or
                any(placed.get(k)is not True for k in ('completed','exact_Q4_BF16_and_older_rollbacks_preserved',
                    'canonical_and_rollback_native_whole_SHA256_verified','all_five_settings_verified','fresh_idle_confirmed')) or
                any(placed.get(k)is not False for k in ('native_title_running','gateway_running','model_loaded')) or
                placed.get('application_SELF')!=installation.get('application_SELF') or
                normal.get('native_whole_SELF_SHA256')!=installation.get('application_SELF',{}).get('sha256') or
                placed.get('previous_production_SHA256')!=installation.get('previous_production_SHA256') or
                context.get('Expert_format')!='Gate_Up_Q2_K_Down_Q4_0'):
                raise ValueError('Completed exact mixed quality, inference, resource and rollback qualification required')
        if isinstance(installation,dict) and installation.get('precision')==q4_precision:
            # Q4 has its own closed counting/F32/routes qualification. Never
            # invent the historical BF16 arithmetic-smoke flags for this model.
            required=('canonical_startup_SELF_full_readback_verified','installed_configuration_full_readback_verified',
                'source_GPU_model_resources_positively_retired','ordinary_OS_shutdown_verified','previous_production_rollback_preserved')
            if installation.get('qualification_report')!='docs/expert-q4-adoption-20261029.json':
                raise ValueError('The exact closed Expert Q4 adoption report is required')
            q4=read(ROOT/installation['qualification_report'])
            flags=('completed','production_adopted','all_same_Q4_routes_passed','finite_counting_quality_passed',
                'source_GPU_model_owners_positively_retired','ordinary_OS_close_verified',
                'production_native_whole_SHA256_identity_EOF_verified','all_five_settings_verified','previous_and_older_rollbacks_verified')
            if (q4.get('schema')!='ps5-qwen-Expert-Q4-adoption-v1' or any(q4.get(k)is not True for k in flags) or
                q4.get('production_SELF')!=installation.get('application_SELF') or q4.get('final_native_owners')!=0 or
                q4.get('Expert_format')!='Q4_0' or q4.get('KV_type')!='F32' or q4.get('activation_quantization')is not False or
                q4.get('same_Q4_maximum_absolute_logit_error')!=0 or
                q4.get('previous_BF16_SELF',{}).get('sha256')!=installation.get('previous_production_SHA256')):
                raise ValueError('Completed exact Q4 inference, resource and rollback qualification required')
        if not isinstance(installation,dict)or installation.get('schema')!='ps5-qwen-production-installation-v1'or any(installation.get(k)is not True for k in required):
            raise ValueError('The exact qualified production installation record is required')
        if context.get('production_deployment_completed')is not True or context.get('original_restored')is not False or context.get('console_reserved')is not True:
            raise ValueError('The task must still own the installed qualified production control')
        control=context.get('production_SELF',{});expected=installation.get('application_SELF',{})
        if set(expected)!={'bytes','sha256'}or any(control.get(k)!=v for k,v in expected.items()):
            raise ValueError('The preserved production SELF differs from its qualified installation')
        return control
    if(context.get('original_restored')is not True or context.get('original_numerical_re_admission')!='passed'or
       context.get('complete_original_SELF_readback_after_shutdown')is not True or context.get('original_moe_admitted')is not True):
        raise ValueError('The completed original restoration and indexed-MoE context is required')
    return context['original_SELF']


def data_plan_path(complete, completion_path, cache):
    """Bind a reviewed continuation to its original plan and positive directory proof."""
    if complete.get("schema") == "ps5-qwen-model-data-continuation-complete-v1":
        return completion_path.parent / "plan/plan.private.json"
    if complete.get("schema") != "ps5-qwen-model-data-continuation-complete-v2":
        raise ValueError("Unknown complete data continuation schema")
    def cached(row):
        path = Path(row["path"])
        if path.is_symlink() or not path.resolve().is_relative_to(cache.resolve()):
            raise ValueError("Reviewed data evidence must remain in the task data cache")
        return bound(row)
    plan_path = cached(complete["original_plan"])
    reviewed = read(cached(complete["reviewed_directory_resume"]))
    required = dict(schema="ps5-qwen-reviewed-directory-resume-complete-v1",
        existing_empty_directory_verified=True, prepare_and_MKD_repeated=False,
        marker_uploaded_once=True, finalize_positive=True, parent_ownership_restored=True,
        automatic_retries=0, title_launches=0, GPU_calls=0)
    if any(type(reviewed.get(k)) is not type(v) or reviewed[k] != v for k, v in required.items()):
        raise ValueError("Positive reviewed directory finalization is required")
    if (reviewed.get("original_plan") != complete["original_plan"] or
            reviewed.get("directory_preparation") != complete["directory_preparation"]):
        raise ValueError("Reviewed directory evidence differs from the completed data plan")
    failure = read(cached(reviewed["original_failure"]))
    if failure.get("phase") != "mkdir" or failure.get("title_launches") != 0 or failure.get("GPU_calls") != 0:
        raise ValueError("The retained reviewed directory failure differs")
    directory = read(cached(complete["directory_preparation"]))
    plan = read(plan_path)
    if (directory.get("schema") != "ps5-qwen-model-directory-preparation-v1" or
            directory.get("parent_ownership_restored") is not True or
            directory.get("marker_full_readback_verified") is not True or
            directory.get("plan_sha256") != sha(plan_path) or directory.get("owner_nonce") != plan["nonce"]):
        raise ValueError("The exact original plan needs positive owned-directory evidence")
    marker = read(cached(directory["marker"]))
    if marker != dict(schema="ps5-qwen-model-directory-owner-v1", nonce=plan["nonce"],
            original_receipt_sha256=plan["original_receipt"]["sha256"]):
        raise ValueError("The reviewed directory marker differs from the original receipt")
    return plan_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "cache", "package", "data-completion", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument('--production-control',action='store_true',
        help='Preserve the exact already qualified installed Qwen SELF instead of the historical MOSS control')
    args = parser.parse_args(); cache, out = args.cache.resolve(), args.out.resolve()
    if out.parent != cache or out.exists(): raise ValueError("A fresh separate physical case in the data cache is required")
    package = read(args.package)
    if (package.get("integrity_verified") is not True or package.get("roundtrip_segments_verified") != 6 or
            package.get("real_module_import_audit", {}).get("missing") != []):
        raise ValueError("A packaged candidate with successful native imports and SELF roundtrip is required")
    candidate = bound(package["SELF"])
    complete = read(args.data_completion)
    if (complete.get("schema") not in {"ps5-qwen-model-data-continuation-complete-v1",
                                      "ps5-qwen-model-data-continuation-complete-v2"} or
            complete.get("native_SHA_verified") is not False or complete.get("model_loaded") is not False or
            complete.get("full_inference_qualified") is not False or complete.get("GPU_calls") != 0):
        raise ValueError("Complete data-only transfer evidence is required")
    transfer = read(bound(complete["transfer"]))
    plan_path = data_plan_path(complete, args.data_completion, cache); plan = read(plan_path)
    if (transfer.get("schema") != "ps5-qwen-model-transfer-complete-v1" or
            transfer.get("state") != "awaiting_native_SHA_admission" or
            transfer.get("positively_completed_files") != len(plan["files"]) or
            transfer.get("complete_original_payload_bytes") != plan["total_bytes"] or
            transfer.get("native_payload_SHA_verified") is not False or transfer.get("model_loaded") is not False):
        raise ValueError("Every original data file must have one positive completed transfer")
    receipt = bound(plan["original_receipt"])
    if transfer["original_receipt_publication"]["sha256"] != sha(receipt):
        raise ValueError("The published full-model receipt differs")
    reservation = args.workspace / "driver-work/PS5-Vulkan-Inference/.local/gpu-development-20261021/active-context.private.json"
    context_path = Path(read(reservation)["context"]); context = read(context_path)
    installation=read(ROOT/'config/production-installation.json')if args.production_control else None
    original = bound(qualified_control(context,args.production_control,installation))
    if not args.production_control and sha(original) != "2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d":
        raise ValueError("The exact preserved original SELF differs")
    policy = read(ROOT / "config/development.json")
    if any(policy[key] is not False for key in ("console_operations_enabled", "deployment_enabled", "console_validation_enabled", "validation_deployment_enabled")) or policy["allowed_modes"] != []:
        raise ValueError("Committed execution/deployment controls must remain disabled")
    out.mkdir(); (out / "private-policy").mkdir()
    binding = dict(candidate_SELF_sha256=sha(candidate), candidate_SELF_bytes=candidate.stat().st_size,
        model_receipt_sha256=sha(receipt), model_receipt_bytes=receipt.stat().st_size, run_id=secrets.token_hex(16))
    binding_path = out / "policy-binding.private.json"; write(binding_path, binding)
    host = args.workspace / "toolchain/msys-clang64/clang64/bin"
    upstream = cache / "upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569"
    executable = out / "native-policy.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror",
        "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"),
        str(ROOT / "tools/first_generation_policy.cpp"), "-o", str(executable)]
    environment = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    result = subprocess.run(command, env=environment, capture_output=True, timeout=120)
    (out / "policy-compile.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError("The actual native admission-scope emitter failed to compile")
    result = subprocess.run([str(executable), str(binding_path)], env=environment, capture_output=True, timeout=30)
    (out / "policy-run.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise ValueError("The actual native gate rejected the case binding")
    policy.update(phase="bounded-full-model-plan", console_operations_enabled=True, console_validation_enabled=True,
        validation_deployment_enabled=True, deployment_enabled=False, allowed_modes=["first-generation-validation"],
        native_first_generation_validation=json.loads(result.stdout))
    write(out / "private-policy/development.json", policy)
    write(out / "preflight-complete.private.json", dict(state="original_normally_closed_source_SELF_preserved",
        SELF=record(original),control_kind='qualified production Qwen SELF'if args.production_control else'legacy MOSS SELF',
        legacy_MOSS_rollback=context['original_SELF']if args.production_control else None,
        prior_completed_context=record(context_path), console_connections=0, GPU_calls=0))
    write(out / "case-inputs.private.json", dict(schema="ps5-qwen-first-case-inputs-v1", binding=binding,
        package=record(args.package), candidate=record(candidate), original=record(original),
        model_receipt=record(receipt), transfer=record(complete["transfer"]["path"]), data_completion=record(args.data_completion),
        data_plan=record(plan_path), prior_context=record(context_path), reservation=record(reservation),
        native_policy_emitter=record(executable), policy_command=command,
        native_policy_sources=[record(ROOT / "tools/first_generation_policy.cpp"), record(ROOT / "native/app/first_generation_policy.h")],
        preserved_production_control=args.production_control,
        fresh_session_required_before_mutation=True, console_access=False, learned_host_inference=False))
    shutil.copyfile(args.package, out / "candidate-package.private.json")
    print(json.dumps(dict(private_case_prepared=True, native_policy_gate_passed=True, console_connections=0, GPU_calls=0)))


if __name__ == "__main__": main()
