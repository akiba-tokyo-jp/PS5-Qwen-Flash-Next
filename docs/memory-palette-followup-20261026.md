# Memory attribution and exact BF16 GPU delivery follow-up

Historical partial checkpoint. The remaining frame-memory attribution, fused
comparison and restoration subsequently completed; see the
[completed finite plan](memory-plan-completion-20261026.md). The original
observations and refusals below remain unchanged.

The standalone GPU restoration cohort **completed and lost at 0.561503x** paired
delivery throughput. It is rejected. The fused restoration/GEMV candidate passed
host controls, SPIR-V validation, native linking/import checks and SELF roundtrip,
but its unchanged physical prelaunch gate refused before any title/GPU launch.
It has no measured GPU speed or numerical result. The requested overall plan
remains incomplete; no new candidate was adopted and no full-model rate was
measured. See the [allowlisted numeric evidence](memory-palette-followup-20261026.json)
and the [preceding memory investigation](kernel-memory-cause-20261026.md).

## Memory attribution

The earlier matched control established that a complete 28,017,271-byte HTTP
executable readback consumed 1,712 free kernel pages. Required complete Direct
SHA256/identity/EOF verification returned those pages. This follow-up adds file
residency and process metadata; it does not identify every allocator or prove a
global leak.

Case 2371 completed two bounded process inventories: 89 processes in each, no
stopped processes or zombies, and unchanged RSS for all seven tracked services.
The largest two RSS values were 584.4375 and 308.59375 MiB. RSS can include shared
pages and cannot be summed into physical kernel consumption. This short interval
does not exclude earlier service growth. No process memory contents or service
controls were used.

The new file probe uses only `PROT_NONE | MAP_PRIVATE` windows of at most 1 MiB,
`mincore`, and positive `munmap` completion. It never dereferences a source window,
reads its payload, or issues cache advice. Each file is limited to 128 MiB and
128 windows, with exact path/descriptor identity, size/link checks, vector
canaries, a finite checkpoint deadline and the original kernel floor plus a
64-page mapping allowance. Mapping metadata itself can consume kernel resources;
zero explicit Direct allocation does not mean zero kernel overhead.

| Physical census | Selected sources | Resident pages observed, 16 KiB each |
| --- | --- | ---: |
| 2375 | Installed production SELF | 1,711 |
| 2375 | Retained case-2354 SELF | 1,713 |
| 2375 | Three other retained palette SELF files | 0 |
| 2375 | Original palette pack / title-visible copy | 156 / 0 |
| 2375 | Original rollback | 0 |
| 2378 | 29 positively completed CPU helper executables | 217 of 217 inspected pages |
| 2381 | Eight older retained SELF files | 0 |
| 2381 | Sealed demand pack | 96 |

Every selected mapping, metadata query and unmap positively returned. These are
bounded point observations, not a census of every console file, a claim that
resident pages are immediately available, or permission to use inactive pages
for admission. The FreeBSD [`mincore` interface](https://github.com/freebsd/freebsd-src/blob/releng/11.0/lib/libc/sys/mincore.2)
and [`sys_mincore` implementation](https://github.com/freebsd/freebsd-src/blob/releng/11.0/sys/vm/vm_mmap.c)
informed the design. The PS5 imports and one-page probe were separately qualified;
the proprietary kernel is not asserted to be byte-identical to FreeBSD.

Required preservation integrity then covered the installed/retained artifacts,
sealed packs and 38 completed CPU helpers. Case 2384 completed 11 exact sources
before a positive CPU refusal caused by host-side path rendering. Its remaining
31 sources completed in a distinct audit, case 2387; completed work was not
replayed. The latter observed 9,895 -> 10,191 free pages. A global nonce
substitution had changed a data path; final helpers now render actual receipt
paths separately from control strings and assert every path literal before use.
All failed records remain preserved.

The operational reduction is to reuse sealed artifacts and put all required
large HTTP readbacks before final required native Direct integrity. It preserves
whole SHA256, stable identity, EOF, memory floors, deadlines and exclusive journals.
It does not use cache purges, pressure, service resets, kernel resizing, reserve
changes or deletion of forensic artifacts. Flexible availability is a separate
quota and cannot be added to free kernel pages.

## Completed standalone GPU screen: case 2390

The headless title used the pinned driver and the same nine original 3,276,800-byte
BF16 matrix samples in six rotated raw/palette rounds. The integer restoration
check preserved all 65,536 possible BF16 bit patterns. All 108 original matrix
deliveries and 110 GPU submissions/readbacks passed, followed by positive device
idle and worker-epoch retirement. Every fence returned within its original finite
wait. The exact owner was ordinarily closed and the fastest SELF/settings restored.

This comparison measures the extra cost of supplying an original weight matrix.
Raw delivery times the Direct read; its GPU copy correctness check is outside that
baseline interval. Palette delivery includes Direct read, complete CPU format
validation, restoration dispatch and fence. This deliberately charges the added
restoration step. It is not a comparison of two complete inference engines.

| Per-matrix median component | Raw | Exact palette |
| --- | ---: | ---: |
| Direct read | 5.795642 ms | 5.014195 ms |
| Dispatch/completion interval | 4.633274 ms, excluded from raw delivery | 4.758163 ms, included |
| Complete timed delivery | 5.795642 ms | 10.013957 ms |
| CPU validation and other host residual | Outside baseline scope | 0.229571 ms |

The six paired round ratios were 0.565607, 0.555924, 0.529643, 0.573171, 0.558637
and 0.564369. The median was **0.561503x**, failing the predeclared >1.05x median
and every-round-positive screen. Median round totals for nine matrices were
52.770387 ms raw and 92.676866 ms palette. Component medians need not sum to the
median total. The approximately 4.76 ms interval includes recording/submission
and fence overhead; it is not an isolated GPU shader-time measurement.

Reduced read time did not repay the separate restoration dispatch. This tested
standalone variant is rejected without a whole-model conversion or generation
rerun. Its small-fixture ratio is not tokens/s and cannot be applied directly to
the installed 0.391093/0.398430 tok/s short-request results.

## Fused candidate: implemented, physical measurement pending

| File / function | Implemented change | Current qualification |
| --- | --- | --- |
| `native/qwen_flash_next/bf16_palette_gemv.comp::original_bits/main` | Two separately compiled raw/palette pipelines; exact BF16 load into F32 accumulation, fixed 64-thread row reduction, no full restored matrix | Both SPIR-V variants validated; no physical execution |
| `native/app/palette_gpu_dispatch.cpp::matvec/dispatch_internal` | One command submission/fence per matrix for both arms; same two owned 4 MiB coherent buffers and 16 MiB explicit-allocation ceiling | Native link and host API ownership controls passed |
| `native/app/palette_gpu_admission.cpp::admit_palette_gpu` | Independent CPU-double reference for first raw outputs, then bit-exact F32 equality for every raw/palette output; identical read+compute+fence timing scope | Built; runtime checks have not executed on PS5 |
| `native/app/palette_gpu_policy.h::require_palette_gpu_policy` | Separate strict GEMV schema, exactly nine 640/2,560-column shapes, fixed six rounds | Actual private-policy host admission passed |
| `tools/palette_gpu_result.py::parse` | Matching policy/result schemas, complete counts and both timing scopes; passing a fixture never admits production | Host malformed/completion/schema controls passed |

The loader restores the original BF16 bits; exponent palette codes are a lossless
storage format, not lower-bit numerical quantization. Both pipelines use the
same reduction order and F32 arithmetic. The fixture input vector is deterministic;
it is not an actual model hidden state. Initial all-pattern copy checks remain
separate from GEMV. The design removes a separate dispatch and decoded-matrix
write, but any speedup remains a hypothesis.

Case 2420 published and fully verified the distinct candidate, verified all five
required published/preserved sources through Direct, then received a positive
zero-work refusal at **9,941 free pages versus 10,142 required**: a 201-page,
3.140625 MiB deficit. Title launches, GPU initialization, allocations, payload
reads inside the metadata gate, submissions and automatic retries were all zero.
It is neither a GPU hang nor a rejected GPU speed result.

The exact fastest SELF and prior settings were restored and fully read back.
Fresh idle boot/service/owner checks passed. The final required preservation
audit, case 2430, verified those retained executables and 12 newly completed CPU
helpers: 15 complete hashes/identities/EOF checks. It observed 6,400 -> **9,928**
free pages, or 155.125 MiB, still 3.34375 MiB below the unchanged 158.46875 MiB
prelaunch requirement. This in-audit observation is not admission for a later
launch. No further publication or GPU retry was attempted under that condition.

## Provenance and maintained checks

The standalone SELF was
`9ceec2293884197a296164f9b283585cc336180070862711ffbdf615bf18f093`.
The fused SELF was
`a9b16ea7584b47c5077ee1ea3854a5c8d17a6bd6462c90d951e10921587c48af`,
28,058,327 bytes, built from main base
`d4b4039ee72ec3961b01022fe765ce7c32a4cca6` plus the recorded source overlay.
Actual runtime import checks and all six SELF segment roundtrips passed.
The same 51,183,616-byte sample pack was reused. Execution source snapshots,
input receipts, failed controls, raw observations and executables remain private.
JSON source hashes identify raw working inputs. Native bytes are preserved in
Git; the host result parser's separately recorded Git hash accounts for verified
newline-only text normalization.

Application relinking reused the qualified native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`,
driver revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
The generic donor archive is separately recorded in the package; no driver or
engine archive was rebuilt. Persistent shader/pipeline caches remain disabled.

`native/qwen_flash_next/kernel_process_memory_probe.c` supplies the bounded RSS
inventory. `native/app/file_residency.h` owns the bounded mapping/query/release
state machine; `native/qwen_flash_next/file_residency_probe.c` binds it to the
qualified module imports and native identity/memory guard. The diagnostic link
selects `libkernel_web` before SDK libc to use the observed dynamic `mmap` import.
The first SDK raw-wrapper link was rejected on the host and never executed.

Manual, host-only checks:

```text
python tools/check_file_residency.py --workspace WORKSPACE --out NEW_OUTPUT
python tools/check_palette_gpu_probe.py --workspace WORKSPACE --cache DATA_CACHE --out NEW_OUTPUT
```

They cover full 128-window bounds, invalid vectors/canaries, failed queries/maps/
unmaps, unknown or failed submission/fence reuse, both GEMV shapes, strict policy,
matching result schema and timing scopes. Native module/import qualification and
actual GPU results are separate evidence. Repository visibility was checked as
private and Actions as disabled. CI runs remain zero.

## Disposition and next admission

The memory cause is partly isolated and the integrity-order reduction is applied.
The earlier one-worker demand queue remains rejected at 1.040344x; the standalone
GPU palette now has a completed negative result. Fused GEMV is implemented and
built, but its physical numerical/speed screen and conditional full-model
integration remain outstanding. Ready-expert scheduling, router forecasting and
speculative verification retain their earlier unimplemented/unqualified status.

Before another candidate publication, identify additional consumption through
bounded owned-file/service metadata and require fresh unchanged memory admission.
Avoid repeated candidate publication/readback cycles when the prelaunch gate
cannot pass. Consolidating future CPU metadata checks into a separately qualified
reusable observer is a design option to reduce executable/journal churn; it is
not implemented and does not establish that the current deficit is recoverable.

Only an admitted fused comparison passing original numerical/completion checks,
median >1.05x and all six rounds >1.0x should proceed to actual engine integration.
That integration would require original full-model outputs/routes, source bytes,
memory ledgers, prefill and decode measurements before production adoption.
The existing fastest startup SELF
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`
remains installed. No native owner, gateway, loaded model or uncertain completion
remains. No fresh numerical generation was repeated during restoration.
