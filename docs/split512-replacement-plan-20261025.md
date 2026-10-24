# In-place 512 MiB model layout

The owner authorized replacing the PS5 model originals with a complete 512 MiB
layout, without keeping a second full original model on the console. This
supersedes the previous duplicate-layout storage prerequisite. Retain the exact
host originals and all conversion/integrity evidence. The original application
executable and its restoration contract are separate and remain preserved.

## Required implementation and completion

1. Freshly verify all 76 host originals against the pinned conversion receipt.
   Pipeline the independent host reads and console replacement by file: a console
   source may change only after its own complete host-original verification and
   stable current host identity. The host originals remain read-only throughout.
2. Implement exact logical-to-physical source ranges, including reads crossing a
   512 MiB boundary, original-size GGUF metadata and virtual address keys. Retain
   the eight-descriptor and 8 MiB source-window bounds. No file-backed model mmap.
3. Qualify a CPU-only migration helper and failure controls. Copy each tail
   fragment into a fresh pending file, flush it and independently read every byte
   back with SHA256 before publication and before truncating the source prefix.
   Truncate from the end so the 102.4 GB source never needs a complete second
   copy. Retain all failed/unknown operations, without automatic retry or cleanup.
4. Require fresh idle CPU ownership, exact current source identity, original
   integrity lineage, an exclusive console-layout writer lease and unchanged storage/kernel/Flexible
   reserves before migration. Journal every publication and prefix truncation.
   Never truncate any unverified tail. Keep source timestamps and output identities
   in private records, and stop dependent work on unknown completion.
   The host verification lease protects host original data; the separate console
   lease protects the remote layout. Only one remote mutation helper may run.
5. Verify every reassembled logical file against its original complete SHA256,
   seal all physical identities and the new layout, and independently validate
   all 76 GGUF headers, original BF16/F32 shapes, experts and required PLE.
6. Build/link/import/SELF-qualify the application with all previously qualified
   prefill/source-schedule improvements and the selected cumulative-idle driver.
   Persistent shader/pipeline caches remain disabled. General release and CI
   remain disabled.
7. Complete the physical numerical/control requests, passive frame review,
   source/GPU/model retirement, ordinary close, exact original application
   restoration and fresh numerical readmission, ordinary shutdown and final idle
   CPU/full executable readback. Record TTFT and decode separately from CPU I/O.
8. Save English implementation/results in the private repository and merge the
   reviewed result. A host test, migration or individual numerical check is not
   completion of this replacement/inference task.

The intended storage peak is one bounded tail fragment plus metadata, rather
than a complete second model. The unchanged 32 GiB disk reserve applies. File
count is projected at 711 while logical source byte count remains 359,246,956,672.
This plan does not assume that the representative 1.439x read gain translates
into the same native inference gain.

## Adopted optimization coverage

The split candidate must preserve the complete adopted baseline, rather than
reimplementing a subset of its source path. The coverage review found no other
omitted adopted optimization:

| Adopted mechanism | Required candidate behavior |
| --- | --- |
| Capacity admission and Maya expert cache | Preserve the admitted working set, 53 expert slots and aged LFU4096 policy. |
| Completed-miss overlap | Preserve source production/upload overlap with the same bounded window and completion ownership. |
| File/range read schedule | Preserve selected two-read batches, adjacent-range coalescing and the serial fallback. Physical boundary joins must not bypass the original byte checks. |
| Bounded prefill | Keep four prompt tokens per batch, required prompt outputs and one generated token per batch. |
| Compact completed-route observation | Keep bounded integer rows during inference and publish the JSON only after positive model/GPU/source retirement. |
| Shader and metadata storage | Preserve byte-identical external shader resources, bounded codec input, Direct metadata and original logical GGUF sizes. |

Alternative cache settings, predictive route-ahead, host prefix checkpoints,
expert packing, BF16 compression and draft-token execution did not meet their
recorded acceptance prerequisites. Their absence is a recorded disposition,
not an omitted adopted implementation. See
[all eight proposal dispositions](performance-results-20261025.md).
