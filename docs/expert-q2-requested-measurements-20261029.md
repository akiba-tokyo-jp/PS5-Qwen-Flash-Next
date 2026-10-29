# Requested Q4 versus all-Q2 I/O and compute measurements

## Completed whole-request comparison

These are positively closed PS5 counting cases 7820 and 8780, with the same
30-token prompt and 22 generated output tokens. Each evaluates 52 model input
tokens including prompt and final EOS evaluation. The normalized columns below
include prefill/EOS; **they are not accepted-decode GB/token or calls/token**.

| Format | Physical GB/request | Calls/request | GB/evaluated token, prompt/EOS included | Calls/evaluated token, prompt/EOS included | Amortized producer wait ms/call | Effective GB/source-wait s |
| --- | --- | --- | --- | --- | --- | --- |
| Q4_0 | 44.919764 | 48,037 | 0.863842 | 923.788 | 0.790431 | 1.183035 |
| Gate_Up_Q2_K_Down_Q2_0_MSE | 21.707681 | 41,492 | 0.417455 | 797.923 | 0.765529 | 0.683420 |

Whole-request physical bytes decrease **51.675%**, approximately halving.
Physical read calls decrease **13.625%**, much less than half.
The Expert triplet itself shrinks from 2,764,800 to 1,536,000 bytes, a 44.444%
reduction; metadata means the stored format is not exactly half of Q4.
The larger cache and changed routes also affect actual request traffic.

The mean physical read shrinks from 913.19 to 510.92 KiB.
Producer wait per call changes little while bytes fall sharply. This is
consistent with request/granularity overhead becoming more important at these
compressed sizes. It does not isolate a fixed SSD command delay: runs have
different extents, routing and cache layouts, and two I/O lanes overlap.
Producer wait divided by calls is explicitly an amortized critical-path cost,
not the measured duration of one physical read.

## Exact accepted-decode interval

The existing Q4 diagnostic 8010 measures **1.029585 GB/token** and
**1105.857 calls/token**, using token-1 to token-22
completed-counter differences. Prefill and final EOS are excluded.

Exact Q2 decode-only GB/token, calls/token and individual read latency remain unmeasured. The dedicated measurement SELF is built and import/roundtrip/safety audited, but automatic approval review rejected the new console launch pending explicit owner freeze-risk confirmation. No case launch, GPU work or production change occurred for that attempt.

The new observer records 128-microsecond latency histogram bins and 64-KiB
read-size classes, exact returned bytes/counts and each pread entry-to-return
wall time on both existing lanes. It adds no per-read logs, allocations, GPU
queries, new GPU work, source reads, scheduling changes or modified memory
guards. Static counters occupy 960 bytes. The original independent reader
bytes/calls must match these new counters exactly before results qualify.

## Effective bandwidth and latency diagnosis

Whole-request effective delivery per producer-wait second is
**1.183 GB/s for Q4** and **0.683 GB/s for Q2**.
Sony specifies 5.5 GB/s raw read bandwidth for the original internal PS5 SSD
([official specification](https://sonyinteractive.com/en/press-releases/2020/playstation-5-launches-this-november-at-399-for-ps5-digital-edition-and-499-for-ps5-with-ultra-hd-blu-ray-disc-drive/)). The Q2 software-path ratio is
12.43% of that reference number; it is **not device utilization**.
The actual mount/device sequential throughput has not been measured here.
This path is far below the nominal reference, but physical SSD service, kernel,
filesystem and queue/scheduling costs remain combined. A same-extent,
same-byte-volume request-count intervention at actual compressed sizes is
needed to causally separate fixed request/granularity cost from byte cost.

## Quantized compute, including fused decoding

Existing actual-weight PS5 GPU components provide the following width-one
timings. Q4 case 7560, Gate/Up Q2_K case 8160, and fitted-scale Down Q2_0 case
8600 use layers 0/23/47, ten selected IDs with three unique Experts, independent
own-format F64 references and four timed samples per format/group. Each run
also contains its paired BF16 control. These are historical cohorts.

| Projection | Q4 compute ms | Q2 compute ms | Q2 change |
| --- | --- | --- | --- |
| Gate/Up | 7.197537 | 7.135824 | -0.857% |
| Down | 7.668560 | 7.426239 | -3.160% |

These times include the fused quantized matrix graph, host submission,
synchronization and the original completion checkpoint. SSD delivery is timed
separately and excluded. They are not pure GPU timestamps or standalone decode
timings. In the measured width-one path, the shaders unpack/scale weights
inside matrix multiplication, so there is no separate dequantization pass to
time independently in that path. This does not classify every other graph width.
No fused-graph wall-time increase is observed in these finite samples.
Whole-model process time outside source wait also falls from
7.299 to 6.299 s/request,
but that remainder includes CPU/framework work and must not be labeled GPU-only.

Sources: `native/app/expert_q4_fixture.cpp`, `expert_q2k_fixture.cpp` and
`expert_q2_fixture.cpp` implement `compute`/`measure`; the pinned Vulkan
`mul_mat_vec.comp` performs dequantization inside the matrix loop. The complete
model and source proofs remain in the staged-Q2 report. This report performs
no console or network operations and runs no CI. Production is unchanged.
