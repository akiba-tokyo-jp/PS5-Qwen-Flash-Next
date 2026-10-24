# Original-precision performance work

The owner authorized speed improvement after the complete physical plan passed.
The immutable control is application source
`701f474cb8ca94dae5c854f080f3ec972d0d0c26`, SELF
`cb775555fd7423738cc6ef53efa760362c8b1c384ef2574b5b5797295bccbb3b`.
Its two counting requests measured 0.284548 / 0.288819 tokens/s and
104.619 / 102.145-second TTFT. See the
[complete result](native-full-generation-success-20261024.md).

The second request added 1,170 expert-cache hits and 23,790 misses, with
233,865,216,000 uploaded expert bytes. Transfers are a candidate bottleneck;
these counters alone do not establish elapsed storage or GPU time.

## Execution queue

1. Add bounded aggregate source-headroom, descriptor/identity, direct-read and
   consumer intervals; separately measure decode calls, synchronization, positive
   checkpoints, work guards and explicit stage-observer time. Preserve every
   existing guard and GPU operation. Perform affected host checks and native
   link/import/SELF checks, reusing the seven unchanged engine objects.
2. Use one distinct guarded physical session with the same arithmetic and two
   external requests. Reuse sealed same-boot data integrity without conversion,
   transfer or another whole-model hash. Collect validated per-request counters,
   actual native frames and the complete restoration/readmission boundary.
3. Change the concrete largest measured cost, one mechanism at a time. Retain
   original BF16/F32 tensors, every required expert/PLE, the selected driver and
   cache policy, and all current memory limits. Compare the same requests/cache
   conditions through positive retirement and original restoration. Adopt only
   a completed measured improvement with unchanged smoke answers and ownership.

The first candidate adds instrumentation; it makes no speedup claim. It appends
three completed metadata reports, without per-chunk logs or new GPU commands.
Source consumer time covers the interval from a prepared read window to its
positive completion, including existing CPU copies or backend waits. Decode
process time contains source and backend work; synchronization is separate.
The intervals are nested wall times, not GPU timestamp queries, and must not be
summed as independent totals or described as isolated GPU compute time.

General inference/release deployment, CI and persistent shader/pipeline caches
remain disabled. No retries, force-kill, GPU reset or uncertain resource release
are permitted. Profile completion is an intermediate step of speed improvement.
