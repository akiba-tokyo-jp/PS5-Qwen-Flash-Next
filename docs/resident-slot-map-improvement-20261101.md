> Status: not adopted. Standalone57400 passed, but full-model57500 did not
> complete its numerical qualification. Exact9824 is restored after an observed
> external new boot; see `SSD-cleanup-20261101.md` / `.json`. The unsafe prototype
> remains refused. No speedup is claimed.

# Measured selection: retain GPU Expert slot maps

The owner authorized measurement, selection and implementation. Current production
remains SELF9824030372e2eed7204275209a9bb6a6700a385ced8f9ca6e40d22fae258c135.
No measured winner has yet been placed by this follow-up.

## Completed diagnosis

Standalone56600 validates 36 synthetic observation graphs, exact bytes/canaries,
positive retirement and ordinary restoration. Model56400 completes 14 requests
with unchanged numerical work and restoration. Its first 40 driver fields are
usable, but its three platform-time fields are withdrawn: the original platform
getter consumes a legacy log window. The corrected overlay preserves every
legacy update/reset and adds independent monotonic counters. Standalone56800
validates another 36 graphs, including counter activation, before model56900.
All titles finish with zero model/source/device ownership and ordinary close.

Model56900 completes 14 requests, exact returned counting work, and the bounded
GPU diagnostic. One query pool is created/destroyed, 111315 role ranges are
drained over 123 calls, and no query remains pending. Retrieval follows the
existing successful completion checkpoint and adds no queue wait.

Two retained diagnostic requests record:

| Measured scope | First ms | Second ms |
| --- | ---: | ---: |
| Complete request | 2300.016 | 2288.112 |
| Accepted decode | 1809.835 | 1796.529 |
| Selected GPU roles, complete request | 419.100 | 417.685 |
| Selected GPU roles, accepted decode | 212.941 | 209.547 |
| Native sequence waiting, inclusive | 653.785 | 650.621 |
| Actual sleeping within waiting | 8.861 | 7.758 |
| Submit lock acquisition | 4.062 | 4.074 |
| Command copying/planning copy interval | 6.335 | 6.334 |
| Native AGC call alone | 25.396 | 25.189 |

The scopes overlap and must not be summed. Role timestamps do not cover every
GPU operation. Busy sequence waiting includes useful GPU work and scheduling.
The native submit-and-log interval is about33 ms; it is not the pure AGC call.
No dedicated command allocation or ring-overlap wait occurs in these requests.
The four-member observation overlay leaves every other driver archive member
identical and changes no allocator ABI, kick protocol, visibility or timeout.

GPU role instrumentation raises retained complete time by about99.705 ms /4.54%
versus its uninstrumented controls. These are diagnostic timings, not a new
production speed or an optimization gain. The performance candidate uses the
original production driver and original GPU/shader provider, without these
observation overlays or timestamp commands.

## Concrete implementation

The actual cache provider's `llama_moe_cache::impl::copy` downloads selected IDs,
synchronizes, runs the authoritative CPU cache plan, loads actual missing weights,
then always uploads a512-entry I32 slot map. Its final upload is the target.
Normal56100's accepted decode has777/1008 layer records with no first-use miss.
In model56900,4423 nonempty native submissions accompany1104 cache-planning
records per retained request. The source proves the unconditional map transfer;
these counts motivate testing its elimination when the contents are identical.

`native/app/resident_slot_maps.h` owns dedicated GPU maps with the same cache
lifetime as the existing Expert banks. Each of49 maps has512 I32 values and64
guard values at either side,125440 logical bytes total. Physical allocation
size and peak ledger must be measured rather than assumed from that payload.
CPU content is compared byte-for-byte against the last accepted publication.
Changed entries, cache resets and cross-layer evictions are detected from the
authoritative complete CPU map. Selected IDs, routing, fills, precision, bank
capacity, source reads and the original completion checks are unchanged.

Publication uses the ordinary backend transfer and binds a contiguous non-view
GPU destination to the dedicated table. Unexpected type/layout/backend uses
the original copy. Every value is checked in[-1,capacity) before dispatch.
Dedicated storage has no graph allocator output aliases; GPU consumers read it.
The existing ID download/synchronization still precedes every publication.

Both internal comparison arms allocate and bind the same dedicated storage.
The control performs every upload; only the candidate omits byte-identical
uploads. This isolates reuse fairly, but this control is not literally the
old application's allocation layout. Final original-normal qualification remains
mandatory; an improvement against a slower new layout alone is not adoption.

## Acceptance and remaining work

1. Standalone GPU I32 lookups must validate unchanged reuse, changed entries,
   rebinding the same graph destination between layers, complete table bytes,
   guard values, successful completion, retirement and ordinary close.
2. The complete model cohort must show actual reused uploads, identical full
   F32/routes/tokens, unchanged source demand and equal model work. Both paired
   retained complete-time savings must exceed control A/A spread. Report
   candidate memory footprint and cold/retained behavior separately.
3. If useful, compose the actual normal/API/display program with the original
   driver, enable reuse explicitly, qualify all three normal request conditions
   and actual native frames, preserve the exact9824 rollback, and verify program
   and settings by complete native readback. Compare against the original app;
   otherwise retain original production and record the candidate as a completed
   negative with its measured reason.

The initial diagnostic's withdrawn fields, host-only preparation namespace
corrections and finite consumed cases stay in private immutable evidence.
No reboot, force-kill, manual GPU free/reset, CI or agent delegation is used.
