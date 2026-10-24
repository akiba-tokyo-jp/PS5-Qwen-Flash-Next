# Source-read contention investigation

The owner requested the internal cause of the rejected two-read regression.
The original completed arithmetic read/wait interval increased from 81.865 to
237.555 seconds for the same 123,411,118,080 logical bytes. This is the target
regression; an unrelated small I/O test is not sufficient to explain it.

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
Native execution and the root-cause conclusion are pending; no cause is yet proven.
