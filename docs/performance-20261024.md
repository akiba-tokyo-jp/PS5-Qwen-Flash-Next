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

## Completed profile and selected candidate

The distinct profile session completed all three requests, actual native frame
review, positive resource retirement and exact original restoration/readmission/
shutdown. See [the sanitized counters](performance-profile-20261024.json).
Its two external requests measured 0.282978 / 0.287113 tokens/s. Direct source
read wall time was 158.595 / 155.781 seconds inside 181.311 / 177.761 seconds of
decode processing: approximately 87.5%. These are nested CPU wall intervals,
not isolated GPU time. Source headroom and identity checks remain required.

The selected next candidate adapts known-miss batching from
[Strata's pinned source](https://github.com/Niko1221/Strata/blob/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec/src/core/expert_source.cpp).
It splits the existing 8 MiB Direct source window into two aligned 4 MiB halves.
One persistent CPU I/O worker and the existing producer read two known cache
misses concurrently. No speculative expert is read. Existing contiguous-range
merging and the serial odd/large-range path remain available.

Each pair retains both halves until two exact reads and both synchronous backend
consumers complete. Failed or uncertain work quarantines the pair and retains
its backing; it never retries or publishes completion. The worker passes an
equal-byte CPU preflight before Vulkan initialization and stops only after
positive model/source retirement. No additional read buffer, GPU command,
quantization, matrix fallback, memory allowance or driver/cache change is added.
The v2 read counter measures batch wall time, not the sum of overlapping calls.

Focused host checks passed actual concurrent entry, original-byte and EOF parity,
buffer canaries, exact failure retention and a real worker timeout. The actual
patched cache loop passed paired/serial/contiguous/odd byte comparisons and
consumer-failure controls. Native compilation passed; link/import/SELF and a
distinct matched physical comparison remain required. These host results do not
qualify a speedup. See [the upstream review](strata-update-review-20261024.md).

The two-read physical candidate was subsequently rejected: its completed
arithmetic read interval increased to 237.555 seconds, and its first external
request explicitly failed the unchanged kernel headroom predicate. Exact
original restoration/readmission/shutdown and all final guards passed. Preserve
[this failure](source-concurrency-refusal-20261024.md); never replay its intents.

The next implementation uses two half windows with only one outstanding read.
The producer reads the first window, then the CPU worker reads the second while
the producer synchronously consumes the first. Both read results and consumers
must complete before reuse. A first-consumer exception still waits for the
issued read's known completion; an uncertain read retains both windows. Native
concurrent-read entry is now rejected. Original contiguous/odd/large paths and
all budgets remain unchanged. v3 separates worker read/dispatch diagnostics from
producer read/wait time; overlapping worker intervals are not added to decode
time. Focused actual-worker and extracted-cache-loop controls passed. Link and
physical comparison are pending, so this implementation has no speedup claim.

The first single-read physical candidate completed 26 prefill decodes and its
first sample, including positive GPU idle/worker completion. The next work guard
refused kernel headroom before another GPU boundary. No full request or external
POST completed. Ordinary close, exact original restoration/readmission/shutdown,
final CPU and whole SELF readback passed. See the
[sanitized result](source-pipeline-refusal-20261024.json). Single-read concurrency
alone therefore does not explain or solve the transient admission failures.

The next application adds passive backpressure at already completed producer
boundaries and before unissued source reads. It retains the original kernel
minimum plus max(reserved, 4 MiB) predicate and all other memory allowances.
It only observes independent OS paging, at 100 ms intervals, for at most 2 s at
one boundary and 10 s cumulatively in the whole process. No I/O, allocation,
inference or GPU operation is retried or purged. Every continuation requires a
fresh observation satisfying the unchanged predicate. Invalid metadata, a wait
deadline or failed clock quarantines admission and retains the graph. The
per-boundary and cumulative bounds, exact threshold, failure quarantine and
unhealthy metadata controls passed on the host. Native link and a distinct
complete physical comparison remain required.
