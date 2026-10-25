# BF16-preserving system optimization research

> Historical research baseline. Demand refill and CPU/standalone-GPU/fused-GEMV palette screens subsequently completed and failed their adoption gates. Use the [current plan index](plan-index.md) for those decisions and the remaining unimplemented proposals; the original estimates and priorities below describe the research date.

Research date: 2026-10-25. Application baseline: `3e4276a86f52129300654d7bc2f845545c60e903`.
This report adds offline analysis and implementation proposals. It changes no
inference source, model, driver, production executable or console state, and
runs no build or CI. The [analysis data](bf16-system-optimization-research-20261025.json)
separates completed measurements from calculations and unimplemented designs.

The recommended objective is **less critical-path time and fewer physical
bytes per accepted output token**. Queue throughput, predicted-route hit rate,
compression ratio and GPU kernel speed are intermediate metrics.

## Precision and current baseline

Preserve original BF16 weights, original F32 tensors, F32 KV, all selected
experts and all required PLE/hyper-connection state. Lossless storage encoding
is eligible only if it reconstructs the original bits before arithmetic.
Do not cast original F32 routers to BF16. Do not change the target router,
discard selected experts, or use FP16 arithmetic as an assumed BF16 substitute.

The qualified production SELF remains
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
Its deployment check measured 0.391093 / 0.398430 tok/s, with TTFT
50.130 / 49.280 seconds. These are short, thinking-disabled requests, not a
representative reasoning benchmark. See [production evidence](production-installation-20261025.md).
The pinned driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, with persistent shader/pipeline caches disabled.

The same-SELF owned-bank qualification supplies the detailed timing baseline:

| Quantity | Completed evidence / derived value |
| --- | ---: |
| Decode transitions, two runs | 42 |
| Time inside `llama_process` | 104.8514 s |
| Source wait within those processes | 96.9198 s, **92.435%** |
| Physical reads per transition | **4.475 GB**, decimal |
| Physical bytes / source wait | **1.939 GB/s** effective ratio |
| Payload delivered directly to owned coherent banks | About **97%** |
| Expert cache | 512 MiB; **53 global slots**, not 53 per layer |
| One complete original expert | 9,830,400 bytes across gate/up/down |
| Runtime text layers / top-k | 48 / 10 |

The effective ratio includes scheduling and waiting; it is not an isolated SSD
bandwidth measurement. Worker, consumer and source counters overlap and must
not be added indiscriminately. The model's logical size is 359.247 GB; a complete
text-expert pack alone is 241.592 GB. Most active weights cannot remain resident.
Sources: [owned-bank evidence](native-owned-bank-success-20261025.json) and
[SSD screen](ssd-io-validation-results-20261025.md).

Even eliminating *all* non-source process time would improve this process-time
model by only 1.082x. That residual includes more than GPU arithmetic. Thus
shader-only tuning is a secondary task. Merely hiding unchanged compute under
unchanged I/O has the same small ideal ceiling; a larger gain needs less traffic,
better effective I/O service, or more accepted tokens per verification cycle.

## Candidate comparison and implementation targets

All upstream llama.cpp paths below refer to
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`. Changes should be maintained in this
repository's overlays, never in immutable qualified build products.

| Candidate | Difference from current engine | BF16-preserving approach / source target | Potential and difficulty |
| --- | --- | --- | --- |
| Completion-driven demand reads | Production waits for paired reads before moving to the next pair. The experimental CPU queue can refill a completed lease immediately. | Integrate `CompletionSourceIO::submit/take/release` from `native/app/completion_source_io.h` with `MappedSourceReader::try_owned_bank_reads` in `mapped_source.h`, `paired_source_io.h`, and `0002-llama-moe-cache.patch`. | Low-to-medium implementation burden. Two CPU cohorts showed about 4% delivery improvement, with losing rounds; no generation gain is qualified. |
| Compute already-ready experts while loading other actual selections | `src/llama-moe-cache.cpp::impl::copy` synchronizes selected IDs, fills all bank roles, then publishes the slot map. The current FFN cannot consume a completed subset early. | Split actual selections into ready and pending whole experts; evaluate ready experts/shared expert through `src/models/qwen4exp.cpp::graph::build_layer_ffn`, retain indexed output positions, then combine in the original reduction order. | High integration burden. Avoids prediction waste, but overlap-only gain is limited by current compute fraction. Extra graph splits can cost more than they save. |
| One-layer, two-slot forecast | Current route-ahead evidence concerns previous-token IDs, not current hidden-state router reuse. | Add a bounded observation tap around `qwen4exp.cpp::build_hc_mix/build_hc_combine` and `build_layer_ffn`; reuse original F32 router tensors; reserve at most two existing slots through `expert_policy.h` and cache overlay. | Medium-to-high. Unmeasured accuracy, useful lead time and contention; first qualify prediction without issuing speculative reads. |
| Fixed-tile lossless encoding with GPU reconstruction | The tested LZ4 exponent path reconstructs on CPU and loses end-to-end. No fixed-palette GPU decoder exists. | Independent codec beside `bf16_lossless.h`; bounded encoded-source handling in `mapped_source.h`; a new integer reconstruction shader through `0004-ggml-vulkan.patch`. Restore into an owned BF16 destination before the existing kernel. | High, but directly targets physical byte volume. New sample size calculation predicts about 26.5% fewer stored/read bytes; speed remains unmeasured. |
| Fused reconstruction and indexed BF16 matvec | Current vector shader reads a complete expanded BF16 bank. | After standalone reconstruction qualifies, consider `mul_mat_vec.comp::iter_aligned_nonquant`, its load helper and `ggml_vk_mul_mat_id` dispatch. Reconstruct exact bits on load and retain the existing F32 arithmetic/reduction. | Very high. Could avoid expanded-weight writes and increase useful cache density. Requires a distinct encoded layout, strides, dispatch and precision proof. CUDA code is not portable as-is. |
| Exact speculative verification, width 2 then 4 | Generated tokens are currently processed one at a time; prefill width four is already enabled. No recurrent rollback snapshots are reserved. | `llama_engine.cpp::next/process_batch`, `streaming_context_params`; upstream `llama-memory-recurrent.cpp::seq_rm/state_read/state_write`, hybrid and KV modules, and Qwen4Exp PLE state. Start with prompt lookup rather than additional draft weights. | Very high. Actual accepted-path route analysis finds duplicate-use reduction, but rejected drafts and state recovery can erase it. |
| Memory lifetime and cache-capacity planning | GPU/CPU share physical capacity. The CPU peak leaves 83,820,544 bytes in its 512 MiB budget; this is not necessarily available Direct capacity. | Audit lifetimes in `model_cpu_budget.h`, cache allocation in `0002`, `owned_mapped_backend.cpp`, and graph/buffer allocation in `0003`/`0004`; then replay larger cache capacities with the real layer-floor policy. | Enabling work, not a promised gain. Release only completed, owned transient allocations. Do not lower reserves or count the same UMA capacity twice. |
| Zero-copy expert-major layout | The tested packed path added copies; the current banks are role-major with padded strides. | Explore aligned gate/up/down extents whose reads land directly in the three owned banks. Keep source identity, 512 MiB part bounds and fallback decisions in `mapped_source.h`; cache overlay supplies complete destination leases. | High. Potentially improves locality/call amortization, but PS5 vectored Direct I/O is unqualified and a full second pack does not fit. First use a bounded sidecar. |

### What the new primary implementations actually show

**LES, OpenBMB, revision `a64932ec615e1463158129feaf2f0752d0c07a2e`.**
[The implementation note](https://github.com/OpenBMB/llama.cpp-omni/blob/a64932ec615e1463158129feaf2f0752d0c07a2e/docs/les/lookahead-expert-scheduling.md)
separates scheduling, direct weight delivery, mixed-precision quantization and
speculative sampling. Only the precision-preserving scheduling/delivery ideas
are relevant here. Its mobile rates are not a BF16 Flash-Next control.
[qwen35moe.cpp lines 455–465](https://github.com/OpenBMB/llama.cpp-omni/blob/a64932ec615e1463158129feaf2f0752d0c07a2e/src/models/qwen35moe.cpp#L455)
applies the next router to a current normalized hidden tensor.
[llama-moe-slot.cpp::read_expert_directv](https://github.com/OpenBMB/llama.cpp-omni/blob/a64932ec615e1463158129feaf2f0752d0c07a2e/src/llama-moe-slot.cpp#L1437)
uses packed source spans and scatter I/O into owned slots. This differs from
our losing gather-and-copy prototype. Its automatic retry and diagnostic
skip-read modes are not eligible for this application.

For Flash-Next, the actual FFN input follows hyper-connection mixing at
[qwen4exp.cpp lines 482–491](https://github.com/ggml-org/llama.cpp/blob/0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/models/qwen4exp.cpp#L482).
An arbitrary earlier attention vector is only a prediction input, never an
exact next-layer router input. Current original routers are already F32;
another roughly 245 MiB router copy is unnecessary. The two-slot design must
measure useful *nonresident* predictions, wasted bytes, displacement, ready
time and foreground-read delay. Idle demand capacity, complete three-role
publication and actual-router authority remain mandatory.

**ZipServ, ASPLOS 2026, revision `6f8a209bfe46b0905f90d61b0796e352147ff041`.**
The [paper](https://www.cse.ust.hk/~weiwa/papers/zipserv-asplos26.pdf) describes
fixed bitmap decoding fused with matrix multiplication.
[L_Kernel.cuh::LoadBF16FragWithTripleBitmap_SingleRow](https://github.com/HPMLL/ZipServ_ASPLOS26/blob/6f8a209bfe46b0905f90d61b0796e352147ff041/csrc/L_Kernel.cuh#L136)
reconstructs common values and retains exact uncommon values. Its CUDA/PTX,
Tensor Core layout and published speedups do not transfer to PS5. The inspected
repository is Apache-2.0. A Vulkan design should use supported integer loads,
bit operations and the existing BF16-to-F32 path; the qualified device reports
32-wide subgroups and no native BF16 arithmetic feature.

Other relevant references are [ZipMoE v2](https://arxiv.org/html/2601.21198v2),
which separates CPU exponent decoding from GPU reconstruction, and
[Unweight's technical report](https://research.cloudflare.com/papers/unweight-2026.pdf),
which evaluates different decoding/fusion paths rather than assuming one is
best. ZipMoE's Academic Non-Commercial implementation was not copied. Unweight
is intermediate Hopper work, not a completed PS5 implementation.
[ISCA 2026's tile-level ANS work](https://arxiv.org/abs/2606.15789) reinforces
matching compression to compute tiles; its multi-batch serving results and
cross-format compression headline are not BF16 batch-one predictions.

**SpecFit, 2026-10-11, revision `4973b3cdc48e5c016bc6c5ed18639d3163e8b2f5`.**
The [paper](https://arxiv.org/html/2610.15417v1) optimizes accepted tokens per
verification cost, including the union of required experts. Its measurements
use a previously collected route atlas outside the timed request; a deployed
predictor remains separate work. Therefore this is a cost-model reference,
not evidence of a ready PS5 predictor. Its
[selection adapter](https://github.com/Chlience/SpecFit/blob/4973b3cdc48e5c016bc6c5ed18639d3163e8b2f5/src/specfit/runtime/eagle3_selection.py)
exposes `ExplicitRawIdTreeSelector::decide` and `TreeSelectionDecision::materialize`.
Our first design should use a short linear verification block, not its tree
search or additional learned drafter.

**Slipstream, revision `3de2e03534012a2875d5e8995557171887404c6a`.**
[Qwen4ExpTarget.cpp](https://github.com/npanj/slipstream/blob/3de2e03534012a2875d5e8995557171887404c6a/models/qwen4exp/Qwen4ExpTarget.cpp#L1333)
provides concrete expert-major ready/missing waves and
[`addVerify`](https://github.com/npanj/slipstream/blob/3de2e03534012a2875d5e8995557171887404c6a/models/qwen4exp/Qwen4ExpTarget.cpp#L1811)
is a reference for Qwen-specific state handling. It uses Metal and different
quantized/modified model variants; its tokens/s are not transferable. Its
unbounded waits are also unsuitable here.

## New offline findings

### Fixed-palette format size, not a decoder benchmark

Rechecked the original SHA256 of the retained 27 BF16 matrices: gate/up/down,
layers 0/23/47, experts 0/257/511. Only saved host samples were read; the full
model was neither converted nor scanned again.

A proposed independent format stores each value's eight sign/mantissa bits,
three palette/escape bits, and the exact eight-bit exponent for every escape.
It includes a 64-byte header/palette, one 32-bit exception prefix per 64 values
plus a terminal prefix, and final 16 KiB read alignment. All uncommon exponents,
including exceptional bit patterns, must be retained exactly.

Using each matrix's seven most common exponent values, the median escape rate
is 2.946%. **Calculated aligned size is 73.5–74.0% of original, median 73.5%.**
This is format-size arithmetic, not an implemented encoder, a round-trip test,
a full-model compression ratio or a PS5 speed result. It motivates a simpler
parallel decoder with independent tiles, rather than more LZ4 CPU workers.

At the previous raw sample median of 4.4035 ms, a 26.5% ideal read-time reduction
leaves approximately **1.17 ms per matrix** for all additional restoration,
dispatch and ownership work before the gain disappears. Actual read savings
must be measured; size and time need not scale linearly. A small standalone GPU
restoration probe should precede fused matvec work. Both extra encoded storage
and BF16 output storage must fit simultaneously with the existing reserves.

### Actual expert reuse across generated tokens

Validated the three completed route/result pairs from the selected owned-bank
case, then reproduced their actual cache hit/miss/upload counters with the
existing integer-only replay. Analyzed the 21 decode transitions per external
run, excluding the final EOG decision. The two runs use the same short prompt
and have identical routes; they are not independent workload coverage.

| Ideal verification width | Mean distinct experts per layer | Separate uncached steps | Duplicate activations eliminated |
| --- | ---: | ---: | ---: |
| 2 tokens | 17.329 | 20 | **13.354%** |
| 4 tokens | 26.988 | 40 | **32.529%** |

These are overlapping sliding windows of already-known accepted paths. They
assume unchanged routes under rebatched arithmetic and do not include rejected
draft branches, existing cache savings, checkpoint memory, extra compute or
sampling cost. They are not measured traffic reductions. They nevertheless
show that width four can reuse more expert work than simply forecasting the
next token's selected IDs.

Use `accepted_tokens / (draft_time + target_verify_time + recovery_time)` as
the decision metric. A wide block is worthwhile only when it outperforms the
same number of ordinary accepted tokens. Prompt lookup has no extra neural
weights, but still needs target verification and complete state rollback.
The current context has zero recurrent snapshots. A host snapshot needs at
least 118,038,528 recurrent/PLE bytes before KV/logits, exceeding 83,820,544
bytes of CPU-budget slack. The upstream recurrent constructor also scales
its rows with `1 + n_rs_seq`; simply enabling snapshots is not memory-safe.
First price a complete device checkpoint/commit plan. Do not assume removing
KV positions restores recurrent or PLE state. Original MTP is a later option
after its own weights, state and extra I/O have been admitted.

## Whole-system priorities and exclusions

1. **Use existing evidence before more console experiments.** Preserve the
   fastest artifact and negative results. Establish a compact set of Japanese
   dialogue, code/copying, reasoning and low-repetition prompts within context
   256, separating TTFT, decode and per-token tail latency. Current two short
   runs are insufficient to rank workload-dependent prediction/drafting.
2. **Retest continuous demand refill under production request geometry.**
   Preserve two read leases, owned direct destinations, coalescing and split
   fallbacks. This is the smallest incremental candidate. Do not add worker
   count and change observer cost at the same time. A repeatable gain below
   5% may be useful; the earlier fixture's 5% gate was not a universal rule.
3. **Screen fixed-palette restoration and shadow router forecasts.** The
   former attacks bytes; the latter measures whether useful overlap exists.
   These are independent research tracks, each with separate bounded memory
   accounting. No complete model repack is needed to reject a slow candidate.
4. **Qualify ready-expert scheduling or speculative reads only after their
   prerequisites pass.** Preserve one synchronized GPU producer. A read buffer
   is reusable only after CPU completion and any consuming GPU completion.
   Slot state must distinguish filling, ready and GPU-pinned. Output reduction
   retains original expert order even if physical execution order changes.
5. **Solve state-memory admission before exact speculative verification.**
   Start at width two; compare width four only after rollback and numerical
   continuation pass. Reuse/cache expansion is not free on this UMA platform.
6. **Tune kernels and repeated-prefix TTFT afterward.** Existing Flash
   Attention, GPU recurrent state, BF16 indexed-vector dispatch and prefill
   four are already enabled. Prefill eight currently exceeds worst-case slot
   capacity. Prefix reuse addresses repeated-prompt latency, not steady decode.

Do not repeat the losing CPU LZ4/packed-copy designs unchanged. Do not replace
Maya LFU4096 merely with another cache policy: prior exact replay found no
winning alternative, and its optimistic 53-slot oracle saved only 2.39% on
that trace. This does not bound a larger cache, compression, batching or overlap.
Do not remove verification/monitoring, which the owner explicitly retains.

Do not import CUDA Tensor Core/PTX, Metal command APIs, Linux `io_uring` or
GPU-direct storage as if supported by the current native runtime. A PS5
vectored Direct-read path needs independent ABI, alignment and completion
qualification; qualified `pread` remains the fallback. CPU expert arithmetic
does not avoid SSD reads or create a separate RAM pool here. Persistent cache
enablement and driver changes are separate qualification work.

Also exclude [S2-MoE's reuse-biased target routing](https://arxiv.org/html/2608.15018v2)
from the exact-preservation path: its paper explicitly describes a controlled
target-routing approximation. BF16 storage alone would not make that change
equivalent to the original model. [ReaDy](https://arxiv.org/abs/2610.20503v2)
requires trained drafting machinery and is evaluated on a different model and
B200; it is a longer-term idea, not an immediately portable optimization.

## Speed sensitivity and acceptance criteria

For source fraction `s = 0.92435` and reduction `r` in source wait, the simple
process model is `speedup = 1 / (1 - s*r)`. The illustrative token rates below
scale the 0.39444 tok/s qualification baseline. They assume unchanged other
work and no new overhead, so they are **conditional calculations, not forecasts**.

| Source-wait reduction | Process speedup | Illustrative decode |
| --- | ---: | ---: |
| 10% | 1.102x | 0.435 tok/s |
| 20% | 1.227x | 0.484 tok/s |
| 25% | 1.301x | 0.513 tok/s |
| 30% | 1.384x | 0.546 tok/s |
| 50% | 1.859x | 0.733 tok/s |

The palette size estimate therefore suggests investigating roughly the
0.5 tok/s region **only if** its traffic savings become wait savings and decode
cost is low enough. It supplies no evidence for multiple tokens/s. Candidate
percentages share the same bottleneck and must not simply be multiplied.

For each candidate, first verify original bytes or numerical operation/state
equivalence, then compare complete delivery, then a bounded same-model PS5
sequence. A rejected or ambiguous candidate never replaces production.

| Mechanism | Decisive measurements and controls |
| --- | --- |
| Continuous reads | Same physical bytes/calls and banks; paired alternating order; elapsed delivery, p95 read/lease wait, queue idle gaps, zero premature reuse. Then external decode/TTFT. |
| Ready-expert execution | No missing/duplicate contributions; original reduction order; all selected IDs equal; graph submission overhead and real overlap; positive per-slot GPU completion. |
| Router forecast | Shadow precision on *missing* experts, readiness at demand, wasted bytes/evictions, prediction graph cost; then foreground latency with 0/1/2 reserved slots. Disable when added cost exceeds saved wait. |
| Lossless GPU format | All 65,536 BF16 bit patterns, exact escapes and malformed bounds; original sample SHA256; 2560x640 and 640x2560 operations; include encoded read, restoration, extra allocations and retirement in time. |
| Speculative verification | Forced rejection at every position; full KV/recurrent/PLE/logit continuation; exact greedy tokens/routes versus ordinary decoding; accepted tokens, unique experts, bytes/token, wasted work and recovery. Sampling later needs distribution validation, not just same seed. |
| Capacity/lifetime changes | Correct layer-floor cache replay and complete peak-live allocation ledger before any allocation; measured benefit per added byte; preserve all startup/kernel/Flexible floors. |

Use sequential controls on the existing console; no second Flash-Next machine
is required. Keep repetitions finite, observe drift and uncertainty, and use
fresh cases rather than replaying consumed run bindings. No expanded context,
new concurrent model, force reset or unrestricted endurance run is proposed.
