#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render the measured native service/kernel dispositions as repository documentation."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 r=json.loads((ROOT/'docs/service-kernel-results-20261101.json').read_text());w=json.loads((ROOT/'docs/service-kernel-worklog-20261101.json').read_text());names=['Per-request durable token ledger','Paired completed/before-operation stage records','Same-generation positive idle certificate','HC-prefill existing splitK2 pipeline','Q4 small-row existing LARGE workgroup']
 text='''# Ordered service and GPU kernel validation

The owner requested1/2 first,3 next, then4/5. Six fresh native comparison cohorts (84 requests) cover the five categories: HC first verifies that split-removal is a null intervention, then tests actual bounded splitK2 parallelism. Every cohort positively retires model/source/device owners, reaches zero live device ledger, ordinarily closes and restores the exact8858 program/settings. No reboot, CI, agents, learned host inference, persistent shader/pipeline cache, weight change, Expert-count change or allocation-limit increase is used.

The common installed control is normal47100/placement47200. All stages use Expert Gate/UpQ2_K, DownQ2_0 MSE,109 resident Q4 matrices including output, other Q8 except original F32/tiny BF16 PLE;3712 active slots/3713 planes, Top2 decode/six-Expert prefill, node256/divisor40 and the qualified serialized tail policy. Driver remains872cc1264ad8ba5d6b888b092968fa5858a38c58/cumulative-idle, archive67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9.

## Native comparison outcomes

Percentages below are isolated matched-cohort differences. They must not be added; final normal performance is measured separately.

| Stage | Candidate | Case | Retained decode change | Whole-time reduction | Semantic task passes | Disposition |
| --- | --- | --- | ---: | ---: | ---: | --- |
'''
 for s,name in zip(r['stages'],names):
  a=s['speed'];text+=f"| {s['id']} | {name} | {s['case']} | {a['retained_decode_gain_percent']:+.6f}% | {a['retained_whole_time_reduction_percent']:+.6f}% | {sum(a['quality_grades'])}/4 | {s['status']} |\n"
 text+='''
Stage1 replaces per-token open/create/chmod/write/fsync/close with one bounded append-only request ledger. **Every token still completes fsync before API publication.** All candidate ledgers are read back after positive close; IDs, piece bytes, counts, order and exact lengths match actual native output. The new format is JSONL metadata, not a lossy or asynchronous log. Existing stage journals, safety admission, full F32 validation and monitoring remain enabled. Boundary-memory diagnostic mode is not active in these speed cohorts.

Stage2 pairs only the returned llama synchronization marker and the following before-device-idle record, with both lines durable before the operation and all observations retained. It executes68 pairs in the timed candidate groups but whole-time savings(-8.810ms,+12.784ms) do not exceed15.042ms A/A spread. It is tested and not selected; it is not left unverified. Production retains the original stage record path.

Stage3 holds the existing queue lock and reuses a positive certificate only for the same frontend/device/submission generation and freshly matching, healthy, quiet requested/completed worker epoch. A new submit invalidates reuse through its changed generation. Owner snapshots, retirement and journal checks remain. Focused host API stubs exercise positive reuse, new-submit invalidation, producer overlap and pending/epoch/log/snapshot/retirement failures. Native timed candidates execute132 positive reuses and preserve every complete target F32 row/token. Paired whole savings27.634ms/41.090ms exceed9.533ms A/A spread.

Stage4 initial case49300 inspects1160 eligible HC choices in the timed candidate groups: every original split is already1 and zero forced-removal selections execute. No speed gain is attributed to this unchanged path. Follow-up49900 therefore exercises actual existing splitK2 only for Q8 HC matrices with K>=2048, M<=512 and N16-32; existing workspace/device/single-buffer budgets remain. This is a changed parallelism experiment, not a replay of the null comparison. It executes1158 split-two selections across the complete native cohort, passes all four semantic tasks and reduces retained whole time4.153832%; cross-control maximum F32 difference9.662799 is disclosed separately from exact independent-candidate reproduction.

Stage5 reuses the identical GPU object and recompiles only its entry selector. The existing Q4 LARGE workgroup is exercised8208 times overall, preserves candidate-independent complete F32 SHA256/routes, but changes routes relative to control. It produces no repeatable speedup and fails1/4 semantic tasks; maximum cross-control F32 difference is7.871416. It is not selected. This decision uses actual speed/answer results, not an arbitrary maximum-F32 cutoff. Candidate repeatability alone does not establish answer quality.

## Numerical and measurement scope

CPU-only stages1-3 preserve all full target F32 rows and tokens exactly. GPU choices may change reduction order. All target rows remain finite; full cross-control maxima, distributions and ordered routes are recorded separately. Independent candidate cold/retained repeats hash all evaluated F32 vocabulary rows after request timing and match their own complete ordered routes. Hash work is performed in both arms. Same fixed counting output remains required. Altered routing/I/O makes GPU-candidate timings whole-configuration observations, not isolated shader speed claims. Four semantic tasks are a finite quality scope; no general accuracy or sustained-service qualification is claimed.

The source partition remains caller-wall accounting, not CPU cycles. Inclusive spans must not be added, and GPU waits/source I/O remain inside model-processing wall. `work_guard` is not separately isolated. No GPU diagnostic timestamp provider is installed.

## Implementation and evidence

- `native/app/durable_token_ledger.h`: bounded per-request records, synchronous per-token persistence and explicit close.
- `native/app/service_options.h`: explicit experiment mode and bounded stage-pair state.
- `tools/build_service_cpu.py`: identical-current-GPU CPU factors and optional precise stage pairing.
- `tools/build_service_completion.py`: application `DriverLifecycle::finish_boundary` certificate reuse; shared driver archives remain unchanged.
- `tools/check_service_completion.py`: actual transformed frontend API-stub refusal/invalidation checks.
- `tools/build_service_gpu.py`: existing pipeline selectors in `ggml_vk_mul_mat_q_f16` and `ggml_vk_get_dequantize_mul_mat_vec`.
- `tools/build_service_HC_split_two.py`: bounded actual HC splitK2 follow-up.
- `tools/retarget_service_gpu.py`: reuse the frozen GPU provider for the Q4 factor.
- `tools/build_service_normal.py`: qualified normal API/display composition with only selected factors.
- `tools/verify_service_records.py`: every persisted token's closed-file readback against native output.
- `tools/analyze_service_kernel.py`: immutable measured results and exact exclusive CPU span reconciliation.

Raw console logs, target rows, ledgers, images, models and binaries stay outside Git. Source/build failures and the zero-launch preparation refusal remain preserved in the worklog; they do not represent PS5 launch attempts or physical impossibility. [Worklog](service-kernel-worklog-20261101.json), [machine-readable results](service-kernel-results-20261101.json), [adoption](service-kernel-adoption-20261101.json) and [installation](../config/production-installation.json) distinguish completed comparisons, selection, normal qualification and verified production placement.
'''
 if 'normal'in r:
  n=r['normal'];text+='\n## Final actual normal application\n\nOne local cold generation, two actual streamed API generations and a finish POST complete; two actual positive native VideoOut frames are viewed. Fixed30-token prompt; cold/retained generate22 tokens, selected prefix25 versus previous22. Previous47100 and selected50100 are sequential cohorts, not matched A/B.\n\n| Condition | Previous47100 tok/s | Selected50100 tok/s | Counting correct |\n| --- | ---: | ---: | --- |\n'
  for label,before,after,quality in zip(('Cold Expert cache','Independent KV reset, weights retained','Exact prefix with causal reuse'),(7.215937995634785,9.18616970652997,10.47628803254429),n['rates'],n['quality']):text+=f'| {label} | {before:.6f} | {after:.6f} | {str(quality).lower()} |\n'
  text+='\nPrefix counting remains incorrect and its changed25-token output is not a same-output speed comparison. Its rate is not correct-answer throughput; no returned output is rewritten. All three actual ledgers are read back exactly. Exclusive caller-wall intervals reconcile exactly with every enclosing request.\n\nRetained request exclusive intervals:\n\n| Caller interval | ms |\n| --- | ---: |\n'
  for g in sorted(n['CPU'][1]['groups'],key=lambda x:x['exclusive_ms'],reverse=True):text+=f"| {g['group']} | {g['exclusive_ms']:.6f} |\n"
  text+=f"\nSelected service mode{r['selected_service_mode']}; actual CPU peak{n['CPU_peak']}bytes, device-ledger peak{n['device_peak']}bytes. Original CPU536870912 and device6199160832 limits remain.\n"
  text+='\nFinal placement50200 preserves immediate8858 and its five settings, verifies all12 selected/control files natively before/after placement and restores idle runtime ownership without another title launch. Its exact positive state is in the adoption and installation records.\n'
 (ROOT/'docs/service-kernel-results-20261101.md').write_text(text,newline='\n');print('Measured native comparison documentation reconciled.')
if __name__=='__main__':main()
