# Current production bottlenecks, including Vulkan

## Scope and exact production binding

This investigation reconciles the existing, positively completed normal56100
cohort against the current production configuration. It starts no PS5 program,
changes no runtime code or installed configuration, and runs no CI. The private
reproducible analysis is `.local/analyze_throughput_bottlenecks_56100.py`; its
asserted result is `.local/current-bottlenecks-56100.private.json`.

Production SELF is `9824030372e2eed7204275209a9bb6a6700a385ced8f9ca6e40d22fae258c135`,
compiled source `c60c1ab891dbbcf250db2bf919fa323f0ebc8727`. Model receipt is
`46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426`:
Expert Gate/Up Q2_K, Down Q2_0 MSE, 109 large resident Q4_0 matrices, other
resident Q8 except the small BF16 PLE convolution and F32 tensors/state.
There are 3712 active Expert slots. Decode selects two Experts; prefill six.

## Current normal measurements

| Condition | Decode tok/s | TTFT ms | Complete request ms | Source producer wait ms |
| --- | ---: | ---: | ---: | ---: |
| Empty Expert cache | 9.7593 | 4183.157 | 6428.954 | 2990.435 |
| Retained weights, independent empty request state | 11.5746 | 387.499 | 2295.868 | 443.043 |
| Exact prefix reuse with six accepted speculative proposals | 12.8013 | 52.413 | 1794.088 | 145.539 |

Each request has 30 prompt tokens and 22 generated tokens. Decode covers the
21 intervals between emitted tokens; it excludes prefill and final EOS work.
These are finite counting measurements, not sustained or arbitrary-input rates.
The separate headless current-core55900 repeats reach 12.2032 and 12.2665 tok/s;
their configuration/protocol is not pooled with the normal/API observations.

## Nonoverlapping time partition

The nested caller timer covers 2297.319 ms for the retained request, 1.450 ms
more than the public request metric. Its exclusive categories sum exactly to
the enclosing timer. These are elapsed caller times, including waiting, not
CPU instruction execution or pure GPU timestamps.

| Retained request component | ms | Fraction of enclosing wall |
| --- | ---: | ---: |
| Source producer wait | 443.043 | 19.29% |
| Model process excluding source producer wait | 1204.652 | 52.44% |
| Outside model process | 649.623 | 28.28% |

The last group includes stage observation 267.787 ms, checkpoint boundary
137.428 ms, epoch begin/complete 111.859 ms, token persistence 42.495 ms,
full-row validation 15.187 ms and sampling 12.718 ms. Stage observation includes
memory sampling and native stage reporting. These values are exclusive; do not
add inclusive observer counters to them. A checkpoint boundary here is the
driver lifecycle call, not evidence of a 119 MB recurrent snapshot at every token.

The analogous source-wait share is 46.50% for the empty-cache request and 8.11%
for exact-prefix reuse. Cold prefill remains an I/O priority, while retained
generation has a larger execution/synchronization and state-management share.

## Vulkan archive and source verification

The selected shared source is `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, based on Mesa `1ba9874f478657ccf6da72ce55f0260164cc0bd0`.
The profile includes H1 packed-half selection, H3 late LICM, completion snapshot
validation and the cached already-complete idle path. Persistent shader and
pipeline caches remain disabled.

The final link actually uses `driver-table-storage-3275/libvulkan-cold-tables.a`,
SHA256 `a325dcd4584b1f1fccc6b46e90faa081ca86d18544aca610efea9e3ca3774f32`.
Its native-platform predecessor is `b57fe26e...`; the shared profile archive is
`67fe76cc...`. These are different stages of the recorded composition, not
interchangeable archive identities. This investigation freshly hashes the final
archive and extracts its `radv_shader.c.o` and
`winsys_ps5_radv_ps5_winsys.c.o`: both are byte-identical to the selected profile's
objects. The platform composition replaces only `radv_ps5_platform_native.o`;
the later cold-table change concerns the recorded NIR table member.

The driver worktree HEAD is `b453ff86de5fb5c5a9106f26a9aa4bcf2ed0bf3a`.
That is a local source observation, not a remote-latest claim. It contains newer
host-checked development candidates. Those candidates are not the installed,
native-qualified driver. The ABI 3 development contract is not a drop-in
replacement for the preserved application-native adapter.

## Where execution and synchronization spend time

Between adjacent retained-request counter snapshots, the normal application
records 5888 Vulkan queue-submit calls / 96.871 ms, and 2597 measured serialized
fence calls / 731.705 ms. Their means are 16.452 us and 281.750 us. The counters
measure different nested/interval scopes from the table above; they must not be
added as independent extra components of request wall time. The fence timer
contains genuine GPU execution, marker polling and OS scheduling. The queue API
timer contains RADV/platform work; it is not a pure lock-time measurement.

The full normal cohort records 5918 backend graph calls, 6767 classified batch
boundaries, 851 FLOP-boundary events and **zero 256-node-cap events**. This is
cumulative, not the retained request alone. Graph count / boundary count is
87.45%; it is not an exact disjoint boundary classification or a savings estimate.
Increasing the node cap cannot remove a cap-triggered boundary in this cohort.

Concrete inspected sources:

| Layer | File and function | Finding / improvement direction |
| --- | --- | --- |
| MoE scheduler/cache | `build/Next-five-Q4-cache3712-20700/cache.private.cpp`, `llama_moe_cache::impl::copy`, lines 806 and 829-845 | Downloads selected IDs and synchronizes before cache planning, including all-hit layers. Investigate a device slot-map lookup and execution continuation for all-hit work, with an explicit coherent miss/resume protocol. This is a substantial graph change. |
| Vulkan backend | `build/Frontier-split4-51620/gpu.private.cpp`, graph-compute `submit_after`, lines 14545-14569; `vk_queue_handle_*::submit`, lines 16631-16656 | Serialized graph/FLOP boundaries cause CPU waits. Reduce unnecessary boundaries and transfers while preserving real routing/upload dependencies and successful fences before reuse. Larger node caps alone miss the observed trigger. |
| Shared driver completion | Generated pinned `radv_ps5_winsys.c`, `radv_ps5_queue_poll`, lines 60-90; `radv_ps5_queue_wait_seq`, lines 102-130 | The already-complete fast path is active. Outstanding work still polls with cache maintenance; initial spin is up to 1.5 ms, then sleeps request 1000 us. Current logs do not count spins or sleep entry, so this sleep is not established as the bottleneck. |
| Shared driver synchronization | Pinned Mesa `radv_ps5_sync.c`, `radv_ps5_sync_wait_many`, lines 116-165 | Wait-all delegates submitted work to sequence waiting. The measured application call supplies one fence; Q02's many-fence microbenchmark gain cannot be assigned to this path. |
| Shared driver submission | Pinned Mesa `radv_ps5_cs.c`, `radv_ps5_cs_submit`, lines 534-678; `radv_ps5_queue_claim`, lines 405-449 | Planning/copy/AGC work runs under the queue submit lock. Ring reuse already exists. Dedicated command allocation occurs above half the ring; current application evidence does not establish that it is frequent. |
| Native adapter | `native/driver/radv_ps5_platform_native.c`, `native/driver/kick_impl32.c` | Preserve application ownership, address placement, kick completion and platform ABI when instrumenting shared-driver changes. |

Current pure GPU kernel-group durations, busy-spin/sleep counts, queue-lock time,
command bytes/copy time, ring-pressure waits and AGC time are not separately
bound to these normal request intervals. The pinned CS source has a 10-second
window stderr summary (`radv_ps5_note_submission`), not request-bound counters.
Driver overhead cannot be equated with all 731.705 ms of fence waiting.

## Expert demand and remaining I/O

The entire cohort has 3246, 260 and 94 misses. Independent ordered-route set
accounting proves that these equal the first-use keys in each request, with
3246, 3506 and 3600 cumulative distinct keys. No observed miss is an already-used
key being requested again. More slots alone cannot remove these observed
first-use misses. This is not a claim about unrelated prompts or long sessions.

Retained complete-request miss rate is 5.017%; accepted decode alone is 12.649%:
255 misses over 21 transitions, or 18.651 MB of logical Expert payload per
transition. This is not a separately measured physical SSD GB/tok rate.
The 1008 accepted-decode layer records contain 777 with no misses (77.08%), 207
with one miss and 24 with two. Simply increasing the four I/O lanes cannot
create more simultaneous demands when the current layer needs zero or one new
Expert and later routing depends on preceding computation.

New first-use misses by layer band are 39 / 67 / 99 / 55 for layers 0-11 /
12-23 / 24-35 / 36-47. Layers 36, 32 and 35 contribute 12, 11 and 11. This is
one input's distribution, not a universal hotset.

The retained request physically reads 0.401752 GB in 330 calls. Mean syscall
wall is 1.470 ms, median is in [1.408,1.536) ms, P95 [2.176,2.304), P99
[2.688,2.816). These 128-us histogram bounds include prefill and EOS. Summed
syscall wall overlaps and includes OS scheduling; it is not raw SSD latency.

The new triplet layout serves 256/260 misses (98.46%) in 256 1504-KiB calls.
The four remaining Experts use 12 role reads. Small indexed non-Expert reads
account for 62 calls / 1.196 MB physical / 51.080 ms summed syscall wall: 18.79%
of requests but 0.30% of bytes. Their 51.080 ms is not an independently additive
request saving. New bundles cover 93.46% of the model, but their coverage of this
request's actual misses is already higher; completing the last model tail has
limited retained-request benefit, while cold behavior must be assessed separately.

The inspected `predict_next_expert` in the actual cache provider (lines 764-787)
still assumes ten selected IDs and original three BF16 banks / LFU policy.
It cannot simply be enabled for current Top2/Q2. A useful new candidate is
Q2-triplet staging prefetch with dynamic selection cardinality and current
transition observations. Keep staged bytes private until demand and positive
completion, so speculative prefetch does not silently alter cache-aware routing.
Compare new work against the existing completed prediction negatives rather
than re-running an unchanged predictor.

## Recommended next priorities and measurable acceptance

| Priority | Change target | Bound and verification |
| --- | --- | --- |
| 1 | Reduce all-hit CPU/GPU readback and graph synchronization, beginning at cache `copy` and graph split boundaries | First isolate request-bound GPU ranges versus host wait/poll time. Compare identical prompt, cache, precision and output work; count ID readbacks, graph splits, submit/wait calls, complete time and p95 intertoken latency. Test all-hit, one-miss and late-miss paths with full state/output validation. |
| 2 | Reuse unchanged state observation/journal preparation across the same boundary | Outside-process wall is 649.623 ms. Preserve monitoring, per-token durability, fresh fault/completion checks and allocation-generation invalidation. Inspect `DriverLifecycle::finish_boundary`, `observed_inference_stage`, `driver_journal_impl.inc` and the existing retirement certificates. Count actual OS queries, record formatting, writes and fsyncs; do not simply disable them. |
| 3 | Overlap Q2 first-use reads with preceding GPU work; improve small indexed-row locality | Source wait is 443.043 ms retained, 2990.435 ms cold. Measure useful/unused prefetch bytes, lead time, demand-blocked wait, small-read calls, output/routes and total time. Retain current scratch leases, integrity/ownership checks and ordinary completion. |
| 4 | Select shared-driver candidates based on the measured busy path | Q03 is relevant if sleep/wakeup tails are frequent; Q04 if planning/metadata cost is material; Q06 if dedicated allocations/ring overlap waits occur. First expose their actual counts/time in the matching adapter; qualify only a dependency-closed candidate with standalone exact readbacks before a matched application comparison. |

Q02/Q03/Q04/Q06 currently have source/host evidence, not PS5 application gains.
See the driver repository's `docs/experiments/q02-batched-completion-scan.md`,
`q03-deadline-backoff.md`, `q04-immutable-submission-plans.md` and
`q06-submission-memory-reuse.md`, and its shared integration contract. Q06 can
retain up to 16 MiB, so its value depends on actual command-allocation reuse.
Do not substitute the whole newer ABI 3 development archive as a shortcut.

As conditional arithmetic, reducing retained source wait by 25% saves about
110.8 ms (4.8% of public request time); reducing outside-process work by 10%
saves about 65.0 ms (2.8%). Even eliminating all 443.0 ms of source wait would
bound complete-request speedup to about 1.24x if other work were unchanged.
These are elapsed-time scenarios, not measured gains or decode tok/s predictions.

The earlier GDN Q4 join, WAR barrier narrowing, secondary-command replay and
split-K8 have completed negative dispositions. Current evidence does not
justify repeating them unchanged or further quantizing weights as the first step.

## Startup, separate from token throughput

The measured internal startup span is 17.721 s: preflight 7.347 s, pre-settle gap
0.001 s, settling 0.100 s, model loading 8.448 s and context creation 1.824 s.
OS loader time and unobserved gaps are excluded. Startup work can improve
launch-to-answer latency, but it does not explain retained 11.5746 tok/s.
