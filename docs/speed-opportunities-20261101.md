# Optimization opportunities after the Top2/Q4 transition

Proposal only. No console launch, driver/model mutation, deployment or CI run is performed. The reference is selected normal30200 / production30300, SELF `5b829d396dbbf4f7b6d07b139917ee5d3740c44bbb245cf4542f24371d1e36cd`, application source `76870d256094c93d083aa72a45b626e1b8b04975`. Use the existing current-performance-analysis-20261101 reports for exact measurements and caveats.

## Basis and scope

Retained request time is 3.945386 s: 0.520185 s source-producer wait, 2.429432 s other model-process work and 0.995769 s outside model process. The second category mixes CPU/backend/GPU work; no isolated GPU time is available. Removing producer wait alone, holding other work fixed, would reduce latency by 13.18% and increase whole-request throughput by 15.19%.

Cold requests still have 4.570359 s of source wait. Prefill accounts for 3091 of 3290 cold Expert misses. Startup has a separate 34.967628 s recorded span, including a 5.006610 s settling interval.

Current repeated-prompt cache occupancy reaches 3678/3712 with no eviction. All misses are first reads of new keys. More slots cannot eliminate those compulsory misses in this sequence. The exact replay additionally shows 766 of 1008 accepted-decode layer records have no misses (75.99%). This is an opportunity to reduce host interaction, not a claim that 76% of request time can disappear.

The current sampler is greedy (`native/app/llama_engine.cpp`, `llama_sampler_init_greedy`). The base graph-reuse path is already enabled. Proposals must target work beyond that existing reuse.

## New incremental candidates

| ID | Candidate | Mechanism and reason | First decisive experiment |
| --- | --- | --- | --- |
| N1 | GPU greedy selection and deferred full-logit collection | Compute argmax over already computed logits on GPU, return a compact token/finite-status result, and collect complete validation rows in bounded batches. Avoid full-vocabulary CPU sampling/readback on every step while retaining the full numerical evidence. Match greedy tie-breaking exactly. | Compare unchanged Q8 output-head logits and token IDs against CPU greedy selection. Time sampling, readback and callback intervals separately; verify every full row after the batch. Bound/price actual GPU and CPU buffers or reuse existing reference storage. |
| N2 | Top2-specific Vulkan recording/submission policy | Reuse stable subgraphs and recorded work where bindings permit it; tune submission partitioning to the smaller current Expert workload. Existing ggml graph reuse is not itself new. | Count actual command recording, submissions, barriers and waits for one unchanged workload. Compare a small set of bounded batch sizes, preserving every true dependency and maximum GPU-call duration. |
| N3 | Output-head Q4 plus shape-specific matvec | The remaining Q8 output projection is 675,430,400 bytes. Q4_0 would be 357,580,800 bytes, saving 317,849,600 bytes. The goal is less output-head memory/compute cost, rather than merely more Expert slots. | First measure the output projection's actual time. Then compare the two formats with full vocabulary/quality reporting. Do not derive a speedup directly from payload reduction or assume extra cache is useful. |
| N4 | Prefill-specific Expert budget | Decode is Top2, but prefill remains Top6. Test Top6/Top4 and then an adaptive budget separately for prefill. This directly targets cold Expert reads, unlike another decode-only pruning test. | Measure cold TTFT, unique prefill Experts, physical bytes/calls and subsequent decode quality. Deduplication means reducing selected count does not imply the same proportional reduction in SSD bytes. |
| N5 | Condition-based startup admission | Replace unconditional settling time with observed admission/stability conditions and reuse valid preparation metadata. The observed five-second interval has unchanged free-page counts. | CPU-only admission observations first, followed by a fresh bounded startup comparison with the original physical/OS/ownership checks. Report launch-to-first-answer separately from tok/s. A single quiet observation does not prove the delay unnecessary. |

N1 preserves the current target math if implemented correctly; N3 and N4 change the approximate model. Current correctness is not a broad model-quality baseline: the exact-prefix counting answer ends in 7 instead of 8.

## Previously negative or inconclusive candidates worth re-evaluating

| ID | Prior evidence | Materially changed candidate and reason | Priority/condition |
| --- | --- | --- | --- |
| R1 | Native17800 Gate/Up fusion is 26.80% slower for one token and 98.94% slower for two. The fixture fixes six selected IDs, using three physical samples, with a 128-thread shared-memory reduction. | Build a genuinely different Top2 kernel: two selected Experts, vectorized Q2_K unpacking, shared activation loads, scale reuse and a suitable reduction/tile. Test both distinct and duplicate IDs. Validate shader subgroup features before using optional operations. | High-value small fixture first. A six-to-two workload change justifies a new design; it does not imply the old shader becomes faster. Whole-model testing follows only a positive current-shape result. |
| R2 | The up-to32-attempt headless trial21400 has only about +0.39% decode and +0.24% whole-time change; timed arms actually use five attempts. | Current normal30200 reaches its cap of six attempts and accepts all six. Compare cap6/8/12 in this normal-controller workload, with complete verification and EOS accounting. | Strongest cheap re-evaluation. More attempts must actually execute; compare the matched controller/proposal policy rather than infer benefit from an old different workload. Report prefix error and target agreement independently. |
| R3 | Two-token GDN fusion17700 gives +0.697%, within A/A variation. Scalar GDN evidence is confounded by changed routes/read counts and does not isolate shader speed. | Re-evaluate GDN variants only after current Top2/Q4 profiling shows GDN is material. Lower MoE/I/O work increases its relative importance; use matched routes for the isolated comparison. | Conditional medium priority. Require actual candidate dispatches and whole-time benefit, not a repeated noisy estimate. |
| R4 | All-phase1444-key placement27600 reduces read calls but regresses decode; prefill-only28800 does not improve retained performance. The pack was selected using an older routing distribution. | Refit placement on current Top2/Q4 miss traces with held-out different inputs. Select packed versus parallel-role reads by phase and actual critical-path cost. | Conditional medium priority. Do not fit all 275 new misses and claim generalization on the same prompt; preserve unchanged-source controls and evaluate the larger file/lookup cost. |
| R5 | Early refill21700 adds an owned copy and regresses decode about 0.26%. | Test a zero-extra-copy, explicitly owned slot ring or next-layer lookahead on cold prefill, after busy-period measurements show a useful overlap window. | Low priority for retained inference; a copy-heavy identical implementation has less remaining wait to hide. This is a new implementation, not an unchanged rerun. |

Further cache growth and relaxed layer floors are conditional on different-input/long-session traces showing real evictions and later reloads. That condition is absent in the current three requests. KV-F16 saved only 8 MiB with no demonstrated speed gain, so it is not a priority unless that memory specifically enables a measured winning combination. Recurrent-S-F16 and width4 fail initialization in their current prototypes; compatibility/state-layout work must precede a meaningful new speed comparison. These are not physically impossible features, but changed timing proportions alone do not fix initialization.

## Combinations that may be more effective together

| ID | Combination | Why the effects can complement each other | Validation requirement |
| --- | --- | --- | --- |
| C1 | N1 GPU selection + N2 stable command segments + batched validation transport | Removes a CPU dependency and permits larger stable GPU segments, while keeping full validation rows and compact live monitor updates. | Validate individually, then together. Do not add percentage gains. Preserve token publication after positive completion and retain every full finite/reference check. |
| C2 | R2 longer speculation + R3 two-token GDN + R1 two-Expert kernels | More accepted verification batches use the exact one/two-token kernels being optimized, potentially amortizing Expert weights and graph overhead. | Compare whole completion time, accepted tokens per verification, rejected work and state rollback. The custom additional-shader registry currently has a software capacity of one; combination requires explicitly priced capacity and immutable hash verification for every shader. |
| C3 | N4 prefill budget + R4 current-distribution placement + R5 owned lookahead | Fewer unique demands, fewer source calls and better overlap attack different terms of cold startup-to-answer latency. | Measure changes in both cold prefill and later decode; route/quality changes must be reported. Keep a held-out input set and avoid claiming linear savings from reduced Expert count. |
| C4 | Reallocate memory among Expert cache, logits transport and hot execution buffers | With no eviction in this trace, another slot is not automatically more valuable than a bounded logits buffer or execution workspace that removes a CPU stall. | Treat 3712 slots and ledger caps as software choices, not physical limits. Test a Pareto curve on different inputs and price simultaneous allocations/VM pressure. A cache reduction can cause evictions and must be measured. |

As a scale illustration, reducing the current 2.429432 s non-source process by 20% and 0.995769 s outside process by 25%, holding the rest fixed, changes whole time from 3.945386 to 3.210557 s (18.63% shorter). This is arithmetic for a hypothetical combination, not a forecast, measured speed or decode tok/s projection.

## Larger architectural alternatives

| ID | Redesign | Potential benefit | Main work and limits |
| --- | --- | --- | --- |
| D1 | GPU-resident Expert-cache hit path with bounded host miss handling | Mirror cache/routing metadata on GPU; execute hit-only segments without host route downloads. The 766/1008 miss-free layer events give a concrete target. CPU remains responsible for SSD misses and owned source buffers. | Major backend/scheduler change, indirect dispatch and stable descriptors, coherent metadata/epochs, miss-list feedback and explicit dependencies. No persistent GPU spin loop waiting for SSD. Validate driver support and bounded completion on the selected PS5 driver; do not assume CUDA graphs or GPUDirect. |
| D2 | Matched MTP-assisted speculative decoding | Reuse main-model hidden state/output weights with the checkpoint's currently skipped MTP component instead of relying only on history-based proposals. A cheaper, more accurate draft could commit more target-verified tokens per model call. | First establish the head's training/architecture compatibility. Its 970 MB tensor category is not automatically all resident memory: it includes Expert payloads. Prefer a bounded auxiliary graph on the same backend; own draft state separately and isolate effects on the target's cache-aware routes. No PS5 speed or quality-preservation claim exists yet. |
| D3 | Shared Expert basis plus compressed per-Expert residuals | Change stored Expert representation rather than lower bits again. Shared low-rank projections can reduce first-read bytes, cache footprint and duplicate compute across selected Experts. | New model format, compression/calibration, specialized kernels, changed source/cache geometry and broad quality evaluation. Test one representative layer/rank first. The extra factorized operations can outweigh I/O savings when the cache is warm. |

D3 is supported as a research direction by D2-MoE and MoE-SVD, which study shared components/low-rank Expert representations. Their benchmark multipliers do not establish any PS5 Flash-Next result.

## Efficient decision order

1. Use one bounded current-configuration capture to split sampling/readback, command recording/submission and actual GPU kernel classes. This attaches a cost to each candidate; it is not an open-ended investigation.
2. Run the cheap current-shape R1 fixture and cap-binding R2 test; screen N1 without changing target weights. No unchanged old negative launch is repeated.
3. Select N2 and GDN work using the measured kernel/submission share; test combinations only after their parts have evidence.
4. Run N4/R4 as the cold-input lane, distinct from retained decode. N5 is a startup-latency lane and is never advertised as higher tok/s.
5. Design D1 in parallel with these bounded experiments. D2/D3 begin with a small feasibility slice; do not convert or deploy a full replacement before that slice succeeds.

Use the same PS5 with interleaved controls where the format/context permits. A format change must respect the demonstrated single-context lifetime rather than assume hot context replacement works. Preserve positive resource retirement, ordinary close and current observations; no reboot is required by the plan. Memory quotas can be explicitly repriced from actual allocations, while OS thresholds, source identity and real GPU dependencies remain valid. Keep persistent shader/pipeline caches disabled until separately qualified.

All candidates above are unmeasured hypotheses for the current selected composition, except the explicitly cited prior results. Adoption requires repeated whole-time benefit beyond observed A/A variation, actual execution of the candidate, separately recorded mathematical/quality changes and positive ordinary completion. Lower kernel time alone is not a whole-model gain.

## Primary references

- Current local measurements: `current-performance-analysis-20261101.md` and `.json`.
- Prior native dispositions: `next-five-worklog-20261031.json`, `four-next-results-20261031.md`, `strata-followup-results-20261031.md`.
- Greedy and callback scope: `native/app/llama_engine.cpp`; current cap variants: `native/app/next_five_causal.h`; six-Expert fixture: `native/app/expert_gate_up_fixture.h`; prototype shader: `native/app/expert_gate_up_q2.comp`.
- Integrate command work against the actual selected Vulkan provider; the pinned upstream anchor is `ggml_backend_vk_graph_compute` in `ggml-vulkan.cpp`, not a claim that editing unused upstream changes the installed app.
- Vulkan command buffer lifetime and dependencies: https://docs.vulkan.org/spec/latest/chapters/cmdbuffers.html
- Vulkan dispatch and indirect dispatch: https://docs.vulkan.org/spec/latest/chapters/dispatch.html
- Shader subgroup feature requirements: https://docs.vulkan.org/guide/latest/subgroups.html
- D2-MoE: https://arxiv.org/abs/2502.17298
- MoE-SVD (ICML 2025): https://proceedings.mlr.press/v267/li25az.html
