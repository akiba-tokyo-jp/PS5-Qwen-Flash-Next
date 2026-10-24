# File/range source schedule candidate

The owner requested implementing the source-bandwidth proposal and comparing it
on the physical PS5. The candidate retains all BF16/F32 weights, experts and PLE,
the 8 MiB Direct source window, every CPU/device/system budget and reserve, driver
872cc1264ad8ba5d6b888b092968fa5858a38c58 with cumulative-idle and native archive
b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925. Persistent
shader/pipeline caches, CI and general deployment remain disabled.

## Implementation

Expert IDs are already sorted by the existing cache planner; that is preserved.
No speculative expert or new payload buffer is introduced. The candidate adds:

- Selected parallel reads only for complete aligned ranges inside one 1 GiB
  region, inset by 4 MiB on both sides. Same-inode aliases retain the same-region
  restriction; different files must share the qualified device. Unknown or
  excluded combinations use the existing one-read consumer pipeline.
- A single coalesced read for two adjacent original experts even when their cache
  destination slots are separate. Both consumers retain their exact original
  offsets and destinations; the full read fits the same 8 MiB window.
- A private first-generation policy and a pre-Vulkan CPU check of both actual
  candidate paths against completed serial reference-byte digests. Default
  source behavior remains at one read without this explicit policy.
- Completed physical-read byte/call counters, separate from required logical
  bytes, so aligned or merged reads cannot inflate a useful-throughput claim.

Unknown reads or failed consumers retain the worker, source lease and backing.
There is no operation retry, force-close, memory reclamation or reserve reduction.
The 1 GiB restriction is an empirically qualified candidate policy, not a claim
about a proprietary BFS implementation or universal safety on other firmware.

## Completed CPU-only qualification

The finite physical control completed 768 pairs across three counterbalanced
rounds, with the last sampler disabled. It used the application's actual C++
selector/executor, the sealed source files and unchanged 8 MiB Direct window.

| Pattern | Mean time | Sampled returned-byte rate |
| --- | ---: | ---: |
| Sequential 4 MiB | 5.5751 ms | 0.7523 GB/s |
| Sequential 8 MiB | 10.2031 ms | 0.8222 GB/s |
| Single coalesced-size span | 8.1733 ms | 0.8038 GB/s |
| Serial same-region pair | 8.8674 ms | 0.7428 GB/s |
| Selected same-region pair | 6.9894 ms | 0.9423 GB/s |
| Selected distinct-file pair | 6.9500 ms | 0.9477 GB/s |
| Excluded cross-region pair, serialized | 10.0091 ms | 0.6580 GB/s |

Both inset edges, excluded adjacent edges and an extent crossing the region
selected the expected branch. The second file also passed the same-region
parallel control. Exact return counts, positive worker/observer joins, source
identity revalidation, Direct release and fresh before/after idle CPU guards
passed. No title, model or GPU was started. The original title, numerical
readmission, boot/services and held reservation were unchanged.
See [sanitized CPU measurements](source-schedule-cpu-20261024.json).

This ordinary CPU-helper path did not approach the SSD's nominal 5.5 GB/s.
Those measurements cannot predict the loaded native application's absolute
bandwidth or tokens/s. A single distinct matched native comparison is required,
including all three requests, actual frames, positive retirement, ordinary close,
exact original restoration/numerical readmission/shutdown and final verification.
Native execution and performance adoption are pending.

## First native admission refusal

The distinct artifact at source `2c7b39d`, SELF
`92f83670e9f8e110d6ad97aa452f095c3fc4ae1e13acc05ee7f53076263a34d0`,
refused the unchanged kernel threshold during metadata checks, before source
reservation, worker startup, Vulkan, model loading or any generation request.
Free pages fell from 2,140 initially to 1,089, below the required 1,154. Its
20-second boundary wait expired; no operation was retried.

The finite parent ended with all 197 frozen inputs unchanged. Known pre-GPU
failure/fatal records preceded ordinary OS close, exact original restoration,
full original SELF readback and fresh idle CPU checks. The preceding same-boot
original numerical admission remains preserved; no additional GPU launch was
needed after this CPU-only refusal. No native owner/model remains.

The next distinct artifact requires the observed kernel free target before
metadata, sharing the unchanged 20/60-second passive wait budget. A separate
finite metadata-only launch gate requires target + 1,024 pages for ten consecutive
100 ms samples before publication/launch. An initial no-allocation observation
found 5,668..5,672 free pages against 3,998 required, with unchanged boot/services
and original title. Neither gate relaxes the original work-boundary predicate or
reserves. The refused artifact/intents will not be replayed.
