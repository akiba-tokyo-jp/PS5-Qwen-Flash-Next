# Memory attribution before PLE execution

The owner requested a PLE-specific physical admission plan and made memory
attribution the first priority. This supersedes preparing unrelated optimization
prototypes while treating the regular launch gate as the only outstanding issue.
The controllable closed-file contribution has since been measured and reduced,
and native CPU shader attribution has completed. The precise proprietary
allocator and the overall implementation/validation request remain incomplete.
Do not wait for assumed recovery or replace 10,142 with an arbitrary
smaller constant: `target + 7,168` is not a measured PLE kernel-memory cost.

## Completed physical diagnosis

New CPU-only case 2662 completed two process inventories and three category
observations on the same reserved console. It made no explicit allocation,
payload read, title launch or GPU call. There were 89 processes, no native title,
no stopped/zombie accumulation and no material tracked-service RSS growth.

| Final kernel VM observation | 16 KiB pages | MiB |
| --- | ---: | ---: |
| Free | 6,274 | 98.03125 |
| Active | 27,355 | 427.421875 |
| Inactive | 72,306 | 1129.78125 |
| Wired | 32,804 | 512.5625 |

These sequential counters describe the kernel VM domain, not all PS5 RAM or the
Direct/Flexible pools. Inactive is not an admission allowance; process RSS is not
additive unique physical consumption. Against case 2590, free fell 762 pages,
active fell 3,577, inactive rose 4,270 and wired rose only 69.
`AgcCompositor.elf` and `SceShellUI` RSS fell 2,812 and 2,597 pages. This does not
support a new large retained-process or wired-pool leak claim.

Case 2664 used qualified PROT_NONE/mincore inspection on seven owned files:
the installed inactive production SELF, three closed candidate executables,
both closed checkpoint frames and the external shader resource. All had **zero
resident pages**. All 132 map/query/unmap windows returned, with no live/pending
mapping, content reads or cache advice. Rehashing these files cannot be justified
as current memory recovery. A historical preservation benefit does not mean the
same files remain resident. No production executable or setting was changed.

## Localize the remaining loss before changing a gate

Saved case 2616 retained all 51 boundary observations. They localize a
**1,406-page / 21.96875 MiB** decline to **717.446223 ms** between the completed
post-SELF-integrity report and the next CPU budget guard in shader preparation.
CPU Direct heap mapping/peak stayed exactly 16 MiB. No GPU, model parser,
source worker or virtual-model operation had started.

That interval includes external shader SHA256, registry/codec setup, a small
prior proof read and their existing durable stage writes. Its shader report
records 169 returned Direct reads / 8,258,588 bytes, a 49,152-byte input window,
101,204/101,208-byte output/order buffers and 7,160 bytes of codec scratch.
It does **not** identify the responsible operation. Code paging and concurrent
OS activity remain alternatives.

The older [SELF-only control](native-SELF-read-controls-20261024.json) is a
counterexample: without shader initialization or model metadata, free pages fell
4,728 -> 2,994 during five seconds of quiet, while wired rose 34,406 -> 36,147.
That executable was 38,095,127 bytes, not the current fixture; its magnitude is
not a current matched estimate. It nevertheless disproves the claim that shader
work is necessary for this decline. Do not repeat that unchanged historical
control or diagnose a shader leak from timing alone.

Current SELF/receipt Direct integrity in that case changed free pages from
1,411 to 3,139. This supports the existing integrity order but does not explain
the later loss. Case 2601 separately lost 1,259 pages during metadata checks
and only 13 during the following virtual rehearsal. The later pre-metadata
refusal prevents attributing all pressure to the metadata parser.

## Execution order

1. **Finish shader startup attribution.** Use one fresh CPU-only case, existing
   SELF/receipt integrity and the same shader resources. The new independent
   `native_shader_startup_memory_diagnostic` reuses qualified `StageMemoryProbe`
   observations: matched 2 ms idle, write return and fsync return around every
   existing stage marker. Fixed operation boundaries separate file verification,
   registry/codec setup and prior proof. End before model metadata, workers or
   Vulkan; do not require a later full-model startup gate to finish CPU evidence.
   Preserve the original CPU operational floor and Direct/Flexible guards.
2. **Fix the measured contributor.** Compare stage writes, fsync, inter-read
   marker gaps, matched idle and operation boundaries. Global changes during
   an interval do not prove proprietary allocator/cache causality. Keep hashes,
   monitoring, ownership and durable completion records. Do not remove logs
   because they are a suspect. Validate any supported API/order/lifetime change
   in the same bounded CPU interval before a GPU run.
3. **Freeze a PLE-only admission contract from those measurements.** Price title
   launch, CPU verification, backend/pipeline setup, actual rounded buffers,
   workspace and readback separately. Check real Direct/Flexible availability
   and kernel pages independently. Do not convert Direct payload bytes into
   kernel-page demand, double-charge shared UMA, or treat a conservative ledger
   reservation as actual physical use.
4. **Qualify a small GPU smoke case.** Implement a strict separate width-one
   scope: original graph first, then three copy-elision variants, one graph each.
   Require Vulkan placement, F64 tolerance, bit-identical F32 outputs, canaries
   and positive retirement. The four-graph smoke policy is not implemented yet;
   do not silently alter the existing 208-graph package. No speed claim follows.
5. **Run the finite comparison after smoke.** Use widths 1/2/3/4 and the existing
   alternating pairs. Measure initialization/construction separately from
   compute/readback, minimum free pages and all allocation/ownership peaks.
   Only a surviving candidate proceeds to same-model comparisons and production.

Each refusal consumes its case. Unknown completion retains backing and stops
dependent console work. Use ordinary close and exact fastest/settings restoration.
No forced stop, reset, pressure, cache purge, kernel-pool resize or automatic retry.

## Phase-specific admission

| Phase | Evidence required |
| --- | --- |
| Idle read-only diagnosis | Qualified CPU helper and its actual fixed-storage allowance; no GPU/title 10,142-page gate |
| CPU-only title attribution | Operational floor plus measured title/startup decline, declared variability and exact CPU allocation scope |
| PLE GPU initialization | Fresh post-CPU startup target plus independent actual Direct/Flexible admission |
| Each PLE allocation/graph | Existing rounded ownership/workspace bounds, operational floor and positive completion |
| Whole-model regression/production | Separate existing full-model admission/adoption contract |

The observed operational floor is `898 + max(206, 256) = 1,154` pages and the OS
startup target is 2,974. Both remain unchanged. A saved case observed a 5,195-page
decline between its final prelaunch observation and pre-integrity title snapshot.
`5,195 + 1,154 = 6,349` is reference arithmetic **before** variation/allocation
overhead, not a qualified gate or a PLE minimum. At 6,274 that worst saved decline
would leave 1,079 pages, below the floor. Substituting the old 6,046-page
experiment therefore also lacks a safety basis. This describes the earlier
unreduced state; the separately priced CPU-only case below did not use 6,046.

PLE tensor metadata establishes 8,643,328 raw root bytes, a 16 MiB raw-buffer cap
and 64,000 bytes of used GGML metadata. It also uses the existing 8 MiB source
scratch and real backend/workspace. This supports a smaller staged test, not
a claim about total driver/kernel consumption. The shared diagnostic check of
1 GiB Direct / 64 MiB Flexible must also be priced against actual initialization
evidence before a PLE-specific replacement.

## Source preparation and limits

`native/app/native_main.cpp::admit_shader_storage_CPU` now has default-disabled
operation observations. The independent CPU diagnostic stops before the stronger
model-startup gate. Its strict policy is in `shader_startup_memory_policy.h`;
`tools/shader_startup_memory_result.py` reviews signed changes without declaring
a cause, reclaimability, GPU qualification or adoption. Source/host/SDK checks
are distinct from packaging and execution. The later independent small-title
result below supplies physical CPU evidence. Ready-expert/router prototypes
remain paused behind the PLE sequence.

Keep the installed fastest SELF, driver `872cc126` / `cumulative-idle`, disabled
persistent caches and production limits. Raw identities, paths, SDK inputs,
binaries and console records remain private.

Package 2670 passed the full application link, actual module import audit
(zero missing imports) and six SELF segment roundtrips. It uses source commit
`fa9ff60` and unchanged driver/engine/shader archives. The linked PIE SHA256 is
`04c13268f6244a2976bdcdf869398df816600a365af2dd993cc12587ed221447`;
the converted ELF is `aa56eaf2b5e3918c7e61087f444f0cd70a9f6a8f92a398523a73421091f0422d`;
the 28,258,439-byte SELF is
`8dddba9df84629a5e12a74152b0bee17c00da6a6b81809798ee9218b4b1c54f5`.
It has not been published or executed. Host 2667 passed 35 scope refusals and
actual main compilation; 2668 passed shared shader orchestration and nine
refusals. Five reviewer test groups passed, including owner/scope, finite reads,
paired stages, invalid/ring-overwritten observations and strict numeric types.

## Subsequent physical controls and reduction

[Aggregate evidence](CPU-shader-memory-controls-20261026.json) records the later
finite cases. The isolated 8,258,588-byte input controls completed 169 reads and
338 durable markers each. Static input case 2674 lost two free pages; case 2679
used a separately owned 128 KiB CPU Direct allocation, positively unmapped and
released it, and lost 19 pages including allocation and unclassified gaps.
Neither reproduces the historical 1,406-page decline. The Direct window is not
the title heap arena, so these controls alone do not qualify title initialization.

Cases 2677/2678 refused before allocation. A zero Direct-size result in the CPU
helper context was not treated as an empty physical pool. Case 2679 bound the
already qualified CPU allocation sequence from the successful 8 MiB control;
no GPU or production quota predicate changed.

Eight older retained SELF files had 160 resident pages; complete original
SHA256/identity/EOF verification recovered 158 pages without changing their
bytes. The saved owned-file catalog avoided further directory enumeration.
Stable-prefix case 2690 completed 694 returned reads across 347 other files,
changing free pages from 2,420 to 3,790. A historical container-format refusal
was retained separately; that consumed source was excluded.

Whole-range case 2692 completed 301 files and part of one more, then positively
refused with all 13,987 reads returned and no live mapping. Its exact refusing
predicate was not logged; elapsed time alone is not proof of which predicate
failed. The separately declared continuation 2693 excluded the completed 301
files, finished the remaining 46 with 1,344 returned reads, and changed free
pages from 8,155 to 8,856. These cohorts record current whole-file hashes and
stable identities; they do not authenticate every historical file against its
original digest. All source files were opened read-only. No cache-advice,
pressure, pool resize, GPU operation or automatic resubmission was used.

A large change before the older-file scan coincided with preparation that
included FTP directory enumeration. No matched interval isolates that operation,
so a causal FTP claim is not established. Process inventories remained stable;
the larger category change was inactive memory. The demonstrated controllable
component is retained owned-file residency. It does not make all inactive pages
available for admission.

Detailed durable before/returned records remain enabled. The new CPU observer
polls a fixed 512-byte completed-boundary status and retrieves the complete
journal once after its terminal record. It avoids repeatedly fetching a growing
journal. Four manual tests cover ambiguous acknowledgements, wrong owner,
existing output and finite observation limits; actual C variants compile for
the static/Direct and prefix/whole scopes. This changes observation transport,
not the amount of native completion evidence.

## Independent small CPU title result

`mini_shader_memory.cpp` links the actual shared shader-admission helper,
original tracked heap, registry, file reader and decoder, with no inference
engine or Vulkan implementation. Six exact CPU zlib members come from the
unchanged qualified archive. Duplicate CRC member names are resolved by their
exported symbol and recorded occurrence. The 1,195,526-byte SELF
`98401bd5b0d5474d83697d369f4865c16e0ef8e2e939fbb3b8050b0284c14d8c`
passed real strong-module imports and six segment roundtrips.

Case 2694 required ten fresh observations of at least **6,605** pages:
5,195 measured worst full-title startup decline + 1,154 operational floor +
256 separately declared metadata/variation pages. This was frozen after the
reduction, not substituted for the previously insufficient 6,239-page state.
Actual observations were 8,783–8,784. CPU Direct heap and Flexible metadata
limits remained separate; no Direct payload was counted as kernel RAM.

The physical title completed 169 shader read pairs and 340 stage observations:

| Original CPU operation | Signed free-page change | Elapsed |
| --- | ---: | ---: |
| Complete external file verification | -26 | 1.440045080 s |
| Registry and decoder initialization | 0 | 0.000605480 s |
| Prior complete CPU proof | 0 | 0.000181059 s |

The entire shader interval changed free pages 3,885 -> 3,863. The tracked heap
remained 16 MiB. Matched idle/write/fsync/read-marker changes were -47/+44/-17/+4
pages; these are sequential global changes, not a causal subtraction or evidence
that removing monitoring is appropriate. The large old shader-correlated event
was not reproduced by actual shader initialization.

The small title still had a substantial wired component: 38,111 pages while
active versus 32,801 after ordinary closure and restoration. This occurs
without a linked inference engine or Vulkan implementation. It prices the
native-title/runtime interval; it does not identify one proprietary allocator or
prove that all of the difference belongs exclusively to the OS.

Exact fastest SELF and all five original settings were restored. Native complete
integrity of 15 restored/closed sources passed. Five post-close category snapshots
observed 9,079–9,080 free pages, 71,460 inactive and 32,801 wired. No native owner,
gateway, loaded model, GPU initialization or unknown completion remained.
These point observations are not a later launch admission or a speed result.

## Next PLE admission and execution

The separate provisional PLE prelaunch calculation is **8,425 pages**:
5,195 measured startup decline + the existing 2,974-page GPU startup target +
256 variation pages. Require fresh consecutive admission and independently
repeat the existing post-CPU target, operational floor, Direct/Flexible and
ownership checks. This is an experimental cohort allowance, not a measured
hardware minimum or a replacement for the regular 10,142-page full-model gate.
Keep the conservative 1 GiB Direct / 64 MiB Flexible setup checks while measuring
their actual peaks; they are not currently the blocking condition.

The strict four-graph width-one smoke scope still needs implementation before
execution. It must use its own schema, preserve F64/exact-F32/canary and Vulkan
placement gates, and retain backing after uncertainty. It must not silently
alter the frozen 208-graph benchmark. Surviving variants still need the finite
comparison, same-model acceptance and production placement. No optimization or
generation-speed improvement was adopted by these CPU diagnostics.
