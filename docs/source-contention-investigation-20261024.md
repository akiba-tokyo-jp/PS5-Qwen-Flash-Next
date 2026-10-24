# Source-read contention investigation

The owner requested the internal cause of the rejected two-read regression.
The original completed arithmetic read/wait interval increased from 81.865 to
237.555 seconds for the same 123,411,118,080 logical bytes. This is the target
regression; an unrelated small I/O test is not sufficient to explain it.

The completed native trace and subsequent CPU-only interventions now isolate
the trigger: concurrent reads into different approximately 1 GiB offset regions
of the same BFS-backed file amplify kernel I/O waiting. Independent opens of
that file do not remove the slowdown. Distinct files and same-region reads do
not show it in the measured controls. GPU work is not required to reproduce it.
This identifies an actionable filesystem access conflict, not a proven name or
implementation of a proprietary kernel lock. Production remains at one read.

## Completed isolated CPU controls

All completed controls used the physical PS5, the same 8 MiB CPU Direct window
and the actual `libkernel` pread/synchronization providers. Fresh idle CPU guards
passed before and after. The original application was never changed or launched;
there was no model loading, Vulkan initialization or GPU work. Every I/O worker
was positively joined and the source window was positively released.

| Control | Serial pair mean | Parallel pair mean | Result |
| --- | ---: | ---: | --- |
| Separated 4 MiB reads, C worker | 11.267 ms | 8.889 ms | Regression absent |
| Actual expert geometry, C worker | 9.116 ms | 7.384 ms | Regression absent |
| Actual expert geometry, application C++ executor/runtime | 8.954 ms | 7.172 ms | Regression absent |

The expert-geometry suites each completed 528 pairs across three counterbalanced
rounds. They compared the same descriptor, independent opens of the same file,
different files and adjacent experts sharing an aligned 16 KiB source page.
The final round disabled wait-channel sampling. No case reproduced the earlier
threefold full-model regression. Actual C++ no-read handoff averaged 0.03293 ms.

Bounded original GGUF header inspection found 3,276,800-byte BF16 experts and
3,293,184-byte aligned reads. Leading skips were 2,784 / 1,632 bytes in the two
selected tensors. Adjacent expert reads overlap one 16 KiB alignment page. That
overlap alone did not cause the target regression in the completed controls.

The supported PID metadata sampler identified the actual producer thread and
recorded `BfsClSs1`, `BfsClSs2`, `BfsPWtFr`, `BfsIpInd`, occasional `nsid1_wa` and
`getblk`, and relatively few `ucond` samples. These are measured wait-channel
names, not documented semantics of proprietary filesystem functions. The C and
C++ expert suites had 1,997 / 1,981 successful sampler calls and zero errors.
An earlier INC_THREAD variant failed every query; it has no qualified wait-channel
evidence. Preserve those failures separately.

The standalone CPU process has neither the native application's namespace nor
its model, protected mappings and GPU allocations. Its favorable parallel result
does not prove that the loaded native process has the same behavior. In particular,
the earlier claim that thread handoff was small was initially based on the adopted
single-read pipeline, not on isolated timings of the failed two-read session.

## Bounded native diagnostic implementation

The optional private policy records 32 positively completed production pipeline
pairs, one every 512 completed pairs, across the actual arithmetic request's
file/layer stream. Only file indexes, offsets and byte counts are retained.
There is no extra model payload buffer and no predicted expert access.

After exact arithmetic output `4` and a fresh positive GPU completion boundary,
the diagnostic holds the existing 8 MiB source lease and replays that exact trace
in counterbalanced no-read, serial, parallel and serial controls. It uses the
existing persistent application C++ worker and the same eight-descriptor cache.
Each real read retains the original Flexible/kernel admission and passive wait
bounds. No I/O operation is retried. Unknown reads retain the entire lease.

Per-read wall/CPU intervals, voluntary switches, return counts, post-read wait,
raw memory observations and supported PID wait channels separate syscall waiting
from completion handoff in the loaded native process. Page samples are compared
after positive completion; this is explicitly not a full-payload hash comparison.
The final round disables the sampler as an observation-overhead control.

Production inference still permits at most one outstanding read. The diagnostic
permits two only inside the explicit, finite private policy and a quiet source/GPU
boundary. Driver 872cc1264ad8ba5d6b888b092968fa5858a38c58, cumulative-idle, all
BF16/F32 tensors, all memory limits/reserves and disabled persistent caches remain.
No new GPU commands are part of the diagnostic.

Host trace capture/replay, identity/reserve, failed-lease and unchanged production
pipeline/cache controls precede native link/import/SELF checks. The distinct
physical candidate must still complete all three requests, actual native frame
review, positive retirement, ordinary close, exact original restoration,
numerical readmission, ordinary shutdown and final CPU/whole-SELF verification.
The completed physical results below supersede the initial pending status.

## Completed loaded-native comparison

Native source `de84978fdde599e4018b955c0eaae019009c9c3a` and SELF
`09d87b0ddb6c5bcff3072da5c72e857543fab5021275d5fde15298cb773e61bb`
completed the diagnostic and the full surrounding physical plan. The existing
seven engine overlay objects were unchanged. Focused trace/pipeline/backpressure,
provider/import and patched cache-loop controls passed before native link,
actual module-import and six-segment SELF checks.

The exact 32 completed pairs span 27 source files. Each mode replays the same
geometry, with three counterbalanced rounds and the final sampler disabled.

| Loaded-native mode | Mean wall time per pair |
| --- | ---: |
| No-read C++ handoff | 0.0236 ms |
| Serial before | 4.6691 ms |
| Parallel | 17.6888 ms |
| Serial after | 4.5554 ms |

Parallel mean syscall wall times were 17.5514 / 17.6343 ms, while thread CPU
times were 0.6949 / 0.6837 ms. Dispatch averaged 0.0115 ms and the interval after
worker completion about 0.043 ms. The expensive interval is inside completed
`pread`, not worker startup or the application condition-variable handoff.
All counts and sampled pages matched; this was not a full-payload hash test.

The slowdown is concentrated in seven pairs, at trace indexes 1, 3, 5, 6, 14,
21 and 30. All seven access different 1 GiB start-offset regions of the same
file. Their parallel mean is 69.9267 ms, versus 5.1271 / 4.9300 ms serial.
The other 25 pairs have starts in the same region: 3.0621 ms parallel versus
4.5409 / 4.4505 ms serial. This separation repeats in all three rounds,
including the round without sampling. A long seek distance within one region
is not sufficient to trigger the slowdown.

The sampler completed 1,551 PID queries with zero errors or unmatched producer
threads. Parallel samples include `BfsIpInd` (427) and `nsid1_wa` (432), compared
with six `ucond` samples. These labels corroborate filesystem/storage waiting;
they do not document what an internal function or lock does. Kernel free pages
remained above the unchanged required 1,154-page predicate; parallel observations
were 1,854..1,884 pages. The later CPU-only intervention separates this from
the loaded process's GPU allocations and low-headroom context.

See [the sanitized native result](source-contention-native-20261024.json).

## Causal boundary and file-identity interventions

The next finite control used the application's exact C++ executor/runtime,
three read-only `O_DIRECT | O_NOFOLLOW` descriptors, the same 8 MiB Direct window,
and two already sealed GGUF files. There was no title launch, model load,
Vulkan initialization or GPU work. It completed 720 pairs across 15 modes.
Each mode has 16 pairs in each of three counterbalanced rounds; the final round
disables sampling. Each syscall requests 3,293,184 bytes, entirely inside its
selected region. Pair offsets advance by 16 KiB within that region.

| Access pattern | Base offsets, MiB | Serial pair | Parallel pair |
| --- | --- | ---: | ---: |
| Same file, same region | 1000 / 1016 | 9.0986 ms | 6.9711 ms |
| Same file, across 1 GiB, same fd | 1016 / 1032 | 9.9941 ms | 49.2425 ms |
| Same file, across 1 GiB, independent opens | 1016 / 1032 | 9.9615 ms | 49.4295 ms |
| Distinct files, offsets on opposite sides of 1 GiB | 1016 / 1032 | 8.8295 ms | 6.9194 ms |
| Same file, distant offsets in one region | 640 / 1000 | 8.9391 ms | 6.9621 ms |
| Same file, across 2 GiB | 2040 / 2056 | 9.9429 ms | 49.1094 ms |
| Same file, across 3 GiB | 3064 / 3080 | 9.8805 ms | 49.2411 ms |

This intervenes on file identity, offset region and descriptor sharing, rather
than relying on correlation in the native trace. No-read handoff is 0.0353 ms.
All 7,679 sampler calls succeeded. Slow same-file parallel modes show `BfsIpInd`
and `nsid1_wa`; the fast same-region/distinct-file parallel modes have no
`BfsIpInd` samples in this run. The sampler-disabled round retains the effect.

A second finite CPU control completed 912 pairs across 19 modes. It repeated
the controls and added same-file cross-region reads on the second GGUF file:

| Second file pattern | Serial pair | Parallel pair |
| --- | ---: | ---: |
| Across 1 GiB | 9.9340 ms | 48.8006 ms |
| Across 2 GiB | 10.0680 ms | 48.8903 ms |

The original-file cross-1-GiB result repeated at 49.8951 ms, independent opens
at 48.5258 ms, and distinct-file parallel reads at 6.9146 ms. All 10,912 sampler
calls succeeded. `BfsIpInd` samples in the slow modes have sleeping state 3.
The own-process metadata interface returned zero `ki_wchan` values, so anonymous
wait-object labels are all zero. This does **not** establish wait-object equality
or prove a particular per-inode mutex. No raw kernel address was logged or
dereferenced. Further raw kernel inspection is not part of this investigation.

Both CPU controls positively joined the executor and observer, revalidated all
source identities, released the Direct window, and passed fresh idle CPU guards
before and after. Original title bytes, numerical-readmission evidence, boot,
services and reservation remained unchanged. No read or helper was retried.
See [the sanitized causal controls](source-contention-causal-controls-20261024.json).

## Attribution and remedy

The supported conclusion is same-file, cross-region BFS I/O wait amplification.
The leading explanation is contention or churn in per-file indirect mapping
state, consistent with `BfsIpInd`, the approximately 1 GiB trigger, independent-fd
failure and distinct-file success. The closed kernel implementation was not
inspected: cache size, eviction algorithm and exact lock ownership remain
unproven. The tests do not establish an exact safe boundary near 1 GiB, or safety
on other firmware/filesystems. A start-offset shift alone is not a qualified
production parallel-admission rule. Both complete aligned read ranges matter.

This finding explains the rejected two-read access pattern. It does not explain
the historical mmap freeze, every memory refusal, or all model latency. The
completed diagnostic is not an end-to-end speed candidate.

The qualified workaround remains one outstanding read with source/consumer
overlap. The best next candidate is file/region-aware scheduling, with cross-region
same-file reads serialized and only separately qualified combinations considered
for parallel execution. Independent fds are ruled out as a remedy. Repacking
weights into smaller distinct files is a later possibility, not a measured
whole-model fix, and would need a new exact-byte integrity/transfer plan.
See [PS5-specific source I/O research and candidate selection](ps5-source-io-workarounds-20261024.md).

## Complete physical lifecycle

The native session generated exact arithmetic `4`, then both planned external
counting responses with 22 tokens each. Both actual native frames were viewed.
Positive GPU/model/source/worker retirement, ordinary OS close, exact original
SELF restoration, numerical readmission, ordinary shutdown, fresh final CPU
guards and complete original SELF readback all passed. The finite parent ended
normally and all 194 frozen inputs were verified unchanged before further edits.
The subsequent CPU controls left that restored title untouched. No native owner
or loaded model remains. The reservation is held; release, general console flags
and CI remain disabled. Original precision, memory limits/reserves, driver
revision/profile/archive and persistent-cache policy are unchanged.
