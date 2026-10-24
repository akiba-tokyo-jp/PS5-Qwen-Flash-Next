# Physical source-schedule performance result

The complete implementation and physical validation plan finished on one PS5
on 2026-10-25 (Asia/Tokyo). The candidate completed arithmetic `4` and two
external counting requests, with exact output bytes and token IDs matching the
completed single-read control. Mean decode throughput increased from 0.287381
to 0.335329 tokens/s, an observed 16.68% gain. All final retirement, restoration,
fresh original numerical readmission and shutdown checks passed.

## Matched native measurements

| External request | Expert cache | Control tokens/s | Candidate tokens/s | Gain | Control / candidate TTFT | Control / candidate total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Initially empty | 0.285184 | 0.332877 | 16.72% | 104.248 / 89.441 s | 181.342 / 155.528 s |
| 2 | Retained | 0.289577 | 0.337782 | 16.65% | 101.808 / 87.378 s | 177.750 / 152.508 s |

Both external requests used the same fixed counting prompt, 30 prompt tokens,
22 generated tokens, context 256, maximum output 32 and thinking disabled.
Their answer was `1, 2, 3, 4, 5, 6, 7, 8`. The model stayed loaded across all
three requests. The first external request started with an empty expert cache;
the second retained it. File pages and pipelines were not claimed cold.
Decode rate excludes prompt prefill and first-token latency. Arithmetic produced
one token at 78.298 s TTFT and 81.370 s total; one token has no decode interval.
The observer matched the external token streams to durable native results.

The control is the completed [bounded source-pipeline result](source-pipeline-success-20261024.json).
This is one complete matched short-request sequence, without counterbalanced
native repetitions. The improvement belongs to the candidate bundle: its startup
and lossless shader representation also changed. It does not isolate the effect
of one scheduling branch or establish general answer quality, long-context
performance or sustained service.

## What changed and what the counters show

The actual source executor coalesces adjacent original bytes inside the existing
8 MiB window. It permits at most two reads for qualified file/range pairs:
same-file extents stay within one 1 GiB region, inset by 4 MiB; distinct files
must share the qualified device. Excluded pairs retain the single-read pipeline.
No extra payload buffer, speculative expert, file splitting or weight-layout
change was introduced. The existing Strata-style capacity admission and Maya
aged-frequency expert cache remain active; this comparison does not separately
measure either policy's contribution.

| Completed source counter | Request 1 | Request 2 |
| --- | ---: | ---: |
| Logical bytes, identical to control | 238,417,223,680 | 233,826,426,880 |
| Physical read bytes, including alignment | 239,610,767,424 | 234,996,732,224 |
| Physical read calls | 72,890 | 71,474 |
| Selected parallel batches | 29,316 | 28,532 |
| Coalesced batches | 684 | 756 |
| Producer source-read/wait, control -> candidate | 156.500 -> 128.970 s | 153.633 -> 126.722 s |

Producer source-read time includes waiting. Worker and consumer durations overlap
and must not be summed. These counters do not establish nominal SSD bandwidth.
No extra GPU operation, timestamp query or hot-path log was added.

Original BF16/F32 tensors, every expert and required PLE were preserved. Inference
ran on the PS5, without quantization or substitute learned host inference.
The 76 containers still total 359,246,956,672 bytes. Same-boot complete native
integrity plus current sealed identities avoided another conversion, transfer
or whole-model hash pass. Every current virtual reservation/release and both
2,974-page startup gates remained required. The 1,154-page work predicate,
20 s boundary / 60 s process passive waits, 512 MiB CPU heap and 160 MiB
scheduler arena were unchanged. CPU heap peak was 436,273,152 bytes with zero
untracked libc fallbacks; post-load device buffers peaked at 945,815,552 bytes
and returned to zero.

All 1,527 original shaders retain prior direct same-boot byte verification;
this run checked the complete immutable external resource and 382 lookups.
Every actually used module still required current original-byte SHA256.
The external resource contains reversibly stored original SPIR-V, with a separate
49,152-byte tracked input window. Persistent shader/pipeline caches stayed off.

## Display and complete shutdown boundary

Both actual 1920x1080 native frames were saved after positive display completion
and visually inspected. The passive display showed CPU/GPU identity, 16 logical
threads, calibrated UTC, 22 generated tokens, TTFT, total time and 0.33 / 0.34
tokens/s. It has no chat input or controls. Unqualified CPU/GPU utilization remains
`--`; raw driver memory estimates remain diagnostic, separate from native
allocator admission.

The first host controller refused its post-launch owner observation after
returned reads while the native model continued. A separately reviewed fresh
metadata-only owner admission bound the same running title; the continuation
preserved the original deadlines. The app/model was not relaunched and no
generation request was retried. Historical refusals remain preserved.

The complete sequence then passed:

1. Arithmetic and exactly two external generation POSTs with matched results,
   plus both actual native frame reviews.
2. One finish acknowledgement, listener stop, completed source I/O, positive
   GPU completion/worker retirement and model-resource release.
3. Ordinary candidate close and exact original executable restoration.
4. Fresh original numerical readmission, ordinary original shutdown, fresh idle
   CPU guards and complete original SELF readback.
5. Final unchanged boot/service/double-snapshot guards and complete raw original
   readback. The finite continuation ended; all 428 frozen inputs were unchanged.

No native owner, gateway or loaded model remains. No force-kill, GPU reset,
reboot or manual uncertain resource release was used in this sequence. The task
retains its reservation. General execution/release flags and CI remain disabled;
the successful finite validation does not automatically launch a service.

## Pinned build provenance

| Component | Identity |
| --- | --- |
| Runtime implementation reference | `a0f7e589316a87b2a4797e7c829a87d2807a9137` |
| Launch/preservation control source | `886b911e3b8eecd59093b346e08c06aaf5916389` |
| Candidate SELF SHA256 (27,798,695 bytes) | `c354b82c75a4e60f783c80e16485c4132bcd40cb35fb34a62d92e528f57debf7` |
| Application link receipt SHA256 | `9d4bc1bc9db3625c331c04bfc82c3a398e65f445475f6eba85d456f1bc8dc7fc` |
| Driver repository | `akiba-tokyo-jp/PS5-Vulkan-Inference` |
| Driver source / profile | `872cc1264ad8ba5d6b888b092968fa5858a38c58` / `cumulative-idle` |
| Selected shared driver archive SHA256 | `67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9` |
| Relinked native frontend archive SHA256 | `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925` |
| Native platform manifest SHA256 | `1f701e2b64ca117dd6bf8e25d11a90c986179bebf831bf4fba9300930066b6e0` |
| Engine source | `0a1ef309cdbb9f2024f58a38fb4c42352c5db569` |
| Model source | `de4b8e4d43b917e7706784d8bb445c9af86a3540` |
| Original-precision model receipt SHA256 | `d2a0705e0e8d8d5999cf2e6bd9519ccb0654837abcf1ab47d0295030a8bb5495` |
| Restored original SELF SHA256 | `2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d` |

The candidate passed 293 real-module imports with none missing and all six SELF
roundtrip segments. The private link/package receipts retain exact compiler,
header, object and source input provenance. See the
[sanitized measurements](native-source-schedule-success-20261025.json) for complete
metrics and aggregate counters. Raw device identities, endpoints, frames,
binaries, weights and controller evidence remain outside commits.
