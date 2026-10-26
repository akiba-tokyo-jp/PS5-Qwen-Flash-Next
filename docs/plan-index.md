# PS5 Flash Next plan status

Status consolidated on 2026-10-26 against main
`6f067d056a6eaae9c0fc38138a0c8dd257a41528`. **Implementation and validation of
all proposed techniques are not complete.** Ready-expert execution, hidden-state
router forecasting, speculative verification and other proposals below remain
incomplete; several now have default-off host prototypes. Individual finite plans have completed within their recorded
scope; the latest delivery screens produced no new production winner.

Use this index for current dispositions. Dated plans and intermediate reports
retain their original measurements and refusals as historical evidence. Their
old pending statements do not create a second work queue. This index changes
neither execution authorization nor the admission and preservation requirements
in [AGENTS.md](../AGENTS.md).

## Current production baseline

The installed finite application is the qualified original-precision engine,
SELF `ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`
(28,017,271 bytes). Original MOSS remains preserved as rollback. The latest
completed restoration retained this Qwen executable and its settings; it did
not replace it with MOSS. See [production placement](production-installation-20261025.md),
the [selected profile](../config/qualified-performance.json) and
[final restoration](memory-plan-completion-20261026.md#completion-and-provenance).

| Setting | Qualified value |
| --- | --- |
| Model precision | Original BF16/F32, F32 KV, all experts and required PLE |
| Physical layout | 76 logical files, 711 physical parts, at most 512 MiB each |
| Cache and reads | 53 global active expert slots, 512 MiB cache, 8 MiB source window; qualified pairs use at most two reads |
| Token processing | Context 256; prefill up to four tokens; decode one token at a time |
| Driver | PS5-Vulkan-Inference `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle` |
| Linked driver archive | `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925` |
| Persistent caches | Shader and pipeline caches disabled |

The previous deployment check measured **0.391093 / 0.398430 tok/s** and TTFT
**50.130 / 49.280 s**, for two 30-token prompts with 22 generated tokens each.
These short, thinking-disabled results remain the latest production generation
measurements. They do not establish broader reasoning quality or sustained
service. Later matrix-delivery ratios are not tokens/s results.

The last completed session ended with no native owner, gateway, loaded model or
unknown completion. This is a recorded terminal state, not a fresh console
observation. Another launch requires fresh admission. CI and general execution
defaults remain disabled.

## Historical plan lifecycle

Completion of a screen means every candidate received a disposition and the
selected implementation and lifecycle gates finished. It does not mean every
proposed technique was implemented or adopted.

| Plan or investigation | Current disposition | Terminal evidence |
| --- | --- | --- |
| [Initial execution plan](execution-plan-20261022.md), including the [efficiency review](execution-efficiency-review-20261023.md) | Complete on 2026-10-24; preparation and first-generation milestones are historical | [Full-model generation](native-full-generation-success-20261024.md) |
| [Initial read/upload overlap](performance-20261024.md) and [file and range scheduling](source-schedule-performance-20261024.md) | Complete; bounded overlap and qualified schedule adopted | [Overlap result](performance-20261024.md), [source-schedule result](native-source-schedule-success-20261025.md) |
| [Eight-proposal performance plan](performance-plan-20261025.md) | Screening and selected implementations complete; later in-place splitting resolved the earlier duplicate-storage blocker | [Eight dispositions](performance-results-20261025.md), [complete split](native-split512-success-20261025.md) |
| [512 MiB replacement](split512-replacement-plan-20261025.md) | Complete, including original-byte verification and full-model comparison | [Split result](native-split512-success-20261025.md) |
| [GPU qualification plan](gpu-optimization-plan-20261025.md) | Complete; vector route and owned banks selected, other proposals rejected or deferred by applicability | [GPU results](gpu-optimization-results-20261025.md), [production placement](production-installation-20261025.md) |
| [SSD validation plan](ssd-io-validation-plan-20261025.md) | Initial delivery and capacity screens complete; no production candidate admitted | [SSD results](ssd-io-validation-results-20261025.md) |
| [BF16 system research](bf16-system-optimization-research-20261025.md) | Research complete; its broader implementation proposals are not all complete | [Remaining proposals below](#remaining-proposals-and-prerequisites) |
| [Initial BF16 validation](bf16-system-validation-20261025.md), [kernel-memory investigation](kernel-memory-cause-20261026.md), [palette follow-up](memory-palette-followup-20261026.md) | Historical partial checkpoints; the finite demand, memory-recovery and GPU screens subsequently completed | [Memory-plan completion](memory-plan-completion-20261026.md) |
| [Remaining proposal validation](remaining-validation-plan-20261026.md) | In progress; metadata, vector ABI and bank/source fixtures executed. Actual production-source screen remains inconclusive; other packages remain open | [Execution progress](remaining-validation-progress-20261026.md) |

The [Strata source review](strata-update-review-20261024.md),
[PS5-specific I/O research](ps5-source-io-workarounds-20261024.md) and
[PS5LM transfer assessment](ps5lm-transfer-assessment-20261025.md) preserve the
source comparisons behind these plans. Their upstream benchmarks are not
same-model PS5 BF16 speed measurements. The
[freeze investigation](freeze-forensics-20261024.md) retains failure evidence.

## Adopted techniques

These techniques belong to the qualified baseline or the maintained validation
workflow. Percentages below have different controls and must not be multiplied
or added to estimate a combined gain.

| Technique | Current disposition and measured scope | Evidence |
| --- | --- | --- |
| Strata-style UMA admission and Maya aged LFU4096 | Implemented; preserve actual selections and memory floors. No tested replacement cache policy saved payload on the captured demand trace | [Expert policy](expert-policy.md), [cache replay](performance-results-20261025.md#actual-route-comparison) |
| Known-demand overlap, file/range-aware reads and adjacent-expert coalescing | Adopted with qualified serial fallback. The source-schedule bundle measured +16.68% mean decode; that result also includes startup and shader-storage changes | [Source-schedule result](native-source-schedule-success-20261025.md) |
| Bounded prefill width four | Adopted after separate widths two/four qualification; mean TTFT fell 35.30% against width one. Decode remains single-token | [Prefill comparison](native-bounded-prefill-20261025.md) |
| Physical model parts up to 512 MiB | Adopted in place; full-model mean decode +1.50% versus the matched unsplit control. Small short-request result, not proof of a global optimum | [Layout qualification](native-split512-success-20261025.md) |
| Compact completed-route observer | Adopted; unchanged heap peak and zero memory-pressure events in its qualified sequence. No isolated speedup claimed | [Observer result](performance-results-20261025.md#compact-observer-and-complete-native-lifecycle) |
| BF16 indexed-vector decode | Adopted with narrow shape/layout eligibility and F32 activation/accumulation; final same-SELF mean decode gain 1.36188% | [GPU dispositions](gpu-optimization-plan-20261025.md#candidate-dispositions-after-sequential-qualification) |
| Owned mapped padded-bank reads | Adopted with coalesced/scatter/split/EOF fallback; mean decode +12.1829% in the matched same-SELF comparison. About 97% of payload delivered directly into banks | [Owned-bank comparison](gpu-optimization-results-20261025.md#final-same-self-full-model-comparison-selected) |
| Flash Attention and GPU recurrent state | Already present; not additional unimplemented GPU optimizations | [System baseline and priorities](bf16-system-optimization-research-20261025.md#whole-system-priorities-and-exclusions) |
| Native Direct frame writing | Adopted while retaining monitoring. Four matched frame writes lost 508 free pages per buffered sample versus four per Direct sample; not a decode benchmark | [Frame qualification](gpu-optimization-plan-20261025.md) |
| Preservation integrity after large readbacks | Applied to closed captured artifacts; two resident frames contributed about 15.875 MiB of recovered free-page headroom in the measured interval. Reusable bounded builder implemented and natively qualified | [Memory completion](memory-plan-completion-20261026.md), [builder](../tools/build_preservation_integrity.py) |

## Rejected and inconclusive variants

Retain these results and experimental sources. Do not repeat an unchanged losing
variant as unfinished work. A materially different mechanism needs its own
hypothesis and controls. Fixture ratios greater than 1.0x mean faster delivery;
they do not predict full-model decode by themselves.

Rejected means the listed implementation was measured or its stated configuration
failed a concrete prerequisite. Unimplemented means implementation and validation
work remains. Deferred means that work has not been completed and its next gate
has been identified. These dispositions are not interchangeable.

| Variant | Decision and scope | Evidence |
| --- | --- | --- |
| Unrestricted same-file parallel reads or independent opens | Rejected schedule: approximately 49 ms per cross-region pair versus 10 ms serial and 7 ms across separate files. Proprietary internal lock/cache cause remains unproven | [Contention investigation](source-contention-investigation-20261024.md) |
| 256 / 128 MiB parts instead of 512 MiB | Not adopted: representative parallel means 6.807 / 6.869 / 6.896 ms for 512 / 256 / 128 MiB across 576 exact-byte pairs; no material smaller-part benefit | [Size comparison](source-layout-size-comparison-20261025.md) |
| Alternative cache policies and previous-token route prediction | Tested cache alternatives saved no payload; previous-route predictions missed 57.01% / 68.91% of nonresident predictions at limits one / ten. This does not test hidden-state forecasts | [Eight-proposal results](performance-results-20261025.md) |
| Four 2 MiB reads instead of two 4 MiB reads | Inconclusive approximately 1.03% fixture difference; do not widen production concurrency | [GPU plan dispositions](gpu-optimization-plan-20261025.md) |
| Non-temporal mapped copies | Rejected after full-model mean decode regression of 3.55552%, despite a favorable warm copy microbenchmark | [Full-model comparison](gpu-optimization-results-20261025.md#complete-non-temporal-copy-comparison-rejected) |
| CPU lossless zlib, exponent LZ4 and overlapped LZ4 | Rejected tested paths: zlib failed the host delivery-cost screen; native LZ4 variants measured 0.777x / 0.780x / 0.883x, and overlapped reconstruction 0.918x | [Initial screen](performance-results-20261025.md), [SSD results](ssd-io-validation-results-20261025.md) |
| Packed reads with gather/output copies | Rejected CPU paths at 0.875x and 0.934x. A different layout landing directly into owned banks remains a separate proposal | [Packing scope](ssd-io-validation-results-20261025.md#continuous-reads-and-packing-scope) |
| Completion-driven known-demand refill | Prototype retained, not adopted. Two-worker screens 1.039x / 1.038x and production-thread-count screen 1.040344x failed their original median >1.05x and all-rounds-positive gate | [SSD results](ssd-io-validation-results-20261025.md), [finite-plan disposition](memory-plan-completion-20261026.md#completion-and-provenance) |
| CPU exact-palette reconstruction | Rejected at 0.488x complete matrix-delivery throughput; faster reads did not repay reconstruction | [CPU result](bf16-system-validation-20261025.md#implemented-and-measured) |
| Standalone GPU exact-palette reconstruction | Rejected at 0.561503x; raw timed control is read-only, with its copy correctness check outside that interval | [Standalone result](memory-palette-followup-20261026.md) |
| Fused exact-palette restoration and GEMV | Rejected at 0.980634x paired throughput, five of six rounds slower. Both arms include read, GEMV and fence. All exactness/completion checks passed | [Fused result](memory-plan-completion-20261026.md#completed-fused-gemv-comparison) |

The standalone and fused GPU ratios have different baseline work and cannot be
compared as equivalent speedups. Their losing screens did not trigger whole-model
conversion or integration. The original fixture adoption gate remains recorded;
it is not a universal 5% requirement for every future improvement.

## Remaining proposals and prerequisites

The owner now prioritizes [memory attribution before PLE](PLE-memory-first-plan-20261026.md).
Later closed-file controls reduced a measured retained-file component. An
independently linked small CPU title completed actual shader initialization:
registry/decoder change was zero pages and the complete interval lost 22 pages,
with no Vulkan/model code linked. Exact fastest restoration and post-close
observations passed at 9,079–9,080 free pages. The native-title wired component
must still be priced separately; no proprietary allocator or new speed result
is claimed. See the [aggregate evidence](CPU-shader-memory-controls-20261026.json).
The next distinct four-graph PLE smoke remains unimplemented; its provisional
8,425-page allowance retains fresh post-CPU/pool/operational guards. It does not
change the regular full-model gate or complete the remaining optimization plan.

These proposals have no qualified production speed result. They are a research
backlog, not unfinished steps of the completed finite memory plan. The pinned
upstream source targets refer to llama.cpp
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`; maintained changes belong in this
repository's overlays, not immutable qualified build products.

The [execution progress](remaining-validation-progress-20261026.md) records
native CPU metadata, original-byte vector-delivery and device-copy fixtures.
GPU-bank exactness passed, but the actual original-file layout comparison was
inconclusive at 1.040x source / 1.037x total, with only seven of eight rounds
faster. No production-layout migration or model speed gain follows. The 136 MiB
device-copy prerequisite also passed; complete-model continuation is a separate
qualification.

The [remaining-proposal validation plan](remaining-validation-plan-20261026.md)
defines the implementation targets, dependency order, bounded tests, stop/adoption
conditions and full-model/production gates for every row below. It is a plan,
not evidence that these proposals have been implemented or run.
The [Radiance reference mapping](remaining-validation-plan-20261026.md#radiance-references-and-applicability)
adds CPU metadata reuse, temporary lifetimes, graph fusion, small-GEMM dispatch
and adaptive verification depth to those existing packages. The rows below
distinguish implemented host prototypes from remaining physical and graph work;
original BF16/F32 is preserved.

| Proposal | Implementation status and source targets | Prerequisite before a new comparison |
| --- | --- | --- |
| Broader workload characterization | Four execution-disabled prompts rendered through the actual C++ template and original tokenizer metadata: 20/21/27/17 tokens; native control counts matched. [Host scope](remaining-validation-progress-20261026.md#bounded-workload-metadata) | Native token-ID equality, quality and matched metrics remain open. Expand surviving mechanisms beyond the fixed regression; existing two counting traces are insufficient to rank workload-dependent ideas |
| CPU metadata reuse | Native-fixture-qualified prototype; [measured scope](remaining-validation-progress-20261026.md#cpu-batch-metadata). The specific loop's generous saved-work estimate is only 0.1334 ms per fixed request; not linked into `LlamaEngine` | [Audit 2644](remaining-feasibility-20261026.md#scope-the-small-cpu-metadata-candidate) does not justify a new full-model comparison solely for this loop. Other context/backend metadata costs are not bounded by this result |
| Execute ready experts while actual-demand reads continue | Whole-expert/actual-backing metadata and same-53-slot split-root prototypes passed host controls. Saved-route serial-pair opportunities occur in 18.37% / 17.33% of external decode layer steps. [Scope](remaining-feasibility-20261026.md#ready-expert-ownership-and-backing) | Qualify independent backing, partial indexed widths, multi-owner source leases and original-order two-wave graph; measure actual overlap and total cost. Preserve existing parallel/coalesced packets |
| One-layer hidden-state router forecast with at most two reserved slots | Capacity/source review only; no hidden-state capture, forecast kernel or speculative transfer. Upstream `qwen4exp.cpp::build_hc_mix/build_hc_combine`, `build_layer_ffn`; `native/app/expert_policy.h` and cache overlay | Shadow observation of useful missing experts and readiness at demand, graph cost and wasted bytes before speculative I/O. Reuse original F32 routers without an extra cast/copy |
| Exact speculative verification or model-free drafts | Complete-model checkpoint qualified. Past-only draft and one-draft width-two adapter prototypes passed host controls, including actual-adapter rollback/bonus/EOG/unknown-completion cases. [Scope](remaining-validation-progress-20261026.md#model-free-draft-and-width-two-adapter-prototypes) | No native policy/controller enables the prototype. Actual two-target arithmetic, all continuation/route checks, discarded I/O and matched speed/memory remain unqualified. Width four/adaptive controller remain open |
| Repeated-prefix state reuse | Default-off consumer implemented and host-qualified; same-SELF A1 case 2601 returned a known pre-backend memory refusal, with zero GPU/model execution. [Consumer and refusal evidence](remaining-validation-progress-20261026.md#exact-prefix-consumer-and-reduced-headroom-experiment) | Diagnose the metadata-phase kernel decline before continuing the finite A/B then B/A cohort. Restore 2608/preserve 2609 passed. The owner's separately recorded experimental gate does not change production defaults; no prefix speed result exists |
| Zero-copy expert-major layout or vectored Direct I/O | Native bank numerics/retirement passed. Compact-record bank screen: 1.252x source / 1.183x total. Actual original-file comparison: 1.040x / 1.037x, only 7/8 rounds faster; inconclusive and unadopted. [Results and scope](remaining-validation-progress-20261026.md#compact-records-and-actual-production-source-layout) | No migration or integration from the failed production-shaped screen. Coalescing/fallback, partial-pack coverage and whole-model results remain unqualified; do not infer tokens/s from same-file fixtures |
| Larger useful cache or shorter allocation lifetimes | Partial host screen: packed 54 slots save 0.049% traffic; conservative 128-slot expansion saves 4.899% for 706.641 MiB extra banks and exceeds the existing cache cap. Same-53 cyclic eviction candidates failed the host screen. [Scope](remaining-validation-progress-20261026.md#cache-capacity-feasibility) | Wider peak-live ledger and metadata pressure attribution remain incomplete. Current native geometry/caps, LFU policy and fastest SELF are unchanged; no expansion or kernel-pool resize is adopted |
| Additional graph/vector/workgroup tuning | Actual shapes audited. Native PLE fixture now has a strict headless mode, complete graph/readback checks, 208-graph finite design and full linked/import-audited SELF. [Package and gate](PLE-slice-fixture-20261026.md) | New CPU-only 2656 refused regular prelaunch at 6257/10142 pages, with zero title/GPU execution. Physical placement/numerics and complete cost comparison remain open before model integration. Broader dual-output/GDN/small-GEMM tuning requires material cost evidence |

Start future selection with workload evidence and source-wait reduction. Ready
execution and router observation have distinct ownership and numerical gates;
neither is justified by the losing refill screen. State-based batching follows
checkpoint admission. Extra shader tuning follows evidence of a kernel bottleneck.
No new experiment is started by this consolidation.

The earlier 0.435–0.733 tok/s sensitivity table is conditional arithmetic for
assumed source-wait reductions, not a prediction or measured improvement. The
tested palette variants supplied no production gain. Larger gains still require
less critical-path traffic, better effective I/O service, or more accepted tokens
per verification cycle without changing the original model.

## Exclusions and maintenance

- Prefill eight fails the current worst-case 53-slot capacity; host snapshots
  fail the measured CPU slack. These reject those configurations, not every
  possible future batching or device-checkpoint design.
- Quantization, reduced KV precision, pruning and reuse-biased target routing
  are outside the original-precision objective. They are not measured failures.
- CUDA/PTX, Metal, Linux `io_uring` and GPU-direct storage have no qualified direct
  port in this native runtime. A PS5 ABI alternative needs separate qualification.
- Persistent caches and driver changes remain separate unqualified work. Keep
  the pinned driver and cache policy; no kernel-pool increase has been qualified.
- Keep validation and monitoring. Perform required large transport/visual capture
  before native preservation integrity and fresh admission. Do not assume all
  old captures are resident: the eight later frame controls each recovered zero
  pages. Inactive pages and an old free-page count never grant launch admission.

Update this index when a disposition changes, linking the terminal result and
preserving its baseline and scope. Add a new plan only for a distinct executable
sequence; update an existing proposal for refinements. Mark intermediate reports
historical and link forward rather than duplicating pending lists. Keep exact
SELF/settings preservation, current memory floors, positive completion, ordinary
close and private raw evidence; do not replay consumed cases.
