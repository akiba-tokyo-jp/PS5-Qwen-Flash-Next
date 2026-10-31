# Remaining I/O, GPU and cache follow-up results

No new performance default is adopted. Installed SELF `5564792aa1a8e193d60a13e0ea12f8293900fbc8c2e8ff3c8414c7c8ac212257` and its five settings are restored exactly. The final native title, gateway and models are inactive. The historical qualified independent-request decode rate remains4.894846 tok/s; exact-prefix repeat is6.579934 tok/s. These rates were not remeasured in this campaign.

The three candidates have final dispositions below. This does **not** mean that every intended full-model comparison completed: two model-load scopes were refused by the unchanged memory policy. Their returned failures are execution evidence, not speed measurements. The machine-readable report explicitly keeps `all_planned_full_model_comparisons_completed=false`.

| Priority | Implemented/tested scope | Result | Production decision |
| --- | --- | --- | --- |
| 1 | Exact current-miss triplet pack; native CPU sealing/readback; combined and original-GPU-only full-model launch attempts | Complete native pack proof; full-model timing execution unavailable under observed memory policy | Keep original448-key placement; new676-key placement disabled |
| 2 | Four-column GDN128 specialization; actual lazy-loader registry host checks; eight native F64/ABBA operator cases |288 graphs complete, all outputs pass;0/8 cases qualify for at least2% improvement in both orders | Tested unconditional variant fails speed qualification; keep original specialization |
| 3 | Actual3072-slot planner, accepted-only causal history, caps0/512/1024/1536, prompt identity and observed-overlap rules | No tested policy improves the installed fixed-prompt1536-key control | Keep the installed fixed-prompt policy; experimental adaptive code disabled |

## Unchanged implementation boundary

Keep Expert Gate/Up Q2_K and Down Q2_0 MSE, resident Q8_0, original BF16 PLE convolution, F32 inputs/KV,3072 active/3073 physical planes, four source workers, original CPU/Direct/kernel reserves and every completion/ownership guard. Driver source is `akiba-tokyo-jp/PS5-Vulkan-Inference` revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, native archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`; persistent shader/pipeline caches remain disabled. No CI, agents, reboot, Unix signal or GPU reset was used.

## 1. Current-miss triplet placement

The new immutable394264576-byte file contains256 exact Gate/Up/Down triplets:28 existing supplemental keys and228 newly ranked current-miss keys. Together with the unchanged base420, the control exposes448 keys and the candidate676. Every triplet and the whole file pass native SHA256/identity/EOF readback; the8 MiB CPU Direct scratch allocation positively retires. Original tensor bytes/encodings and fallback are preserved. The new file's SHA256 is `680e24d63a350bc37953e99efec7578727de28094a762e8d32a1c1b49075e1bb`.

The pack is ranked from actual current planner fills. This is placement coverage, not a measured reduction in physical calls: the existing reader already coalesces some requests, and misses do not map to a fixed number of physical calls. Do not convert coverage directly into tok/s. Both new comparison arms share the same sealed file for the original28 keys; physical placement versus the previous installed file is not held identical.

| Case | GPU application provider | Returned result | Completed model copy bytes/calls | Model requests |
| --- | --- | --- | ---: | ---: |
|12600 | Initial trial loader | Application defect: repeated lazy-loader walk rejected as a second device | Not a model timing |0 |
|12640 | Corrected bounded device registry | Model-load memory refusal:1148 free pages versus1154 required |2539077920 /661 |0 |
|12680 | Exact installed original GPU object | Model-load memory refusal:1137 free pages versus1154 required |3384249632 /929 |0 |

The original-GPU control object in12680 is `d49976ac3b328c3dbe73aa89ba02ca0120e9de5908b6c72da03e7e0210efe6fe`. This control prevents blaming the trial registry alone. Global kernel observations do not establish exclusive ownership or physical impossibility. The full-row reference vectors are allocated after model/context load, so shrinking those vectors cannot remedy this particular pre-context refusal. Do not replay these consumed scopes or reduce the reserve merely to obtain a timing.

All three cases return native failure evidence and complete ordinary OS close, PID absence, whole-SELF readback, exact settings restoration and fresh idle. Their conservative pre-close resource-retirement-unknown status is preserved.

Adoption requires a materially changed application memory scope that can finish model/context admission with the existing reserves, followed by a fresh declared comparison: at least2% retained whole-request reduction in both orders, no cold regression beyond2%, exact full-vocabulary rows/routes/tokens/bytes for byte placement, then normal/API/display qualification. The current campaign schedules no identical refused relaunch. The conditional normal/adoption stages are not triggered without a speed-qualified winner.

## 2. GDN128 four-column specialization

The existing F32 `gated_delta_net.comp` SPIR-V is reused. Only specialization constants/workgroup geometry change from the existing applicable selection to four columns; original reduction feature selection, legal divisibility, barriers, buffers, shared device ABI and driver archives remain. The trial pipelines are owned by their exact logical device in a bounded registry. Repeated `ggml_vk_load_shaders` walks must revisit `ggml_vk_create_pipeline` for requested lazy compilation; initializing a pointer once is insufficient. Compiled Vulkan handles are destroyed only after positive completion, before strong trial owners retire.

Native case12720 loads no model, model context, KV or Expert cache banks. Scalar gates use48 value/16 query heads and one sequence. Additional vector-gate cases use four value/two query heads and two sequences sharing query/key inputs. Each geometry crosses1/32 tokens with1/2 snapshot slots. Every attention/state value is compared with a CPU F64 recurrence; caller-owned unwritten snapshots and a separate canary are checked. Four warming graphs and A/B/B/A groups of eight samples per case total288 graphs. All144 candidate graph executions actually select the trial pipeline.

All cases pass the predeclared1e-6 absolute bound. Maximum error is **1.7101234629779416e-8**. Source/model-device owners retire positively; the ledger is0 before ordinary close. The69206016-byte peak includes original indexed startup qualification and fixture allocations; it is not whole-console memory consumption.

Positive percentages below mean a reduction in synchronized graph wall time. Both directions must reach2% for qualification.

| Scalar gate tokens | Snapshot slots | Forward reduction | Reverse reduction | Qualifies |
| ---: | ---: | ---: | ---: | --- |
|1 |1 |-6.528% |+0.059% |No |
|1 |2 |-0.098% |-6.399% |No |
|32 |1 |-1.101% |-4.812% |No |
|32 |2 |-0.167% |+2.386% |No |

No vector-gate case qualifies in both orders either. This rejects adopting the tested unconditional specialization. Timings include original boundary memory/completion checks and have an approximately7 ms floor; they do not isolate pure shader execution or prove that every underlying kernel is slower. No operator timing is converted into model tok/s. Reopening GPU work would require a materially different specialization or a timing scope that separately measures the guard cost, followed by whole-model/quality/normal qualification. It is not a pending rerun of this variant.

The initial host collector expected the model-phase `.resident.startup-memory` file, which this no-model branch never produces. The already completed native terminal remains unchanged. A separately recorded host reconciliation verifies all eight cases, all288 graphs and the completed native stage, then performs the original normal-close/restoration sequence. No inference or GPU graph is repeated to repair collection. Case12720 ends with exact5564/settings restoration, a fresh idle session and no unknown completion.

## 3. Causal history capacity and adaptive policy

The selected actual3072-slot planner reproduces native controls exactly. The captured comparison contains two installed identical-prompt requests and four different-input requests; counts below are summed Expert cache misses, not throughput. Capacity0 means disabled protection. Smaller histories preserve original accepted-only commit semantics and all planner ownership checks; the production history class/default is unchanged.

| History keys | Fixed protection, installed prompt | Prompt-identity gate, installed prompt | Fixed protection, different inputs | Prompt-identity gate, different inputs |
| ---: | ---: | ---: | ---: | ---: |
|0 |6193 |6193 |11108 |11108 |
|512 |6159 |6159 |11158 |11108 |
|1024 |5971 |5971 |11210 |11108 |
|1536 |5732 |5732 |11270 |11108 |

Observed-layer overlap thresholds1/8,1/4,1/2 and the identity-plus-overlap rule also complete. None reduces the installed fixed-prompt count below5732. The1536 identity gate restores the different-input unprotected11108 control but provides no incremental benefit for the currently compiled identical-prompt application. One smaller-history/different-input overlap screen removes one miss out of11108; this is neither installed-scope improvement nor native speed evidence. Do not promote it as a throughput gain.

The existing seven-policy aging screen completes13200 route observations over20 requests, including4096/8192/12288 aging boundaries, with valid ownership maps. The additional512/1024 capacity screen separately completes the same frozen six-request traces; it does not claim another aging campaign. Native arbitrary-prompt integration is not implemented by this metadata-only screen. A separately requested arbitrary-input application or a materially better causal rule must first beat the relevant fixed1536/unprotected control before a fresh native comparison is justified.

## Files and reproduction boundary

| File/function | Role |
| --- | --- |
| `tools/build_io_gpu_comparison.py::pack_header`, `main` | Exact sealed256-triplet map, original28-key control gate,448/676 arms and bounded full-row comparison |
| `tools/build_io_only_comparison.py::main` | Ten-request A/B/B/A comparison with the exact installed original Vulkan object |
| `tools/build_io_gpu_comparison.py::gpu_variant`, `registry_fix`, `GPU_STATE` | Trial GDN constants, bounded device owners, original lazy compilation and final compiled-handle retirement |
| `tools/build_gpu_registry_fix.py` | Reproduce the correction from the captured initial12586/V1 lineage; not a default production provider |
| `tools/finalize_io_gpu_build.py` | Historical12582 label/manifest correction; current builders already emit the corrected labels |
| `tools/rebind_gpu_provenance.py` | Bind actual GPU/cache overrides to exact storage controls without weakening original SPIR-V/resource validators |
| `tools/check_gdn_registry.py` | Extract actual generated source and exercise repeat walks, requested compile, device bound, pending-owner refusal and handle retirement |
| `native/app/gdn_columns_fixture.h::gdn_fixture::one`, `run` | F64 recurrence, complete outputs/snapshots/canary and bounded native ABBA graphs |
| `tools/build_gdn_columns_fixture.py::main` | Isolated no-model branch retaining pinned providers, memory callback and final epoch |
| `tools/analyze_gdn_columns_fixture.py`, `tools/analyze_io_gpu_comparison.py` | Require complete native evidence, declared arm order, positive retirement and exact restoration before reporting speed |
| `native/app/adaptive_prefill_protection.h::AdaptivePrefillProtection` | Disabled experimental prompt/observed-overlap rule using accepted decode history |
| `tools/check_adaptive_prefill.cpp`, `tools/screen_adaptive_prefill.cpp` | Bounds/commit/reset tests and exact selected-planner trace screen |
| `tools/screen_protection_capacities.py` | Frozen host-only512/1024 variants; no change to production1536 history |

The pinned application engine uses llama.cpp revision `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`; the relevant original sites are `ggml/src/ggml-vulkan/ggml-vulkan.cpp::ggml_vk_load_shaders`, `ggml_vk_op_get_pipeline` and `vulkan-shaders/gated_delta_net.comp`, plus `ggml/src/ggml.c::ggml_gated_delta_net` for output/snapshot geometry. Actual native compile/link receipts bind the generated application overrides, selected Vulkan object, original shader assets and pinned driver archives. This work does not substitute a new upstream driver or an unqualified shared-structure ABI.

Manual checks complete: accepted-history invariants, native-control planner reproduction, bounded aging ownership, generated registry lazy protocol, native compile/import/dispatch and SELF roundtrip audits, CPU pack sealing/readback, native operator F64/canary/snapshot checks, all ordinary closes and exact restorations. CI runs remain0. Exact private evidence labels, byte counts and SHA256 digests are preserved in `io-gpu-cache-adoption-20261031.json`; binaries, model data, private controllers/endpoints and raw evidence remain outside commits on the data disk.
