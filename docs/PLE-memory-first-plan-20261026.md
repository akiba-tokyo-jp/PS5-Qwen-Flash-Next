# Memory attribution before PLE execution

The owner requested a PLE-specific physical admission plan and made memory
attribution the first priority. This supersedes preparing unrelated optimization
prototypes while treating the regular launch gate as the only outstanding issue.
Neither the memory cause nor the overall implementation/validation request is
complete. Do not wait for assumed recovery or replace 10,142 with an arbitrary
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
experiment therefore also lacks a safety basis. No new threshold is activated.

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
are distinct from packaging and execution. No physical shader-attribution result
exists yet. Ready-expert/router prototypes are paused behind this sequence.

Keep the installed fastest SELF, driver `872cc126` / `cumulative-idle`, disabled
persistent caches and production limits. Raw identities, paths, SDK inputs,
binaries and console records remain private.
