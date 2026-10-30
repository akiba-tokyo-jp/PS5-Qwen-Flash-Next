# Six-candidate PS5 inference results

All six requested finite candidate scopes are closed. The selected composition
is implemented, qualified through the normal application, and installed. See
the [sanitized evidence](six-candidate-adoption-20261030.json) and
[installation record](../config/production-installation.json).

## Selected normal application

| Metric | Previous normal 9720 | Selected normal 10140 |
| --- | ---: | ---: |
| Independent TTFT | 11.634333 s | **7.800974 s (-32.949%)** |
| Independent whole request | 20.179917 s | **15.986655 s (-20.779%)** |
| Independent decode | 2.567815 tok/s | **2.681407 tok/s (+4.424%)** |
| Exact repeated-prompt decode | 3.448557 tok/s | **3.676969 tok/s (+6.623%)** |
| Repeated-prompt TTFT | 63.143 ms | 63.669 ms |
| Capture-charged two-request throughput | 1.621072 tok/s | **1.949547 tok/s (+20.263%)** |

These are separate cache conditions on one PS5. The normal control is the
historical 9720 protocol, not a new normal ABBA. Each input has 30 prompt tokens
and produces 22 counting tokens. Model cold load is excluded. Pair throughput
includes prefill and prefix capture; it is not decode throughput. Candidate
percentages are never added to predict this measured combination.

The selected weights are Gate/Up Q2_K, Down Q2_0 MSE, output Q8_0 and original
BF16/F32 for the remaining non-Expert tensors. Inputs and KV remain F32. All
Experts remain available. Prefill and decode each select six Experts, with
width16/all-output prefill and the existing cached-ranking multiplier1.5.

The cache has 997 active slots, 998 physical planes and 1,533,419,520 raw bytes.
There are 448 bundled Experts: the original420 plus28 supplemental triplets.
Adjacent reads, four-read delivery, two-touch probation and temporal window0
remain selected. Full identical-prompt reuse and final-consumer causal
verification remain enabled.

## Candidate decisions

| Technology | Physical result | Final disposition | Implementation |
| --- | --- | --- | --- |
| Resident output Q8 and cache redistribution | Same-Q8 867/997 ABBA: decode +3.274%, whole time -1.858%; all six fixed content/format checks pass | Q8 output and997 slots adopted | `ResidentOutputQ8Receipt`, `resident_output_Q8_source_integrity`, `reset_resident_output_Q8_cache`; `tools/build_normal_output_q8.py` |
| Prefill Top8/Top6 | Top8: TTFT -16.233%, whole -8.436%, decode -2.091%. Top6: TTFT -32.167%, whole -15.327%, decode -6.807% | Top6 adopted for whole-request speed; Top8 remains a tested alternative | `qwen_app_six_prefill_experts`, `build_moe_ffn`; `native/app/normal_performance_policy.h` |
| Current-trace Expert placement | Additional28 triplets: decode +0.905%, whole -0.292%,132 fewer reads/request; complete counting F32 difference0 | Adopted; normal requests actually use53/53/16 supplemental triplets | `qwen_app_Q2_bundle_index`, `qwen_app_try_Q2_bundle_group`; `tools/build_normal_current_placement.py` |
| Shared16-token prefix with different suffixes | Two-request time -17.134% including capture; suffix TTFT -38.210%; first prediction after the changed suffix has full-vocabulary F32 difference0;9/9 arithmetic tasks pass | Implemented and physically qualified as the shared16 workload mode | `native/app/partial_prefix_prefill.inc`: `LlamaEngine::prefill`; `ModelCheckpoint::capture` / `restore` |
| Late output-head crop after all final-layer Expert rows | Whole time +0.06765%, decode -0.456%; no separated whole-request gain | Tested without a qualified gain; not selected | `qwen4exp.cpp`, `crop_before_nextn` / `crop_after_nextn`; `tools/build_six_candidate_screen.py` |
| Guarded graph reuse | Decode +3.057%, whole time -1.372%, full F32 difference0;21 actual reuses/counting request | Adopted with route bits, phase and every original input/shape check | `llm_graph_result::can_reuse` / `set_inputs`; `tools/build_normal_performance.py` |

The shared16 mode is an implemented alternative for different suffixes. The
normal repeated identical-prompt protocol retains its complete30-token
checkpoint and approximately64 ms TTFT. These modes do not hold two simultaneous
snapshots. Shared16 is exercised by the native placement/prefix entry built by
`tools/build_placement_prefix_screen.py`; it is not silently enabled in the
identical-prompt normal default. This is a completed workload choice, not a
pending validation or a claim that the two modes' gains can be combined.
The exact0 comparison covers the complete vocabulary of the first prediction
after suffix prefill. Later cache-biased decode is checked for finite values and
the fixed outputs, rather than asserted equal at every position.

The initial84-triplet materialization returned a short write. A subsequent
helper transfer explicitly returned ENOSPC. The28 complete triplets were
individually verified, sealed and physically compared. The selected finite
implementation uses those28; no speed claim is made for a complete84-triplet
pack. The failed writer was not replayed.

## Source traffic and memory

The isolated output-Q8 comparison uses Top10 prefill and Top6 decode. Its867 to997
slot change reduces decode source traffic0.127959 to0.116424 GB/token and read
calls227.33 to208.90/token. Producer wait falls211.31 to200.72 ms/token. Mean
individual read time stays about1.502 ms. These are source-reader observations,
not SSD-controller bandwidth. They are not relabelled measurements of the final
Top6-prefill/graph/placement composition.

Output quantization saves595,968,000 resident payload bytes. Exactly199,680,000
bytes of post-load quota are transferred to the cache. The original512 MiB
single-buffer and CPU limits,248 MiB workspace cap and every physical
Direct/Flexible/kernel reserve remain. Actual final CPU heap peak is503,382,016
bytes; model-device ledger peak is2,071,986,176 against2,078,728,192 permitted
bytes. The remaining6,742,016 ledger bytes are not the console's physical free
memory or OS kernel headroom.

## Correctness and lifecycle

Case9800 completes32 requests, case9980 completes20, output-Q8 case10050 completes11
and normal case10140 completes3. Each successful lifetime positively retires all
model/source/GPU owners, ordinarily closes and restores its exact control before
the final placement. There is no remaining request in these finite scopes.

The normal independent F32 comparison is exactly0 and all counting tokens match.
The final unlike-cache/width comparison reaches6.634334, with finite complete
vocabulary and matching emitted tokens. Seven causal attempts reconcile as six
acceptances, one rejection, seven captures and one restore. Actual graph reuse
counts are21/21/3. This does not establish broad reasoning quality or sustained
service.

Both exact native frames were viewed: CPU/GPU information, synchronized UTC,
2.68/3.68 tok/s and an explicit output-Q8 label are legible. No chat controls are
present. Unknown utilization counters remain dashes.

The normal observer's final capacity assertion still expected867 after all
three POSTs had already completed. The preserved terminal and frames were
reconciled against their exact997-slot scope, without repeating a POST or model
operation. The observer now uses its declared slot and graph policies; targeted
regression checks retain all positive retirement requirements.
Four observer tests and ten current/historical production-admission tests pass
manually, including mismatched capacity, precision, quota and retirement cases.

Earlier CPU proof/type refusals, the full-volume empty report, and the returned
context-budget refusal remain in the evidence. Each title ordinarily closes and
restores; the original collector flag for10010 remains preserved. The corrected
Q8 context requires exactly1,533,419,520 cache bytes. All1,256 actual receipt
tensors,15 receipt/type/source negative controls and three non-output Q8 guard
negative controls pass before the final successful run.

## Installed provenance

Implementation revision: `37ac48b07cf0742636e8639fec13c4374108cb30`.
Installed SELF: `5487e687dbc13a5f6a7655faf52d91752f3d029ba13938762b133b99e6a3a7a5`
(18,299,623 bytes). Driver remains
`PS5-Vulkan-Inference@872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`,
linked archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader and pipeline caches remain disabled.

Placement10160 verifies13 programs and five settings through two original-bounded
native whole-SHA256/identity/EOF batches. Exact previousf49ba8ef and every older
named rollback remain. Host-preserved duplicate files and three closed trial
executables were retired; model assets and the shared-prefix program remain.
The native title, gateway and model are inactive. The finite binding is consumed;
a future run needs a fresh binding. No CI, reboot, forced Unix signal or delegated
agent is used.
