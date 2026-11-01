# Ordered service and GPU kernel validation

The owner requested1/2 first,3 next, then4/5. Six fresh native comparison cohorts (84 requests) cover the five categories: HC first verifies that split-removal is a null intervention, then tests actual bounded splitK2 parallelism. Every cohort positively retires model/source/device owners, reaches zero live device ledger, ordinarily closes and restores the exact8858 program/settings. No reboot, CI, agents, learned host inference, persistent shader/pipeline cache, weight change, Expert-count change or allocation-limit increase is used.

The common installed control is normal47100/placement47200. All stages use Expert Gate/UpQ2_K, DownQ2_0 MSE,109 resident Q4 matrices including output, other Q8 except original F32/tiny BF16 PLE;3712 active slots/3713 planes, Top2 decode/six-Expert prefill, node256/divisor40 and the qualified serialized tail policy. Driver remains872cc1264ad8ba5d6b888b092968fa5858a38c58/cumulative-idle, archive67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9.

## Native comparison outcomes

Percentages below are isolated matched-cohort differences. They must not be added; final normal performance is measured separately.

| Stage | Candidate | Case | Retained decode change | Whole-time reduction | Semantic task passes | Disposition |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Per-request durable token ledger | 48100 | +13.030957% | +9.214183% | 4/4 | adopted |
| 2 | Paired completed/before-operation stage records | 48500 | -0.164698% | +0.075496% | 4/4 | tested_not_selected |
| 3 | Same-generation positive idle certificate | 49000 | +1.589209% | +1.307485% | 4/4 | adopted |
| 4 | HC-prefill existing splitK2 pipeline | 49900 | +0.952242% | +4.153832% | 4/4 | adopted |
| 5 | Q4 small-row existing LARGE workgroup | 49700 | -0.129924% | -0.065426% | 3/4 | tested_not_selected_speed_and_semantic_regression |

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

## Final actual normal application

One local cold generation, two actual streamed API generations and a finish POST complete; two actual positive native VideoOut frames are viewed. Fixed30-token prompt; cold/retained generate22 tokens, selected prefix25 versus previous22. Previous47100 and selected50100 are sequential cohorts, not matched A/B.

| Condition | Previous47100 tok/s | Selected50100 tok/s | Counting correct |
| --- | ---: | ---: | --- |
| Cold Expert cache | 7.215938 | 7.983627 | true |
| Independent KV reset, weights retained | 9.186170 | 10.555503 | true |
| Exact prefix with causal reuse | 10.476288 | 11.719167 | false |

Prefix counting remains incorrect and its changed25-token output is not a same-output speed comparison. Its rate is not correct-answer throughput; no returned output is rewritten. All three actual ledgers are read back exactly. Exclusive caller-wall intervals reconcile exactly with every enclosing request.

Retained request exclusive intervals:

| Caller interval | ms |
| --- | ---: |
| model_process | 1839.944849 |
| stage | 266.694945 |
| checkpoint | 164.137791 |
| epoch_complete | 147.785664 |
| request_run | 62.544461 |
| token_persistence | 42.518319 |
| epoch_begin | 36.047438 |
| full_validation | 15.167633 |
| sampler | 12.836003 |
| finite_scan | 2.787245 |
| publication | 1.771214 |
| logit_access | 0.111299 |
| token_render | 0.079065 |
| work_guard | 0.000000 |

Selected service mode69; actual CPU peak503382016bytes, device-ledger peak6167724032bytes. Original CPU536870912 and device6199160832 limits remain.

Final placement50200 preserves immediate8858 and its five settings, verifies all12 selected/control files natively before/after placement and restores idle runtime ownership without another title launch. Its exact positive state is in the adoption and installation records.
