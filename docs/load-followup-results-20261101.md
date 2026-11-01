# Current-load priorities1-3: native validation results

All three requested verification stages completed on the same PS5 without a reboot. Production placement is recorded separately in the adoption/installation records. No CI, learned host inference, driver change, weight change or increase in cache/allocation limits was used. The diagnostic query provider is excluded from the normal candidate.

## P1: serialized Vulkan tail batching

Case46100 compares only the serialized `almost_ready` predicate in a14-request matched cohort. Both arms use node256/divisor40 and the same outputQ4, Top2 decode, six-Expert prefill, cap6 and CPU measurement. In serialized mode, `almost_ready_fence_pending` was never set by the asynchronous-only branch, so its tail predicate repeatedly cut submission batches. The candidate disables this asynchronous notification trigger in serialized mode; real dependencies, final flushes and serialized completion waits remain.

The repeated retained request improves decode by **9.9784%** and whole time by **7.7822%**. The paired whole savings are260.1033ms and229.8492ms against a27.4586ms control A/A spread. Actual queue submissions fall14555 ->4423 (**69.6118% fewer**); serialized wait calls fall12135 ->2003 (**83.4940% fewer**). These are actual calls rather than software boundary estimates. Count reduction is not a proportional GPU-time improvement. Every full F32 target row/token comparison is exact; all four fixed semantic tasks pass. No node-cap widening is used.

Implementation: `tools/build_load_followup.py` transforms `ggml_vk_graph_compute` in the pinned GPU provider; `tools/build_load_normal.py` selects only the qualified provider and original normal model/API/display flow. `native/app/load_followup_timing.h` provides nested caller-wall accounting.

## P2: actual normal controller caller-wall attribution

Case47100 contains one local cold self-test plus two actual streamed generation API requests. A third POST completes validation and retires model/source/GPU owners; it is not a third external generation. Both positive native VideoOut frames were viewed. Each API token ID and output byte equals its own native result.

These measurements are inclusive/exclusive wall spans, **not CPU utilization or pure CPU cycles**. GPU waits and source I/O remain inside model-call wall. Each request's sum of exclusive intervals equals its enclosing request span exactly; inclusive spans must not be added. The instrumented request endpoint differs slightly from the published model-metrics endpoint.

Retained-request enclosing span: 2990.573883ms.

| Exclusive caller interval | ms | Share of enclosing span |
| --- | ---: | ---: |
| model_process | 1954.398150 | 65.352% |
| token_persistence | 286.708026 | 9.587% |
| stage | 263.894309 | 8.824% |
| epoch_complete | 183.414929 | 6.133% |
| checkpoint | 164.088317 | 5.487% |
| epoch_begin | 46.028275 | 1.539% |
| request_run | 59.009655 | 1.973% |
| full_validation | 15.281016 | 0.511% |
| sampler | 12.880824 | 0.431% |
| finite_scan | 2.831591 | 0.095% |
| publication | 1.845709 | 0.062% |
| logit_access | 0.115705 | 0.004% |
| token_render | 0.077377 | 0.003% |

The actual normal controller's non-model overhead is dominated by durable token persistence, stage observation and device ownership/completion epochs. Sampling, finite scanning and API producer publication are much smaller. `request_run` exclusive is the remaining unclassified interval; `work_guard` is not separately isolated, so zero instrumented calls do not mean zero guard work. `publication` measures producer-side publication, not network transit. Cold local self-test has no API publication callback; both external requests do. Required monitoring/durability remains enabled.

## P3: actual selected GPU ranges

Case46500 holds the adopted tail policy in both arms and enables bounded timestamps only in the diagnostic arm. No query WAIT, extra queue completion, forced graph synchronization or batching change is introduced. Query results are read only after the existing positive device-completion checkpoint. One pool is created and destroyed,123123 ranges are completed and zero remain pending. Every full F32 target row/token comparison is exact. Diagnostic whole-request overhead is **2.47585%**, so this provider is not used for the production speed claim.

Retained diagnostic requests5/7 average **559.44642ms** in the selected matrix/SSM ranges, including prefill, accepted decode and EOS/completion. These are fused operator/dependency intervals, not all GPU work or complete shader time. Q2 unpacking is fused into the matrix range and is not separately isolated. HC/shared labels are role based and mainly Q8, not unconditional dtype checks. The `output_Q4` bucket includes final-output-related HC projections and is not a measurement of the output head alone.

| Role/range bucket | Whole selected ranges ms | Accepted decode ms | Share of selected ranges |
| --- | ---: | ---: | ---: |
| HC_Q8 | 194.68928 | 49.50782 | 34.800% |
| Expert_Q2_matmul_with_unpack | 143.20680 | 24.75624 | 25.598% |
| other_Q4_matmul | 84.26772 | 59.11066 | 15.063% |
| other_Q8_matmul | 38.20740 | 21.89952 | 6.830% |
| output_Q4 | 33.57000 | 25.03540 | 6.001% |
| shared_Expert_Q8 | 28.11818 | 16.21834 | 5.026% |
| router_F32 | 22.11240 | 14.27834 | 3.953% |
| GDN_SSM_ranges | 15.27464 | 12.16704 | 2.730% |
| other_matrix | 0.00000 | 0.00000 | 0.000% |

HC is largest across the measured whole request, followed by Expert Q2. For accepted decode alone, other Q4 matrices lead HC. Therefore a single whole-request GPU ranking should not be used as a decode ranking. Subsequent candidates should separate HC prefill fusion, Q4 decode matrix kernels and ownership/durability overhead while retaining the current dependency and completion rules; these are findings, not additional uncompleted stages of this three-item campaign.

Implementation: `tools/build_load_gpu_profile.py` adds bounded ranges in `ggml_vk_build_graph`, drains after the existing `gpu_checkpoint_` and destroys the query owner after existing backend cleanup. `tools/analyze_load_followup.py` reconciles each bucket into prefill/first token, accepted decode and EOS/completion. The existing Vulkan performance logger remains disabled.

## Actual normal application qualification

Fixed30-token prompt,22 generated tokens. Configurations45100 and47100 are sequential, not matched A/B; causal tail evidence is the separate46100 cohort above.

| Condition | Previous45100 tok/s | Normal47100 tok/s | Whole request ms | Counting correct |
| --- | ---: | ---: | ---: | --- |
| Cold Expert cache | 6.587471 | 7.215938 | 9012.397628 | true |
| Independent KV reset, weights retained | 8.203185 | 9.186170 | 2989.162941 | true |
| Exact prefix with causal reuse | 9.451015 | 10.476288 | 2231.314812 | false |

The prefix answer still ends in7 instead of8, as in the preceding normal45100; its rate is not correct-answer throughput. Finite fixed-task passes do not establish arbitrary-prompt quality or sustained reboot-free service.

Normal47100 source relink is revision`e909298` with SELF`8858dd5eaa63733accabfa50b057971fa8b54c9acad4e8e6365f7b5a54b424b1`. Driver source remains`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile`cumulative-idle`, archive`67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9`; persistent shader/pipeline caches remain disabled. Normal CPU peak503382016bytes and device-ledger peak6167724032bytes remain inside the original536870912/6199160832 limits. Active cache remains3712 slots/3713 planes and5703659520bytes. The normal program has no diagnostic GPU timestamps.

Native scopes46100,46500 and47100 positively retired all model/source/device owners, reached zero live device ledger, ordinarily closed, and restored the exact preceding2d66 program/settings. Production placement47200 subsequently verifies both selected/current and immediate-control programs plus five settings each, without another title launch. Its final result and strict admission/refusal checks are recorded in [adoption](load-followup-adoption-20261101.json), [worklog](load-followup-worklog-20261101.json) and [installation](../config/production-installation.json). Raw native logs/frames/build artifacts remain outside Git; report fingerprints identify their immutable evidence.
