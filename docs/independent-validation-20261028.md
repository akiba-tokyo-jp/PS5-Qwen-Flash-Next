# Independent completion of the remaining native comparisons

This report preserves its original finite dispositions. The subsequent
[width-two qualification](speculative-qualification-20261028.md) completed the
additional same-width/state, eight-input, causal speed and normal-application
gates and adopted the bounded final-prefix handoff. Its current installation
supersedes the width-two-off disposition below; the original failed tests and
measurements remain unchanged.

The selected independent validation decisions and production adoption are now
terminal. Six-demand delivery and exact complete-prefix reuse passed their
128-slot model comparisons and are installed in the original passive monitor/API
application. Prediction remains off after slower observations; width-two work
remains off after exceeding the original numerical tolerance. The failed C2
cohort is not relabeled successful. Broader missing research integrations remain
explicitly unimplemented in the complete 16-family / 22-item ledger.

The independent lifetimes removed an unnecessary C2-to-prefix dependency.
Consumed cases were not replayed unchanged. The old 128-slot production is
preserved as rollback, with the original model, precision and driver retained.

## Changes and fixed conditions

`tools/resident_independent_scopes.py` derives each entry from its exact captured
native source. C2 keeps its original ten requests: warmup, ordinary/prediction
ABBA, ordinary/speculation ABBA and forced rejection. Prefix keeps its original
nine requests, including the cost of capture and both request orders. C4 keeps
its original five requests: warmup plus ordinary/six-demand ABBA. Prefix no
longer depends on C2 completing first, and the separate lifetimes do not retain
two full F32 reference vectors together.

The original vocabulary has 248,320 columns. These fixed demo comparisons
already require all 23 continuation rows. Their reference allocation is now
22,845,440 bytes instead of 32,778,240 bytes, saving 9,932,800 bytes. Every column
and all 23 rows remain checked. The request upper limit stays 32 output tokens;
an unexpected extra reference row fails validation rather than being omitted.
This is a Direct CPU-heap reduction, not a claim of an equal kernel-VM recovery.

The load-only Vulkan upload retains a staging buffer of at most 64 MiB. The new
entry releases only that exclusively owned buffer, after every original upload
fence and command-pool cleanup has returned. The original per-BO allocator
defers a free callback until a positively quiet frontend boundary. Therefore
the entry completes the producer, starts a destruction epoch, runs the ordinary
buffer destructor, completes that epoch, and verifies the allocator's owned-byte
decline before resuming the original context admission. It does not invoke raw
kernel free calls or alter the driver. Completion uncertainty preserves the
original graph for ordinary OS close.

The driver implementation explaining this ordering is
`native/driver/perbo_owner_impl.c::radv_ps5_memory_free` and
`ps5_ai_driver_retire_quiet`, called through
`native/app/driver_lifecycle.cpp::DriverLifecycle::finish_boundary`.
GPU initialization and model load retain the original 1,154-page floor. The
separately scoped postload revision below prices the next context and subsequent
operation separately. Direct/Flexible reserves and the once-only CPU metadata
boundary remain in force. Kernel VM and Direct capacity remain separate resources.

Original BF16/F32 weights, F32 activations/accumulation/KV, all Experts, context
256, prefill four and 512 MiB physical model parts are preserved. Each independent
initial comparison uses 53 slots so its candidate and control are matched.
Separate 128-slot cohorts qualify the actual combination before adoption.

## Execution evidence

| Case | Scope | Current outcome |
| --- | --- | --- |
| 5050 | First staging-destructor attempt | Original model loaded and all 1,816 upload calls returned. The C++ buffer object retired, but physical allocator ownership had not yet declined. The explicit ownership check refused before context or generation. Ordinary OS close and exact 128-slot production/settings restoration completed. |
| 5080 | Corrected C4 at 53 slots | Completed all five requests, complete F32/route comparison, ordinary close and exact production restoration. Decode ratio 1.0265708197x; total-time ratio 1.0204692133x. |
| 5100 | Independent prefix cohort | Warmup stopped at 1,106 free pages against selected 1,154. Normal close/restoration completed; no prefix performance result. |
| 5120 | Independent prediction/speculation/rejection cohort | Three requests completed; later prediction stopped at 1,030 against 1,154. Normal close/restoration completed; matched C2 result remains incomplete. |
| 5160 | First 128-slot delivery combination | Warmup and ordinary control completed; the public activation API still had an independent 53-slot-only guard. Known software refusal, normal close and exact restoration. |
| 5300 | Post-context minimum-plus-64 experiment | Original model loaded, but before-context selected price 1,197 refused at 1,162. The experimental activation was not reached. Normal close/restoration completed. |
| 5320 | Corrected 128-slot activation API | Refused before GPU in the incremental table restorer; its independent arithmetic still charged minimum plus 256 plus the output allowance. The original diagnostic conflated this with restoration/protection failure. Normal close/restoration completed. |
| 5400 | CPU table arithmetic corrected, 128-slot delivery comparison | All 673 tables and 1,250 chunks completed, all original hashes and readonly protection passed. Warmup completed; next request stopped at 1,083 against the original 1,154. Normal close/restoration completed. |
| 5420 | Independent prefix with corrected CPU tables and separate postload/context pricing | All nine requests, 184 complete F32 rows with maximum error zero, and every original Expert route passed. Ordinary close and exact production/settings restoration passed. Two-request total speed ratio 1.3059139973x. |
| 5440 | Independent C2 with the same corrected phase pricing | Six requests completed. The first speculative request completed generation/reset but failed the original full-F32 check. Normal close and exact restoration passed. Prediction's two measured samples were slower; no C2 speed was adopted. |
| 5480 | Actual 128-slot six-demand combination | All five requests, 92 complete continuation F32 rows with zero error, complete original routes and positive common retirement passed. Decode ratio 1.0227047969x; total ratio 1.0181737494x. Normal close and exact restoration passed. |
| 5520 | First Prefix128 + six-demand cohort | Five requests, including the first capture/restore pair, passed. The second capture refused a full new-snapshot price despite the context retaining its previous snapshot. Normal close/exact restoration passed; this consumed case is not a completed cohort. |
| 5620 | Isolated speculative numerical and forced-rejection closure | All three requests, common model/source/device retirement, normal close and exact restoration completed. Actual accepted width-two work produced a finite F32 mismatch; candidate rejected. Forced rejection restored all 23 full rows with zero error. Prediction was not repeated. |
| 5680 | Corrected same-context checkpoint pricing, Prefix128 + six-demand | All nine requests, 184 full F32 rows with zero error, complete original routes and positive common retirement passed. Both capture/restore groups completed under unchanged allocator caps; normal close and exact restoration passed. Pair total ratio 1.3152489439x. |
| 5580 | Actual passive monitor/API production combination | Smoke and both external requests, 23 full F32 rows with zero error, original routes, positive owner retirement and both actual native rasters passed. Normal close, complete native canonical/rollback/five-setting readback and fresh idle passed; candidate retained as production. |

Case 5420 compared ordinary two-request totals of 210,250.7320 and
210,295.3028 ms with prefix totals of 161,004.1423 and 161,027.8105 ms. Both
orders won, with separated observed ranges. The repeated request fell from
104,449.6232 / 104,396.9137 ms to 55,174.3187 / 55,169.8184 ms. Its prefill
fell from 49,228.9858 / 49,166.6110 ms to 31.3603 / 37.7053 ms. Capture and
restore work are included in the measured requests. Decode changed only from
0.3989212 / 0.3989969 to 0.3996304 / 0.3998581 tokens/s; the principal gain is
complete-prompt reuse, not a general decode-throughput improvement. This
qualification uses the same fixed 30-token prompt and 22 emitted tokens.

The first host collection requested the old combined entry's optional VM
sidecar, which this independent success path does not emit. Recovery 5428
preserved the frozen controller, removed only that unsupported diagnostic
request in a recorded runtime copy, collected all five actual cache resets,
all nine F32/results/routes and the explicit phase-pricing evidence, then
normally closed and restored. No native request was repeated. Future
independent collectors use their actual exports.

Case 5480's ordinary decode rates were 0.4086388409 / 0.4086591440 tokens/s;
six-demand rates were 0.4195313086 / 0.4163232610. Both reverse orders won and
the candidate range was separated from the observed control range. Each
candidate used 8,371 actual batches, 50,226 reads and 164,580,556,800 logical
bytes. Source timing/read conservation also passed the original API performance
reviewer offline on all five actual completed requests. The device ledger peak
was 1,690,304,512 bytes under the existing 1,792 MiB cap. Geometry qualification
alone is not used as speed evidence.

Case 5440's ordinary prediction controls were 0.3911526868 / 0.3912116331
tokens/s versus 0.3886292484 / 0.3895018896 with prediction: a 0.9945892446x
observed decode ratio. All six completed continuations had zero F32 error.
The later width-two request accepted one batch, returned through EOG and
positive request reset, then failed the full-F32 validation. The failure
reported 1,626 free pages and no pressure event; it is not a memory refusal.
Its common model/source/device retirement frontier was not reached, so the
partial timing observations are not promoted to a qualified winning cohort.
The original ten-request case remains recorded as failed. A separate finite
closure diagnoses the mismatch and executes the previously unreached forced
rejection; it does not relabel that original case as successful.

The additional refusal in 5520 was traced to the complete checkpoint admission,
not a returned allocation error or a kernel-free-page refusal. The pinned
llama.cpp revision `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`,
`src/llama-context.cpp:3058` (`llama_io_write_device`) retains the snapshot in
`mem_storage[seq_id]` (`state_seq_get_data`, line 3418). Lines 3097–3153 reuse
the existing buffer for unchanged total size, including rebuilding views inside
that buffer when needed. It is owned by the retained context, not by the short
application checkpoint wrapper.

`native/app/resident_checkpoint_capacity.h` prices the first snapshot in full.
Only an actual capture followed by a positive complete request reset registers
capacity for that exact context and payload. The next identical snapshot adds
zero new payload allocation; another size is priced in full and another context
is refused. The original 1,792 MiB aggregate ledger, 512 MiB single-buffer cap,
actual allocator checks and Direct/Flexible reserves remain strict. The changed
entry also records each independent reserve/ledger cause on refusal. This
corrects double accounting rather than claiming memory was freed or increasing
available physical capacity. Actual compiled-helper owner, completion, reuse,
changed-size and refusal controls passed before the new native scope.

Case 5680 measured a complete payload of 119,881,728 bytes and an initial
2 MiB-rounded admission of 121,634,816 bytes. The second same-context capture
required zero additional payload allocation. The reviewer derives that rounded
price from the measured admitted payload, rather than assuming that the earlier
118,038,528-byte minimum is the exact size of every snapshot. The initial
host-only size assertion was corrected without replaying the completed model.
Both full prefix groups passed: ordinary pair totals were 198,234.9029 /
198,405.9835 ms and prefix totals were 150,752.4921 / 150,818.4677 ms. Repeated
request totals fell from 98,110.8161 / 98,123.5948 ms to 50,517.1691 /
50,563.1241 ms. Their prefill intervals were 47,234.5273 / 47,284.0741 ms versus
30.6571 / 31.3349 ms. Decode was 0.4331753 / 0.4335268 versus
0.4367710 / 0.4363282 tokens/s. All 184 F32 rows and original per-token routes
matched exactly after both capture and restore operations.

Case 5620 positively completed one accepted width-two batch, with 23 correctly
shaped finite full-vocabulary callbacks. The first difference occurred at
zero-based callback row 8, vocabulary column 0. Maximum absolute logit error was
1.9925699234, exceeding the unchanged original tolerance. Emitted greedy tokens
matched, but this does not establish numerical equivalence. Conversely, a
maximum taken over all positions and vocabulary columns does not by itself
establish a functional defect or model-quality regression. The saved diagnostic
does not contain per-element arrays, error distributions, top-k margins or
softmax divergences; those cannot be reconstructed from its maximum. The
width-two path remains off pending such qualification. Its forced rejected batch
restored the original continuation: all 23 full F32 rows had zero error.
The shared model/source/device retirement, normal OS close and exact production
restoration then completed. The exact failing GPU operator within the accepted
path is not isolated by this finite diagnostic; the negative adoption decision
does not claim that additional investigation was performed.

The owner's subsequent review requires explicit adoption conditions. The
[same-batch reference, eight-input greedy behavior, accepted/rejected coverage,
matched speed and physical lifecycle criteria](speculative-adoption-criteria-20261028.md)
are now defined. That additional implementation and native qualification has
not run. The existing tolerance failure is preserved without treating its
maximum alone as proof of a defect or silently widening the numerical limit.

The earlier attempt is retained as a software-ordering failure. It is not a
memory-capacity failure or a throughput measurement. No consumed title is
automatically relaunched. Later cases require their own current owner, full SELF
integrity, configuration, native memory admission and ordinary close.

Case 5080's original upload staging requested **8,388,608 bytes**, not the
64 MiB upper bound. Its positive destruction epoch reduced native allocator
ownership from 8,780,759,040 to 8,772,370,432 bytes. Sampled kernel free pages
remained 2,034 before/after. This establishes an 8 MiB owned Direct reduction,
not recovered kernel VM or a universal stability result.

Both six-demand samples completed 8,878 actual batches and 53,268 reads per
request, with 174,548,582,400 logical bytes. All continuation F32 differences
were zero and every original ordered Expert selection matched. Their decode
rates were 0.4016243667 / 0.4015855534 tokens/s versus ordinary
0.3911949210 / 0.3912254485. This 53-slot win is not substituted for the
separately required 128-slot combination.

The native combination additionally required widening both
`ResidentMappedSourceReader::try_owned_bank_batch` and
`configure_native_six_bank_refill`. The actual public activation function now
has host execution for 53/128 slots and six refusal controls, in addition to
the actual native reader's 180 exact reads at slot 127, 30 original residues,
three pre-I/O fallbacks and eight refusal controls. Predictive overlap remains
excluded from six-demand delivery; leases, source identity, EOF, coalescing,
destination separation and maximum two in-flight reads remain unchanged.

`tools/resident_table_admission.py` applies the already selected CPU-only
21-page base to `ResidentTableMemory::permit`; output/scratch allowances stay
20/19. Non-CPU callers retain the original formula. It records mapping versus
first-touch observations, original table/hash counts, scratch state and the
actual protection return code/errno. Case 5400 sampled 3,780 pages before
mapping, 3,779 after mapping and after first touch, and a 3,779 restoration
minimum. The error in case 5320 is not evidence that readonly protection or
an actual allocator failed.

## Explicit experimental phase-pricing revision

The original post-context-only revision could not reach its activation in
case 5300. The current experiment therefore selects its new application
margin only **after the original model load and positive upload retirement**.
GPU initialization and model loading retain their original floor. The next
context is priced separately at 962 + 43 = 1,005 pages. After context creation,
the selected operational price is 898 + 64 = 962 pages. OS minimum/reserved
sysctl values are read without modification; they remain 898/206. The prior
application rule added `max(reserved,256)` beyond the minimum.

The 64-page component screen adds 17 sampled Direct metadata pages, two sampled
idle pages, the earlier 41-page context interval, two context-margin pages and
two selected rounding pages. Those observations are not an exclusive allocation
attribution, an instantaneous peak bound or a universal safe limit. This is a
finite native experiment, with original Direct/Flexible/heap limits, exact
precision, complete numerical checks, unchanged waits and positive retirement.
This exact scoped revision is now included in the qualified production image;
it is not a general admission change. The unexecuted 206-page additive experiment was
superseded after C2's actual 1,030-page refusal showed it would not cover that
observation.

`tools/build_resident_postload_pricing.py` reuses the complete coherent app-object
set and recompiles only the entry. `tools/build_cache128_postload.py` also
recompiles the actual widened 128-slot source owner, preserving the same seven
engine/delivery objects and driver. Each new receipt binds the actual generated
headers and objects; no consumed physical case is replayed unchanged.

Case 5080's first host close attempt failed before building or executing the
close helper because an unrestricted case-number replacement altered a substring
inside its fixed source SHA256. Recovery 5086 preserved the frozen case, checked
the real unchanged close source and empty output directory, and executed only
the not-yet-issued ordinary close and restoration. No inference was replayed.
`tools/case_identifiers.py` now replaces only delimited identifiers and refuses
any changed 64-digit digest; the actual regression and nonrecursive mappings
have host tests. A separate host-only package-read race was corrected to wait
for final integrity and all six segment proofs, not merely a receipt filename.

The three corrected SELF hashes are:

- C4: `4f3540f1ba84876b21fb385aa8986801c21ba26cfbea5845079c13e4f6cade52`
- Prefix: `7e6591d9caa4caa184126fdd5d56e17b49e6e7093523b9c3a3b4da934c2f9902`
- C2: `86563ab341340cc85046cf1a7f98d5377aac9e37531039ab4b00784ec6451c9c`

## Build provenance and checks

`tools/build_independent_resident.py` recompiles only the native entry and the
small upload-buffer extension; later entries reuse the byte-identical buffer
object. Every actual generated source, compiled object, library, toolchain and
private header remains bound to a complete capture. Historical generator/source
aliases that changed after Git integration are disclosed separately; old build
receipts are not edited or rehashed. Line-ending differences are checked against
the exact historical LF digest. Superseded original source aliases never replace
the actual captured source of a reused object. The complete ABI-consistent app
view and seven actual engine/delivery objects are retained.

The host check compiles and executes the actual generated retirement function
with completed/incomplete upload counts, missing ownership, shared ownership,
zero/oversized buffers and exact one-time destruction. Entry checks preserve
original request geometry, F32 bounds, separate cohorts, complete owner
retirement and both positive completion boundaries. Native link/import/dispatch,
original table geometry and all six SELF segment roundtrips passed.

The focused host regressions for complete F32/routes/timing, profile admission,
phase pricing, exclusive upload retirement, bounded case identifiers and
checkpoint capacity passed manually. Tests needing retained private native
sources use the explicit `QWEN_FROZEN_BUILD_DIR` environment variable and skip
when that external evidence is absent; no private data-disk location is required
in the repository. The final profile was also checked offline against the exact
physically qualified private package and policy, preserving every case binding.

`tools/review_independent_resident.py` requires complete native requests,
full-vocabulary F32 continuations, original per-token Expert routes, positive
model/source/device retirement, normal OS close, exact restoration and the
measured upload ownership reduction before evaluating reverse-order speed.
It does not infer model tokens/s from a source fixture or partially completed run.

## Combination and application source boundaries

| Source / function | Concrete integration |
| --- | --- |
| `tools/build_refill_cache128.py::widen_reader` / `widen_controller` | Qualify both the actual private reader and public six-demand activation for 53/128 slots; preserve disjoint leases, source identity and two outstanding reads |
| `tools/build_prefix_cache128.py::generate` | Reuse the coherent 128-slot app/engine objects, retain the bounded loader observer and apply complete-prefix reuse independently of speculative state |
| `native/app/resident_checkpoint_capacity.h::ResidentCheckpointCapacity` / `tools/build_checkpoint_reuse_entry.py` | Price an actual completed same-context snapshot once, retain exact payload/owner binding and allocator caps, and expose each independent refusal cause |
| `tools/build_prefix_delivery_monitor.py::generate` | Keep the original passive VideoOut/API tail, collect all 23 original F32 rows, validate actual capture/restore and six-demand counters, and compare continuation routes after the 30-token reused prefix |
| `tools/expert_route_result.py::validate_routes` | Accept omitted prefill only under explicitly bound 128-slot, 30-prompt/22-output, prefill-four continuation; every decode layer/selection and transfer counter remains required |
| `tools/performance_result.py::validate_performance` / `validate_backpressure` | Price the exact repeated continuation and require explicit native postload/context evidence before accepting the changed application margin; the old default remains strict |
| `tools/qualified_performance.py::apply_profile` | Require an already prepared matching 128-slot layout and immutable runtime scopes; a feature fragment cannot manufacture those admissions |
| `tools/build_speculative_closure.py::generate` | Record the first full-vocabulary mismatch and close forced rejection under the original tolerance; a known finite failed candidate is rejected, never silently accepted |

Prefix and speculative checkpoints share the context's original on-device
snapshot owner. They are not enabled together. A numerical failure is a
failure of the stated equivalence test even when emitted greedy tokens match;
the additional adoption criteria above separate that from a quality verdict.

The source revision remains PS5-Vulkan-Inference
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, linked archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. No CI or reboot is used.

## Production placement and scope

Source revision `b6b54638a6b6dd90328e8fb513e4a6c6ad4af08a` contains the
physically tested implementation. Case 5580 qualified the actual original
passive monitor/API tail, rather than installing a headless benchmark.

| Request | Exact prompt reuse | Decode tokens/s | TTFT ms | Total ms |
| --- | --- | --- | --- | --- |
| 1 | No | 0.4184315797 | 48299.571 | 100890.370 |
| 2 | All 30 prompt tokens | 0.4359474450 | 60.344 | 50613.457 |

Both emitted the original 22-token sequence; all 23 full F32 continuation rows
and ordered Expert selections matched exactly. The actual native scanout-source
rasters visibly showed 0.42 / 0.44 tokens/s, CPU identity and 16 logical threads,
GPU identity/shared memory, advancing UTC time and 22 generated tokens. They
are exact CPU rasters after completed VideoOut flips, not TV photographs.
Unmeasured utilization remains `--`; there are no chat controls.

The model/source/device owners retired positively. The title normally closed.
Final native complete SHA256, stable identity and EOF checks verified the new
17,540,407-byte SELF
`e2821af3cbf7e3bf69ab4ab4c6af5b556a6b3d9b54449abaa13432b55cfd968f`,
the exact previous `56763d373c04e2e684d79b703e5baa1ee1ba26315754f85d97a6162bd1521596`
rollback and all five current settings. Fresh idle confirmed no native owner,
gateway or loaded model. There was no redundant restore/reinstall or relaunch.

The [installation](../config/production-installation.json) and
[qualified fragment](../config/qualified-performance.json) now name that exact
image and its required runtime scopes. Historical installation/profile records
remain separately preserved. This is fixed-prompt, thinking-disabled, bounded
qualification, not sustained-service or general reasoning-quality validation.
The measured ratios have different controls and must not be multiplied.
