# Width-two native qualification

All four additional adoption gates are complete, and the exact normal-mode
SELF is installed with its previous production preserved as rollback. Source
revision is `5ee168ff6b6c6ee5f3ecf59affcd9380709851dc`.

This report follows the [declared adoption conditions](speculative-adoption-criteria-20261028.md).
It separates identical-width arithmetic and state correctness, greedy behavior,
actual causal speed, and conditional application adoption. A full-vocabulary
maximum logit difference is not used as a universal quality threshold.

## Unchanged platform

All experiments use the original BF16/F32 model, F32 activations/accumulation
and KV, every Expert and PLE, context 256 and prefill four. The llama.cpp source
is pinned to `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`; model revision remains
`de4b8e4d43b917e7706784d8bb445c9af86a3540`. The source model is not quantized.

The owner driver is PS5-Vulkan-Inference
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, with
linked archive SHA256
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches stay disabled. No driver code, OS reserve
counters, CPU/Direct/Flexible/device caps, firmware, or registration is changed.
No reboot, CI or concurrent native GPU title is used.

## Same-width reference: case 5720

From one captured original state, the native diagnostic executes the same two
causal tokens normally, repeats that reference, restores, and executes the
actual speculative acceptance path. Both complete 248,320-column rows match
the reference exactly in both comparisons: four full F32 comparisons, maximum
error **0**. All 109 active original F32 tensor sections, totaling
**120,434,688 bytes**, match bit for bit across the three states. Metadata,
tensor geometry and sequence positions also agree. Readback uses a 65,536-byte
window; unused allocation padding is excluded.

The draft is actually accepted, the bonus logits are pinned, and the committed
position is consistent with the complete active state. A separate deliberately
wrong draft restores all 23 ordinary F32 continuation rows exactly. Positive
model/source/device retirement, normal exact-owner OS close, full original
artifact/settings verification and fresh idle pass.

The width-one versus width-two maximum remains **1.992569923400879** on this
counting input. The largest row KL(reference || candidate) is approximately
**6.3063e-7**. At the tested position, the difference is reproduced by ordinary
width-two evaluation; it is not unique to speculative state handling. This
does not prove universal quality equivalence or exact arithmetic across widths.

## Eight-input behavior: case 5760

The eight [frozen inputs](../config/speculative-qualification-workloads.json)
are rendered and tokenized again by the original native implementation. Every
rendered byte and prompt token ID matches the frozen host metadata. There is
one original model load and **27** positively completed requests, with output
limited to 32 tokens. All generated token IDs, bytes, EOG/limit reasons and
applicable ending positions agree with their own ordinary controls.

There are **eight actual accepted batches**, including bonus emission. **One**
uses the unchanged causal controller. On seven inputs that have no causal
acceptance, a separately labeled diagnostic supplies a correct draft from the
already completed control to exercise the acceptance branch. These seven
diagnostics establish branch coverage only; they do not establish a useful
causal predictor or a speedup.

Four wrong drafts on four inputs are rejected at different committed positions.
All **100** full-vocabulary continuation rows in those requests match the
ordinary F32 controls exactly. Across all noncontrol requests, **441** complete
full-vocabulary rows are compared; all top-1 IDs match, all values are finite,
and every recorded comparison has the same committed history. The largest
row KL in this finite cohort is **0.003491431148495649**; this diagnostic is not
a general quality certificate. All 48 trunk layers and ten distinct selected
Experts per token/layer are present in the original route captures. Route
geometry is checked; bit-exact routing across different batch widths is not
assumed.

| Input | Generated tokens | Causal accepted batches | Diagnostic accepted batches | Forced rejection |
| --- | ---: | ---: | ---: | --- |
| Japanese arithmetic | 18 | 0 | 1 | No |
| Japanese summary | 19 | 0 | 1 | Position 1 |
| English explanation | 32, output limit | 0 | 1 | Position 2 |
| Stack/queue comparison | 29 | 0 | 1 | Position 3 |
| Integer sequence | 32, output limit | 0 | 1 | No |
| Python function | 17 | 0 | 1 | Position 4 |
| Structured JSON | 12 | 0 | 1 | No |
| Repeated context | 12 | 1 | 0 | No |

One host filesystem-GET collection timeout occurs after 17 completed request
boundaries. The original native application continues. Read-only collection
resumes against the same owner, with no added launch or inference request.
The complete terminal report, positive retirement, ordinary close, exact prior
production/settings restoration and fresh idle are subsequently verified.
The original failed ten-request C2 cohort remains failed and unchanged.

## Matched causal speed and adoption

The separately bound case 5800 uses 128 active cache slots / 129 planes and
actual six-demand reads, matching the installed engine optimizations. One
causal warmup precedes ordinary/candidate/candidate/ordinary. Each request
begins with an empty Expert cache in the same retained context. No OS file-page
coldness is claimed. The single actual attempt bound is explicit; no known
control draft is supplied. Every emitted token is also checked against the
already closed ordinary counting reference.

The actual warmup must capture the complete snapshot before its identical-size
resident capacity can be credited to later requests. Capture, draft selection,
verification, rejected work, restore, bonus handling, source reads and request
completion remain in the measured request time. All timed arms collect the
same full-row diagnostics. The numerical reference for these timing diagnostics
is the causal warmup, not a new width-one F32 equivalence claim.

All five requests finish with their original greedy outputs and positive
reset/retirement. Both timed causal requests actually accept one target batch
and emit its bonus. Both reverse pairs improve total time and decode throughput,
with separated observed ranges. No additional ABBA block is needed.

| Metric | Ordinary A1 / A2 | Causal B1 / B2 | Mean improvement |
| --- | --- | --- | --- |
| Total request time | 100.611784 / 100.618861 s | 99.983790 / 99.833237 s | 1.007075x throughput |
| Decode | 0.416123 / 0.416420 tokens/s | 0.421625 / 0.422560 tokens/s | 1.013984x, approximately +1.40% |

All model/source/device owners retire, followed by normal close, exact baseline
and five-setting restoration, native whole-artifact verification and fresh idle.
The causal width-two requests repeat all 23 warmup F32 rows exactly. Width-one
controls retain the separately recorded batching difference. Their per-token
Expert selections also differ at some positions; cross-width route equality is
not assumed. The saved causal route stream is the reference for the application
combination, after removing its reused prompt and any explicit diagnostic replay.

## Actual passive application combination

The combination preserves 128 slots, six-demand delivery and complete-prefix
reuse. Its first API request remains ordinary and saves the complete prefix.
Only after the second and final API request positively restores that prefix
does the generated engine transfer the same checkpoint owner to the causal
controller. The complete prefix snapshot is 119,881,728 bytes and the later
pre-verification speculative snapshot is 120,311,808 bytes. Both round to
121,634,816 bytes. The later active state after the two-token batch is
120,434,688 bytes; it is not the pre-verification capture size.
The pinned writer releases its old buffer before allocating a changed-size
replacement; this source boundary is audited. The actual allocator cap remains
independent. The replacement also retains the measured 19-page metadata
allowance above the 962-page operational floor. This is an exact final-consumer
handoff, not a general claim that incompatible saved prefixes can coexist.

One SELF provides an explicit diagnostic mode and normal mode. The diagnostic
mode checks the ordinary width-two reference/repeat and complete active state
inside the real accepted application path, and saves SHA256 fingerprints for
all 46 complete F32 rows in its two API requests. The normal mode omits those
extra reference executions and must reproduce all 46 row fingerprints. Both
modes retain full finite-vocabulary observations, greedy checks, source and
route accounting, passive native frames and normal ownership retirement. Legacy
validators stay unchanged; an explicitly selected observer installs isolated
combined-mode geometry and proof checks.

The actual diagnostic combination passes in **case 5940**: four complete
same-width F32 comparisons have maximum **0**, and all active state/metadata
matches bit for bit across reference/repeat/acceptance. Normal mode in **case
5980** uses the exact same SELF, omits the extra reference executions, and
matches **all 46 complete F32 row fingerprints**. Its ordered Expert streams
match the closed causal reference after removing the exact reused prompt.
Both native frames are inspected in each mode. The normal application metrics
are **0.418102 / 0.437587 decode tokens/s**, TTFT **48.293025 / 0.077678 s**,
and total time **100.905314 / 50.489103 s**, with 22 emitted tokens per request.
The controlled headless comparison is the speed evidence; these application
measurements establish the actual integrated behavior and displayed metrics.

The model/source/device owners retire positively. Device peak is
**1,811,939,328 bytes (1728 MiB)** against the unchanged 1792 MiB cap; CPU heap
peak is **469,827,584 bytes** against the unchanged 512 MiB cap. After normal
exact-owner OS close, the canonical normal-mode SELF, previous production and
all five settings pass native whole SHA256, stable identity and EOF checks.
Fresh idle is confirmed. Production SELF is
`75c7aabccc62a55408309d614d1db66c71d77b35cb342c16e05059d6eae975fa`
(17,597,111 bytes); exact `e2821af3...` and older rollbacks remain preserved.
The title is inactive, gateway stopped and model unloaded. No replay of the
consumed binding is granted by this installation.

The earlier **case 5880 remains failed**. Its pre-capture admission mistakenly
required the later post-batch active payload, 120,434,688 bytes. The request
returns explicitly after eight tokens, before a speculative capture starts;
the actual saved capture size in the already completed 5800 receipt is
120,311,808 bytes. Resources remain conservatively retained until normal OS
close, and the original production/settings are restored. The exact corrected
guard is tested in fresh 5940/5980 cases. The first three successful gates are
retained rather than repeated. Original failed source capsules and raw reports
remain private and unchanged.

Host preparation also stops rehashing unused ancestor ELFs at every runtime
stage. Complete source ancestry is still verified during the manual build.
Runtime binds the exact current package/SELF/image, every explicit linked
object/archive, generated source view and all controller/observer guards;
native whole-artifact checks remain. The observed host hash set falls from
2,148,772,838 to 440,485,986 bytes. This is a preparation improvement and is
not counted as inference acceleration.

## Concrete source boundaries

| Source | Purpose |
| --- | --- |
| `native/app/logit_difference.h::compare_logits` | Allocation-free full-vocabulary maximum/RMS/percentiles, centered errors, top-five margins and stable softmax KL; caller owns scratch |
| `native/app/speculative_batch_probe.cpp::StateWriter` | Hash only active original F32 KV/recurrent state using bounded readbacks and exact tensor/metadata geometry |
| `native/app/speculative_batch_probe.cpp::SpeculativeBatchProbe` | Observe ordinary reference/repeat/actual acceptance without altering the engine class layout |
| `tools/build_speculative_batch_probe.py::engine_source` | Instrument a generated engine copy around `process_batch_once`, checkpoint restore and the actual acceptance decision |
| `tools/build_speculative_behavior.py::LOOP` | Eight independent ordinary/causal comparisons, conditional diagnostic acceptance and four forced rejections; finite loops and positive retirement |
| `tools/build_speculative_speed.py::speed_loop` | Causal-only 128-slot ABBA, complete source accounting and positive resident-snapshot capacity credit; no oracle timing arm |
| `native/app/prefix_speculative_handoff.h` | Certify one completed original prefix and admit only its exact final restored consumer and same-capacity replacement |
| `tools/build_speculative_monitor.py` | Preserve the original passive app while combining final-prefix handoff, actual same-width/state observation and complete-row bit fingerprints in one SELF |
| `tools/speculative_monitor_result.py` / `tools/observe_speculative_monitor_plan.py` | Isolated combined-mode proof, original layout/pool/source checks and explicit replay-inclusive geometry; legacy validator files are unchanged |
| `tools/review_speculative_qualification.py` | Offline review of closed identity/retirement/restoration, all rows, route geometry and both speed orders; never launches or admits GPU work |

Only explicitly generated engine/entry objects are rebuilt. Original ggml,
driver, shader and model-source objects remain bound by the retained receipts.
The source production `LlamaEngine` layout and default-off speculative controls
are not silently changed by these diagnostic builders. Raw native reports,
runtime artifacts, endpoints, prompts/token captures and source capsules remain
outside Git. The machine-readable companion records sanitized evidence hashes.

These are finite greedy experiments. Longer contexts, stochastic sampling,
broader reasoning quality, width four and sustained service require distinct
qualification. The historical 16-family / 22-item ledger and its broader
unimplemented integrations remain separate from this follow-up.
