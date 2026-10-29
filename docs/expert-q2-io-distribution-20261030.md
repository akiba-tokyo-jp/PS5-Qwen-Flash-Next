# Q2 I/O latency, adjacency, concurrency and cache concentration

All four requested investigations are complete. Implementation: `afb2dbe0c5237233f61d27f662f468dccd3943ed`; base: `c4cfae3b4adbe28fe47f97f3df944cb856a324fa`. Native case 9340 used one finite model lifetime and ended with exact selected production and settings restored. This report qualifies an investigation candidate; the deployed monitor/API application remains SELF `bb61e2af...` from case 9290/placement 9310.

## Comparable conditions

The complete Flash-Next model uses Gate/Up Q2_K and fitted-scale Down Q2_0 MSE, original non-Expert BF16/F32 and F32 activation/KV. All Experts, top-10 routing and all required layers remain. The cache has 867 slots / 1,333,739,520 bytes. Five native-owned requests run warmup, A, B, B, A; each starts with an empty Expert cache and uses the same 30-token counting prompt. There is no prefix/speculative reuse, HTTP request or display. Each request emits 22 tokens. Decode measurements span 21 transitions, excluding prefill and final EOS. Each timed arm therefore contains 42 transitions. These rates are separate from production normal/API and retained-prefix conditions.

## Individual read-time distribution

| Native 9340 arm | Calls in decode sample | Mean ms | Median ms | P95 ms | P99 ms |
|---|---:|---:|---|---|---|
| A: existing single-Expert bundles | 30,710 | 1.445542 | [1.280, 1.408) | [2.048, 2.176) | [2.176, 2.304) |
| B: adjacent bundle groups | 30,342 | 1.457091 | [1.280, 1.408) | [2.048, 2.176) | [2.176, 2.304) |

Intervals are inclusive at the left and exclusive at the right. The original diagnostic records each actual `pread` completion into 65 bins at 128,000 ns; bin 64 is overflow at 8.192 ms. These are measured percentile bounds, not interpolated exact values. All read-size classes are included. Independently sealed cases 8900 and 9180 give the same P50/P95/P99 bounds. The public JSON retains the histograms and size classes.

The mean rises slightly after merging because a call can return several Experts. Fewer calls still shorten total delivery. The distribution does not support treating rare long-tail calls as the principal cost: the P99 remains below 2.304 ms in both arms. These are syscall wall times including scheduling and OS work, not pure SSD access times. Concurrent call times must not be summed as critical-path waiting.

## Physical adjacency and measured effect

| Metric | A: one Expert per bundle read | B: adjacent groups |
|---|---:|---:|
| Whole-request physical calls | 35,339 | 35,026 |
| Decode calls/token | 731.190476 | 722.428571 |
| Decode physical GB/token (decimal) | 0.430369237 | 0.430369237 |
| Decode tokens/s, pooled within the same arm | 1.144370357 | 1.149977315 |
| Effective GB per source-producer-wait second | 0.641870 | 0.645728 |

The existing 336-Expert immutable bundle file stores one triplet in a 1,540,096-byte aligned stride. Only consecutive physical indices demanded by the same graph and layer are merged. Gate/Up/Down roles remain 537,600 / 537,600 / 460,800 bytes. Groups contain at most five Experts: 7,700,480 bytes, inside the existing 8 MiB scratch window. No gap, unused Expert, new file, new worker or extra scratch is introduced. Identity, reserve, whole-file admission, short-read, complete-consumer and fallback guards remain.

Exact native planner replay predicts 313 fewer calls per complete request and 184 fewer calls over its 21 decode transitions. Native execution confirms those exact reductions: decode calls decrease 1.1983%, while read bytes and misses are unchanged. The two A rates are 1.145118 and 1.143624 tok/s; B rates are 1.150981 and 1.148976. Both candidate observations exceed both controls. The pooled gain is **0.489960%**. This is a useful but small result, with two observations per arm; it is not a general performance guarantee. The mean call time and percentile bins alone would have hidden this improvement.

Each timed request compares 23 full-vocabulary F32 rows against warmup. Maximum absolute difference is zero; ordered routes and emitted tokens match exactly. Host checks cover every role byte in groups 1 through 5, one-call accounting, invalid count/range refusal, short reads and two-lane occupancy.

## Actual application I/O concurrency

| Metric over decode | A | B |
|---|---:|---:|
| Maximum observed in-flight calls | 2.000000 | 2.000000 |
| Average calls while any read is active | 1.587545 | 1.590566 |
| Two-read share of I/O-busy time (%) | 58.754541 | 59.056631 |
| I/O-busy share of decode observation (%) | 76.292459 | 76.207048 |

The existing producer plus its one admitted worker reach two simultaneous `pread` intervals. In A, 58.755% of I/O-busy time has two calls and 41.245% has one. The measured average is 1.58755. The application therefore uses its two-call ceiling, but not continuously. Adjacency merging changes this little. Atomic event accounting measures time at depths 0, 1 and 2; each completed-token snapshot requires zero in-flight reads. Observed call counts reconcile exactly with reader physical-call counters.

This establishes application overlap, not actual SSD hardware queue depth. One large `pread` can itself become multiple device commands. No kernel/block/NVMe queue telemetry was collected, and this test does not establish whether depth 4 or 8 would help. A future depth experiment must retain independent bounded buffer ownership and compare equal real-model bytes; unchanged previously losing composite-parallel or split-graph variants need not be repeated.

## Cache-miss concentration and the 68.51% denominator

| Policy on the same independent counting request | Unique demands | Misses | Miss rate | First-seen misses | Repeat misses |
|---|---:|---:|---:|---:|---:|
| Historical aged LFU | 20,014 | 13,711 | 68.507045% | 6,503 | 7,208 |
| Selected two-touch probation | 20,014 | 12,717 | 63.540522% | 6,503 | 6,214 |

The requested 68.51% is **13,711 / 20,014**, the whole-request aged-LFU unique-demand miss rate. It is not the miss rate of the adopted probation cache, and it does not use the 24,960 raw top-k selected positions as denominator. Repeated selections in a multi-token graph count once per unique Expert demand. Exact replay of the actual native planner reproduces hits, misses and fill order before any concentration analysis. Case 9340 again confirms 12,717 probation misses in every arm.

| Phase | Historical misses | Probation misses |
|---|---:|---:|
| prefill | 6,917 | 6,673 |
| decode | 6,538 | 5,736 |
| final_EOS | 256 | 308 |

Decode has 10,080 unique demands: 48 layers × 10 Experts × 21 transitions. Its miss rates are 64.8611% aged LFU and 56.9048% probation. Neither should be confused with whole-request percentages. All layer/Expert identifiers below are zero-based.

| Whole-request layer | Aged-LFU misses | Probation misses |
|---|---:|---:|
| 0 | 379 | 438 |
| 22 | 368 | 353 |
| 38 | 357 | 341 |
| 5 | 339 | 351 |
| 28 | 339 | 294 |
| 1 | 332 | 330 |
| 12 | 327 | 323 |
| 30 | 324 | 276 |

Historical whole-request leaders are layers 0, 22, 38, 5 and 28: together only 13.00% of misses. Historical decode leaders differ: layers 30 (174), 27 (170), 28 (170), 7 (167) and 29 (167). Selected-probation decode leaders are layers 0 (181), 7 (169), 5 (166), 12 (162) and 17 (154). Global probation improves total misses while layer 0 gets worse; a global average hides that tradeoff.

Historical whole-request Expert leaders include (layer, Expert) (4, 11), (1, 497), (2, 279), (0, 88), (3, 508), each with seven misses. Decode leaders include (0, 50), (1, 312), (2, 463), each seven. With probation, decode leaders include (0, 180), (0, 482), (0, 50), (1, 312), again seven each. The JSON lists the leading keys, their demand counts, repeat misses, every layer and phase-specific detail.

Top 100 Expert keys explain only 4.4709% of historical misses and 5.1742% under probation; top 1,000 explain 34.3082% and 32.2010%. There are 6,503 distinct demanded keys across 24,576 trunk layer/Expert combinations. Under the cold initial condition all 6,503 first-seen keys miss. Probation reduces repeat misses from 7,208 to 6,214. The remaining pressure is spread widely; pinning a few named hot Experts cannot remove most misses. These counts describe this fixed workload, not arbitrary prompts.

## Interpretation and application boundary

The four investigations are complete. Adjacent merging is implemented and useful in a complete native comparison, but the gain is below one percent and leaves bytes/token unchanged. The principal remaining targets are distributed Expert reuse/eviction and periods where only one of the two application I/O lanes is occupied. P99 tails are now measured and do not explain the majority of this workload's source time. Neither the timing histogram nor API occupancy alone proves raw SSD media saturation or a particular NVMe queue bottleneck.

This requested investigation does not replace the selected passive monitor/API application. Applying the candidate to that composed application would require its normal exact-prefix/final-speculative qualification and verified placement; those are distinct from the completed headless comparison and are not reported as performed. The current normal first-independent rate remains 1.143314 tok/s, with the separate retained-prefix result documented in the prior report.

CPU heap peak is 402,718,720 bytes; device ledger peak is 1,749,024,768 bytes, with final live bytes zero. All source/model/GPU owners retired positively, ordinary OS close succeeded, exact original SELF and five settings were restored, and a fresh idle observation confirms no title/gateway/model. No reboot or CI ran. The finite case is consumed and must not be replayed.

## Source map and reproduction

| Source | Relevant function / purpose |
|---|---|
| `native/app/source_io_occupancy.h` | `SourceIOOccupancy::begin/end/snapshot`: bounded application overlap, no per-read allocation/log |
| `tools/expert_q2_adjacent_bundle.py` | `header_source`: bounded group read; `owner_source`: physical adjacency and immutable source; `cache_source`: exact per-slot role scatter and fallback |
| `tools/build_expert_q2_adjacent_comparison.py` | `entry_source/main`: one same-model ABBA with fixed probation, bundle and atomic hint |
| `tools/analyze_expert_q2_io_distribution.py` | `quantile_interval/concentration`: sealed histogram ranks and exact native planner replay |
| `tools/analyze_expert_q2_io_occupancy.py` | `analyze/main`: reconcile per-token calls, bytes, occupancy and numerical results after retirement |
| `tools/prepare_first_case.py` | `qualified_control`: preserve the latest positively qualified optimized SELF as rollback |
| `tests/expert_q2_adjacent_reader.cpp` | Actual generated reader byte/scatter/cap/refusal tests |
| `tests/test_optimized_production_control.py` | Reject missing retirement/integrity/width/quality or live context |

Public sanitized data: [JSON](expert-q2-io-distribution-20261030.json). Private native snapshots and route/fill traces remain off GitHub. The pinned driver/profile/archive and persistent-cache policy are unchanged. The linked candidate SELF is `4ea9809abc277044136fead672da4b65b7e8dd4b46b21c9b25b0544aa4c25f8b`. Historical native controls are cases 8900 and 9180; no unchanged losing experiment was rerun. Host preparation corrected a stale output namespace before launch and continued the already completed transfer without uploading it again. One actual title/model lifetime ran.

A local operator with the sealed data disk can run `tools/analyze_expert_q2_io_distribution.py --cache <data> --workspace <workspace> --out <fresh-private-output>` and `tools/analyze_expert_q2_io_occupancy.py --cache <data> --case 9340 --out <private-json>`. The second refuses incomplete retirement/restoration or counter/numerical mismatches. Native builds and launches require the existing private source seals, qualified owner/session and current-boot contract; these commands never launch console work.
