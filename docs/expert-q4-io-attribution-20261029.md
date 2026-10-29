# Post-Q4 I/O bottleneck measurement

A fresh PS5 diagnostic measured the selected Q4 model, 481-slot cache and
original GPU/driver/I/O schedule. Only completed counter observations and
existing token record fields were added. One warmup and two API requests
passed full same-Q4 vocabulary/routes, correct counting, source/model/GPU
retirement and ordinary close. The exact selected Q4 executable and all five
settings were restored and verified; the diagnostic is not adopted.

| Request (0 warmup) | Decode tok/s | Model process seconds | Producer source-wait seconds | Wait / process | Physical GB/token |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.866708 | 23.3524 | 19.1448 | 81.982% | 1.029585 |
| 1 | 0.871416 | 23.2004 | 19.0901 | 82.284% | 1.029585 |
| 2 | 0.871445 | 23.2014 | 19.1083 | 82.358% | 1.029585 |

The interval covers 21 accepted decode transitions per request. Prefill and
final EOS work are excluded by subtracting token-1 from token-22 cumulative
counters. Pooled timed source wait is **82.321%**
of model process time, or **79.255%**
of decode wall time. The latter also contains ordinary reporting/observer work.
Source wait includes filesystem/kernel/scheduling time. It is not an isolated
NAND service-time or raw SSD-bandwidth measurement. Overlapping worker times
are not added; process minus source wait is not labeled GPU-only time.

## Named non-Expert reads in the decode interval

The existing CPU GET_ROWS path exposes its original source tensor name. The
diagnostic brackets those synchronous row reads with existing source counters;
it changes no source offset, read size, number of reads, conversion or routing.
Expert payload comes from the original cumulative cache-upload counter and
is reconciled against complete source logical bytes. Physical bytes include
16-KiB Direct-read alignment. Logical bytes describe requested weight payload.

| Request | Tensor group | Logical bytes | Physical bytes | Physical calls | Source-wait seconds |
| --- | --- | --- | --- | --- | --- |
| 1 | token_embedding | 107,520 | 491,520 | 21 | 0.028737 |
| 1 | PLE_embedding | 107,520 | 5,554,176 | 336 | 0.465128 |
| 1 | other_CPU_rows | 0 | 0 | 0 | 0.000000 |
| 2 | token_embedding | 107,520 | 491,520 | 21 | 0.028631 |
| 2 | PLE_embedding | 107,520 | 5,554,176 | 336 | 0.464390 |
| 2 | other_CPU_rows | 0 | 0 | 0 | 0.000000 |

Named non-Expert rows account for **0.027962%**
of measured physical decode reads and **2.584%**
of producer source-wait time. All logical source bytes classified without a
remainder: **True**.

The complete non-Expert tensor payload is 112,610,847,232 bytes,
including the 102,400,491,520-byte PLE table,
1,271,398,400-byte token embedding and
1,271,398,400-byte output projection.
Stored size is not per-token traffic: selected embedding/PLE rows are fetched
on demand; the ordinary dense weights remain resident after model load.
Model-load GPU upload, excluding the completed fixture, is
8,755,105,280 bytes; this startup
transfer is reported separately from decode streaming.

## Diagnosis and priorities

Routed Expert delivery remains the main measured bottleneck. After removing
the named non-Expert subset, Expert source wait alone occupies
**80.194%** of model process time.
The earlier BF16 normal-application observations were about 92%; the Q4 decode
observation is about 82%. These are serial finite cohorts with different
precision/cache representations, not a same-time paired experiment.

Each accepted token still requires about 1.03 GB of physical reads and 1,106
physical requests, with a mean request of about 0.888 MiB. Effective bytes per
producer source-wait second are about 1.13 GB/s, not a raw hardware bandwidth
reading. This supports a Q4-specific comparison of Expert batching/pipelining
and cache-miss reduction. It does not prove fixed syscall/request latency or
SSD hardware saturation as the underlying cause.

Non-Expert decode I/O is secondary. The PLE table is large on disk but fetches
16 original 320-byte rows/token (5,120 logical bytes); ordinary token embedding
fetches one 5,120-byte row/token. Together they consume 10 KiB of payload and
about 281.14 KiB of physical I/O/token after alignment. Other non-Expert source
payload did not recur in the measured decode interval. PLE small-read alignment
amplification is real, but removing *all* measured non-Expert source-wait time
would produce only an optimistic **1.0209x**
decode improvement with the other observed costs fixed. This is a counterfactual
upper bound, not an implemented cache speedup. Broad non-Expert quantization
would therefore not directly remove the dominant streaming traffic. Freeing
resident memory for more Expert cache is a different, untested indirect effect.

## Scope and reproduction

This is a finite counting diagnosis. It adds CPU counter/record overhead and
does not establish a new speedup. The selected production SELF remains
`98a573396af615f754fe4286c6600ccf5596b8fad9d4ab00b99d7e9295dfd8fa`. Driver revision/profile, precision,
cache budget, memory floors, ownership, completion checks and persistent-cache
policy are unchanged. No reboot or CI occurred.

`tools/build_expert_q4_io_probe.py` derives a separate measurement entry and
adds two counter callbacks around the original CPU row loop.
`native/app/expert_q4_io_profile.h` checks exact logical completion and nested
scope consistency; `tests/expert_q4_io_profile.cpp` checks independent examples
and refuses duplicate/missing/short/incomplete/reversed scopes.
`tools/analyze_expert_q4_io.py` verifies completed native records and writes
this sanitized analysis without a console/network client.
