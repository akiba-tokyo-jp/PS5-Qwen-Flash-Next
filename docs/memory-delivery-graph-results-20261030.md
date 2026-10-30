# Memory, delivery and graph results

All six candidate investigations are closed. The selected shared-Expert Q8 and
1381-slot composition is installed by placement10820. Its executable is
`5c5d70347f25d2fe0905da3325519c056038475254fbf90af745af61c7b126ea`.
See the [measured results](memory-delivery-graph-results-20261030.json),
[adoption record](memory-delivery-graph-adoption-20261030.json) and
[implementation/evidence history](memory-delivery-graph-plan-20261030.md).

| Candidate | Actual verification | Decision |
| --- | --- | --- |
| Memory redistribution | Native997/1125/1253 comparisons; actual workspace8 MiB; shared-Q8/1381 normal10760 including prefix/causal checkpoints | Adopt1381 slots,64 MiB workspace reservation and explicit checkpoint allowance |
| Additional resident Q8 |144 active shared projections, contiguous GGUF offsets, sealed payloads/prefixes; native normal and four fixed task pairs | Adopt with the expanded cache;221,184,000 additional resident bytes saved |
| Miss-aware retention and placement | Exact1253 policy replay; capped/full frequency increase misses;532-triplet placement10780 reduces I/O calls but slows whole pair0.672% | Keep two-touch policy and existing448 placements |
| Completion-ordered delivery | Actual callbacks overlap other reads; normal10270 independent total-0.715%, retained+0.163% | Mixed result; retain existing delivery |
| Width-specific CPU graph plans | Normal10640 captures14 topologies but accepts zero reactivations under original reuse checks | No benefit; retain existing graph path |
| GPU kernel work | Native10560 timestamps, valid64-bit queue counters and bounded completion | Diagnostic complete; no specific production shader improvement established |

The source mechanisms are `build_cache_capacity_1125.py`,
`build_shared_cache_capacity.py`, `resident_shared_q8_{receipt,source}.h`,
`source_overlay.h`, `build_expanded_miss_placement.py`, `completed_read_pool.h`,
`width_graph_bindings.h` and `build_gpu_kernel_timing.py`. Builders retain exact
application source/object/archive receipts outside Git. Driver872cc126,
`cumulative-idle`, linked archiveb57fe26e and disabled persistent caches remain.
No CI, reboot, agents, forced signals or GPU reset is used.

| Normal measurement | Fresh997 control10240 | Selected1381 normal10760 |
| --- | ---: | ---: |
| Independent decode |2.719437 tok/s |2.892716 tok/s |
| Independent TTFT |7.779691 s |7.460586 s |
| Independent total |15.857094 s |15.038473 s |
| Exact-repeat decode |3.698140 tok/s |4.534210 tok/s |
| Exact-repeat TTFT |59.810 ms |63.558 ms |
| Exact-repeat total |6.533394 s |5.335282 s |
| Capture-charged pair throughput |1.965120 generated tok/s |2.159641 generated tok/s |

Whole-pair throughput improves9.898685%. Repeated TTFT increases3.748 ms.
These are sequential normal cohorts with the same fixed prompt, not matched
ABBA or broad workload estimates. Independent and retained cache conditions
must remain separate. Individual gains are not added.

Routed Expert Gate/Up stays Q2_K and Down Q2_0 MSE. Output plus144 active
shared-Expert matrices use Q8_0; other weights retain BF16/F32. Activation/KV
remain F32; integer-dot/cooperative matrix paths remain disabled. Cache payload
budget is2,123,243,520 bytes with1382 physical planes. Actual CPU peak503,382,016,
device ledger peak2,470,445,056 and internal workspace capacity8,388,608 bytes
are separate measurements. Fixed CPU/Direct reserves remain512 MiB; workspace
reservation is64 MiB. The software ledger cap is2,480,332,800 bytes. None of
these values is a measurement of free kernel memory.

Same-policy independent complete F32 error is0 with exact ordered routes.
The final retained-cache/mixed-width full-vocabulary difference7.568034 is
finite with identical counting tokens. Fixed task pairs have8/8 correct answer
contents and6/8 strict raw formats: JSON contains Markdown fences. The app
does not normalize that output. The strict-format early failure remains in
10740; only its remaining JSON comparison is run in10800. Sustained service,
long contexts and broad reasoning remain outside this finite qualification.

Placement verifies both current/immediate-control programs and both sets of
five settings with native whole SHA256, stable identity and EOF. Permissions
are restored; fresh idle, no native/gateway owner and unloaded models pass.
The finite run binding is consumed; future execution needs a fresh binding.

Eleven obsolete trial executables are removed with host packages retained.
Deletion of55 previously inventoried old setting backups awaits explicit permission after automatic
review rejected changing their directory protection. No rejected permission
change or repeated DELE is performed. This optional cleanup does not leave a
candidate comparison or production-placement step pending.
