# Resident model window and geometry correction

The current continuation keeps all C0–C5 comparisons and the previous 16
families / 22 items in scope. It does not claim native validation is complete.
No reboot, CI, precision change or production speed adoption occurred.

Case 3840 loaded the complete original BF16/F32 model and completed warmup and
one ordinary 22-token request. Ordinary decode was 0.3914249099 tokens/s;
prefill was 50.082738364 s and total request time 106.323106752 s. This is a
control observation, not a matched speedup. Source producer wait accounted for
97.099889102 s of 105.302691784 s processing time. These overlapping intervals
are not additive GPU/SSD measurements.

Three separate defects were corrected, with the failed cases preserved:

| Case | Observed result | Correction |
| --- | --- | --- |
| 3760 | Fixture-only policy API refused before SELF read or GPU work | Use the actual operational plus new-Direct-allocation guard |
| 3790 | Whole postloader SELF verification passed; model load failed | Capture the bounded in-process model error instead of repeatedly requesting private logs |
| 3810 | Error at 1,169 pages despite the ordinary 1,154-page floor passing | Charge 19 measured metadata pages at allocation; stop charging that allocation again on reads of the existing window |
| 3840 | Warmup and ordinary request passed; predictive context refused | The original model has 48 trunk layers plus one retained MTP layer, rather than 48 total layers |

All four cases ended with one ordinary OS close, exact fastest SELF and all
five settings restored, native whole integrity verification and a fresh idle
session. Retained/unknown GPU ownership before OS close is preserved in the
failure records; it is not an active owner after the admitted close.

The opt-in v2 source profile keeps the original 1,154-page operational floor
and every actual allocation, Flexible/Direct capacity, heap, identity, EOF and
completion check. CPU preflight retains its existing 8 MiB owned buffer. Only
model-load submissions use a 1 MiB maximum; postload inference restores 8 MiB.
This is a separate generated reader class, preserving the original reader ABI.
The selected context allowance is 43 pages (observed net decline 41 + 2), not
a universal instantaneous peak bound. Actual operation guards remain required.

One complete Direct SELF pass after the OS loader recovered 1,032 pages in
3790 and 3810, and 1,033 in 3840. Case 3840 measured 2,961 → 3,994 free pages,
92,324,932 ns, with the entire 16,900,842-byte SELF hash verified. This is an
observed global free-page change; no recovered amount is assumed in admission.
There is one pass, no read retry, and no speculative cache-eviction operation.

The corrected predictive guard requires exactly 48 trunk layers, 49 total
layers, one MTP layer, 512 experts and maximum route width 10. Forecasts still
cover only the 48 trunk layers. No tensor, expert, MTP component or arithmetic
is removed. Ten altered-geometry controls were rejected on the host.

The corrected native object is derived from the actually linked
`predictive-model-io-3201/llama-moe-cache.cpp.o` source and recipe. New parent
and extended model-I/O manifests select that same new MoE object while
retaining the original seven-object and immutable shader-resource validators.
Old manifests and binaries remain unchanged. The first package attempt failed
because its provenance still selected the old object; the later immutable
manifest rebind passed the existing validators instead of bypassing them.

Relevant source: `resident_phase_vm.h`, `resident_load_window.h`,
`resident_load_error.h`, `predictive_model_geometry.h`,
`tools/resident_phase_source.py`, `tools/resident_load_reader.py`,
`tools/predictive_model_geometry.py`, `tools/build_predictive_geometry.py` and
`tools/rebind_model_io_provenance.py`.

The next finite native scope combines the ten prediction/verification requests
and nine prefix requests in one model lifetime. Its completed terminal,
retirement, route/numerical comparison and matched timing remain prerequisites
for any adoption. The 53/128 cache cohort and actual-model six-demand delivery
comparison remain separate pending validations, not physically impossible items.

Driver source remains PS5-Vulkan-Inference
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`; linked archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent pipeline and shader caches stay disabled. Original fastest SELF
remains `ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.

## Later consumed scopes

Case 3870 returned a model-load memory refusal at 1,143 pages, before any new
comparison request. GPU-entry free pages were 1,798; the ordinary floor stayed
1,154. Ordinary close and exact restoration passed.

CPU case 3891 replaced one page inside its own 64 KiB anonymous allocation with
a 16 KiB-aligned CPU Direct mapping at the same address. Neighboring patterns,
read-only protection and complete unmap/release passed. No title or GPU started.
This qualified the fixed-mapping API, not model-memory recovery.

Case 3910 mapped only the audited, exclusive 9,486,336-byte table NOBITS span
to 9,502,720 bytes of CPU Direct backing. All 673 tables and 9,471,408 original
bytes passed SHA256 and read-only protection. Flexible quota increased from
436,207,616 to 446,693,376 bytes. Mapping samples were 1,243 → 1,242 kernel free
pages: this does **not** establish kernel recovery. Model load later returned
at 1,127 pages, below the unchanged 1,154 floor. No model request completed;
ordinary close and exact restoration passed.

The distinct load-only GPU-copy path preserves original submit/fence wait/
reset/cleanup and uses the existing positive idle/epoch checkpoint after
64 MiB of completed transfers. The indexed numerical fixture must exercise
and pass this path before model load. Ordinary inference/expert-bank delivery
switches back after load. Avoiding CPU first-touch of large resident mappings
is a hypothesis, not an established kernel-memory saving.

Case 3960 never reached that fixture: startup returned at 1,017 pages before
table mapping or GPU work. Restoration had a bounded HTTP read timeout.
Configuration hashes and rename states were reconciled; accepted close,
rename and finalization calls were not repeated. Remaining integrity/idle
work passed and the exact fastest/settings are restored.

The next opt-in pure-C early SELF scope uses one 64 KiB Direct window before
C++ constructors. Its distinct CPU-only rule is kernel minimum plus 17 sampled
Direct metadata pages, 2 sampled idle pages and 2 selected extra pages.
Reserved is recorded separately. This selected 21-page margin is not a universal
I/O bound or a verified proprietary kernel allocation rule. Ordinary/GPU
admission keeps its 1,154-page rule. Complete stable inode, EOF and SHA256 bind
to the current root-verified launch before GPU work; the duplicate later SELF
scan is removed. Native execution remains pending, not a completed validation.
