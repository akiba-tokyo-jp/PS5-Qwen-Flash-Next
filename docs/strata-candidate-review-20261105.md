# Strata source review, 2026-11-05

Subsequent user-authorized work is recorded in
[Strata validation](strata-validation-20261105.md). ST1/ST2 are ineligible under
the selected activation policy. Both distinct ST3 cache-wait refinements pass
native numerical/route equivalence. Timing is interrupted by console transport
loss while collecting an already submitted ordinary close; console restoration
is unconfirmed. No new speedup is adopted. The source-only review below remains
the historical basis for that work.

The latest `Niko1221/Strata` main observed for this review is
[`ffa80d73133ea5c548aefe57889a16e8085a938f`](https://github.com/Niko1221/Strata/tree/ffa80d73133ea5c548aefe57889a16e8085a938f),
committed 2026-11-02 22:37:27 UTC (2026-11-03 JST). GitHub's branch API and the
separate local checkout agree. The previous inspected reference was
`7ddc17a38fe7f31637e895ecfba58c2cd43d65ec`: the new main is 1,887 commits ahead,
with 1,628 changed paths across the repository. The review enumerated that
delta and inspected the relevant expert-source, cache, input-conversion,
prefill, execution and test paths. It does not claim a line-by-line audit of
all application, packaging and unrelated-model changes.

**Three mechanisms merit a PS5 adaptation study. None is a measured PS5 gain
or a production adoption.** The selected R1+P1 program remains
`c5afc565fdbb4adcf830eae645a32589825331dfa7783a1b9ae2985e7fb5c2ed`.
This review makes no console connection, launches no model and changes no
runtime, driver, source pack, allocator limit or deployment. The completed
eight-candidate campaign remains closed; these are new source-review candidates.

## Candidates

| ID | Mechanism to adapt | Intended endpoint | Required eligibility check |
| --- | --- | --- | --- |
| ST1 | Reuse an existing Q8_1 activation image between projections/branches | Decode and prefill, when repeated conversions actually occur | Both consumers must already select the same quantizer, layout and original activation; its storage must survive both consumers |
| ST2 | Fuse SwiGLU with the next matrix operation's input conversion | Decode where the Q8_1 path is selected; prefill for supported layouts | Match the actual Vulkan consumer, original rounding, strides, padding and live ranges before bypassing an intermediate |
| ST3 | Sparse transfer-completion records and deduplicated release waits | Prefill first; a decode extension requires a separate transfer-scope proof | One ordered transfer stream, bounded ring ownership and a completion covering every consumer; never remove a true dependency |

These priorities are engineering judgments from source inspection. ST1 and ST2
first require confirmation that the selected PS5 provider takes the eligible
conversion path often enough. Existing request counters do not measure repeated
Q8_1 conversions. ST3's upstream implementation is a streamed **prefill** path;
its presence supplies no direct evidence of ordinary decode acceleration.

### ST1: share input conversion rather than recomputing it

The latest
[`NativeSharedWeights::x_q8_1`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/include/strata/kernels/shared_expert.hpp#L35)
and [single-token shared-expert implementation](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/src/kernels/cuda/shared_expert.cu#L348)
allow a caller-owned activation image to serve gate/up without another
conversion. This single-token wiring changed since the previous reference
(commit `1f8ca8de`). The multi-token verifier also contains
`STRATA_VERIFY_QDEDUP`; its applicability is restricted when the shared expert
uses its own concurrent stream. Some of that mechanism predates this delta.

The pinned llama.cpp Vulkan base already caches the last converted input by
pipeline and tensor in `ggml_vk_mul_mat_id_q_f16` and
`ggml_vk_mul_mat_vec_id_q_f16`. Merely enabling that existing cache is not a
new optimization. The possible gap is the same activation used across
intervening projections or graph splits, after the single scratch image has
been replaced. This remains a candidate, not proof that the selected compiled
provider currently repeats those conversions.

Two distinct implementation scopes would be useful: preserve a verified input
image across the routed/shared-expert branches, then separately evaluate having
the original producer write that same image alongside its existing output.
Either must bind input contents, buffer generation, offset, shape, quantizer
and completion epoch. A reused address alone cannot identify valid contents.
Any additional storage must be priced before allocation; the existing shared
scratch cannot be overwritten while a consumer owns it.

This changes no weight format. F32-to-Q8_1 is reused only where the incumbent
path already performs that exact activation conversion. If a consumer uses
F32/F16 input instead, converting it to Q8_1 would be a different numerical
experiment and is outside ST1.

### ST2: produce the consumed activation layout directly

New commit `dd97421d` adds
[`mmq::swiglu_quant`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/src/prefill/moe_mmq.cu#L151):
SwiGLU and the down projection's existing Q8_1 packing are computed in one
kernel without writing and rereading the intermediate F32 H tensor. Its
[parity fixture](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/tests/cuda/prefill_swiglu_quant_test.cpp)
covers split/interleaved gate/up, Q2_0/IQ4_NL/Q8_0 down types, 1/37/4,113 rows
and zero/extreme input rows. That fixture was inspected, not executed here.

The new prefill implementation is compiled only for CUDA's experimental SM60
build; `swiglu_quant_ok` explicitly returns false on HIP. It is **not an AMD
or Vulkan implementation ready to enable**. The existing single-token
`native_swiglu_quantize_q8_1_kernel` is a related, older reference, not a new
change discovered in this delta.

The PS5 integration target is the boundary between `GGML_OP_GLU` and the
conversion used by the following `MUL_MAT_ID`. The pinned Vulkan code has
separate GLU and input-quantization dispatches, but Q8_1 eligibility is
conditional on device support, shape and the selected matrix kernel. The
selected PS5 path must be established before implementing a Q8_1 fusion.

The first scope should be ordinary single-token decode with the incumbent
Q2_K/Q2_0 weights. The second should cover multi-token prefill and its padding.
Both require the incumbent Vulkan activation arithmetic, rounding and block
layout, full output/state checks and pre-allocation lifetime protection.
CUDA intrinsics, warp width and the CUDA padding layout cannot be copied
unchanged. The older rejected Gate/Up matrix-fusion experiments do not test
this narrower activation-to-conversion boundary and must not be replayed.

### ST3: reduce completion bookkeeping while preserving transfer ownership

New commits `a11f8b0a` and `f217b23b` add and correct
[`copy_event_due`, `copy_event_entry` and `copy_wait_dedupe_ok`](https://github.com/Niko1221/Strata/blob/ffa80d73133ea5c548aefe57889a16e8085a938f/include/strata/prefill/copy_events.hpp).
An in-order copy stream can record completion for a group and let a consumer
wait on a later record that covers its copy. Repeated slot-release waits can
also be omitted when the earlier wait covers the same current-walk release.

The correction is material: the ring must be longer than a compute group,
and the reused slots must both have been released in the current walk.
The original first-round rule can observe a stale event. Upstream's existing
`src/prefill/copy_events_test.cpp` was compiled and executed **once on the PC**;
all checks pass, including the simulation that detects that original race.
This is a host bookkeeping result, not Vulkan or PS5 completion qualification.

Two separate scopes are appropriate: sparse copied-event records, then release
wait deduplication. A PS5 implementation needs positively completed source
leases, explicit transfer/consumer ordering and exact scratch-slot generations.
It cannot infer that every recorded backend wait is redundant. Existing
checkpoint copy batching and prior queue-batching winners are already adopted;
ST3 concerns transfer-ring completion records, not repeating those experiments.

## Existing evidence and exclusions

The completed P1 comparison case65400 records whole-model-process/source-wait
seconds of 5.782/2.974 cold, 1.633/0.444 retained and 1.194/0.151 exact-prefix.
Those source intervals include prefill and final work; they are not decode-only
percentages. They support investigating transfer/execution overhead without
predicting a tok/s gain for any candidate. They contain no GPU timestamp split
or repeated-conversion count. Legacy package-policy labels are not substituted
for the actual request's routing/shape observations.

The following are not additional current-priority candidates:

* `STRATA_PREFILL_ROUTED_STREAM` skips unrouted entries in a large prompt's
  stream-all walk. The selected PS5 cache already forms fills from selected
  misses; no equivalent all-expert walk is established for the fixed workload.
  Upstream also disables routed streaming beside sparse copied events or wait
  deduplication. These switches cannot simply be enabled together.
* `replace_resident_staged` reuses a live stage buffer for a host-RAM tier
  promotion. PS5 already delivers read misses directly to their assigned GPU
  cache banks. No second RAM-tier reread saving is established; a complete
  host expert arena does not fit the current memory budget.
* Larger verification windows, graph eviction, DFlash2 and speculative-policy
  changes are not ordinary decode improvements by themselves. Current S1
  results remain slower than ordinary generation. No failed initializer,
  source-cache window or completed model case is reopened by this review.
* New NVIDIA-specific MMVQ tables, PTX load instructions and 4-bit expert
  nibble slots are not PS5 RDNA2 implementations. New GDN long-prompt/tensor-core
  paths have different shape, scratch and numerical requirements from the
  current single-token path.
* UMA sizing and batched-DMA reference headers are unchanged across this
  source interval. State-copy batching, checkpoint metadata reuse and F32
  convolution/SiLU/QK-normalization fusion are already integrated in the
  selected application's lineage.

## Qualification endpoint

Before a model timing run, an adaptation must demonstrate eligible executed
operations, retained original bytes/precision where claimed, correct buffer
ownership, full numerical/route checks and positive ordinary retirement.
The performance endpoint remains `(generated_tokens-1)*1000/decode_ms`,
separately cold/retained/exact-prefix. TTFT-only changes stay separately named.
Existing evidence is reused; no unchanged rejected benchmark is required.

PS5 driver provenance remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, with persistent shader/pipeline caches disabled. A later
adaptation must use that repository's integration contract and preserve the
current no-reboot/no-initializer constraint. No PS5 implementation or timing
run was performed during this source review. The companion JSON records exact
source hashes, the host-test result and the conditional candidate scopes.
