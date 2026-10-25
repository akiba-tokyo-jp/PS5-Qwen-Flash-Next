# PS5LM transfer assessment for original-precision Flash-Next

The strongest explanation for PS5LM's high generation rates is GPU residency of
small quantized weights. That configuration differs fundamentally from this
application's 359,246,956,672-byte logical BF16/F32 model and bounded SSD expert
streaming. There is no measured PS5LM Flash-Next control. The same console can
instead compare this application's candidates sequentially. The owner authorized
implementation and physical validation after the initial research-only request;
CI remains disabled.

## Source revisions and evidence scope

The inspected public snapshots are:

* [PS5LM ecbcb8c](https://github.com/cobanov/PS5LM/tree/ecbcb8cc54faf33b7987011b4708d5e0b9ee5f52), including its llama.cpp gitlink `04f7226a2c12c7f382c545a6db5a034266aa53cb`.
* [PS5LM-Plus 6729b4a](https://github.com/abhi245y/PS5LM-Plus/tree/6729b4acbaf65e23b2e8bc8708b2acba524a7aa8), including its llama.cpp gitlink `620d2225cc436ab0b001e3200e590e3b286ef9ab`.
* [PS5_Vulkan f410e67](https://github.com/mihawk-99/PS5_Vulkan/tree/f410e67a0241b3e8edcdbcd2a9b285dfc4a412ed) and [PS5_Mesa 1ba9874](https://github.com/mihawk-99/PS5_Mesa/tree/1ba9874f478657ccf6da72ce55f0260164cc0bd0), research references only.
* This application's upstream [llama.cpp 0a1ef30](https://github.com/ggml-org/llama.cpp/tree/0a1ef309cdbb9f2024f58a38fb4c42352c5db569), plus the committed and experimental overlays described below.

The application continues to link the owner's `PS5-Vulkan-Inference` revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle` profile, native archive
SHA256 `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader and pipeline caches remain disabled. The external driver
snapshots above are not a replacement driver or a relink authorization.

## Published throughput: what can actually be compared

Both projects' console notes identify PS5 Slim CFI-2015, firmware 13.60. These
are author-reported measurements, not independently reproduced results here.

| Primary report | Model and weight format | Cache / configured context | Reported generation rate |
| --- | --- | --- | --- |
| PS5LM README | Qwen3.5 0.8B Q4_K_M, 0.5 GB | Not specified in that row | 207 tok/s |
| PS5LM README | Qwen3.5 9B Q4_K_M, 5.3 GB | Not specified in that row | 55 tok/s |
| PS5LM README | Qwen3.8 27B UD-Q2_K_XL, 9.2 GB | 64k configured | About 20 tok/s |
| Plus README | Qwen3.8 27B UD-Q2_K_XL, 9.2 GiB | q4_0 / 32k | 20.3 tok/s; 19.7 for a 7,775-token answer |
| Plus README | Qwen3.8 27B UD-IQ2_XXS, 6.8 GiB | q8_0 / 64k | 20.7 tok/s |
| Plus README | Gemma 4 E4B QAT q4_0, 4.8 GiB, USB source | q4_0 / 64k | 61 tok/s |
| Plus README | Llama 3.2 3B Instruct Q4_K_M, 1.9 GiB, USB source | q8_0 / 64k | 124 tok/s |

Sources: [PS5LM README model table](https://github.com/cobanov/PS5LM/blob/ecbcb8cc54faf33b7987011b4708d5e0b9ee5f52/README.md#readme),
[Plus README generation table](https://github.com/abhi245y/PS5LM-Plus/blob/6729b4acbaf65e23b2e8bc8708b2acba524a7aa8/README.md#readme).
Configured context is capacity; those rows do not establish that the entire
context was occupied. USB describes model loading, not continual decode reads.
The screenshots and short tables do not supply every prompt, thread setting,
clock, repeat or raw timing sample needed for a controlled comparison.

The more explicit [native console experiment](https://github.com/abhi245y/PS5LM-Plus/blob/6729b4acbaf65e23b2e8bc8708b2acba524a7aa8/docs/CONSOLE.md#the-native-app)
used Qwen3.8-27B UD-IQ2_XXS, `-ngl 999 -lm none -c 4096 -ub 64`: load 82 s,
**prefill 35–50 tok/s**, decode 21 on a short prompt and 9 after a 371-token
web prompt. These are distinct from the README's later configurations. The
[Tom's Hardware article](https://www.tomshardware.com/video-games/playstation/jailbroken-ps5s-can-now-run-local-ai-models-at-over-100-tokens-per-second-fork-of-ps5lm-goes-native-and-accesses-gpu-and-more-ram)
is secondary coverage, not another benchmark or evidence of 100 tok/s Flash-Next.

This application's baseline uses original BF16 weights, F32 KV, all required
experts/PLE, context 256, prefill four, greedy generation, thinking disabled,
30 prompt tokens and two 22-token answers. Its completed split512 decode rates
were 0.344610 / 0.351360 tok/s; TTFT 57.555 / 56.589 s. Decode and TTFT must
remain separate. None of the external rows supports a speed ratio against it.

## Transfer matrix

Effects below are hypotheses unless a completed local measurement is stated.

| Technology | Difference from current implementation | Transferability | Expected effect | Difficulty |
| --- | --- | --- | --- | --- |
| Native title + static RADV/ACO + ggml-vulkan | Already implemented with one AGC owner and exact relink receipts | Already present | No new gain from repeating the port | Low |
| Unified APU heap / title memory plan | Current app already accounts for the shared Direct pool, CPU heap, display and kernel reserves | Reuse the accounting principle; do not copy advertised capacity | More usable cache only if independently measured | High qualification burden |
| Resident quantized weights | Current BF16 model exceeds the entire title pool many times | Outside current precision scope | Major residency benefit for models that fit; no measured Flash-Next factor | High / model change |
| BF16 indexed-vector dispatch | Upstream predicate excludes BF16; current implementation adds narrow decode-only layout admission | Repeated full comparisons passed; selected in the exact final artifact/profile | Final matched mean +1.36188%; earlier complete comparisons agree in direction; attribution limited by routing changes | Medium |
| Existing fused Flash Attention | Already enabled | Already present | No demonstrated extra decode gain at context 256 | Low |
| Quantized KV | Current KV is F32 | Technically available upstream, outside current precision scope | Saves KV capacity; limited leverage on expert SSD traffic | Medium |
| Complete recurrent prefix checkpoint | No spare capacity for the measured minimum checkpoint | Does not fit the present admitted budget | Could improve repeated-prompt TTFT, not per-token decode | High |
| MoE cache + known-miss overlap + coalesced reads | Maya LFU4096, 53 slots, paired selected reads already present | Already present; retain all experts | Existing qualified source-schedule bundle gained 16.68% against its earlier control | Medium |
| Four smaller concurrent read windows | Two 4 MiB windows currently; tested four 2 MiB within the same 8 MiB | Screened, not adopted | CPU median +1.03%, paired interval includes zero | Medium |
| Eliminate a staging GPU copy | Actual uploads already use host-visible/coherent mapping; staging bytes zero | Inapplicable to this measured path | Zero removable staging bytes | Low |
| Owned mapped-bank I/O | Current source window is copied into an owned Vulkan mapping | Mapping/Direct read, 360 padded GPU graphs and complete same-SELF full comparison passed; selected profile | Mean decode +12.1829%, same outputs/routes/physical bytes; preserves coalesced reads through scatter fallback | High |
| Non-temporal stores for mapped copy | Current coherent branch uses ordinary memcpy | Complete full-model comparison rejected; remain disabled | Mean -3.55552% despite faster warm copy microbenchmark | Medium |
| Driver submit thread / spin-wait knobs | Current pinned cumulative completion/lifetime model | Separate future driver qualification only | PS5LM reports no generation gain on its 0.8B/9B tests | High risk relative to evidence |
| Direct frame persistence | Ordinary BMP writes consumed kernel pages in isolated tests | Implemented and exercised in full sequences | Preserves evidence headroom; not claimed as decode acceleration | Medium |

## GPU arithmetic and allocation details

`scripts/build-app.sh` in both public snapshots links `libvulkan_radeon.ps5.a`
with the PS5_Vulkan native startup/link recipe. `ps5/app/main.cpp` sets
`radv_enable_unified_heap_on_apu` before backend initialization. The driver is
Mesa RADV, ACO shader compilation and a PS5 winsys backed by Direct memory and
AGC submission. It is not a proprietary tensor-core inference engine.

At the inspected Mesa revision,
[`radv_physical_device.c`](https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/amd/vulkan/radv_physical_device.c#L218)
gates cooperative matrices at GFX11 or later and native bfloat16 at GFX11 or
later with additional precision restrictions. PS5's reported GFX10 hardware
does not satisfy those gates. `KHR_shader_integer_dot_product` exposure alone
is not proof of accelerated dot-product properties. FP16 and subgroup paths
are useful; compile-time shader availability alone is not device support.
Keep runtime capability checks. Do not force cooperative-matrix/BF16 flags or
substitute PS5 Pro properties for this console's actual device.

BF16 storage does not imply native BF16 arithmetic. The ggml vector shaders
load BF16 through conversion helpers and accumulate according to their F32
variant. Matrix dispatch can prepare a reduced-precision RHS. The candidate's
F32-input vector path consequently changes intermediate rounding and sometimes
expert routing; it is not a precision reduction, nor proof of identical logits.
Both dyadic timed fixtures and separate non-BF16-exact F32 references are required.

GPU placement is decided by backend support and model/context parameters;
unsupported operations may fall back to CPU. The application overlays bound
CPU row and buffer reads instead of faulting arbitrary model mappings. Preserve
those fallbacks, counters and full model semantics. Never interpret `-ngl 999`
as a capacity bypass or permission to omit experts.

## Memory and KV interpretation

The [Plus console notes](https://github.com/abhi245y/PS5LM-Plus/blob/6729b4acbaf65e23b2e8bc8708b2acba524a7aa8/docs/CONSOLE.md#the-native-app)
attribute the historical 11.44 GiB heap to a native title and the unified-heap
option. Removing unused AMM/page-table reservations later raised reported Direct
capacity to 12.00 GiB, with 11.58 GiB free before a model versus 11.01 with the
dashboard previously. Flexible and Direct allocations divide one fixed title
budget; increasing flexible memory takes capacity from Direct. These are that
application's observations, not guaranteed available space for this engine.

The same notes leave substantial retained memory after unload unexplained and
restart the title to switch models. This engine must retain its positive
source/GPU completion, owned lifetimes and ordinary OS close; it must not copy
automatic restart as recovery from unknown completion. Its 32 MiB native
VideoOut also avoids the other application's approximately 0.35 GiB GL dashboard.

`ps5/app/model_plan.cpp::plan_model` reserves CPU/compute/recurrent checkpoint
space, chooses cache precision/context, enables FA and limits server checkpoint
count to one and RAM prompt cache to zero. These admission ideas transfer;
their numerical constants and statements about quantized-cache quality do not.
This app's complete checkpoint needs at least 118,038,528 bytes versus
83,820,544 bytes of measured budget slack; no checkpoint is integrated.

Upstream `src/llama-kv-cache.cpp` allocates K/V tensors using `type_k/type_v`,
zeros padding and reuses/clears sequence cells. Hybrid recurrent state is a
separate requirement. KV quantization uses supported block layouts and GPU
copy/attention kernels; it does not quantize recurrent state automatically.
The original-precision implementation retains F32 KV and all required state.

GGUF Q2_K/Q4_K and IQ formats pack values with block scales/minima/codebooks;
effective storage includes overhead and mixed tensors. Their Vulkan matvec
shaders dequantize as they multiply rather than expanding the complete model
to resident F32. This is not equivalent to an all-integer tensor-core path.
Even idealized uniform 4-bit or 2-bit compression of this model's BF16 payload
would not establish that the whole model fits a roughly 12 GiB title pool.
No quantized conversion or numerical-quality claim is included here.

## Concrete source targets

All upstream file references below mean llama.cpp `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`.
Local overlays are the integration authority; do not edit cached upstream or
immutable qualified build outputs in place.

| Candidate / invariant | Exact source and function | Required change or check |
| --- | --- | --- |
| P1 dispatch | `patches/native-model-io/0004-ggml-vulkan.patch`; upstream `ggml/src/ggml-vulkan/ggml-vulkan.cpp::ggml_vk_use_mul_mat_vec_id`, `ggml_vk_mul_mat_id` | Admit only the proven BF16 decode layout; count actual vector/matrix calls; keep prefill/default dispatch unchanged. |
| P1 scope | `native/app/llama_engine.cpp::set_bf16_indexed_vector_scope`; `native/app/indexed_vector.h::bf16_indexed_vector_layout` | One generated token, top ten, exact contiguous dimensions/strides; disable scope after decode and on every failure boundary. |
| P1 numerics | `native/app/moe_admission.cpp::admit_indexed_vectors`; `indexed_vector_admission.h`; `tools/indexed_vector_result.py::validate_fixture` | 2560x640 and 640x2560, one/ten F32 input vectors, repeated/boundary expert IDs, independent F64 reference, unrounded F32 extra checks. |
| P1 lower-level tuning | upstream `ggml/src/ggml-vulkan/vulkan-shaders/mul_mat_vec.comp`, `mul_mat_vec_base.glsl`, `mul_mat_vec_iface.glsl`; pipeline specialization in `ggml-vulkan.cpp` | Only after useful end-to-end admission: inspect subgroup width, rows/columns per workgroup and tails; change one specialization, repeat actual-shape readback and full A/B. No speculative precision changes. |
| P2 source scheduling | `native/app/queued_source_io.h`; source reader callbacks exposed by `mapped_source_bridge.h` | Keep identical selected bytes, file-region qualification and total 8 MiB; reject overlap or worse latency rather than increasing outstanding work blindly. |
| P3 cache layout | `patches/native-model-io/0002-llama-moe-cache.patch`; `src/llama-moe-cache.cpp::impl` allocation lambda, layer bank/view construction, `copy_experts`, miss upload loop | Padded plane strides, per-layer source residue, complete tensor/allocation bounds and scatter fallback. Existing consecutive `n*expert_size` uploads are not valid across padded slots. |
| P3 owned mapping | `0004-ggml-vulkan.patch`; `ggml_backend_vk_buffer_set_tensor`, `ggml_backend_vk_set_tensor_async`; buffer context owns `dev_buffer` | Export only a narrow owned lease for the actual buffer; prove HOST_VISIBLE/COHERENT, alignment, extent and generation. `buffer_get_base` returns a synthetic address, not mapped authority. |
| P3 copy / Direct read | `0003-ggml-vulkan-buffers.patch`; upstream `ggml_vk_buffer_write_2d`, `ggml_vk_create_buffer_device` | The measured branch is coherent memcpy. First screen a small real mapping; Direct I/O compatibility and GPU coherence are independent gates. Keep original fallback and counters. |
| P3 split/EOF | Existing split source reader and `mapped_source_bridge.h` callbacks | Model-wide screen found 432 aligned envelopes crossing parts. Preserve qualified final EOF count and requested destination capacity; never pad/rewrite model parts or retry unknown I/O. |
| P3 actual bank lease | `native/app/owned_mapped_backend.cpp::ggml_app_vk_probe_owned_bank`; `padded_cache.cpp::qwen_app_try_owned_bank_reads` | Retain the real shared Vulkan allocation while synchronous file reads target bounded aligned slot envelopes; require actual memory flags and descriptor alignment. |
| P3 source execution | `native/app/mapped_source.h::source_bank_residue`, `try_owned_bank_reads`; `mapped_source.cpp::qwen_app_read_owned_bank` | Resolve immutable original file positions; choose split/EOF/coalesced fallback before I/O, otherwise reuse qualified selected parallel/serial schedules and quarantine failed/unknown reads. |
| P3 padded numerics | `native/app/padded_bank_layout.cpp::admit_padded_bank_layout`; `padded_bank_route.cpp::qwen_app_padded_index_layout`; `tools/padded_bank_result.py::validate_layout` | Actual four-layout/30-residue/360-graph physical gate passed with max absolute error 1.71713e-9; full-model speed remains independent. |
| KV / recurrent prefix | `src/llama-kv-cache.cpp` constructor, `clear`, sequence operations; recurrent/hybrid state serializer | Reuse complete state only if all components fit and exact continuation logits pass; partial KV copies are invalid for hybrid state. |
| Measurement | `native/app/bounded_demo.cpp`, `native_display.cpp`, `tools/indexed_vector_result.py` | Separate prefill, TTFT, 21 post-first-token decode intervals, source wait, upload branch, cache hits, physical bytes and lifecycle. |

The owned-bank screen fits three 54-slot padded planes of 3,293,184 bytes in
533,495,808 bytes, below the unchanged 512 MiB cache cap; active slots remain 53.
It covers all 144 trunk expert tensors and 73,728 experts. This arithmetic
screen is not mapped-I/O, descriptor, GPU or full-model performance validation.
See [owned-bank design](owned-bank-io-design-20261025.md).

## Bounds, priority and validation

One completed decode sample recorded source wait as 84.12% of process time,
with every logical upload using mapped/coherent memory and zero staging bytes.
Treat these as observed accumulated timings with overlap, not an exact causal
partition. Under a simplified unchanged-I/O Amdahl model, halving all remaining
15.88% gives 1.086x (about 0.38 tok/s from 0.35); removing it entirely gives
1.189x (about 0.42). Halving the source-wait term would give 1.726x (about
0.60). These are conditional illustrations, not performance promises. Actual
copy elimination can change cache reuse, routing, coalescing and kernel pressure.

Priority remains: completed measurements; narrow indexed-vector comparison;
same-budget source-window screen; small owned-mapping I/O/copy screen; full
cache integration only if eligible; kernel specialization only if its remaining
cost justifies it. FA is already enabled, complete prefix state does not fit,
and staging elimination has no applicable bytes. Driver waiting/thread patches
are not substitutes for source streaming: the PS5LM [patch notes](https://github.com/cobanov/PS5LM/blob/ecbcb8cc54faf33b7987011b4708d5e0b9ee5f52/patches/mesa/README.md)
report no generation benefit for the tested knobs. Their retirement patch and
our existing completion/epoch guards pursue the same lifetime requirement;
do not combine alternative allocators or free paths without separate proof.

Each eligible candidate needs exact-byte/overflow/ownership host checks, a
manual native build/import audit and SELF roundtrip, then a fresh bounded
physical case. Small GPU fixtures require full CPU references, actual path
counters and positive completion/retirement. Whole-model comparison keeps
prompt, output cap, context, prefill, precision, slots and budgets fixed, records
cold/warm separately, and checks exact answer/token IDs plus routing differences.
Short deterministic answers do not establish broad quality or sustained service.
Require both actual frames, complete model/source/GPU release, ordinary close,
exact original restoration, fresh original numerical readmission, original
shutdown and final idle/full executable readback. Preserve all refusals and
unknown cases. A build, fixture or single answer never completes that plan.

Physical candidate outcomes and adoption status are maintained in
[the results log](gpu-optimization-results-20261025.md). No external PS5LM
benchmark is substituted for those local gates.
