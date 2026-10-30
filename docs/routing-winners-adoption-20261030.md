# Production routing and causal sharing adoption

The successful routing settings are integrated, physically qualified in the
normal passive/API app, and placed in production. The canonical SELF is
`55a8e4c4778481b80e9ad32e4dd1c77a7b9051717de5cdba50e77435b7a6f0e1` (17,500,087 bytes).
The exact db542fa2 program, all older applications and five settings are retained.
See the [sanitized evidence](routing-winners-adoption-20261030.json) and
[current installation](../config/production-installation.json).

## Actual normal application results

| Matched protocol metric | Previous 9400 | Selected 9550 |
| --- | --- | --- |
| First independent decode | 1.293876 tok/s | **2.565459 tok/s (+98.277%)** |
| Exact repeated-prompt decode | 1.264045 tok/s | **3.522102 tok/s** |
| Repeat time to first token | 62.080 ms | **62.492 ms** |
| Capture-charged two-request throughput | 0.906237 tok/s | **1.497207 tok/s (+65.212%)** |

The independent first-token time remains about 14 seconds; repeated-prompt
first-token time is about 62.5 ms. The two cache conditions remain separate.
The group charges prefill, prefix capture/restore, rejected verification work and
the final EOS steps. Initial cold model loading is outside the API intervals.
Both actual native frames were viewed: 2.57 and 3.52 tokens/s, CPU/GPU information,
synchronized UTC date/time, correct precision/Top-6 cache labels and no chat controls.
Unavailable CPU/GPU utilization remains `--`.

## Direct composition comparison

One resident model lifetime uses counting order `2,2,6,14,14,6,2`, then nine
quality requests. Every request starts with an empty Expert cache. The two
candidates for each composition are symmetric around the controls. Graph reuse
is disabled uniformly, with all previous I/O winners and the same driver.

| Composition | Decode tok/s | Whole-request generated tok/s | Physical GB/decode token | Reads/decode token |
| --- | --- | --- | --- | --- |
| Top-6 | 1.970974 | 0.874773 | 0.216583 | 378.52 |
| Top-6 + cached ranking | 2.531554 | 0.973308 | 0.126792 | 225.00 |
| Top-6 + cached ranking + repeated verification | 2.736387 | 0.976006 | 0.128755 | 228.24 |

Repeated verification adds about 8.09% decode over cache plus Top-6, with both
decode repetitions faster than both controls. Its aggregate whole-request gain
is only 0.277%, with overlapping individual intervals. The initially written
strict whole-request rule would select policy 6. The selection criterion was
refined after this exploratory comparison to reflect the owner's generation-speed
priority; this change and the uncertain whole-request gain are disclosed.
Normal 9550 then independently confirms the selected full composition against
the installed protocol. It is not another normal policy-6/policy-14 ABBA.
Individual first-stage percentages are not added.

## Integrated behavior and numeric scope

Prefill keeps ten Experts; decode uses six. Cached ranking multiplies selection
scores by 1.5 while mixture weights use original probabilities. Preferences are
latched before a target event and stay fixed across both verification rows and
any rejection replay. Both decode widths use the same selected Expert count.
The policy implementation also retains the measured Top-8 alternative.

The first API request retains its complete prompt snapshot. Its final exact-prefix
consumer can reuse that single GPU snapshot for up to eight causal pair attempts.
The actual normal run completes seven: six accepted, one rejected, seven complete
captures, one complete rejection restore and six delivered bonus samples.
The first API repeat matches warmup F32 exactly. The final retained-cache/mixed-width
maximum difference is 3.666849; values remain finite and every emitted counting
token/byte matches. This approximate cache/width difference is not treated as an
ordinary same-input precision bound or hidden behind a blanket equality claim.

All three composition settings pass the fixed translation, arithmetic and raw
JSON tasks, 3/3 contents and 3/3 strict format each. Raw outputs are retained.
These finite tasks do not establish broad reasoning accuracy. Expert weights stay
Gate/Up Q2_K and Down Q2_0 MSE; other BF16/F32 weights, F32 inputs/KV, every stored
Expert/layer, 867 cache slots, original probation, 420 bundles, adjacency merging
and four-demand reads remain. Every selected routing and retained I/O path executes
in the normal application.

## Placement, guards and implementation

Normal 9550 retires all model/source/GPU owners positively, leaves device ledger
zero, closes ordinarily and restores the exact control before placement.
Placement 9560 verifies all **11 programs and five settings** with native complete
SHA-256, stable identity and EOF. The growing rollback inventory is 283,582,840
bytes, so its after-placement check uses two original-bounded batches rather than
raising the 256 MiB per-helper envelope or the 1 MiB input window. No rename,
model run or GPU work is replayed. A preparation definition collision was also
resolved by proving source equality and resuming only unfinished CPU preparation.

Fresh idle is confirmed after placement. The native title, gateway and models are
inactive. The inherited finite binding is consumed; sustained service remains
outside this qualification. Peak private heap is 503,382,016 bytes within 512 MiB;
peak device ledger is 1,870,659,584 bytes within 1792 MiB. These are measured
retained-context limits, not universal bounds for arbitrary workloads.
The original twelve physical/resource/owner/completion guard families pass.
No CI, reboot, Unix force signal or persistent shader/pipeline cache is used.

Application implementation: `d2c166573dd8f1b7cae552b35e574fc0581d9715`.
Driver: PS5-Vulkan-Inference `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
profile `cumulative-idle`, linked archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Exact generated entry and shared provider hashes are in the JSON.

- [Routing policy](../native/app/expert_routing_policy.h) and
  [runtime](../native/app/expert_routing_policy.cpp): consistent width-one/two
  cardinality, deterministic residency and event-latched selection.
- [Causal adapter](../native/app/causal_expert_sharing.h): committed-history drafts,
  complete decisions and queued bonus handling.
- [Normal link](../tools/build_routing_winners_monitor.py): passive/API integration,
  exact-prefix final-consumer handoff and positive replacement accounting.
- [Normal observer](../tools/observe_routing_winners_monitor.py) and
  [qualification](../tools/qualify_routing_winners_monitor.py): actual source,
  route, stream, frame, numeric, ownership and measured adoption criteria.
- [Bounded preservation batches](../tools/preservation_batches.py): keep every
  rollback verification within the original read envelope.

All requested integration, verification and production-placement steps are complete.
