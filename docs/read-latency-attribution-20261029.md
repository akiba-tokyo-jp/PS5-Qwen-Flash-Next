# Read-request latency and byte-volume attribution

The completed physical evidence supports **byte-volume-dependent source I/O as
the dominant cost**, with a smaller fixed request/granularity cost. This is a
diagnosis of the effective application I/O path, including filesystem and
kernel work. It does not isolate NAND, the SSD controller or raw device bandwidth.

This analysis reuses existing measurements. It starts no console helper, title,
model or GPU work, changes no production file, and runs no CI. The selected
134-slot normal profile and original BF16/F32 precision remain unchanged.
The [machine-readable analysis](read-latency-attribution-20261029.json) separates
measured values from descriptive estimates.

## Selected production application

Case 7080 qualified the same normal counting SELF later installed in 7420:
`80c28a95e993458c54b5fbf73fe59accde17dd8302dd49a9aeecf367e617739c`.
The completed monitor record confirms 134 slots and adaptive selection disabled.
The second request retains the already adopted causal width-two/prefix path.

Subtracting cumulative counters at generated token 1 from token 22 isolates the
21 accepted decode transitions. It excludes prompt processing and the final
EOS evaluation. All 44 token records were checked against the completed token
streams; times and counters are monotonic. The terminal records confirm source,
worker, GPU and model retirement. These are retained physical results, not a new
live measurement.

| Measured decode interval | Request 1 | Request 2 |
|---|---:|---:|
| Decode tokens/s | 0.418443 | 0.440244 |
| Elapsed time | 50.1860 s | 47.7008 s |
| Inside model process calls | 49.1890 s | 46.4838 s |
| Producer source-read/wait | 45.2972 s | 42.6762 s |
| Source wait / model process time | 92.088% | 91.809% |
| Physical bytes read | 89,075,195,200 | 83,671,719,232 |
| Physical read calls | 27,218 | 25,599 |
| Decimal GB per accepted token | 4.24168 | 3.98437 |
| Read calls per accepted token | 1,296.10 | 1,219.00 |
| Mean physical request | 3.12105 MiB | 3.11714 MiB |
| Physical bytes / producer source-wait | 1.96646 GB/s | 1.96062 GB/s |

The last ratio includes scheduling and waiting. It is not raw SSD bandwidth.
Parallel worker intervals overlap producer/consumer work and are never added.
Dividing producer wait by the physical call count would not produce device
latency. The two requests have different cache/prefix conditions and do not
constitute a new matched speedup comparison.

## Fixed request count, different byte counts

The completed CPU-only case 436 uses the real C++ source executor and sealed
original model files with `O_DIRECT`, one 8 MiB Direct window, three ordered
rounds and 16 observations per mode per round. The last round disables the wait
sampler. Its raw result SHA256 and terminal success were checked before analysis.

| One serial physical request | Observations | Mean wall time |
|---|---:|---:|
| 4 MiB | 48 | 5.57505 ms |
| 6.265625 MiB | 48 | 8.17327 ms |
| 8 MiB | 48 | 10.20311 ms |

Doubling bytes with the request count fixed increases elapsed time by about
83%. A descriptive affine fit is `T_ms = 0.94238 + 1.15651 * size_MiB`.
The three per-round slopes remain 1.1103--1.1836 ms/MiB. The intercept is not a
measured NAND command latency. Different extents and byte-proportional OS work
are included. Do not transfer its fitted percentages to the production process.

## Identical byte ranges, different request counts

The preserved recipes allow a stronger same-range comparison without another
console execution. For each round, mode 1 reads 16 consecutive 4 MiB extents
starting at 64 MiB; the first eight mode-2 reads are the corresponding 8 MiB
extents. Each pair of mode-1 reads exactly tiles the same file bytes as one
mode-2 read. This yields 24 identical-extent comparisons in three rounds.

| Round | Two 4 MiB calls | One 8 MiB call | Time reduction with half as many calls |
|---|---:|---:|---:|
| 0 | 11.02040 ms | 10.21847 ms | 7.277% |
| 1, reverse order | 11.38455 ms | 10.07561 ms | 11.497% |
| 2, sampler off | 11.04536 ms | 10.27527 ms | 6.972% |

Reducing the call count by 50% saves about 7--11.5%, while keeping the byte
range identical. Under the descriptive model `T = N*L + bytes*C`, the inferred
per-call term is 0.770--1.309 ms; the byte-dependent part is 77--86% for the
4 MiB calls and 87--93% for 8 MiB calls. This is a helper-scope estimate, not
an exact current application or device decomposition. Request granularity can
also change internal I/O splitting, so the difference is not pure syscall cost.

The serial 3 MiB pair versus the single coalesced span is retained only as an
auxiliary observation: those recipes use different byte ranges. It is explicitly
excluded as a pure request-count intervention.

## Diagnosis and implications

Measured facts are the large per-token source volume, the current normal
application's approximately 92% source-wait share, the size/time scaling, and
the modest saving from halving requests over identical bytes. Together they
support prioritizing **fewer physical bytes per accepted token and better
effective delivery of those bytes**. Request merging remains useful, but these
controls do not support treating fixed per-request latency as the main cost.

The existing 512 MiB layout, qualified range scheduling, owned-bank delivery,
cache and causal width-two path are already enabled. This diagnosis does not
reopen unchanged tested losers. Wider adaptive verification remains subject to
its separately recorded normal-application adoption gate. More useful cache
reuse or shared Expert reads across accepted tokens would target the dominant
cost; shader-only savings leave most source waiting intact.

The closed kernel path was not instrumented internally. Byte-proportional BFS
mapping, DMA and kernel costs cannot be separated from hardware transfer time
by these records. Therefore **byte-volume-dependent I/O dominates** is the
supported conclusion; **the physical SSD has reached its bandwidth limit** is
not established. The scope is two fixed counting requests, not general reasoning
or sustained service.

## Reproduction and provenance

Run the read-only host analysis against the preserved evidence directory:

```powershell
python -B tools/analyze_read_latency.py --data-root D:/PS5-AI/qwen-flash-next --output docs/read-latency-attribution-20261029.json
```

The script reads completed case 436, its build 435 recipes, the public aggregate,
all normal-application case-7080 token records and completed case-7420 placement.
It has no network or console execution code. Required identities, count/extent
geometry, original raw hash, monotonic counters and positive completion are
checked before producing the aggregate. No private path, owner identifier,
endpoint or credential is included in the report.

Relevant implementation is `native/qwen_flash_next/source_contention_probe.c`
(`PROBE_SCHEDULE` and the completed `PAIR` intervals),
`native/app/paired_source_io.h`, `native/app/mapped_source.h`, and
`tools/performance_result.py`. Original CPU scope is documented in
[the source schedule report](source-schedule-performance-20261024.md) and
[its aggregate](source-schedule-cpu-20261024.json).
Current production qualification is in
[the final proposal report](remaining-validation-20261029.md).
The driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`;
persistent shader/pipeline caches remain disabled.
