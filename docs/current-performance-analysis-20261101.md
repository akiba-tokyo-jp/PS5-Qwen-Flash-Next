# Current selected PS5 performance analysis

This report reanalyzes selected normal30200 and the preceding normal19000. It performs no console launch, model conversion, production change or CI run. The exact frozen native cache planner was replayed on the host: all three native hit, miss and uploaded-byte sequences match. Units below use decimal GB unless MiB/GiB is written explicitly.

## Weight changes

| Resident role | Matrices | Prior Q8 MB | Current Q4 MB | Saved MB |
| --- | ---: | ---: | ---: | ---: |
| attn_qkv.weight | 36 | 1002.701 | 530.842 | 471.859 |
| attn_gate.weight | 36 | 601.620 | 318.505 | 283.116 |
| ssm_out.weight | 36 | 601.620 | 318.505 | 283.116 |

Resident weight payload falls from 4.774100480 to 3.736010240 GB: 1.038090240 GB saved, or 21.74%. The selected 108 matrices fall from 2.205941760 to 1.167851520 GB. Conversion uses verified original BF16, rather than quantizing already quantized Q8. Remaining resident formats are 581 Q8 tensors / 2.305863680 GB, 388 F32 tensors / 0.262213120 GB, and one BF16 PLE convolution / 81,920 bytes. Output projection remains Q8 (675.4304 MB); shared Expert projections remain Q8.

All 24,576 routed Experts remain stored: Gate/Up Q2_K total 26.4241152 GB and Down Q2_0 MSE total 11.3246208 GB. Decode uses two Experts per layer rather than six: 96 versus 288 layer-Expert selections per token across 48 layers. Prefill retains six. This is less approximate model work as well as engine optimization; the original mathematical model is not preserved.

Nonresident BF16 PLE and token embedding payloads remain 102.400491520 GB and 1.271398400 GB. Only indexed rows are read. These are tensor payload totals, not live RAM, virtual GGUF length or occupied SSD space including duplicate packs. The existing 970,284,032-byte MTP category remains excluded by the current text-engine footprint and was not newly removed.

The 1.038 GB resident saving funds 983.040 MB of cache growth: 3072 to 3712 active slots, 3713 physical planes, 5.703659520 GB. Available 1444-key placement applies only to the initial prefill; all decode and later requests use 768 keys.

## Actual speed and latency

| Condition | Decode tok/s | Whole generated tok/s | TTFT s | Whole request s | Counting correct |
| --- | ---: | ---: | ---: | ---: | --- |
| Cold Expert cache | 5.537146 | 2.150751 | 6.282451 | 10.228984 | true |
| KV reset, weights retained | 6.538603 | 5.576134 | 0.563971 | 3.945386 | true |
| Exact prefix + speculation | 7.872825 | 7.489821 | 0.061090 | 2.937320 | false |

The prompt has 30 tokens and generates 22. Decode rate covers 21 intertoken transitions; whole generated rate includes prefill and completion. Cold means an empty Expert cache after model/context admission and excludes executable/model startup. Previous/current normal comparisons are sequential, not ABBA.

Ordinary retained decode improves 5.012038 to 6.538603 tok/s. Whole time falls 6.410564 to 3.945386 s. Source wait falls 2.517762 to 0.520185 s, accounting for 81.03% of the 2.465178 s saved. Remaining model-process time improves 2.901016 to 2.429432 s; outside-process work stays about 0.99 s. Cold whole time improves only 11.410040 to 10.228984 s; cold TTFT remains 6.282451 s.

## Startup latency, separate from decode throughput

The startup memory trace spans 34.967628 s from its first internal stage to model/context completion. The phase labelled CPU preflight takes 15.977627 s; a fixed settling interval takes 5.006610 s; after settling, model loading takes 12.179349 s and context completion another 1.802874 s. The preflight label does not isolate pure CPU compute. Kernel free pages are 5144 both before and after the fixed settling interval in this observation.

The recorded startup span plus the first 10.228984 s request totals 45.196611 s. This excludes OS loader time and unmeasured gaps, so it is not an exact app-launch-to-answer measurement. The 5.537146 decode rate excludes this startup cost. Replacing fixed settling time with qualified condition-based admission is a potential startup-only improvement; this single observation does not justify removing the checks. No startup policy was changed.

## Nonoverlapping time decomposition

| Condition | Source producer wait s | Model process outside source wait s | Outside model process s | Wait / total wall |
| --- | ---: | ---: | ---: | ---: |
| 0 | 4.570359 | 4.501212 | 1.157412 | 44.68% |
| 1 | 0.520185 | 2.429432 | 0.995769 | 13.18% |
| 2 | 0.164900 | 1.827103 | 0.945317 | 5.61% |

For retained inference the visible source wait is 17.64% of model process and 13.18% of total wall. The 2.429 s remainder mixes GPU kernels, CPU graph preparation/submission, synchronization and other backend work; it is not pure GPU time. The 0.996 s outside process includes sampling, output downloads/delivery, GPU completion checks, stage observation and prefix handling. GPU timestamps and utilization were not measured.

Diagnostic timers must not be blindly added as independent partitions. Ordinary GPU checkpoint callback costs 167.135 ms and stage observation 213.497 ms. Explicit synchronize is 0.156 ms, work guard 5.589 ms, planner 6.490 ms and ranking 6.698 ms. The checkpoint callback checks GPU completion/state; it is not a full speculative-state capture, which is already elided. Preserve monitoring and required completion checks while investigating duplicate metadata or same-boundary work.

Holding other work fixed, removing only all ordinary producer wait gives a 3.425201 s request, about 15.19% faster. Attributing all request wait to accepted decode and removing it gives an optimistic 7.802 tok/s. These are limited wait-removal scenarios, not hardware ceilings. The 21-interval observational miss fit gives about 7.00 tok/s if decode misses halve, but that fit does not isolate SSD causality or prove a future gain.

## Cache and physical I/O

| Condition | Physical GB / request | Read calls | GB / output token including prefill and EOS | Whole-request miss rate |
| --- | ---: | ---: | ---: | ---: |
| 0 | 5.168589 | 7388 | 0.234936 | 63.23% |
| 1 | 0.447087 | 825 | 0.020322 | 5.44% |
| 2 | 0.166085 | 315 | 0.007549 | 5.21% |

Ordinary physical reads fall from 2.962277 to 0.447087 GB (84.91%), and requests from 4388 to 825 (81.20%). Exact old/current phase misses are prefill 1000 -> 0, accepted decode 851 -> 275, and EOS/completion 35 -> 8. Their logical Expert-byte savings are 1.536 GB, 0.884736 GB and 0.041472 GB respectively.

Decode demands fall 6048 -> 2016 with the six-to-two Expert change. The decode miss rate changes only 14.07% -> 13.64%; the 5.44% whole-request rate is diluted by a zero-miss prefill. Current accepted-decode logical Expert uploads are 20.114 MB per transition, previously 62.245 MB. Exact physical decode-only traffic and wait are not available.

All current misses are new keys. Occupancy grows 3290 -> 3573 -> 3678 within 3712 slots. There is no eviction, no future-decode key lost to prefill, and no miss for an Expert read in an earlier request. More slots or a new eviction policy alone cannot remove these particular compulsory misses. This conclusion applies to the captured repeated prompt; different inputs may exceed the working set. The top four ordinary layers account for 16.96% of misses, not a dominant narrow hotspot. Leading layers 29/18/26/23/35/41 have 13/12/12/11/11/11 misses; each key is read once.

Ordinary mean read size is 529.22 KiB and mean syscall wall time is 1.390 ms. Histogram ranges are P50 [1.280,1.408) ms, P95 [2.432,2.560) ms, P99 [3.072,3.200) ms. These include OS, filesystem, scheduling and transfer; they are not raw NAND latency. Summed overlapping syscall time is 1.146930 s and must not be added to producer wait. Maximum concurrent reads is four. The 0.389 ratio of summed syscall time to all process time is not SSD busy-period queue depth. Actual streaming executes 204 groups/quad batches; the legacy quad timing is zero because it excludes that path. Zero adjacent merge savings is a workload observation, not disabled concurrency.

Logical non-Expert row reads total 532,480 bytes for 52 evaluated tokens, or 0.122% of logical source bytes. The large nonresident BF16 tables therefore do not imply whole-table reads per token. Reducing those row bytes is not the main retained bottleneck.

## Memory domains

The 3.736 GB resident payload is admitted before and excluded from the post-load ledger. That ledger peaks at 6.167724032 GB, under a 6.199160832 GB software cap, leaving 29.98 MiB of quota. Their major accounting sum is 9.903734272 GB plus other allocations/alignment, not a measured total physical peak. CPU heap peaks at 480.06 MiB under 512 MiB, leaving 31.94 MiB of quota. A 48 MiB fixed workspace reservation covers an actual 8 MiB capacity peak; the 40 MiB difference is accounting reservation, not occupied RAM to free.

The driver snapshot after model/context admission reports 12,280,922,112 bytes total and 2,058,944,512 bytes free (1.918 GiB), not the minimum at later peaks. Kernel inference minimum is 986 pages (15.406 MiB), versus an 898-page OS watermark: a separate 88-page / 1.375 MiB margin. Software quota slack, heap free snapshot and kernel VM headroom are different quantities. No new physical maximum allocation or extra-slot limit was measured.

## Quality, causes and priorities

Cold/retained output is `1, 2, 3, 4, 5, 6, 7, 8`; prefix output is `1, 2, 3, 4, 5, 6, 7, 7`. The last 8 changes to 7. Two of three deterministic passes are not a 67% model-accuracy estimate. Six proposals are accepted with no rejections; six zero-new-demand intervals average 26.47 ms. The 7.872825 tok/s prefix result is not correct-answer throughput.

Precision, Expert count, cache-aware routing, prefix restoration, cached occupancy and speculation change together. The error cannot be assigned to Q4 or a checkpoint bug alone. Full-prefill versus restored-prefix tests should first hold route/cache state matched with speculation off, then add speculation while locating the first logit/token divergence. Existing F32 maxima alone do not establish numerical failure.

Priorities follow the measured scope:

1. Retained speed: partition the 2.429 s non-source process among actual Q4/Q8 matvec, routed Expert kernels, GDN/Attention, CPU graph preparation and submissions. Pure GPU time needs bounded new instrumentation; it cannot be inferred from the remainder.
2. Account for the 0.996 s outside process while preserving monitoring, durable observations and required completion checks. Planner plus ranking totals only 13.2 ms and is not a primary target.
3. Cold/different-input speed: 3091 of 3290 misses occur in prefill. Focus layer-ahead streaming/placement there, or explicitly investigate a new prefill Expert-count tradeoff. Do not rerun the unchanged negative early-refill or all-phase placement prototypes.
4. Retained I/O: hide compulsory new reads with causal hints/preparation. Extra capacity or hot-key retention alone cannot eliminate these captured misses. Measure streaming busy-period occupancy before increasing four workers.
5. Profile remaining Q8 before quantizing more. Output projection is 675.43 MB and resident Q8 totals 2.306 GB, but memory savings alone do not establish speed gains when the current trace fits. Existing KV-F16 and S-F16 results are not invalidated.

The flat historical `maximum_causal_attempts_on_final_request=8` and base `routing_policy.decode_Experts=6` are stale descriptors, not the current execution contract. Selected next_five scope and actual records show six attempts and two decode Experts. This report resolves them without changing runtime configuration.

Full calculations, exact layer/token statistics and evidence fingerprints are in `current-performance-analysis-20261101.json`.
