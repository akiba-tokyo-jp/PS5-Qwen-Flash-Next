# Native worker verification and lossless startup storage

The selected OS I/O, predictive cache and expert-aware verification instruction
remains active. This record adds actual PS5 CPU evidence and a smaller driver
qualification artifact. The later [full-model result](native-model-cold-start-20261027.md)
records one accepted native width-two verification and three completed model
requests; it does not complete rejection or matched-speed qualification. No new
decode speed winner is established. The installed fastest SELF remains `ed4b360b...`; neither feature
is enabled in production. No CI, reboot, GPU reset or forced termination is used.

## Actual PS5 persistent-worker result

Case 3225 used the shipping `ExpertPrefetchIO` with four jobs and twelve original
BF16 role deliveries. It read 39,518,208 physical bytes containing 39,321,600
original BF16 bytes. Full source identities, envelope and original SHA256 hashes,
outer canaries, three current boot/eight-owner boundaries, worker join, Direct
unmap and Direct release passed. One persistent worker had at most one read in
flight. Its foreground expert-cost exercise used synthetic metadata and timing
inputs; this is not speculative-model numerical or speed acceptance.

| Job | Complete interval, ns | Foreground control, ns | Join interval, ns |
| --- | ---: | ---: | ---: |
| 0 | 16,522,607 | 56,210 | 16,466,397 |
| 1 | 14,260,175 | 50,837 | 14,209,338 |
| 2 | 13,282,795 | 42,338 | 13,240,457 |
| 3 | 13,095,001 | 45,385 | 13,049,616 |

No model or GPU was started. The test establishes native worker/codec/source
ownership behavior, not useful GPU overlap or inference acceleration.

Source: `native/qwen_flash_next/predictive_worker_probe.c` / `.cpp`,
`tools/build_predictive_worker_probe.py`, `tools/predictive_worker_result.py`.
Private native build/result receipts are cases 3223/3225. Raw console data,
addresses, credentials, model bytes and runtime binaries remain outside Git.

## Lossless immutable-driver storage

The native link map identified 7.69 MB of relocation-free NIR constants. The
standard SELF writer can read compressed containers but does not implement a
compressed writer; no guessed compressed SELF was launched. Instead, a separate
application overlay changes selected readonly ELF sections to initialized-at-use
NOBITS destinations. The application restores every original byte and SHA256,
then protects the exclusive page-aligned range readonly before Vulkan use.
The original driver archive is never edited. Every untouched member occurrence,
all code, every relocation and all other indexed sections must remain byte exact.
Section indices are used because COMDAT metadata can repeat section names.

The source is PS5-Vulkan-Inference revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
The original native donor archive SHA256 is
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
An overlay is a distinct linked artifact, not the unchanged donor archive.
The native allocator, feature advertisement and disabled persistent-cache policy
remain as before. Original model BF16/F32 data and F32 KV are unaffected.

| Storage scope | Original bytes | Stored bytes | Tables | Evidence |
| --- | ---: | ---: | ---: | --- |
| NIR algebraic constants | 7,688,966 | 247,740 | 640 | Host and PS5 CPU restoration |
| NIR plus four additional constant members | 9,471,408 | 730,669 | 673 | Host/native qualification tracked below |

Case 3239 physically restored all 640 NIR tables in 56,888,348 ns, verified every
original SHA256, released the codec and positively applied readonly protection.
Peak codec scratch was 7,160 bytes. All three current boot/eight-owner boundaries
passed. This standalone CPU data fixture did not execute the Mesa compiler or a
GPU. Its 4,621-page in-process free-memory observation is not a recovered startup
budget. Host controls also reject a changed hash, offset, destination, overlap,
compressed stream, allocator failure and failed protection.

The four extra members are `ac_parse_ib.c.o`,
`radix_sort_radix_sort_u96.c.o`, `radix_sort_radix_sort_u64.c.o`, and
`radv_acceleration_structure.c.o`. Only their large relocation-free readonly
arrays change storage. The exact uncompressed contents, including embedded
driver kernels, must be restored before use. No instruction stream is rewritten.

The first integrated full application SELF is 21,047,415 bytes, versus
28,419,239 bytes for the prior integrated candidate. Real imports, static Vulkan
dispatch callbacks, SELF integrity and all six segment roundtrips passed. This
is a file-size result, not measured kernel savings. It was not installed or run.

## Native startup experiment

The independent `driver_table_fixture.cpp` restores the constants, checks the
current whole SELF/receipt and external shader resource, preserves current-boot
prior shader evidence with per-use SHA256, and then attempts the unchanged
2,974-page GPU gate. Its only graph is the existing 32 x 16 BF16/F32 fixture.
No model, display or HTTP server is started. All GPU work still requires the
original sole native owner, pool predicates, serialized submissions, numerical
readback, positive device idle and epoch retirement, then ordinary OS close.

The smaller CPU entry uses the same declared provisional formula throughout:
1,154 operational pages + 1,407 observed quiet small-title allowance + two
candidate file copies + actual PT_LOAD NOBITS pages + 256 variation pages.
This is a chosen experimental policy, not a proven hardware minimum or upper
bound. It never grants the subsequent GPU/model gate. Screens 3243/3247 refused
with zero launches. Their shortages were 63/33 pages; neither price was reduced
to fit. Subsequent artifacts reduce immutable storage and fixture code instead.

Qualification and restoration outcomes below supersede this experiment's earlier
pending status. A default-off merge is not production adoption.

### Preserved pre-GPU integration failures

Title 3248 returned `Exact isolated fixture operational allowance required`:
the new wrapper called an existing API restricted to a different 1,024-page
fixture with 512. The corrected wrapper retains the common operational floor
and checks its own additional 512 pages directly. A host test now links and
executes that actual wrapper at 1,666/1,665 free pages, including no-retry checks.

Title 3265 then returned before GPU use because the final `.qwen_driver_tables`
range was empty: the primary script consumed `.bss.qwen_nir_*` before the inserted
output section. Standalone CPU assembly did not exercise this real linker
geometry. Both failures were implementation defects, not physical inability.
The corrected inputs use `.qwen_cold_table_*`, which the primary `.bss.*` pattern
cannot consume. `audit_linked_storage()` checks the actual plan and each relocated
target/hash, all non-overlapping exclusive NOBITS spans, complete linked encoded
bytes and writable non-executable load permissions. Packaging requires that audit.
The preserved bad final ELF is now explicitly rejected by the host audit.

Both titles ran zero GPU graphs and zero model loads, reached known returned
CPU terminals, were closed through the guarded ordinary OS path, and ended with
complete native SHA256/identity/EOF verification of the restored fastest SELF
and original settings. Case 3248 also preserved two host close-preparation
failures and an integrity-observer refusal; no native OS close request occurred
until the consolidated owner-checked helper. Case 3265's nested writer-lock
failure likewise preceded its only native OS close request. These failures are
retained rather than rewritten as successful qualification.

## Concrete implementation paths

- `tools/driver_table_storage.py`: indexed ELF preservation, exact NIR object
  transformation, duplicate-preserving archive construction and immutable plan.
- `tools/driver_table_storage_extension.py`: explicit additional readonly-member
  scope, exact parent identity and preservation of every other member occurrence.
- `native/app/driver_table_restore.h`: bounded synchronous production decoder,
  full input/output accounting, SHA256 and exclusive readonly protection.
- `native/app/driver_tables.cpp`: tracked Direct-heap codec allocation, bounded
  admission, no retry after failure, and pre-Vulkan restoration.
- `tools/build_native.py` / `package_native.py`: explicit optional manifest,
  actual overlay archive in the link command and separate relink provenance.
- `tools/build_driver_table_fixture.py`: minimal qualification entry with optional
  separately recorded size compilation and address-safe identical-code folding.
- `tools/check_driver_table_storage.py`, `tests/driver_table_restore.cpp`: actual
  table roundtrip and corruption/admission/protection controls.

Predictive cache and width-two model acceptance still require actual target
arithmetic, rejected-batch state restoration and continuation, all extra I/O
accounting, matched model timings and exact fastest restoration. No standalone
CPU result substitutes for those steps.

## Corrected native GPU qualification and full-model continuation

Corrected fixture 3280 completed all 673 original constant reconstructions and
readonly protection, then the existing 32 x 16 BF16/F32 GPU graph. All 16 outputs
matched exactly (maximum absolute error zero), with positive device idle and
epoch retirement. Model loads were zero. Ordinary OS close, complete native
SHA256/identity/EOF preservation, exact fastest SELF and five-setting restoration,
and a fresh idle session all passed. The original object instruction sections and
relocation records are preserved; final linked addresses naturally change.

The corrected SELF was 12,914,042 bytes, SHA256
`a2ebd8636bf2c00d7dde60fc5548b1a3deaf7e847bb110cfd054e57089a76835`.
Prelaunch free pages were 6,596; main entry 2,957; after reconstruction 2,948;
after integrity 3,749. These global observations qualify this small lifetime,
not exclusive attribution or a full-model startup saving. The 2,974-page GPU
target was unchanged. No reboot, reset or global reclaim was used.

Packaging now additionally audits loader-visible converted ELF metadata:
677 critical relative pointers, all table sizes/offsets/original hashes, exact
embedded compressed bytes, and exclusive writable non-executable NOBITS
coverage. Host control 3311 passed and rejected the preserved empty-range ELF.
This complements, rather than replaces, the actual linked ELF geometry audit.

Independent full-model case 3291 used the original unmodified driver archive and
returned before GPU initialization: 1,911 free pages versus the unchanged 2,974
startup target. All 76 source reservations were positively released. It loaded
no model and submitted no generation request. Ordinary close and exact fastest
restoration passed. Its observed global CPU decline was at most 6,312 pages;
repeating that unchanged artifact would require the separately repriced 9,542
pages. This is a resource-policy refusal, not a failed model-speed benchmark.

Complete changed-artifact build 3287 / package 3288 passed native link/imports,
SELF integrity, six segment roundtrips and both cold-table geometry audits.
Its SELF is 19,236,759 bytes, SHA256
`c128f48038939b83893c7a6c7b335489158bfc4416adfb7e28d6ac98bb8313a2`.
The old candidate was 28,419,239 bytes. Summed page-rounded PT_LOAD memory
increases by 19 pages; file size alone is not counted as recovered kernel memory.

New case 3314 uses CPU-staged entry priced at the largest prior full-title CPU
decline, 6,749 + 19 additional image-memory pages + 1,154 operational + 256
variation = 8,178 pages. Screen 3313 observed 8,408 and passed. This is a distinct
smaller artifact with minimally qualified driver storage, not a replay of 3291.
The staging price grants no GPU admission: the original 2,974-page GPU target,
all pool predicates, numerical checks and positive completion remain mandatory.
Case 3314 subsequently completed model arithmetic and one accepted width-two
verification. See [actual model results and remaining constraints](native-model-cold-start-20261027.md).
Prediction overlap, speculative rejection and matched speed remain unverified.
