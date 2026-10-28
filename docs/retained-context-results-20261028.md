# Matched cache improvement and terminal native dispositions

The 128-slot Expert cache is now installed in the original passive-monitor
application. The exact SELF is
`56763d373c04e2e684d79b703e5baa1ee1ba26315754f85d97a6162bd1521596`.
Native readback verified this SELF, the preserved previous production SELF and
all five current settings files with complete SHA256, stable identity and EOF.
The title was normally closed and a fresh idle session verified. The previous
`ed4b360b...` production executable remains available for rollback.

The finite execution queue is terminal, with explicit unavailable outcomes.
**All requested native comparisons have not passed or completed.** C2, the
dependent prefix cohort and the actual-model C4 comparison remain execution
unavailable under the observed phase predicates. They are not classified as
physical hardware impossibilities or as measured performance regressions.
The [machine-readable results](retained-context-results-20261028.json) preserve
every consumed case, comparison and adoption decision.

## Completed cache comparison

One PS5 ran A53/B128/B128/A53, cases 4780/4880/4900/4920. Each lifetime loaded
the same original BF16 model, ran one warmup and two measured requests, and
positively retired its model/source/device owners before ordinary OS close.
Every measured request began with an empty Expert cache. File pages and
in-process pipelines were not described as cold. Context was 256, prefill four,
prompt 30 tokens and generated output 22 tokens. Model files remain split into
512 MiB parts; this change concerns Expert slots, rather than file part size.

| Metric | 53-slot case means | 128-slot case means | Matched result |
| --- | --- | --- | --- |
| Decode tokens/s | 0.391374 / 0.391599 | 0.408336 / 0.407406 | 1.041851x, approximately 4.19% faster |
| Total request ms | 105819.487 / 105802.801 | 102310.013 / 102564.577 | 1.032936x, approximately 3.29% faster |

Both measurement orders improved, with candidate ranges outside the observed
control ranges. This uses the declared finite-cohort criterion rather than the
old arbitrary 5% cutoff. All original Expert selections matched. All 92 exported
full-vocabulary F32 rows matched with maximum absolute error zero. Weights,
activations, accumulation, KV precision and all Experts are preserved.

## Production application validation

Case 5000 retained the original arithmetic smoke, passive native VideoOut
monitor and exactly two bounded API requests. It did not substitute the
headless benchmark executable for the application.

| API request | Cache condition | Decode tokens/s | Prefill ms | Total ms |
| --- | --- | --- | --- | --- |
| 1 | Empty Expert cache after the completed-context recreation | 0.4075299244 | 48925.056 | 102921.616 |
| 2 | Retained Expert cache | 0.4209830465 | 48061.055 | 100392.025 |

Both requests returned the original 22-token sequence. All 23 full F32 rows and
the complete Expert routes agreed across the two requests; maximum F32 error
was zero. Model/source/device owners retired positively. The two exact CPU
rasters after completed VideoOut flips were visually inspected: CPU identity
and 16 logical threads, GPU identity/memory, calibrated UTC time, generated
tokens, TTFT and 0.41/0.42 tokens/s were legible. Unqualified utilization counters
remain unavailable. There are no chat controls. These are native scanout-source
rasters, rather than photographs of the TV.

The old production bytes were preserved without a redundant restore/reinstall
cycle. Final native readback and fresh idle completed before source integration.
This is a bounded application qualification; sustained unrestricted service and
general answer quality remain separate unqualified claims.

## Other comparisons and memory findings

| Scope | Actual result | Disposition |
| --- | --- | --- |
| C0 / CPU C1 | Reused 27 Direct lifetimes, exact tables and worker proofs; additional full model/startup observations captured | Measurement evidence retained without duplicate probes |
| Retained-context control, 4780 | All three requests completed; three metadata resets changed sampled free pages by 0/0/0 and retained the original banks | Native correctness qualified; long-run memory stability not established |
| C2 combined, 4860 | Warmup completed; the second request returned at 1055 free kernel pages versus the selected operational floor 1154 | Current execution unavailable; normally closed and exact fastest restored |
| Prefix part of C3 | The dependent nine-request prefix cohort was not reached | Implementation exists; complete matched model speed unavailable |
| C4 actual model, 4940 | Model loaded; the before-context predicate observed 1182 pages versus selected 1197 (1154 + 41 observed + 2 selected) | Actual six-demand model requests unexecuted; implementation is present |
| C5 | All previous 16 families and 22 items remain in the updated ledger | No missing implementation is relabeled as physical impossibility |

Case 4220's earlier ten prediction/speculation requests are preserved separately.
Forced rejection restored 23 full F32 rows with zero error. Its two prediction
samples were slower; its speculative samples appeared faster. A subsequent
cohort-join software failure prevented positive common model/source/device
retirement. Those partial results do not qualify a speed adoption. The generator
now preserves the already-completed producer epoch and uses a separate prefix
startup report; host regression checks cover the repair. Physical prefix
qualification is still unavailable.

Approximately 11.404 GiB of Direct capacity is a different resource from free
kernel VM pages. The completed raw-buffer scope allocated 8,755,105,280 bytes;
this is not a universal payload-touch or VM bound. Full cache comparisons now
also exercised the actual original model and 128-slot banks. The 128-slot cache
requests 1,274,462,208 bytes across 129 physical planes per bank.

Only the explicit pre-GPU CPU metadata scope selects minimum plus 21 pages:
17 sampled Direct metadata pages, two sampled idle pages and two selected
extra pages. The irreversible phase switch restores the original GPU/ordinary
floor before GPU pricing and initialization. Neither 21 nor the context
allowance is asserted to be a universal instantaneous peak bound. Global free,
inactive, active and wired observations do not establish exclusive allocator
attribution or promise stable future headroom. No reboot is required or assumed.

## Source and manual verification

| Implementation | Concrete source and behavior |
| --- | --- |
| Cache adoption | `tools/build_matched_cache_monitor.py` requires the closed ABBA numerical/route evidence and recomputes the speed criterion; retains the original UI/API tail and completed-context recreation |
| Context reuse | `native/app/resident_cache_reset.h`, `tools/resident_cache_reuse.py`, `tools/resident_context_entry.py`: original `impl::reset_resident`, metadata-only SLRU/LFU reset, original bank ownership and cumulative counters |
| CPU phase pricing | `tools/build_CPU_metadata_scope.py`: generated `qualified_system_headroom` / `require_resident_source_VM`, once-only CPU phase and unchanged GPU boundary |
| Smaller rebuilds | `tools/build_retained_comparison_entry.py`: replace only the entry object on the complete, ABI-consistent app-object set |
| Correct comparison | `tools/resident_route_review.py` and `tools/review_resident_results.py`: full per-token routes across batch widths, full F32, closed/restored cohort and reverse-order checks |
| Six-demand implementation | `PairedSourceIO::read_batch`, `MappedSourceReader::try_owned_bank_batch`, `native/app/owned_mapped_backend.cpp`, `tools/refill_model_io.py`: original producer plus one persistent worker; six disjoint leases; existing fallback paths |
| API observer | `tools/observe_boot_bound_plan.py`: original two-POST observer with the current boot-qualified journal; no API retry or inference replay |

The actual pinned SLRU host harness passed 768 fresh-behavior comparisons at
53/128 slots with both policies. CPU/GPU phase predicates passed 15 controls.
Route review passed two positive and five refusal controls; promotion passed
one positive and 12 refusal controls. The combined-entry regression checks pass.
Native link/import/dispatch audits and six SELF segment roundtrips passed for
the adopted application. No CI ran.

Driver source remains PS5-Vulkan-Inference
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
Compiler archive is `67fe76cc...c6a9ef30f4e9`; linked archive is
`b57fe26e...3af32328f49925`. Full digests are in the JSON report and private
relink receipts. Persistent shader/pipeline caches remain disabled.
