# All-Expert Q2 bottleneck verification

The dominant measured cost remains routed Expert delivery from storage. This
analysis reuses completed PS5 case 8780 and corroborates it with quality case
8700. It starts no helper, title, model or GPU work and changes no production
file. The selected production remains the mixed model; these all-Q2 results
describe the faster tested candidate pending its normal-app qualification.

| Timed request | Decode tok/s | Whole model-process s | Whole source-wait s | Wait / process | Physical GB/request | Physical calls/request |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.030974 | 38.069 | 31.781 | 83.48% | 21.707681 | 41,492 |
| 2 | 1.031299 | 38.056 | 31.746 | 83.42% | 21.707681 | 41,492 |

Pooled source wait occupies **83.45%** of model-process
time and **81.07%** of complete request wall time. The
whole-request counters include prompt processing and final EOS work. The
**1.031136 decode tok/s** figure instead uses 21 accepted transitions,
excluding prefill and EOS. Do not describe the whole-request wait percentage as
an exact decode-only percentage.

The existing token records do not contain per-token source counters. A
conservative timer bound still proves that at least
**63.59% of accepted decode wall time** must be producer
source wait in this cohort: with total wall T, whole source wait W and decode
wall D, decode wait is at least max(0, W - (T - D)). This is a bound derived from
non-overlapping nested producer intervals, not a new exact decode measurement.

## Weight volume and cache

Each timed request reads 21,707,681,216 physical bytes and
requests 21,060,628,480 logical payload bytes. Exactly
21,060,096,000 logical bytes reconcile to
13,711 Expert cache misses times the 1,536,000-byte triplet.
Expert payload therefore accounts for **99.997472%** of logical streaming.
The remaining 532,480 bytes equal
52 evaluated model tokens times the original 10,240-byte
token/PLE row payload. There is no unclassified logical payload.

The 867-slot cache records 6,303 hits and 13,711 misses,
a **68.51% miss fraction** among unique per-batch demands.
This denominator differs from raw top-10 selections: the batching path already
removes repeated selections within a batch. Physical alignment/envelope overhead
is 647,052,736 bytes per request. Mean physical request size is
510.92 KiB. Effective physical bytes per producer wait are
0.683 GB/s, including filesystem, kernel and scheduling time.
It does not measure raw NAND/controller bandwidth or isolated per-command latency.

| Historical same-console format | Active slots | Decode tok/s | Whole wait / process | Whole physical GB/request | Unique-demand miss fraction |
| --- | --- | --- | --- | --- | --- |
| Q4_0 | 481 | 0.871504 | 83.88% | 44.919764 | 79.69% |
| Gate_Up_Q2_K_Down_Q4_0 | 581 | 0.913361 | 83.61% | 31.416047 | 76.77% |
| Gate_Up_Q2_K_Down_Q2_0_MSE | 867 | 1.031136 | 83.45% | 21.707681 | 68.51% |

The counting prompt and 22 generated tokens / 21 accepted transitions match.
Precision, routes and cache representation differ, and controls were collected
earlier. These observations support reduced streaming volume; they are not a
simultaneous ABBA intervention isolating byte volume from cache/route changes.
Relative to the mixed cohort, whole-request physical bytes fall
30.90% and decode throughput rises
12.89%. Mean physical requests shrink from
662.94 KiB to 510.92 KiB, while effective delivery per
producer wait falls from 0.873 to
0.683 GB/s. These observations motivate testing request
granularity and delivery efficiency at the actual compressed sizes; they do not
causally assign the difference to fixed syscall or hardware command latency.

## Other measured costs and non-Expert weights

For timed request 1, source headroom checks total 1.081 s,
source handle work 0.234 s, and source-consumer intervals
1.175 s. After these intervals and source wait,
3.798 s remains inside model-process calls.
Neither the consumer interval nor the remainder is a pure GPU/dequantization
measurement. Existing validation/monitoring is retained. Overlapping worker
read times are not added to producer time.

Stored non-Expert tensors total 112,610,847,232 bytes,
including the 102,400,491,520-byte PLE table and
1,271,398,400-byte token embedding. Stored size is not
per-token traffic. The completed model-load upload is
8,755,105,280 bytes, separately from decode streaming.
Non-Expert logical traffic is tiny; this all-Q2 candidate does not separately
measure its physical-read amplification or wait. Earlier Q4-only percentages
must not be transferred to all-Q2 as new measurements.

## Next optimization targets

1. Reduce Expert cache misses or share already fetched Expert payload across
   useful accepted work; most requested payload remains Expert data.
2. Improve delivery of the remaining miss bytes, including packing, request
   aggregation and real I/O/compute overlap, using a fresh finite comparison.
   The current counters cannot distinguish SSD service from the OS I/O path.
3. Profile GPU dequantization/GEMV separately before treating it as the next
   dominant bottleneck. Shader-only work leaves the measured source wait.
4. Investigate non-Expert resident compression as a way to free Expert-cache
   capacity if desired; it is an indirect hypothesis, not a demonstrated
   reduction of the dominant streaming bytes.

No speed improvement is claimed from this analysis. Normal all-Q2 monitor/API
qualification and final placement remain separate pending work. Driver
872cc1264ad8ba5d6b888b092968fa5858a38c58 / cumulative-idle, disabled persistent
caches, memory/owner/completion guards and all rollbacks remain unchanged.

## Counter and timing definitions

- [Source reader](../native/app/mapped_source.h): `read_window`,
  `read_pair_windows`, `pipeline_windows` and `completed` define producer waits,
  aligned physical envelopes, handle/headroom work and consumer lifetimes.
- [Engine timing](../native/app/llama_engine.cpp): the `llama_process` scope
  encloses source and backend work; synchronization is a separate interval.
- [Request timing](../native/app/first_generation.h): `FirstGeneration::run`
  measures decode from first to last accepted generated token and completes
  final EOS/reset work before recording total request time.
- [Counter aggregation](../native/app/native_main.cpp): `performance_snapshot`
  and `performance_difference` retain producer-wait semantics and explicitly
  identify overlapping worker timings and the absence of GPU timestamps.
- [All-Q2 derivative](../tools/expert_all_q2_model_source.py): `entry_source`
  validates miss bytes against the 1,536,000-byte Expert triplet.

Reproduce with `tools/analyze_expert_q2_bottleneck.py --cache <private-data-root>
--json docs/expert-q2-bottleneck-20261029.json --markdown
docs/expert-q2-bottleneck-20261029.md`. The JSON binds whole captured evidence
digests without publishing private paths, endpoints, PID or run bindings.
