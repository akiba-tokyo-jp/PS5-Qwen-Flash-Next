# Ready-wave and graph feasibility follow-up

The remaining implementation/validation plan is incomplete. This follow-up uses
saved native traces, exact source inspection, deterministic address fixtures and
manual native compilation. Cases 2640/2643/2644/2646 performed **zero console
operations, model evaluations, GPU submissions or CI runs**. They do not change
the installed fastest executable or establish a speed improvement.

## Ready-expert ownership and backing

`native/app/ready_expert_wave.h::ReadyExpertWave` is a fixed top-ten metadata
prototype. It binds original layer, request, plan, completed GPU epoch and actual
backing-owner identities. A whole expert becomes ready after all three roles
return exact bytes with unchanged identity. One source-lease producer and one
GPU producer are bound explicitly. Unknown/failed reads, stale completions,
GPU completion or final reduction quarantine the owner and retain its state.
No method allocates, reads, submits, retries or frees actual backing.

Different logical slots are insufficient for overlap when they share a GPU
buffer. The prototype compares actual owner IDs across groups. It refuses CPU
writes to any backing pinned by a GPU wave and refuses a wave intersecting a
pending write. Roles within one group may share a backing; overlap requires
independent backing between groups. It does not require six independent BOs.

`split_padded_bank.h::split_padded_slot` describes 26 + 27 useful global slots,
with 27 physical planes per group. The total three-role tensor extent remains
533,495,808 bytes, 53 useful slots and 54 physical planes per role. Byte-storage
roots are required. Current owned-bank and dispatch predicates deliberately
reject these unqualified roots. Native allocation rounding, kernel cost and
additional owner metadata remain unmeasured; equal raw bytes are not physical
memory admission.

Host 2640 passed 64 metadata refusals, ten failed/unknown retention cases,
separate-thread and shared/aliased-backing controls, original contribution order,
resident/missing/repeated selections and pair completion. Actual GGML metadata
covered 120 role/residue views and 3,180 bounded envelopes. Native SDK compilation
measured 432 bytes for the class and 80 bytes for its snapshot. The original
selected indices determine the final left-to-right reduction; grouping sums by
bank would change F32 results.

The actual `MappedSource` frontend remains thread-bound. This metadata test does
not authorize calling its methods from a worker. Existing source memory guards
remain on the original frontend; a worker performs only its existing native read.
Final native teardown still requires the actual joined worker and positive GPU
completion. A metadata completion epoch alone does not free an in-flight owner.

## Preserve existing read packets before introducing overlap

`tools/screen_ready_expert_opportunity.py` replays the completed 2240 routes at
the unchanged 53-slot aged-LFU policy and matches all native aggregate counters.
It reconstructs the cache loop's exact contiguous-run/next-two packet choices,
then resolves original tensor offsets through the sealed 512 MiB physical parts.
Actual C++ `padded_source_envelope` and `source_schedule_parallel` match the
independent Python calculation for 12,471 distinct physical queries.

The narrow hypothesis preloads all other original packets, then uses one
existing **serial** pair last: synchronous read zero returns, its producer-side
consumer computes the ready opposite group while the existing worker reads one.
This preserves packet payloads/call counts by construction and adds no predicted
experts. It requires new multi-owner eligibility and an exact partial graph.
It does not replace existing parallel pairs with a single serial reader.

| Saved request | Decode layer steps | Existing direct parallel pairs | Existing direct serial pairs | Steps with a serial-pair opportunity |
| --- | ---: | ---: | ---: | ---: |
| Arithmetic control | 48 | 674 | 7 | 5 (10.42%) |
| First external | 1056 | 14134 | 246 | 194 (18.37%) |
| Repeated external | 1056 | 13845 | 222 | 183 (17.33%) |

This is an opportunity count, not simultaneous execution, latency saved or tok/s.
Only the last single role read overlaps in this narrow variant. Packet reordering
can change descriptor/LRU and guard costs; include them in a native fixture.
Cross-group pairs need a strict multi-owner lease rather than a relaxed current
single-bank guard. Splitting every original pair by bank can lose existing I/O
parallelism or coalescing and is not the selected first experiment.

The source references are the maintained
[`impl::copy` overlay](../patches/native-model-io/0002-llama-moe-cache.patch),
[`MappedSource::try_owned_bank_reads`](../native/app/mapped_source.h),
[`source_schedule_parallel`](../native/app/source_read_schedule.h) and
[`PairedSourceIO::pipeline`](../native/app/paired_source_io.h). GPU graph integration
still targets upstream `qwen4exp.cpp::graph::build_layer_ffn` and the existing
`llama-graph.cpp::build_moe_ffn` selected-index reduction. Partial indexed widths
one through nine require separate qualification; the qualified top-ten guard is
unchanged.

## Scope the small CPU metadata candidate

The measured width-four clear/add/set loop is 4446.675290 ns per batch. Applying
that largest measured cost to **all 30** process calls gives only 133400.2587 ns,
or 0.1334 ms per saved request. That is 0.000127% / 0.000129% of their 105.366 /
103.534 s process intervals. This estimates this specific microbenchmark's
opportunity, not all backend metadata. Its initialized-batch prototype remains
available, but a new full-model comparison solely for this loop is not justified
on the current workload. The native Python/Torch dispatch chain is absent.

## Radiance analogies against the actual model

Host 2644 checked the original tensor metadata, not assumed model-family layouts:

| Target | Actual original tensors | Consequence |
| --- | --- | --- |
| GDN fixed parameters | 36 F32 `ssm_a` and 36 F32 `ssm_dt`, 13,824 bytes total | An additional repeated BF16/F32 parameter conversion is absent. Dynamic alpha + bias, softplus and gate multiplication remain necessary |
| Routers | 48 F32 `[2560,512]`, 251,658,240 bytes | Reuse these actual owners for a later shadow observation; introduce no duplicate router corpus |
| Shared-input QKV and gate | 36 pairs of BF16 `[2560,10240]` and `[2560,6144]` | 80 MiB original weights per pair remain to be read. Width-one logical shared activation is 10 KiB. A dual-output kernel primarily targets dispatch/reuse, not removal of those weight bytes |
| PLE convolution | **One** BF16 `[4,10240]`, 81,920 bytes | Four recurring tap gathers and lossless casts exist; do not extrapolate this cost to 48 PLE layers or remove the required conversion |

The exact upstream reference is
[`qwen4exp.cpp` at `0a1ef309`](https://github.com/ggml-org/llama.cpp/blob/0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/models/qwen4exp.cpp).
`build_norm_gated` uses sigmoid, not SiLU. The original F32 recurrent states,
normalization, bias, softplus, expert clamp and reduction semantics remain part
of any later specialization. The saved non-source process remainders are
8.212 / 7.723 s, but include CPU work, guards, transfers and completion. They are
not isolated shader times or evidence that any particular fusion saves that time.

## A bounded PLE graph copy-elision candidate

`native/app/ple_slice_graph.h::build_experimental_PLE_tap` and the separate
[`experimental overlay`](../patches/experimental-ple/0001-bounded-tap-views.patch)
prepare four isolated compile-time modes. The maintained production overlays
and original engine tree are unchanged:

| Mode | Change per four-tap process | Precision and placement requirement |
| --- | --- | --- |
| 0 | Original shifted-input copy, coefficient gather and cast | Control |
| 1 | Cast the strided BF16 coefficient column directly to contiguous F32; omit its preceding gather | Keep BF16 -> F32 conversion; qualify strided COPY |
| 2 | Multiply from the original strided F32 history view; omit shifted-input copy | Qualify Vulkan placement; the current CPU MUL requires contiguous src0 |
| 3 | Both changes; eight fewer CONT nodes per process | Both requirements, unchanged cast and arithmetic order |

No new weight pack, permanent converted parameter store, predictor or shader is
introduced. Eligibility is restricted to original F32 history, BF16 `[4,10240]`
kernel, history nine, dilation three, one sequence and widths one through four.
Width three is included for the remainder of ordinary four-token prefill.

Host 2646 passed 64 actual GGML tap graphs, 64 input refusal controls and
1,638,400 exact F32 value comparisons using deterministic finite BF16/F32 data
and an independent F64 product reference. This is a tensor-address interpreter,
**not** a backend execution. All four actual native model unity variants compiled
with the existing PS5 recipe and SDK. No full application was linked/published
for these modes, and no speed or model-quality result exists.

The existing Vulkan sources carry all input strides in
[`ggml_vk_mul` / `ggml_vk_cpy`](https://github.com/ggml-org/llama.cpp/blob/0a1ef309cdbb9f2024f58a38fb4c42352c5db569/ggml/src/ggml-vulkan/ggml-vulkan.cpp)
and index them in
[`generic_binary_head.glsl`](https://github.com/ggml-org/llama.cpp/blob/0a1ef309cdbb9f2024f58a38fb4c42352c5db569/ggml/src/ggml-vulkan/vulkan-shaders/generic_binary_head.glsl).
Binary MUL does not accept BF16; retaining the cast is mandatory. Source support
and successful compilation do not establish native descriptor/placement behavior.

Next qualify one small finite GPU fixture at widths 1/2/3/4, all four taps,
history/descriptor boundaries, finite non-BF16-exact F32 inputs, canaries and
the existing numerical limits. Require exact original operation order and
returned fences, and explicitly verify every candidate operation's Vulkan
placement. Compare the same complete convolution in alternating modes, including
graph construction/submission/fences and peak-live allocation. A candidate that
fails placement or total-time gates does not proceed to full-model integration.
Only a fixture winner may enter the existing A/B then B/A model/adoption contract.

## Allocation attribution and current console gate

The linked diagnostic ELF's five PT_LOAD entries total 29,632,527 memory bytes;
only 1,482,305 bytes are zero fill. The largest 5,142,706-byte read-only symbol
belongs to Mesa's `nir_opt_algebraic` compiler table, not an unused app snapshot.
The link already uses `--gc-sections`. The external shader file and GGUF payload
metadata use Direct I/O. None of these source observations identifies the
native free-page decline or proves safely recoverable kernel memory. Do not
remove the compiler table, required verification, logging or admission checks.

Known ownership remains: one source scratch lease, shared role-bank backing,
separately tracked CPU/Direct/device domains, context-owned checkpoint tensors,
and positively completed consumers before release. A logical device-budget
reservation is not a physically allocated buffer to reclaim. `vector::clear`
does not prove returned heap/kernel headroom. A full physical peak-live audit
and the 380 native metadata observations remain outstanding.

Passive regular-gate case 2641 returned a known refusal at 6,577 free pages
against 10,142. It launched no title and allocated/read no payload. Earlier
owner-authorized reduced-headroom cases 2601/2616 were normally closed and the
exact fastest/settings restored. Do not replay them or repeatedly publish titles
under unchanged insufficient conditions. The next title requires fresh unchanged
memory/owner gates and a new justified finite case. No further reserve reduction,
reset, cache pressure or uncertain resource release is part of this follow-up.
