# Strata follow-up results

All four candidates have a native disposition. Three measured improvements are
integrated in normal SELF `1247c365144f9226ee5d62973256faf49f4aab7579b8493c4d26b7e8a9451eb3`
(20,133,559 bytes), relinked from clean source
`36a44bb1008895430d562e5904232a60efb284fa`. The exact prior A537 program and
configuration are the immediate control. Placement target is17100; consult the
[adoption receipt](strata-followup-adoption-20261031.json) for its verified state.

| Candidate | Native evidence | Disposition |
|---|---|---|
| 3424 active cache slots |14000: retained TTFT1971.550→1501.964 ms; whole6444.964→6120.181 ms; decode4.941265→4.770284 tok/s |Implemented and tested; not the default because decode regresses3.46%. Preserve3072/3073 production geometry.|
| Checkpoint capacity/metadata reuse |14600:60 real save/restore events,10,168,811,520 bytes checked, source identity/chunking/canaries exact.15400: complete F32/routes/tokens/output exact across16 requests |Adopt2 MiB capacity bins and GGML arena/vector reuse within the original136 MiB checkpoint bound.|
| Independent state-copy batching |15400: actual model capture/restore,14 timed requests with7 roundtrips each; all full F32/routes/output exact |Adopt bounded independent copies within one capture or one restore, preserving all outer completion.|
| F32 convolution/SiLU/QK RMS-scale fusion |14800:144 F64/full-state/history/weight/snapshot/canary graphs;16800:14 actual model requests with792 dispatches per timed candidate request |Adopt single-token matching shapes; preserve multi-token/unsupported-shape fallback and the BF16 PLE convolution.|

The capacity comparison uses identical fully priced3425-plane banks for both
active capacities. It isolates active capacity, not the installed3073-plane
allocation. Its TTFT/whole-response improvement is real, but its decode tradeoff
does not justify changing this decode-priority default.

## Measured effects

The checkpoint model experiment deliberately adds7 complete capture/restores
per timed request; its throughput is **not ordinary production throughput**.
Pooling reduces capture time337.387→250.952 ms cold and356.294→248.348 ms
retained (25.62%/30.30%). Batching further reduces combined save/restore time
8.62%/9.20% against the pooled-only A-B-A comparison. Payloads, application
cursor, all F32 vocabulary rows, ordered routes and outputs remain exact.

The ordinary16800 GPU comparison keeps3072 slots and has no injected state
work in its benchmark arms. Cold decode4.637701→4.718228 tok/s improves1.74%;
retained4.930861→4.988623 improves1.17%. Whole times improve0.55%/0.48%;
retained TTFT increases18.751 ms. Both temporal directions improve decode and
the mean effect exceeds observed A/A spread, without a fixed percentage floor.
Routing and I/O may change, so these are whole-model effects, not a pure-GPU
isolation or a claim that halving one subgraph doubles model speed.

Maximum mean KL is3.60644e-6; compared top1 agreement is1.0. Maximum logit
difference is1.201371, disclosed rather than used alone as a rejection rule.
All four fixed tasks pass: counting, `猫`, `42`, and a Tokyo/count3 JSON object.
The unchanged numerical shader's full F64 oracle reaches maximum absolute
error1.26854e-8, including zero/epsilon-dominated heads and unwritten snapshots.
This finite coverage does not establish arbitrary-prompt quality.

## Final normal application

Normal17000 completes all3 requests, both API streams, finish, both viewed
positively completed native frames, full finite vocabulary, actual routes,
positive resource retirement, ordinary close and exact A537/settings restore.
It records checkpoint counters `[6,6,8,872,0]`,1944 GDN dispatches, one separately
SHA256-admitted shader and0 fusion-overlap rejections. No injected benchmark
state work is present.

| Condition | Prior13100 decode tok/s | Normal17000 decode tok/s | Normal17000 TTFT | Normal17000 whole time |
|---|---:|---:|---:|---:|
| Cold start |4.395150|4.392052|6408.971 ms|11385.618 ms|
| Retained weights, empty request/KV |4.956084|4.991265|2010.925 ms|6437.184 ms|
| Exact prefix repeat/causal path |6.548935|6.715606|60.769 ms|3385.929 ms|

These normal comparisons are sequential, not A-B-B-A. Retained decode improves
0.71% and prefix decode2.55%; cold decode is0.07% lower, while retained TTFT is
8.515 ms higher. Do not describe every condition as faster. Prefix whole time
falls78.164 ms. The matched16800 comparison is the isolated GPU evidence.

CPU peak503,382,016 bytes, actual workspace8 MiB and device-ledger peak
5,068,816,384 bytes remain inside the original512 MiB CPU/48 MiB workspace/
5,086,097,408-byte postload bounds. Expert cache3072 slots/3073 planes and all
physical, loading/context and OS minimum checks remain unchanged. Precision is
unchanged: Expert Q2, resident Q8, original80 KiB BF16 PLE and original F32
tensors/activations/KV. The trunk convolution is originally163,840-byte F32.

## Integration and source locations

* `native/app/checkpoint_device_pool_trial.h` and
  `tools/checkpoint_trial_source.py::transform` extend the pinned
  `src/llama-context.cpp::llama_io_write_device` path without changing its ABI.
  The original source, layouts, devices, allocation sizes and capacity are
  checked before metadata/copy changes; unsupported cases fall back.
* `native/app/checkpoint_vk_batch.inc` submits independent validated copies as
  one transfer group. It rejects overlaps/dependencies and preserves positive
  wait/reset/pool retirement and original per-state outer boundaries.
* `native/app/gdn_conv_norm.comp`, `gdn_conv_norm_backend.inc` and
  `gdn_conv_norm_state.inc` implement the original F32 convolution4/SiLU,
  RMS(epsilon/128), then F32 scale. Original SPIR-V data stay immutable; the
  additional program has independent exact-address/size/SHA admission.
* `tools/build_gdn_graph_order_comparison.py` schedules independent one-token
  Q/K normalizations before head repeats in pinned
  `src/models/qwen4exp.cpp::build_layer_attn_linear`, before buffer scheduling.
* `gdn_conv_norm_planner.inc` uses the existing
  `ggml_vk_graph_optimize`/`ggml_backend_graph_optimize_params::add_alloc_dep`
  path, as upstream TOPK_MOE does. `gdn_conv_norm_range_guard.inc` protects every
  member in both generic real/view pulling passes, as interior-QSA protection
  does. Original overlap checks remain active; no flags are weakened.
* `tools/build_strata_followup_normal.py`,
  `finalize_strata_followup.py` and `strata_followup_production.py` bind the
  exact selected providers, clean relink revision, normal telemetry and install.

The llama.cpp base is `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`.
Driver source is `akiba-tokyo-jp/PS5-Vulkan-Inference` revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, original ABI;
native archive SHA256 is
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled.

## Nonqualifying trials and recovery

14200 exposed a one-unused-byte fixture reader contract error;15000 exposed a
missing frontend epoch in the test adapter. The corrected fixture/model paths
complete14400/14600/15400. No inference acceleration is inferred from those
aborts.15200/15800/16600 completed through the original path with0 fused
dispatches; they are explicitly not fusion-performance evidence. The generic
optimizer had pulled span members before a start-only check could see them.
Full-range protection resolves this in16800.

16200's larger-cache load refuses at minimum1132 versus1154 required pages.
It normally closes/restores with conservative unknown GPU-completion evidence
retained; the threshold is not lowered. Reducing application-owned cache by
540,672,000 bytes to the original3072 geometry permits16600/16800 and normal
delivery.15600 passed normal delivery but omitted successful-terminal winner
counters;17000 qualifies the telemetry-corrected exact final program, with
identical mathematical/GPU/cache/context/asset providers. No consumed launch or
unchanged refused scope is replayed. No reboot, CI, agents, forced signal/reset,
manual uncertain GPU release, new quantization or learned host inference occurs.
