# Load analysis of the deployed post-Top2 application

This is a read-only analysis of the exact installed normal45100 / production45200 composition, SELF `2d66ba58810a7c0502564fb7c9181f25e8c2355f34925934f54f43bf20c4ecb9`, model receipt `46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426`, application relink97de33b and driver872cc126/cumulative-idle. It launches nothing, performs no model inference or weight conversion on the host, changes no runtime/production configuration and runs no CI.

The current native source and all three ordered route/counter sequences exactly match the earlier verified3712-slot planner replay. Reusing those identical deterministic results avoids another unchanged replay or PS5 launch. Current source/whole-time, syscall histogram and token timestamps are analyzed independently. Complete checks and evidence fingerprints are in `post-top2-load-analysis-20261101.json`.

## Main findings

1. Retained inference is not predominantly waiting for source reads:0.526683s of3.286629s,16.03%. The process remainder is1.751919s/53.30%, and work outside model processing is1.008027s/30.67%. The remainder mixes CPU/backend/GPU work; it is not a pure GPU measurement.
2. The actual serialized Vulkan source has a concrete repeated-tail splitting mechanism. Of44,091 software batch-boundary calls, at least37,448/84.93% are attributable to the almost-ready tail predicate after conservatively subtracting all graph endings and all FLOP boundary events. This is a source/counter attribution, not a measurement of wasted seconds or independently counted `vkQueueSubmit` calls.
3. Cold prefill remains I/O-heavy:4.566173s source wait/48.64% of9.387578s, with3091 of3290 misses in prefill. This differs from the retained regime.
4. All current miss fills occupy previously empty slots. Final occupancy is3678/3712 with34 slots free, zero evictions and zero misses for Experts read in a prior request. Another cache-capacity increase cannot eliminate the compulsory misses in this trace.
5. Startup and inference are separate. Recorded internal startup spans17.716834s; the largest stages are8.505180s model loading and7.305871s preflight. The6.587tok/s cold decode rate excludes startup.

## Exact time partition

Each row sums to whole inference time. Source wait is nested in model processing and is subtracted once. Other diagnostic timers below are nested observations and must not be added to this partition.

| Condition | Source producer wait | Other model process | Outside model process | Whole | Decode |
|---|---:|---:|---:|---:|---:|
| Model admitted, Expert cache cold |4.566173s /48.64%|3.600074s /38.35%|1.221330s /13.01%|9.387578s|6.587471tok/s|
| Empty KV, Expert weights retained |0.526683s /16.03%|1.751919s /53.30%|1.008027s /30.67%|3.286629s|8.203185tok/s|
| Exact prefix replay |0.167063s /6.80%|1.312461s /53.39%|0.978883s /39.82%|2.458408s|9.451015tok/s|

The prompt has30 tokens and22 generated outputs. Decode counts21 intertoken transitions; whole output throughput also includes prefill and EOS/completion. Cold Expert cache does not mean cold OS/NAND cache or application launch. Prefix replay still outputs7 rather than the final8 and is not correct-answer throughput.

Ordinary retained prefill is551.916ms, TTFT586.294ms, decode2559.981ms and EOS/completion tail140.354ms. Mean/median intertoken latency is121.904/120.460ms, P95142.556ms and max152.719ms across21 transitions. Prefix replay has six zero-new-Expert-demand intervals averaging28.786ms; the remaining host/sampling/completion/durable-output path is material even without another main-model Expert pass. That value is not pure CPU arithmetic.

## What changed since30200

Every ordered route, Expert hit/miss/upload counter, physical byte total and physical read count is identical between the old and new three-request cohorts. This is stronger than merely comparing nominal model names. Their timing remains sequential, not matched A/B; changed driver batching, output precision, startup policy and environmental drift must not be assigned separate causal percentages from this comparison.

| Retained request component | Old30200 | Current45100 | Change |
|---|---:|---:|---:|
| Source wait |520.185ms|526.683ms|6.498ms longer|
| Model process outside wait |2429.432ms|1751.919ms|677.513ms shorter|
| Outside process |995.769ms|1008.027ms|12.258ms longer|
| Whole |3945.386ms|3286.629ms|658.757ms shorter|

The source-wait fraction rises13.18% to16.03% because other processing is faster. The SSD did not become the cause of the measured speedup or a newly measured hardware slowdown.

## Serialized Vulkan tail investigation

The selected entry explicitly enables `GGML_VK_DISABLE_ASYNC` and `GGML_VK_SERIALIZE_SUBMISSIONS`. The actual GPU provider reads that environment into `serialize_submissions`. At its `ggml_backend_vk_graph_compute` boundary, scoped node capacity is256/divisor40; original node setting1 is restored afterward.

Source proof is in the exact selected `gpu.private.cpp` from `Post-top2-submit-nodes256-v16-37220`, SHA `06fb2b5dea710262bd457fd9cc583e1a4b6e5b172239d82d89ad42cf58d2971b`:

- `ggml_vk_compute_forward`, lines12999-13003: serialized submission uses `ctx->fence`. Only the **nonserialized** almost-ready branch sets `ctx->almost_ready_fence_pending=true`.
- `ggml_backend_vk_graph_compute`, lines14849-14854: after entering the last20% of a graph, `(almost_ready && !ctx->almost_ready_fence_pending)` remains a submission condition.
- Lines14883-14887 call `submit_after` whenever that condition produces enqueued work. With serialization, the almost-ready flag is not set by the serialized branch, so more eligible tail nodes can trigger it again.
- `submit_after`, lines14531-14562, counts a software boundary and performs the serialized fence wait. This is a batch-boundary event, not an independent Vulkan queue-submit counter.
- `ggml_vk_build_graph`, lines12398-12404, rejects empty/noncompute nodes. The final computational node therefore contributes at most one graph-ending boundary per graph, even if empty views follow it.

Observed native-cohort counters:5918 selected graph calls;407872 graph nodes;44091 software boundary calls;725 FLOP boundary events;0 node-cap boundary events; maximum graph-node range163. The conservative lower bound is:

`44091 - 725 - 5918 = 37448` repeated-tail boundaries, or84.93%.

This subtracts every FLOP event and every graph call even when reasons overlap, so it does not overstate the tail contribution. It does not establish that84.93% of time is removable, or that removing the predicate would leave all other event counts unchanged. The counters are cumulative across the selected native interval and may include setup/cleanup; there is no per-request split. GPU-backend graph caller wall is5.149878s and explicit backend-synchronize caller wall56.924ms over the cohort, both including waits and nested in other timing. These are not pure CPU or GPU durations.

The next focused experiment should gate **only** the artificial almost-ready split by `!serialize_submissions`. Retain serialized execution and actual fence waits, true tensor/buffer dependencies, final graph flush, node256, original FLOP cap, full validation and ownership/completion. Do not disable all synchronization. Measure actual queue submits/fence waits, split reasons, whole request and exact full F32/routes/tokens/bytes in a fresh matched comparison. This report does not implement or deploy that hypothesis.

Increasing node256 further is not the first experiment: the node-cap boundary count is already zero. Divisor10 and GPU greedy selection already failed relevant full-model tests and should not be repeated unchanged.

## Outside-process work and timing blind spots

In the retained request, observed GPU checkpoint/completion callbacks take164.975ms, stage observation205.444ms, work guards5.548ms and explicit engine synchronize0.160ms. These are observations at particular call sites, not an exhaustive additive classification of the1.008s outside process. Ordinary checkpoints here are completion callbacks, not a full speculative-state copy. Six complete speculative captures remain elided, with zero rejection rollbacks in this normal cohort.

Concrete next observation points are the **actual linked** `LlamaEngine::next_once`, `process_batch_once`, `GpuBoundary` begin/complete, `effective_logits`, the full-row observer/greedy sampler, token persistence and API publication. `native/app/native_bootstrap.cpp::qwen_native_stage` persists each stage using write+fsync; driver epoch callbacks also produce durable stage records. Retain required monitoring and durable-before-operation checks. Investigate redundant same-epoch observations or empty epochs rather than deleting monitoring.

Current logs do not isolate pure GPU kernels, CPU command recording, greedy sampling, complete-row verification, driver epoch management and fsync individually. The existing per-operation Vulkan perf logger changes barriers/submission/wait behavior; its diagnostic proportions cannot simply be substituted for current production node256 timing. Any further profiler should retain production batching and use bounded counters/timestamps without altering its dependencies.

## I/O volume, request latency and cache

| Condition | Physical source GB | Calls | Mean request KiB | Mean syscall wall | P50 range ms | P95 range ms | P99 range ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cold Expert cache |5.168589|7388|683.20|1.475ms|1.280-1.408|2.560-2.688|4.480-4.608|
| Retained weights |0.447087|825|529.22|1.419ms|1.280-1.408|2.304-2.432|3.072-3.200|
| Exact prefix replay |0.166085|315|514.90|1.290ms|1.152-1.280|1.792-1.920|2.560-2.688|

Percentile bounds come from complete128us histograms, with upper bounds exclusive. They include filesystem/OS/scheduling/transfer and all prefill/decode/EOS phases, not raw NAND latency. Per-request syscall wall overlaps across workers; ordinary summed wall1.170825s must not be added to0.526683s critical source wait. Physical GB divided by producer stall is0.849GB/s for retained inference, an application ratio rather than measured saturated SSD bandwidth. Configured width is four; actual busy-period occupancy and device queue depth are unmeasured.

Ordinary retained traffic is20.322MB per generated output including prefill/EOS. Accepted decode has275 misses among2016 Expert demands,13.64%, corresponding to20.114MB of **logical Expert uploads per transition**, averaged over21 accepted transitions. Decode-only **physical** GB/calls/wait were not separately captured and must not be substituted with these logical values.

Cold misses split3091 prefill /198 accepted decode /1 EOS. Retained misses split0/275/8; prefix0/82/23. Cache occupancy grows3290 to3573 to3678, with no eviction or earlier-request Expert rereads. Whole retained miss rate5.44% is diluted by zero-miss prefill and must not replace the13.64% decode miss rate. Layers29/18/26/23 lead retained whole misses with13/12/12/11, only16.96% combined; there is no single dominant Expert/layer hotspot in this trace.

Ordinary logical non-Expert indexed rows total532480 bytes,0.122% of logical source traffic. Huge stored BF16 PLE/embedding tensors are not streamed in full each token. The small-read histogram class contributes5.12% of summed ordinary syscall wall; the class itself does not distinguish embedding/PLE from possible small Expert fragments. Alignment/envelope overhead is11.866MB,2.73% of logical source bytes. These totals do not support making PLE quantization or alignment-only changes the first retained-speed action.

Miss count and ordinary interval latency correlate at0.854 across21 transitions, with a fitted slope1.523ms/miss and intercept101.959ms. This is observational: new reads, uploads and CPU/GPU work vary together. It does not isolate SSD latency or establish a hardware speed ceiling.

## Resident weight and memory inventory

Resident payload is3.418161GB:109 Q4 tensors1.525432GB;580 Q8 tensors1.630433GB;388 F32 tensors0.262213GB; one BF16 PLE convolution81920 bytes. The output Q4 matrix is357580800 bytes. The unused970284032-byte MTP category remains excluded from runtime. Stored routed-Expert payload is37.748736GB, while5.703660GB is allocated for the active shared-memory Expert cache.

| Resident role | Type | Matrices | Payload MB |
|---|---|---:|---:|
| GDN attention QKV |Q4_0|36|530.842|
| Attention Q |Q8_0|12|401.080|
| Output |Q4_0|1|357.581|
| Attention gate |Q4_0|36|318.505|
| SSM output |Q4_0|36|318.505|
| Expert router (`ffn_gate_inp`) |F32|48|251.658|
| Attention output |Q8_0|12|200.540|
| Four HC down/up role groups combined |Q8_0|192|668.467|
| Three shared-Expert role groups combined |Q8_0|144|250.675|

Payload sizes identify profiling targets, not measured time rankings or exact GDDR traffic per token. In particular router F32 and HC/shared Q8 remain worth timing, but changes to router precision can change Expert selection and answer quality; no conversion is performed here.

Qualification peaks: CPU503382016 bytes versus512MiB cap,31.9375MiB quota slack; post-load ledger6167724032 versus6199160832 cap,29.9805MiB quota slack. Actual workspace peak8MiB versus48MiB accounting reservation. The40MiB reservation difference is not occupied memory that can be freed. The post-load ledger excludes preloaded resident weights and separate staging, so it is not total physical RAM. Recorded inference kernel minimum is987 pages versus898 watermark:89 pages/1.390625MiB difference in a separate memory domain. These are measured qualification values, not current idle free memory or universal physical limits.

## Startup and bounded improvement scenarios

Recorded startup:7.305871s preflight +0.001868s gap +0.100191s observed settle +8.505180s model loading +1.803724s context creation =17.716834s. Stage span plus the first9.387578s request is27.104412s. OS loader time and unrecorded gaps are excluded, so this is not an exact power-on/app-launch-to-answer measurement. Do not optimize startup as if it were decode tok/s.

Holding other work fixed, removing all visible retained source wait changes whole3.286629 to2.759946s, at most19.08% greater **whole-request** throughput in that counterfactual. Halving it gives3.023287s/+8.71%. Neither scenario predicts decode tok/s or includes the cost of a new predictor/cache scheme. Improving only SSD wait leaves most current retained work.

## Recommended order from this analysis

1. Validate the serialized almost-ready predicate interaction on the exact selected provider. It has both concrete source evidence and a high measured boundary count; preserve actual serialization/fences and numerical exactness.
2. Split the1.008s outside process at existing lifecycle/sampler/observer/persistence boundaries, keeping monitoring. Target proven duplicate same-epoch work rather than assuming it is all sampling or deleting guards.
3. Profile current Q4/Q8/F32 kernel classes without changing node256 batching. Large output/QKV/router/HC/shared payloads justify measurement, not automatic quantization or a claimed GPU-time ranking.
4. Keep a separate cold-prefill lane:3091 compulsory prefill misses dominate startup-to-answer. Require a materially new source/placement/causal-hint mechanism rather than repeat negative prefill budgets or larger cache against this no-eviction trace.
5. For retained I/O, measure request issue/ready/consume and busy-period concurrency before changing four workers. First-read miss reduction requires new causal prediction or representation/routing changes; capacity alone cannot remove these current misses.

The current production executable, driver, weights, cache geometry and all runtime settings remain unchanged by this investigation.
