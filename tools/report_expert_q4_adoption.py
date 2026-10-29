#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish sanitized Q4 application evidence only after verified native placement."""
import argparse,json
from pathlib import Path
from analyze_expert_q4_model import closed_case
from expert_q4 import require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True);p.add_argument('--placement',type=Path,required=True)
    p.add_argument('--source-revision',required=True);a=p.parse_args()
    require(len(a.source_revision)==40 and set(a.source_revision)<=set('0123456789abcdef'),'Exact committed application source required')
    normal_case=int(a.case.name.rsplit('-',1)[1]);placement_case=int(a.placement.name.rsplit('-',1)[1])
    def load(path):return json.loads(Path(path).read_text())
    screen=load(ROOT/'docs/expert-q4-model-20261029.json')
    native,rows,restored=closed_case(a.case,True)
    monitor=load(a.case/'passive-observer/complete.private.json');visual=load(a.case/'visual-review.private.json')
    placement=load(a.placement/'complete.private.json');summary=load(a.placement/'production-complete.private.json')
    pub=load(a.case/'SELF-published.private.json')
    require(screen['full_model_candidate_screen_passed'] and native['passive_monitor_and_API_completed'] and
        monitor['completed'] and monitor['POSTs']==3 and visual['actual_native_frames_viewed']==2 and
        visual['metrics_legible'] and visual['no_chat_controls'] and visual['Q4_precision_label_correct'] and
        placement['completed'] and placement['native_whole_readback_complete'] and placement['all_five_settings_verified'] and
        placement['production_SELF']==pub['SELF'] and summary['production_SELF']==pub['SELF'] and
        not any(summary[k]for k in('native_running','gateway_running','model_loaded')),'Qualified passive app, frames, placement and final idle required')
    timed=rows[1:];rate=sum(r['generated_tokens']-1 for r in timed)/sum(r['decode_ms']/1000 for r in timed)
    require(all(r['counting_quality_passed'] and r['decode_tokens_per_second']>max(x['decode_tokens_per_second']for x in screen['original_BF16_controls'])for r in rows),
        'The normal Q4 application must retain the measured gain and finite counting quality')
    prior_path=ROOT/'config/production-installation-BF16-cache134-20261029.json'
    current=ROOT/'config/production-installation.json'
    require(not prior_path.exists(),'Preserve the exact prior public installation once');prior_path.write_bytes(current.read_bytes())
    report=dict(schema='ps5-qwen-Expert-Q4-adoption-v1',completed=True,Expert_format='Q4_0',effective_bits_per_Expert_weight=4.5,
        routed_Expert_tensors=147,Experts_per_layer=512,selected_Experts=10,all_Experts_retained=True,
        non_Expert_weights='unchanged original BF16/F32',KV_type='F32',Expert_inputs='F32',activation_quantization=False,
        model_case=7820,normal_application_case=normal_case,production_placement_case=placement_case,normal_requests=rows,
        normal_API_decode_tokens_per_second=rate,BF16_control_decode_tokens_per_second=screen['decode_tokens_per_second']['BF16'],
        normal_decode_ratio=rate/screen['decode_tokens_per_second']['BF16'],
        same_Q4_maximum_absolute_logit_error=max(r['maximum_same_model_absolute_logit_error']for r in rows),
        all_same_Q4_routes_passed=True,finite_counting_quality_passed=True,
        full_non_Expert_payload_SHA256_preserved=True,converted_Expert_matrices=75264,
        original_Expert_payload_bytes=246625075200,Q4_Expert_payload_bytes=69363302400,
        model_logical_GGUF_bytes=181985183872,new_physical_Q4_data_bytes=78313293600,
        active_cache_slots=481,physical_cache_planes=482,cache_budget_bytes=1333739520,
        CPU_heap_peak_bytes=native['CPU_heap_peak_bytes'],postload_device_ledger_peak_bytes=native['device_ledger_peak_bytes'],
        passive_native_frames_viewed=2,monitor_assets_verified=True,clock_calibrated=True,
        source_GPU_model_owners_positively_retired=True,ordinary_OS_close_verified=True,
        production_SELF=dict(bytes=pub['SELF']['bytes'],sha256=pub['SELF']['sha256']),
        previous_BF16_SELF=dict(bytes=pub['original']['bytes'],sha256=pub['original']['sha256']),
        production_native_whole_SHA256_identity_EOF_verified=True,all_five_settings_verified=True,
        previous_and_older_rollbacks_verified=True,final_native_owners=0,final_gateway_running=False,final_model_loaded=False,
        quantized_prefix_reuse_enabled=False,quantized_causal_speculation_enabled=False,quantized_six_demand_enabled=False,
        original_BF16_optimized_profile_preserved=True,production_adopted=True,CI_runs=0,
        driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_profile='cumulative-idle',
        driver_native_archive_sha256='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925',
        persistent_shader_pipeline_caches=False,
        limitations=['Finite repeated counting, not broad reasoning quality or sustained-service certification.',
            'Q4 is lossy; no equivalence of BF16 and Q4 logits is claimed.',
            'BF16 timing controls precede the Q4 runs; these are serial observations on the same console.',
            'I/O counters include prefill and decode.',
            'The compressed Q4 profile does not enable BF16-specific padded delivery or the separately qualified BF16 prefix/speculative path.',
            'The finite launch binding is consumed; a new run requires fresh ownership/resource admission.'])
    write_json(ROOT/'docs/expert-q4-adoption-20261029.json',report)
    install=dict(schema='ps5-qwen-production-installation-v1',date='2026-10-29',
        application_source_revision=a.source_revision,
        application_SELF=report['production_SELF'],driver=dict(repository='akiba-tokyo-jp/PS5-Vulkan-Inference',revision=report['driver_revision'],
            profile=report['driver_profile'],archive_sha256=report['driver_native_archive_sha256'],persistent_shader_cache=False,persistent_pipeline_cache=False),
        precision=dict(Expert_weights='Q4_0',other_weights='original BF16/F32',KV_cache='F32',activation_inputs='F32',quantization='Expert weights only'),
        canonical_startup_SELF_full_readback_verified=True,installed_configuration_full_readback_verified=True,
        previous_production_rollback_preserved=True,previous_production_SHA256=pub['original']['sha256'],
        active_expert_slots=481,physical_cache_planes=482,expert_cache_bytes=1333739520,
        external_requests=[dict(ordinal=r['ordinal'],decode_tokens_per_second=r['decode_tokens_per_second'],TTFT_ms=r['TTFT_ms'],
            total_ms=r['total_ms'],generated_tokens=r['generated_tokens'])for r in timed],
        normal_application_case=normal_case,production_placement_case=placement_case,production_placement_launches=0,
        actual_native_frames_viewed=2,passive_monitor_verified=True,CPU_GPU_utilization_available=False,
        source_GPU_model_resources_positively_retired=True,ordinary_OS_shutdown_verified=True,
        final_native_owners=0,final_gateway_running=False,final_model_loaded=False,
        prefix_reuse_enabled=False,six_demand_enabled=False,causal_width_two_enabled=False,adaptive_selection_enabled=False,
        original_BF16_optimized_profile_preserved=True,qualification_report='docs/expert-q4-adoption-20261029.json',
        historical_installation='config/'+prior_path.name,execution_mode='first-generation-validation',
        run_binding_consumed=True,relaunch_requires_fresh_case=True,sustained_service_qualified=False,CI_runs=0,
        private_repository=True,GitHub_Actions_enabled=False)
    write_json(current,install)
    table='\n'.join(f"| {r['ordinal']} | {r['decode_tokens_per_second']:.6f} | {r['TTFT_ms']/1000:.3f} | {r['total_ms']/1000:.3f} |"for r in rows)
    (ROOT/'docs/expert-q4-adoption-20261029.md').write_text(f'''# Expert-only Q4 production qualification

The Expert-only Q4_0 candidate passed the complete native model comparison,
the passive monitor/API application and production placement. The same PS5
produced correct counting answers in all six requests, with complete same-Q4
vocabulary rows and ordered Expert routes matching on independent repeats.
This is finite counting qualification; broad reasoning quality is not established.

| Request (0 is warmup; 1/2 are API requests) | Decode tok/s | TTFT seconds | Total seconds |
| --- | --- | --- | --- |
{table}

Normal API decode is **{rate:.6f} tok/s**, versus **{report['BF16_control_decode_tokens_per_second']:.6f} tok/s**
in the earlier same-console BF16 controls: **{report['normal_decode_ratio']:.4f}x**.
The isolated Q4 model measured 0.871504 tok/s. Decode counts accepted transitions
after the first token and excludes prefill. Every timed request starts with empty
Expert metadata. Physical request reads fell from 183.1945 GB to 44.9198 GB in
the model comparison; those counters cover both prefill and decode.

Only the 147 routed Expert tensors are quantized. All 512 Experts/layer and
top-10 routing remain; non-Expert BF16/F32 payloads, F32 activation inputs and
F32 KV remain unchanged. Q4_0 stores 32 weights in 18 bytes, including scales
(4.5 effective bits/weight). All 75,264 matrices and complete changed physical
parts passed SHA256/readback; unchanged tensors retain their exact source bytes.
The mixed model is 181,985,183,872 logical GGUF bytes, including reused original
files. No 8-bit comparison, CPU matrix fallback or learned host inference was used.

The same 1,333,739,520-byte cache budget holds 481 Q4 slots plus one guard plane.
This profile uses compressed contiguous delivery. The BF16-specific padded
six-demand path and its prefix/speculative integration remain preserved in the
BF16 rollback; they are disabled in this Q4 profile and are not claimed qualified
under the changed precision. Independent repeats compare Q4 with Q4, not lossy
Q4 logits with BF16 logits.

Both 1920x1080 native CPU rasters were inspected after positive VideoOut
completion. CPU/GPU identity, calibrated date/time and measured token rates
are legible; there are no chat controls. Utilization percentages remain unavailable.
Both API streams match durable native token/output records. Source/model/GPU
owners positively retired, the exact owner normally closed, BF16 restored for
verification, and the proven Q4 executable plus all five settings were then
placed with full native SHA256/identity/EOF readback. Previous BF16 and older
rollback executables were verified. Title, gateway and model are now inactive.

Selected SELF: `{pub['SELF']['sha256']}` ({pub['SELF']['bytes']:,} bytes).
Previous BF16: `{pub['original']['sha256']}`.
The finite run binding is consumed; a new launch requires fresh admission.
This does not certify an unbounded service or general model-answer quality.

## Implementation and reproducible source locations

- `tools/expert_q4_quantize.c`: original BF16 to pinned Q4_0 block encoder.
- `native/qwen_flash_next/expert_q4_local_convert.cpp`: bounded CPU conversion, original/unchanged tensor hashes and full Direct part readback.
- `native/app/expert_q4_receipt.h` and `expert_q4_source_integrity.h`: all 1,256 tensors, mixed precision, 76 logical splits and exact namespace/source admission.
- `native/app/expert_q4_cache_reset.h`: strict 481-slot metadata reset, complete inverse-map validation and retained original GPU banks.
- `tools/build_expert_q4_model_providers.py`: preserve original BF16 dispatch byte-for-byte; only Q4 disables activation quantization and retains F32 inputs.
- `tools/expert_q4_model_source.py::entry_source` / `cache_source`: complete mixed split loader, compressed cache accounting and full repeated Q4 logits/routes.
- `tools/expert_q4_monitor_source.py::monitor_entry_source`: original passive VideoOut/API transport, precise Q4 labeling, bounded generation and matching frame completion.
- `tools/build_expert_q4_model.py` / `build_expert_q4_monitor.py`: immutable relink ancestry, actual ELF loader/callback/import audits and qualified provider reuse.
- `tools/relink_expert_q4_monitor_label.py`: only the fixed CPU raster precision label changes; every inference/cache/driver object is retained byte-for-byte.
- `tools/observe_expert_q4_monitor.py`: durable once-only API intents, ordered stream checks, exact frames, identity and positive retirement.
- `tools/analyze_expert_q4_model.py` / `report_expert_q4_adoption.py`: separate component/model/application evidence and guarded public adoption reporting.

llama.cpp: `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`.
Driver: `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches and CI remain disabled. Cases 7640/7660/7700/
7740/7780 remain their original failed results with ordinary teardown and exact
restoration; corrected model case 7820 and final application case {normal_case} are
separate successful observations. Case 7860 passed the inference/API/retirement
checks; visual review found its stale fixed BF16 header. The final label-only
relink retains all inference/cache/driver objects and is qualified separately.
Application source revision: `{a.source_revision}`.
''',encoding='utf-8',newline='\n')
    print(json.dumps(dict(Q4_production_adopted=True,normal_API_decode_tokens_per_second=rate,ratio=report['normal_decode_ratio'],CI_runs=0)),flush=True)
if __name__=='__main__':main()
