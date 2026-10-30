# Cold and different-input request results

The five finite candidates are decided. The qualified selection combines
prefill32, exact indexed window0 probation and continuous four-lane demanded
reads across Gate/Up/Down. Placement11050 is complete in
`cold-request-adoption-20261030.json`, with exact current/immediate-control
programs, both five-setting sets, ownership and fresh idle verified.
Implementation revision is`2f7ab770a750b1008fe85aa3646570783de1d8d0`.
Complete sanitized measurements are in `cold-request-results-20261030.json`.

## Normal application comparison

These are normal, sequential cohorts on the same PS5/model, not an ABBA trial.
Both use the selected approximate Top6/cache-aware routing and existing
complete-prefix/causal reuse. Independent means an empty application Expert
cache and model context, not a flushed OS or SSD cache. The prompt has30 tokens
and generates22 tokens; decode excludes the first generated token. Request
totals charge the existing checkpoint work. Output/context limits stay32/256.

| Metric | Installed control10760 | Selected10970 | Change |
| --- | ---: | ---: | ---: |
| Independent decode |2.892716 tok/s |3.717603 tok/s |+28.516% |
| Exact-repeat decode |4.534210 tok/s |5.261777 tok/s |+16.046% |
| Independent TTFT |7.460586 s |5.719974 s |-23.331% |
| Independent whole request |15.038473 s |11.635879 s |-22.626% |
| Exact-repeat whole request |5.335282 s |4.609774 s |-13.598% |
| Capture-charged pair throughput |2.159641 tok/s |2.708417 tok/s |+25.411% |

Every counting token is unchanged. The independent same-policy, full-vocabulary
F32 repeat error is0. The final unlike-cache/width comparison is approximate:
maximum3.935983, finite, with the same emitted tokens. This is not a claim of
BF16 equivalence or broad reasoning quality.

## Different-input delivery comparison

Case11010 runs eight requests, two per fixed task, with empty application
caches, prefix reuse and causal speculation disabled. Delivery order alternates
off/on then on/off. Width32, indexed policy, arithmetic and quantization remain
identical. All ordered route records, tokens, output bytes and complete F32
logits match exactly within each pair. Native request/startup/reset evidence
binds1381 slots; the inherited route JSON descriptive `cache_slots` label still
says867 and is not used for geometry admission.

| Task | Legacy delivery | Continuous delivery | Whole-time reduction |
| --- | ---: | ---: | ---: |
| Counting |15.315187 s |11.491367 s |24.968% |
| Japanese translation |7.007512 s |6.077419 s |13.273% |
| Arithmetic |7.394449 s |6.116928 s |17.277% |
| JSON extraction |19.305582 s |16.451497 s |14.784% |

Total time is49.022730 ->40.137210 s, an18.125% reduction. All eight contents
are correct. Strict raw format is6/8: both JSON answers retain Markdown fences.
Host semantic grading parses those fences without changing application output.
This is four fixed pairs, not a statistical population or sustained-load test.

## Candidate decisions

| Candidate | Evidence | Decision |
| --- | --- | --- |
| Prefill32 and workspace48 |10930 completes after the original10890 checkpoint ledger refusal; initial bytes/calls fall; independent total13.695504 s |Adopt |
| Indexed probation |10830 reproduces every actual victim at997/1381 and4096-observation aging;10870 native policy planning65.192 ->10.294 ms with identical bytes/routes |Adopt |
| Cross-projection four-lane demanded reads |10910 independent total12.788926 s, decode3.502166; combined10970 and all four reversed-order input pairs improve |Adopt |
| Past-only layer quotas |10842 frozen-route misses: control4878/461, linear5304/499, square-root5146/508 |Both specific policies tested worse; no native rerun |
| Early actual-router forecast |10990 observer completes; independent total15.242285 vs15.075218 s/control10850, decode2.820556 vs2.888867 |Close this observer without adoption; physical speculative reads screened out |

The layer screen does not exhaust all allocation strategies. The forecast
screen does not establish that every predictor is ineffective. It measures
the actual layer23 pre-attention F32 Top6 prediction:113 predicted nonresident
Experts,33 actual misses,6 useful intersections in the independent request.
Median lead is1.830 ms; callback wall is169.611 ms/request. Even summing useful
leads separately for all three projections yields only33.998 ms of optimistic
overlap. Callback wall includes preceding synchronization and is not an
isolated incremental kernel cost. The actual observer's whole-request and
decode results establish no benefit; wrong-read traffic would require separate
justification. No physical predictive SSD reads were executed or adopted.

## CPU and I/O decomposition

Control diagnostic10850 versus selected10970, independent request:

| Counter | Control | Selected |
| --- | ---: | ---: |
| Physical source bytes |7.705364 GB |6.824150 GB |
| Physical read calls |13,895 |11,827 |
| Producer source wait |9.986150 s |6.749878 s |
| Wait/model-process interval |71.498% |64.077% |
| Cache planning |65.192 ms |8.958 ms |
| Source handle management |73.630 ms |81.167 ms |
| Source headroom/identity checks |173.944 ms |445.613 ms |
| Source consumer/copy interval |433.809 ms |391.318 ms |
| Mean syscall-inclusive read |1.514411 ms |1.398340 ms |
| Read P50 |[1.408,1.536) ms |[1.280,1.408) ms |
| Read P95 |[2.048,2.176) ms |[2.048,2.176) ms |
| Read P99 |[2.432,2.560) ms |[3.072,3.200) ms |

Traffic drops11.436%, calls14.883%. The retained request drops0.735396 ->0.627773
GB and1734 ->1529 calls. Individual tails worsen: selected P99 is higher and
retained P95 rises to[2.432,2.560) ms. Admission selects whole-request/TTFT/decode
improvement; it does not claim every latency percentile improves.

The four read workers reuse the existing four2 MiB scratch leases across up to
12 already-known role reads, refilling after positive completion and producer
consumption. The producer alone scatters into existing GPU banks. Adjacent
coalesced groups retain their previous path. There are no extra GPU buffers,
speculative reads or enlarged cache. Additional guard calls explain some CPU
management growth; removing guards was not necessary to obtain the speedup.

Histogram bins are128 us. Syscall wall includes OS/filesystem/device work and
does not isolate raw SSD service time. Parallel syscall sums overlap; the
selected16.538 s sum is not added to request time. Producer wait excludes
consumer and producer metadata time in the composition; older10910 streaming
counter semantics differ and must not be pooled as isolated SSD wait.

## GPU diagnostic

Case11030 uses the identical previously qualified timestamp provider, pinned
driver and unchanged shader math. It keeps5-second per-graph fences, valid
64-bit timestamps at10 ns/tick and no query WAIT. All three requests, positive
owner retirement, ordinary close and exact restoration complete.

| Timestamp group, independent request | Measured kernel intervals |
| --- | ---: |
| Q2 MoE matrix operations |226.504 ms |
| Output projection |106.846 ms |
| Shared Expert matrices |138.594 ms |
| Attention/SSM-labelled work |751.263 ms |
| Other/fused terminal groups |1333.773 ms |
| Separately identified Q2 conversion |0 intervals |

Total observed intervals are2.557 s. Zero separately identified conversion
intervals does not make conversion free: fused ranges are attributed to their
terminal nodes. In the same diagnostic, producer source wait is6.758 s and
model-process time10.644 s. Isolated timestamp scheduling changes execution;
neither these sums nor a wall-time residual are an exact ordinary GPU/CPU/SSD
percentage. Remaining ordinary time includes graph dispatch, synchronization,
CPU work, external copies and checkpoint/capture work. No specific shader
optimization is claimed from this campaign.

## Exact source application

| File/function | Selected change |
| --- | --- |
| `tools/build_cold_request_variant.py: main`, mode`prefill32` |Update native entry/adapter/context bounds, completed-route bookkeeping and causal capacities consistently to32; retain all prompt outputs |
| `tools/build_cold_workspace.py: main` |Tighten fixed workspace reservation and enforced capacity64 ->48 MiB without raising total device/CPU/physical limits |
| `native/app/indexed_probation_policy.h: observe, replaced, victim` |Maintain exact window0 two-touch eviction ordering and per-layer eligibility without scanning every resident per demand |
| `native/app/streaming_read_pool.h: worker, run` |Four bounded workers; producer callbacks before lease reuse; stop submissions and drain known live reads on failure; retain uncertain owners on timeout |
| `native/app/streaming_q2_source.inc: upload_Q2_stream` |Validate extents, identities, schedule and physical headroom; reuse the original8 MiB scratch; count returned bytes |
| `native/app/streaming_q2_cache.inc` |Gather only demanded Gate/Up/Down source extents and scatter completed data into owned existing cache banks |
| `tools/build_cold_composition.py: main` |Relink the tested entry/cache/owner providers, maintain indexed replacements and subtract producer metadata/copy time from source-wait accounting |
| `tools/build_cold_quality.py: paired_link` |Toggle delivery only at positive source-idle boundaries; pair four inputs with exact F32/routes and alternating order |
| `native/app/cold_router_forecast.cpp: evaluate_cold_forecast, cold_forecast_begin, qwen_app_cold_forecast_demand` |Diagnostic only:96 bounded observations, actual Top6/readback, residency and lead; never linked into selected production |
| `tools/build_cold_forecast.py: main` |Diagnostic shadow router in upstream`src/models/qwen4exp.cpp`; bind callback in initial context params because`llama-context.cpp` resets scheduler callback from cparams |
| `tools/build_current_gpu_diagnostic.py: reuse_link` |Reuse only when generated GPU source, original object and driver match; diagnostic provider excluded from selected production |
| `tools/cold_request_production.py: require_cold_request_production` |Exact SELF/model/driver,32/48 profile, independent quality, positive retirement and current/immediate-control placement admission |

The upstream model/provider snapshot is llama.cpp
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`. The driver remains
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, cumulative-idle, archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Private link/package receipts retain exact generated sources, original provider
objects, compiler/link commands, archive digests and SELF roundtrip evidence.
The application source commit and selected SELF are recorded at placement.
This campaign changes application delivery/bookkeeping, not the driver.

## Memory, failures and limits

Cache1381/1382 planes remains2123243520 bytes. CPU peak503382016 stays under
512 MiB; ledger peak2472542208 stays under2480332800. Actual workspace8 MiB
stays under48 MiB. The512 MiB physical Direct reserve, kernel/Flexible guards,
750780416-byte single-buffer limit and all ownership/fence checks remain.
The ledger is not physical or kernel free memory. Experts stay Gate/UpQ2_K,
DownQ2_0 MSE; output/shared144 projectionsQ8_0; activation/KVF32.

Initial10890 returns a checkpoint refusal with8986624 bytes of software-ledger
shortfall. Ordinary close and exact control restoration complete before the
changed48 MiB variant. Initial forecast10950 returns a missing-callback failure;
the corrected initial-cparams binding completes10990. The first11010 host stage
check finds a missing local frozen input before any staging/launch; supplying
that input permits the still-unlaunched case. No failed native launch or POST
is replayed. No reboot, forced signal, GPU reset, CI or persistent cache is used.

All five finite decisions and selected qualification are complete. Physical
predictive I/O was screened out, not relabelled an implemented test. Broader
predictors, long contexts, sustained service and broad reasoning remain outside
this bounded campaign. The separately pending deletion of55 old setting backups
does not affect these results or the new placement.
