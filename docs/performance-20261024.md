# Original-precision performance work

## Completed result

The three-step performance work plan completed on the physical PS5. Tested
application revision: `86b645623f3de13fd49ad6e2b295565219729be7`; SELF:
`24cd22bbba24223eab5be01412294c33a83a4d5a380cd028acd66dec1983e344`.
See [the sanitized result](source-pipeline-success-20261024.json).

| Fixed external request | Profile control tokens/s | Pipeline tokens/s | Control TTFT | Pipeline TTFT | Control total | Pipeline total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First, initially empty expert cache | 0.282978 | 0.285184 | 105.237 s | 104.248 s | 182.934 s | 181.342 s |
| Second, retained expert cache | 0.287113 | 0.289577 | 102.766 s | 101.808 s | 179.392 s | 177.750 s |

Both returned the exact same counting response and 22 tokens. Mean decode rate
rose from 0.285046 to 0.287381 tokens/s: **0.82% in this two-request comparison**.
Against the earlier non-profile functional control, the observed difference is
only **0.24%**. These small fixed-request measurements do not establish a
statistically significant or general throughput improvement. Source I/O remains
the dominant cost. Arithmetic also completed with exact output `4`.

The source-path read/wait interval fell from 158.595 to 156.500 s in request 1
and from 155.781 to 153.633 s in request 2, with identical original payload bytes.
Worker dispatch totaled 0.263 / 0.257 s; worker reads totaled 78.953 / 77.510 s.
The worker diagnostics overlap producer consumption and must not be added to
decode time. These are CPU wall intervals, not GPU hardware timestamps.

The adopted bounded implementation uses the same 8 MiB Direct source window,
split into two halves. The producer reads one known miss; the CPU worker reads
the next while the producer completes the first synchronous backend upload.
There is **at most one outstanding read**. Native simultaneous reads are rejected.
Unknown reads retain their owner/backing; failed consumers retain the window;
no operation is retried. All original BF16/F32 tensors, experts and PLE remain.

Passive kernel-memory backpressure retains the original predicate and reserves:
100 ms observations, a 20 s boundary limit and a 60 s whole-process wait limit.
The successful run recovered one pressure event after 0.400 s, without retrying
I/O/inference/GPU work, reclaiming pages or reducing any reserve. CPU heap peak
stayed 436,273,152 bytes (416.0625 MiB), with zero libc fallbacks. Post-load device
peak stayed 945,815,552 bytes. No memory allowance or read buffer was enlarged.

Actual 1920x1080 passive native frames were viewed. All outputs, source-window
completion, positive GPU/model retirement and worker shutdown passed. The title
was normally closed; the exact original SELF was restored, numerically
readmitted, normally closed and fully read back after fresh final CPU guards.
No native owner or model remains. The finite parent ended normally, all frozen
inputs matched, and no retry, force-kill or reset occurred. The task reservation
is retained. General release, CI and persistent shader/pipeline caches remain off.

The precise kernel/filesystem cause of the rejected two-read regression has not
been isolated. Its completed arithmetic read interval rose 81.865 -> 237.555 s
for the same source bytes. Separately, a memory refusal was observed before any
I/O worker or Vulkan initialization. These observations do not prove a worker
leak, a particular filesystem defect or isolated GPU compute latency. See the
[two-read refusal](source-concurrency-refusal-20261024.md) and
[pre-worker observation](pre-worker-memory-refusal-20261024.json).

## Reproduce focused host checks

The checked-in runner exercises the actual single-read worker/consumer overlap,
exact bytes and EOF, fixed-window canaries, failed/unknown-read retention, memory
recovery deadlines/total budget, and the actual compiled cache upload loop. Its
timeout case runs only in a synthetic host subprocess. It also compiles the PS5
source/memory providers and checks completed measurement records. It performs no
console access or learned host inference.

```powershell
python tools/check_source_pipeline.py --workspace C:/Users/User/ps5-ai --out D:/PS5-AI/qwen-flash-next/source-pipeline-check-new --model-io-manifest D:/PS5-AI/qwen-flash-next/build/model-io-pipeline-source-345/manifest.private.json
```

The output directory must be fresh. The selected local engine/SDK artifacts are
not redistributed. A host check does not admit a console launch.

## Historical development record

The following queue, intermediate pending statements and refusals are preserved
as development history. The completed result above supersedes pending status;
every failed artifact and consumed intent remains retained.

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

The next refusal occurred before source reservation, worker creation and Vulkan:
kernel free pages were 1,064 against an unchanged required 898 + 256 = 1,154.
The metadata phase still contained a direct predicate before backpressure was
enabled. It is separate evidence that parallel source reads are not necessary
for this memory refusal. The CPU-only title was normally closed; exact original
restoration, fresh CPU and full SELF checks passed. The same-boot preceding
original numerical admission was preserved without another GPU fixture. See
[the sanitized observation](pre-worker-memory-refusal-20261024.json).

CPU runtime/clock admission now occurs once after candidate/receipt verification
and before model metadata. The unchanged bounded wait is enabled there. Each
completed container-metadata read checks the original CPU/system predicate, and
the pre/post source-reservation checks use a fresh admitted observation. The
original kernel predicate and native sysctl observer bodies are byte-identical
to the pre-backpressure implementation. No additional GPU work, source read,
quantization, reserve change or wait allowance is added. The affected native
entry compile, link/import and SELF checks passed. Physical comparison remains
pending.

The early-admission candidate completed arithmetic and external request 1. That
request measured 0.285474 tokens/s, 104.157 s TTFT and 181.164 s total, versus
0.282978 / 105.237 / 182.934 in the profile control. Source producer read/wait
fell from 158.595 to 156.286 s; worker dispatch totaled 0.258 s and worker reads
78.987 s. This is a small single-request difference, not a qualified whole-plan
speedup. It supports source I/O rather than thread dispatch as the main cost.

External request 2 completed prefill and its first sample, then failed the
unchanged kernel predicate before its next work boundary. Two pressure episodes
recovered; the third reached the 2 s boundary limit. Cumulative waits were
3.302 s. Ordinary close, exact original restoration, numerical readmission,
ordinary shutdown, final CPU and full SELF checks all passed. Preserve
[the failed result](bounded-memory-refusal-20261024.json); no request was retried.

Recovery policy v2 changes only passive wait time: 20 s per completed boundary,
60 s cumulatively, still using 100 ms observations and the exact original memory
predicate. The boundary allowance matches the existing pre-integrity CPU wait.
It does not retry I/O/inference/GPU work, release resources, reclaim pages or
reduce reserves. A deadline, invalid observation or invalid clock still
quarantines the graph. Host recovery/deadline/total-budget/no-retry checks and
affected native compilation passed; complete physical qualification is pending.

## Subsequent completed performance results

The [single-read pipeline sequence](source-pipeline-success-20261024.json)
completed all physical and restoration gates. The later
[file/range schedule sequence](native-source-schedule-success-20261025.md)
also completed the entire plan, including original numerical readmission and
final idle/full-readback checks. Its two rates were 0.332877 / 0.337782 tokens/s,
with a 16.68% mean observed gain over the matched single-read control. This
supersedes earlier pending physical status; the reports retain each candidate's
scope, cache conditions and measurement limits. Neither completed sequence is
to be replayed, and general execution/release/CI remain disabled.
