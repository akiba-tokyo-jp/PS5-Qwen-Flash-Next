# Native cache-aware routing, Top-k and multi-token verification results

All three requested algorithm families have completed physical verification.
The five completed requests of 9440 and eight of 9460 are retained; final continuation 9480
completes the remaining 20 requests, positive resource retirement, ordinary close
and exact production/settings restoration. No requested comparison remains pending.
See the [sanitized JSON evidence](expert-routing-sharing-results-20261030.json).

## Measured counting comparisons

Each row has its own interleaved A/B/B/A comparison, the same 30-token prompt,
an initially empty Expert cache and at most 32 generated tokens. Prefill routing
remains Top-10. Cache-ranking changes only selection scores; mixture weights use
original probabilities. Top-8/6 change the actual decoded graph dimensions.
The repeated controller proposes only from committed token history and verifies
each pair using the original GPU target and complete-state rollback.

| Candidate | Decode tok/s, control -> candidate | Change | Physical GB/token, control -> candidate | Read calls/token, control -> candidate |
| --- | --- | --- | --- | --- |
| Cached ranking x1.5 | 1.275516 -> 1.841726 | +44.391% | 0.429676 -> 0.237698 | 689.62 -> 391.52 |
| Decode Top-8 | 1.272934 -> 1.640244 | +28.855% | 0.429676 -> 0.297821 | 689.62 -> 510.71 |
| Decode Top-6 | 1.272166 -> 1.974742 | +55.227% | 0.429676 -> 0.216583 | 689.62 -> 378.52 |
| Repeated causal width two | 1.272544 -> 1.433831 | +12.674% | 0.429676 -> 0.400695 | 689.62 -> 656.00 |

The interval is first-to-last accepted output token: prefill and final EOS are
excluded, while speculative rejected work inside the interval is charged. Source
bytes/calls independently reconcile with returned pread counters. Individual
call durations overlap and must not be summed as critical-path source wait.
Candidate percentages are not additive; combinations are not measured.

The separate whole-request intervals below include prefill, the final EOS step,
complete capture/restore and any rejected verification work. Initial cold model
load is outside these resident requests. Prefill stays Top-10 in every mode,
so a decode-only improvement is not an equal end-to-end improvement.

| Candidate | Whole-request generated tok/s, control -> candidate | Physical GB/request, control -> candidate | Read calls/request, control -> candidate |
| --- | --- | --- | --- |
| Cached ranking x1.5 | 0.703045 -> 0.849020 | 20.050279 -> 15.817347 | 34287.0 -> 27712.0 |
| Decode Top-8 | 0.702271 -> 0.800821 | 20.050279 -> 17.168753 | 34287.0 -> 30396.0 |
| Decode Top-6 | 0.702412 -> 0.876422 | 20.050279 -> 15.320431 | 34287.0 -> 27435.0 |
| Repeated causal width two | 0.702155 -> 0.726739 | 20.050279 -> 19.934178 | 34287.0 -> 34533.0 |

All four candidate settings improve this finite timing comparison. Top-6 has
the largest individual decode gain; cached ranking keeps ten active Experts.
Repeated verification improves decode by 12.674% but whole-request throughput
by only 3.501%; whole-request reads increase from 34,287 to 34,533 (+0.717%).
It is therefore a measured speed improvement, not a general reduction in total
request count. The counting token sequence is unchanged in every candidate.

Graph reuse is disabled uniformly because topology differs across modes. These
absolute rates must not replace the separately qualified normal application
rate of 1.293876 tok/s. All selected I/O optimizations remain common: 420 partial
bundles, adjacency groups, four-demand reads and original probation, with 867
slots and 1,333,739,520 cache bytes. Expert precision and other BF16/F32 weights,
F32 inputs/KV, complete stored weights and the pinned driver remain unchanged.

## Finite quality checks

Each mode runs translation of a fixed Japanese greeting, 17+26, and JSON-only
Tokyo/count=3 output, once each. Answer contents and raw format are separate.
Application outputs are never normalized. These are three fixed tests, not a
broad accuracy or reasoning benchmark. Raw outputs are preserved in the JSON.

| Mode | Answer contents | Strict format |
| --- | --- | --- |
| Ordinary Top-10 | 3/3 | 3/3 |
| Cached ranking x1.5 | 3/3 | 3/3 |
| Decode Top-8 | 3/3 | 3/3 |
| Decode Top-6 | 3/3 | 3/3 |
| Repeated causal width two | 3/3 | 3/3 |

The two timed repeated-verification candidates execute 14 actual pair
verifications: 12 accepted and 2 rejected. Snapshot capture and
restore counters must reconcile every decision. Full-vocabulary values remain
finite in every request; unchanged counting controls retain exact full F32 and
emitted tokens. Approximate candidates are measured without a cross-mode F32
equality veto. Actual variable-k routes reconcile all unique cache demands and
their complete Gate/Up/Down payloads. The JSON records counting token equality
separately from the quality checks.

The repeated controller is specifically the causal model-free `single_latest`
history proposer with width two and at most eight attempts. It tests real
multi-token Expert reuse, including rejected work and rollback, but does not
establish the performance of a learned draft model, wider verification or a
longer workload. Two timing repetitions per candidate and three quality tasks
per mode establish only this finite comparison, not a broad accuracy claim.

## Integration failure and recovery

The first case 9440 completed warmup and the cache-ranking ABBA, then the
application self-terminated at the first Top-8 decode. The graph selected eight
Experts, but the upstream aggregation loop still constructed ten views from
the configured model value. The corrected graph bounds aggregation by the
actual Expert dimension; host regression checks cover six/eight/ten and the
original per-layer cap.

CPU-only observation confirmed zero native owners, AppInfo idle, unchanged boot
and stable management services. Exact production/settings were restored and
read back before the new run. No PS5 forced signal or reboot was used. The old
case has no native whole-model GPU-retirement terminal; that missing proof and
unknown native completion remain explicit. Its five positively reset durable
request results and 110 token snapshots support only that completed comparison.
They are not relabelled a successfully completed 29-request protocol.
The failed runs do not have their deferred complete route sidecars: their
native result rows are emitted only after the route/source reconciliation gate,
and their per-token bytes/calls are independently auditable. Final quality
requests provide the complete stored variable-k route records for each mode.

Case 9460 completed the Top-8 and Top-6 ABBAs, then completed one accepted
width-two verification before rejecting the next checkpoint reservation.
The application charged a full additional buffer when the payload size changed;
the pinned upstream writer actually destroys the old buffer before allocating
its replacement. Its failure terminal, ordinary close and exact restore remain
explicit. Eight completed requests and 176 token snapshots are reused; no
global positive GPU retirement is claimed for that failed run.

The correction credits only the raw payload of a positively completed snapshot
on the same single-Vulkan-buffer context, with no credit for alignment slack.
The replacement upper bound is rounded up by 2 MiB. All original device, Direct,
physical and kernel reserves are retained, with per-attempt diagnostics and a
pinned release-before-allocation writer. Host regression covers first capture,
same-size reuse, growth, shrinkage and the original payload limit.

Final case 9480 runs only the repeated-verification ABBA plus every quality request.
All 20 requests finish; model/source/GPU owners retire positively, the final
device ledger is zero, ordinary close passes and the exact db542fa2 production
SELF and all five settings pass native whole SHA256/identity/EOF restoration.
Fresh idle is confirmed. The title, gateway and model are inactive.

## Implementation and scope

Implementation commits: `313afc47dcf0412abbc9d029526fdf01a6824332`,
`74f12e010d30759e563ae06b03b69761222ffaa0` and the checkpoint replacement
correction `c9b5d7bb004d9a6863a3c4bee9543cdaa7494b18`. Final native build 9472 and SELF
9474 bind exact generated entry/cache/engine/graph/observer/runtime source hashes
in the JSON. The qualified driver remains PS5-Vulkan-Inference
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, linked
archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled; no CI runs or weight changes.
The checkpoint writer is pinned to llama.cpp
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`, `src/llama-context.cpp:3062-3163`;
its SHA-256 is recorded in the JSON. Measured peak private heap is 419,495,936
bytes within 512 MiB; peak device ledger is 1,870,659,584 bytes within 1792 MiB.
The final ledger is zero. These bounds apply to this retained-context cohort.

- [Routing runtime](../native/app/expert_routing_experiment.cpp): deterministic
  residency updates and ranking of the completed 512-score row on the CPU.
- [Policy and bounds](../native/app/expert_routing_experiment.h): ranking,
  decoded Expert cardinality and bounded Expert aggregation.
- [Build derivation](../tools/build_expert_routing_sharing.py): isolated graph,
  cache, complete route observer and repeated causal adapter; all matrix providers
  remain the original GPU implementations.
- [Native cohort](../native/app/expert_routing_sharing_cohort.inc): independent
  cache reset, actual counters, complete-state admission and finite quality runs.
- [Guard audit](../tools/audit_expert_routing_sharing.py): original twelve resource,
  source-identity, ownership and positive-completion families.
- [Analysis](../tools/analyze_expert_routing_sharing.py): accepted-token intervals,
  durable partial evidence and unmodified raw-format judgments.

Production is unchanged. This request is first-stage algorithm verification;
normal application adoption requires its own qualification and a decision on
the observed quality tradeoff. No production speed claim is made for an unplaced
experimental executable.
