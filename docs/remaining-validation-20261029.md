# Remaining proposal qualification

The machine-readable execution ledger is
[remaining-validation-20261028.json](remaining-validation-20261028.json).
It distinguishes completed comparisons without a winner from unexecuted work.
A measured loser does not require a full-model integration or an unchanged rerun.
The original failed cohorts remain failed; a later corrected case is a separate
record. No reboot, CI, weight quantization or persistent driver cache was used.

## Completed comparisons

| Proposal | Actual evidence | Disposition |
|---|---|---|
| Width four | Cases 6040, 6130 and 6260: full acceptance, all three rejection positions, exact restored F32 values; eight same-width vocabulary comparisons and three complete active-state fingerprints | Correctness and bounded repetitive-input timing passed; no production promotion without the normal adaptive application gate |
| Adaptive widths 1/2/4 | Eight fixed inputs in 6260; matched ordinary-width-two/adaptive reverse comparisons in 6540 at 128 slots | All greedy outputs exact; repetitive input decode improves about 23.3%, whole request about 11.6%; this is not a general workload claim |
| Additional Expert cache | 6360: 120 numerical/canary cases, 360 graphs; 6460/6760/6780/6820: actual 128/134 ABBA; normal application 7080 | Small positive timing result; adopted as the normal counting profile in 7420 |
| Actual hidden-router observation | 6170: actual post-PLE hidden inputs and authoritative later routing; layer 23 rank-one decode precision 50%, about 9.28 ms early | Tested diagnostic, no standalone speed gain |
| Hidden-state Expert prefetch | Corrected callback case 7040; same graph off/on/on/off; both candidate requests performed 18 actual Expert loads, nine useful and nine unused | Tested, no qualified speed gain; do not adopt |
| Shared-input packed BF16 projections | 6700 at widths 1/2/4, original shaders, prepacked weights and two output views, without per-token weight or output copying | Tested, no reproducible gain; no full-model integration required |
| Remaining gated normalization fusion | 6700 at widths 1/2/4, original F32 state, weighted RMS and sigmoid retained | Tested, no reproducible gain; existing GDN core was already fused |
| Small dense GEMM dispatch | Actual 6170 profiler identifies existing `MUL_MAT_VEC` at widths 1/2/4 | Existing implementation verified; no new speedup claimed |
| Router workgroup choice | 6700 compares existing LARGE128 and AMD SUBGROUP32 paths at widths 1/2/4 | Tested, no reproducible gain; no full-model integration required |

The nine portable GPU comparisons completed 324 graphs with F64 numerical
references, canaries, synchronization and positive retirement. None passed both
reverse-order improvement conditions and both bootstrap lower bounds above one.
The measured boundary includes the original durable driver checkpoints and
synchronization; it does not isolate very small shader-only effects. That
limitation is recorded as a tested result without a qualified winner, not as
an untested integration debt.

In 7040, full F32 differences were zero. Mean decode throughput ratio was
0.999034x and whole-request throughput ratio 0.999303x. These small differences
do not establish a beneficial hidden-state prefetch implementation. Case 6600
is retained as an invalid earlier experiment: it transferred zero predicted
bytes because a quoted include selected the neighboring original callback
header. The corrected runtime translation unit was isolated before 7040.

Previously completed READY overlap, PLE copy elision, fused GEMV, route-based
prediction, AIO, tested SSD codecs/copies and Expert-major comparisons remain
terminal. Expert-major timing was inconclusive after eight native rounds;
it is not pending a whole-model repack. The CPU metadata comparison is also
complete; its estimated fixed-request saving was only 0.1334 ms.

## Cache timing

| Lifetime | Active slots | Mean decode tok/s | Mean request ms |
|---|---:|---:|---:|
| 6460, A | 128 | 0.4185941981 | 100357.385940 |
| 6760, B | 134 | 0.4198092696 | 99673.651471 |
| 6780, B | 134 | 0.4198160060 | 99665.239179 |
| 6820, A | 128 | 0.4186124880 | 100320.411680 |

Both B lifetimes beat both A controls: +0.28889% decode and +0.67167% total
throughput. All eight timed outputs and ordered routes match. Within-capacity
warmup comparisons cover 184 complete F32 rows with zero maximum difference.
These are counting-workload results; do not add them arithmetically to the
adaptive result on a different prompt.

The selected cache uses 134 active slots / 135 physical planes and
1,333,739,520 raw bytes. Rounded banks add 56,623,104 bytes versus 128 slots.
The priced device peak is 1,782 MiB under the unchanged 1,792 MiB aggregate cap;
single-buffer and CPU caps remain 512 MiB. The retained snapshot envelope
excludes 135 or more slots under these policies, not under every possible PS5
configuration. Case 6480 was a returned startup-policy refusal, not a physical
allocation failure; later 6760 and 6780 actually completed.

## Application integration

The production integration checks retain the native information-only VideoOut,
ordinary arithmetic smoke, exactly two external API requests, complete F32
vocabulary fingerprints, all Expert route records, positive ownership and
normal OS close. Counting remains selectable; the adaptive profile uses a
separate truthful prompt and performance schema v7 with actual mixed widths.
No expected future output IDs are passed to the draft controller.

Case 6840 returned an explicit first-API snapshot owner error. Its API context
had been recreated after the snapshot budget was bound to the smoke context.
The title normally closed and the exact prior production/settings were
restored. `tools/relink_adaptive_monitor_context.py` moves this binding after
the actual API context recreation, preserving all allocation and completion
checks. The original failed case is not relabeled a success.

Case 7080 passed the corrected **normal counting application**: all 46 complete
F32 row fingerprints match the closed 128-slot reference, ordered Expert routes
match, both actual native frames are legible, all owners retire, and normal
close plus exact restoration complete. Case 7280 then passed the **adaptive
diagnostic application**: 26 complete rows observed, all greedy outputs exact,
eight same-width F32 comparisons with zero error, and three complete active
state fingerprints exact across 109 F32 tensor sections. Diagnostic replay
timing is not a normal-mode speed result.

The normal adaptive application in 7320 returned **before GPU initialization,
model loading or generation POSTs**, at 1,112 free kernel pages versus the
selected 1,154-page operational policy. It normally closed and restored the
exact prior production. This is **execution unavailable under the current
startup policy**, not physical impossibility or an absent implementation. Its
normal 26-row reproduction has not passed and is not represented as complete.
All measured no-gain proposals are nevertheless tested, terminal dispositions;
this separate unavailable adoption gate must not put them back in an untested
queue.

Case 7420 installed the already qualified 134-slot **counting** configuration,
including the existing causal width-two final-prefix path. Production SELF is
`80c28a95e993458c54b5fbf73fe59accde17dd8302dd49a9aeecf367e617739c`.
Adaptive selection and diagnostic replays are both off. Native whole
SHA256/identity/EOF readback covers the canonical SELF, all five settings,
the exact previous `75c7aabc...` and older rollbacks. The final fresh idle
observation confirms no native title, gateway or loaded model. Placement
itself starts no title or GPU work. The permissions helper was first passed an
unsupported `verify` mode; its exact source rejects that argument before any
log or control action. The separate supported `finalize` call and complete
readback succeeded without repeating placement.

Reopening the normal adaptive gate requires a material measured startup/resource
improvement that satisfies its native guards, followed by the same-SELF normal
26-row fingerprints, complete routes, positive retirement, visual review and
ordinary close. No unchanged refused model lifetime will be repeated. The
overall native-validation-success flag remains false for this explicit reason;
all nine concrete proposal dispositions are classified.

Completed frame preservation recovered 1,016 pages in 7180 and another 1,016
in 7300, while preserving the original files. Further old-frame verification,
54 closed route reports (20,845,994 bytes) and 120 closed helper images
(13,280,000 bytes) produced no material recovery. These finite attempts are
also closed, not queued again. No file was deleted and no VM floor was lowered.

## Concrete implementation map

* `native/app/causal_wide_engine.h`, `adaptive_draft_depth.h`,
  `model_free_span.h` and `wide_draft_control.h`: causal history-only proposals,
  depths 1/2/4, exact committed prefix and rejected-suffix restoration.
* `snapshot_layout_witness.h`, `snapshot_replacement_budget.h` and
  `snapshot_replacement_runtime.h`: actual metadata-only F32 layout witnessing,
  completed single-buffer replacement credit and the unchanged 19-page charge
  for each new allocation. The pinned upstream `llama-context.cpp` ON_DEVICE
  writer releases its previous changed-size buffer before allocating the next.
* `tools/additional_cache_variant.py` and `plan_additional_cache_build.py`:
  inspect actual include dependencies, overlay the selected geometry and rebuild
  fourteen affected application/ModelIO objects. Driver objects are reused.
* `tools/build_adaptive_monitor.py`, `build_cache134_adaptive_monitor.py`,
  `seal_cache134_adaptive_provenance.py` and
  **`relink_adaptive_monitor_context.py`**: generate the passive application,
  reuse twelve completed non-entry/non-engine geometry objects, then correct
  context ownership before packaging. The seal records the actual selected
  entry/engine separately from historical cache-comparison metadata and verifies
  all fourteen geometry objects and seven ModelIO providers in the link. The
  relink correction is mandatory for
  the earlier generated application; do not deploy the intermediate SELF.
* `tools/cache134_result.py`, `adaptive_monitor_result.py` and
  `observe_cache134_monitor_plan.py`: separately scoped capacity/prompt adapters
  retain the original owner, Direct pool, source, frame and exact-once API
  checks. Counting compares all 46 rows against the closed 128-slot diagnostic;
  adaptive normal mode must reproduce all 26 rows from its own diagnostic.
* `hidden_expert_prefetch.h`, `tools/hidden_expert_source.py` and
  `build_hidden_expert_callback.py`: the tested, unselected layer-23 predictor
  joins its existing persistent worker before authoritative demand and retains
  actual bank leases and source accounting.
* `native/app/portable_kernel_fixture.cpp` and
  `tools/review_portable_kernel_fixture.py`: the completed portable GPU
  alternatives and explicit numerical/timing rejection conditions.

Driver source remains `akiba-tokyo-jp/PS5-Vulkan-Inference` revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`;
the selected native archive SHA256 is
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. Exact source, linked object,
archive, application relink and SELF provenance remain in the private receipts.

## Reopening rules

Measured losers require no further work in this finite plan. Reopen one only
for a concrete different implementation or material new evidence. An absent
larger benchmark does not turn a completed no-gain comparison into untested
work. Long-context, stochastic quality and sustained-service qualification are
separate future scopes and are not claimed by this finite greedy validation.
