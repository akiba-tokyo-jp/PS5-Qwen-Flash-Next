# Delivery follow-up: five native comparisons

The owner authorized native validation of candidates1--5. The control is
placement11050, SELF57043cbe809362e0910e69279caca1a4985c92f93114f0f06dd81ebe81bd2bbf.
All tests use the same PS5 and immutable model sources. Driver872cc126
`cumulative-idle`, actual archiveb57fe26e and disabled persistent caches remain.
No CI, reboot, forced signal, GPU reset or agents are used.

All five candidates have a final disposition. No candidate qualifies for a
production speed update. Keep the installed control and its recorded normal
independent/retained decode3.717603/5.261777tok/s. The last native case11420 is
normally closed; exact program and all original settings are restored with
complete native SHA256/identity/EOF proof and fresh idle services. This closes
the planned comparisons; it does not assert that every failed batch completed
all of its requested timings. The conditional normal/API/display adoption
cohort is not triggered because no headless candidate qualifies.

## Measurement scope

Independent requests start with empty application Expert/KV state in the same
original context. The OS cache is not flushed. Prefix reuse and speculation
are disabled. Keep prefill32, output32/context256, Top6/6, cache1381/1382,
8MiB source scratch, CPU512MiB, physical Direct reserve512MiB, device ledger
2480332800 and workspace48MiB. Do not compare these independent timings with
retained-prefix generation or add overlapping worker wall intervals.

The fixed tasks are counting, Japanese translation, arithmetic and JSON.
Explicit control warmup is excluded from the four-task totals. Same-policy
full-vocabulary F32, ordered routes, token IDs and bytes must match. Semantic
contents and strict raw formatting are recorded separately. Existing JSON
Markdown fences are retained.
F32 covers every vocabulary column at each sampling-observer row (up to33
rows). It is not a separate comparison of every bulk-prefill prompt position.

## Decisions

Positive changes below mean longer whole-request time.

| Candidate | Native result | Decision |
|---|---|---|
|1a: parallel individual admitted bundles | Counting+0.6842%;39 groups/90 individual bundle reads | Tested, no whole-request gain |
|1b: include previously coalesced bundles in four-lane delivery | Four-task sum+0.2964%; counting-0.7416%, translation-0.0092%, arithmetic-3.0450%, JSON+2.4711% | Tested across four inputs; no consistent overall gain |
|2: known-demand queue beyond the12-role barrier | Counting+0.5098%;33 wide groups/2283 role reads | Tested, no whole-request gain |
|3: two or three active reads | About+22.2% and+5.3% against adjacent four-lane controls | Retain four lanes; fixed-depth results do not justify the conditional adaptive-depth extension |
|4: cached numeric memory-counter names, fresh values every time | Timed source-headroom checks329.602301→200.870123ms (-39.0568%); whole11585.673592→11615.781052ms (+0.2599%) | Mechanism works, whole-request gain not established; original fresh observations retained in production |
|5: independent shared-Expert GPU prepass | Buffer-aware implementation submits671 early GPU subgraphs for counting; whole11513.536462→30582.939108ms (+165.6259%), decode3.723656→0.934026tok/s; Japanese F32 comparison also fails | Actual early GPU work tested; severe whole-time regression and mandatory numerical rejection; not adopted |

Candidates1a/2 have positive per-request reset and exact comparisons before the
later returned depth2 failure in11120. The depth2 legacy destination bug is
fixed and host-reproduced against the exact old header hash. Corrected depth2/3
arms5--7 in11160 finish before that cohort's later evidence-array failure.
These are completed, persisted per-arm measurements. Neither failed whole
cohort is relabelled a fully accepted qualification.

## Qualified bundle and numeric comparison11260

All12 native requests complete, all routing bits remain14 and every same-policy
F32 maximum is0. Every owner retires positively with device ledger live0.
Ordinary OS close and exact program/settings restoration complete. Actual
workspace capacity is8MiB, CPU heap peak419495936 and device peak2350907392.

| Task | Four-lane coalescing control, ms | All-bundle candidate, ms | Whole change |
|---|---:|---:|---:|
|Counting |11656.499930 |11570.056519 |-0.7416% |
|Japanese translation |6141.867655 |6141.299701 |-0.0092% |
|Arithmetic |6353.284937 |6159.824698 |-3.0450% |
|JSON |16189.505091 |16589.559779 |+2.4711% |

The counting pair reads6824150368 physical bytes in both modes. Calls increase
11827→11941 when larger coalesced reads are split among bundle lanes. Read-call
mean wall increases1.428634→1.447074ms; median stays within[1.280,1.408)ms,
P95 moves[2.176,2.304)→[2.432,2.560)ms, P99 stays[3.456,3.584)ms. These are
128us histogram intervals for complete synchronous calls, including OS and
scheduling time. They are not raw device latency. Whole time can improve while
individual-call latency or call count worsens because the intervals overlap.

The numeric pair keeps the same6824150368 bytes and11827 calls. Producer source
wait is6836.179953→7007.596319ms while metadata observation saves128.732178ms.
The headroom field includes the timed source-guard path; it is not a direct
isolated syscall-latency measurement.
This single pair does not prove that numeric-name caching causes the I/O-wait
change. It establishes a component reduction without a measured whole-request
benefit under these conditions; it is closed without production adoption.

## GPU lifetime diagnosis

Initial guarded prepass11180 completes four input pairs with exact F32 but
submits zero early GPU graphs: every miss interval has a live-input alias.
Reordering shared-FFN expansion after slot lookup in11220 does not eliminate
the refusal. Its final measurement is rejected for the separate evidence-array
defect below.

Corrected two-request diagnostic11280 completes with exact F32 and routing14.
The actual candidate graph calls set/take/cleared96 times each, confirming that
the intended graph providers and allocation-order hooks execute. The first
refused alias is:

- Writer:`shared_expert_gate-0`.
- Remaining reader:`ffn_moe_slots-0`.
- Still-live input:`ffn_moe_topk-0 (cont) (reshaped)`.

The declared original schedule lets the shared gate reuse selected-ID storage
after the slot lookup. Moving shared work before that lookup would overwrite
IDs still needed by the lookup. The guard correctly refuses this schedule.
`build_overlap_pinned_ids.py` keeps the actual contiguous ID backing and its
view live through the original graph allocator using`ggml_set_output`. Selection
values, dependency/alias refusal and the original48MiB workspace cap remain.
The following final comparison establishes actual submissions, workspace and
the absence of a qualified benefit.

Pinned-ID gated-endpoint comparison11320 completes the warmup pair, an exact
counting control/candidate pair and the Japanese candidate (five successful
requests). Its Japanese control at ordinal5 then fails the unchanged full-F32
gate against that candidate. The remaining candidate batch is stopped; the
failure is retained, normal OS close completes and the exact control/settings
are restored. The conservative failure record retains GPU ownership until OS
teardown; it does not assert manual GPU resource release. No speed result from
this invalid candidate is adopted.

The bounded follow-up keeps the final sigmoid/gating/add in the remaining
graph and selects the raw shared-FFN endpoint. Vulkan can reorder/fuse unary
and multiply operations and recognizes HC post-gate patterns in
`ggml-vulkan.cpp`; separating that terminal group could alter arithmetic.
This is a hypothesis, not the established cause of11320. The follow-up records
full-F32 failure details before preserving the same rejection threshold.

Core-only diagnostic11360 completes two requests with exact F32/routes and
routing14, but still submits zero early graphs. Its first refused alias is
writer`ffn_shexp-0`, reader`shared_expert_gate-0`, input`hc_mixed-0`. The actual
shared input must also remain live while its gate has not run. The final
variant protects both selected IDs and the shared input under the original
allocator/workspace cap.

Protected-input comparison11380 also completes five requests before the
Japanese reverse comparison fails: maximum absolute F32 difference0.0092787743
across two sampling rows, identical token IDs/bytes and a positive request
reset. Early GPU submissions remain0. The counting pair is11513.099852→
11560.306854ms (+0.4100%). This does not establish an answer-quality loss or an
effective GPU overlap. A lower-bound failure collector initially fetched three
results; native completion markers and immutable result files recover the true
five-request prefix. Original failure/close records are preserved.

The dependency fixture also reproduces an additional guard gap: an imported
NONE/view node can have an index inside the graph without regenerating its
value there. Treating only sources absent from the graph as external misses
this live input. The exact old plan065a6dcf accepts a fixture that aliases such
a view; the strengthened plan8b68de15 refuses it and accepts the disjoint
case. This source-level guard defect is established. It is not asserted to be
the sole cause of11320's numerical failure. No dependency or numerical check
is removed to make the prepass eligible.

The next refused pair in11380 is writer`ffn_gate-0` against the separate
Expert-cache down-weight buffer. The actually linked Vulkan object confirms
that`ggml_backend_vk_buffer_get_base` returns the same`0x1000` for distinct
buffers (`movl $0x1000,%eax; retq`). Raw tensor addresses alone therefore produce
false aliases across different device objects. The range key now includes the
allocated device-buffer identity; real host ranges share the CPU address space.
GGML view initialization retains its source buffer, so same-buffer views still
compare in one address space. Host fixtures retain same-buffer/host overlap
refusal and separate different device buffers with equal fake offsets.
This correction changes the representation of the ownership check; no actual
same-buffer collision or numerical threshold is admitted.

Final buffer-aware comparison11420 confirms actual early work:671 subgraphs /
2684 nodes on counting and130 subgraphs /520 nodes on the Japanese candidate.
One Japanese interval still refuses an actual same-space live-input overlap.
The counting pair matches full F32/routes/tokens/bytes but is165.6259% slower.
Producer source wait6776.223257→6625.562232ms decreases slightly while the
consumer path393.088993→6039.196970ms grows substantially. That path includes
prepass completion before scatter. The remaining whole-time increase also
includes graph/submission/control work; no exact low-level driver attribution
or raw SSD speedup is claimed. There are no GPU timestamp queries in this test.
Early-submission counts establish submitted and positively completed work;
they are not a direct GPU/SSD interval-overlap measurement. Actual workspace
capacity remains8MiB under the original48MiB cap.

After five successfully recorded requests, the Japanese control at ordinal5
again differs by maximum0.0092787743 across2 observer rows, with the same token
IDs/bytes and positive request reset. The same difference existed in11380 with
zero early submissions, so it cannot be attributed solely to asynchronous GPU
execution. The original F32 gate is retained. The four remaining arithmetic/
JSON timings for this rejected implementation are canceled, not left as an
untested candidate. The native failure retains owners until normal OS teardown;
no manual GPU release is asserted. Exact restoration and fresh idle complete.

Candidate5 is closed as a tested implementation rejected for measured regression
and numerical qualification. This is not a claim that GPU/I/O overlap is
physically impossible on PS5. No additional variant is queued by this plan.

## Preserved failures and correction

The depth2 legacy API originally refilled a two-lane lease while its four-job
caller still expected all four original targets. An exact-old-header host
reproduction fails; the corrected implementation preserves those original
targets at depths2/3/4 and passes short-read/admission/consumer-failure drains.
The failed11120 native launch is consumed, normally closed and restored.

The comparison harness inherited a nine-element`CompletedRouteEvidence` array.
Extending the request count to10 without resizing it made ordinal9 an
out-of-bounds write. In11160 and11220, first-nine policy bits are14 and the
tenth/terminal field changes to0. Both whole qualifications are rejected and
preserved. This is not evidence of a numeric-sysctl ABI fault. No constant or
collector assertion is relaxed to accept the records.

`finite_route_capacity.py` declares request count before the array, derives
array capacity from that constexpr and changes every access to`.at()`. The
generated12-request source and every lifecycle limit are checked before11260;
all12 native policy fields and the terminal remain14. Host regression tests
reject count drift, unchecked accesses and unsupported bounds. The installed
three-request program has sufficient nine-element storage.

A host-only output-directory collision11220 occurs after returned upload but
before pending native verification. Its immutable failure and returned transfer
are preserved. A fresh verifier proves full pending SELF SHA256/identity/EOF
before the one temporary publication; there is no re-upload or launch replay.
Temporary test placement is explicitly distinguished from production adoption.

## Source map

| Source | Functions / purpose |
|---|---|
|`native/app/delivery_read_pool.h` |`DeliveryReadPool::run`, `read`, `select_depth`: bounded leases, known-demand refill and legacy destination retention |
|`native/app/delivery_bundle_source.inc` |`upload_delivery_bundles`: original scratch, three projection consumers and source identity/completion guards |
|`tools/build_delivery_followup.py` |`main`: replace the actual selected source owner/cache/memory providers; individual bundles, wide queue, depth and fresh numeric modes |
|`tools/build_bundle_all_variant.py` |`main`: coalescing versus independent four-lane bundle delivery |
|`tools/build_bundle_delivery_quality.py` |`paired_link`: excluded warmup, four input pairs and optional separate numeric pair |
|`native/app/numeric_memory_counter.h` |`NumericMemoryCounter::value`: resolve each numeric name once, read and validate every value anew |
|`native/app/delivery_overlap_plan.h` |`DeliveryOverlapPlan::inspect`: dependency closure, side effects and live input/output refusal |
|`native/app/delivery_overlap.cpp` |`range`: device-buffer address-space identity; `qwen_app_overlap_begin`, `before_scatter`, `after_split`: early submission and positive-fence graph restoration; graph-mode epoch and bounded alias diagnostics |
|`tools/build_delivery_overlap.py` |Select the actually linked patched scheduler object, preserve its source callbacks, inject prepass/scatter/split hooks |
|`tools/build_overlap_ordered.py` |Qwen4Exp`graph::build_layer_ffn`, common`build_moe_cache_slots`, context graph-reuse epoch |
|`tools/build_overlap_diagnostic.py` |Actual graph-hook counts/alias and full-F32 failure sidecar; bounded two-request diagnosis or excluded-warmup four-pair qualification; optional protected shared input and raw-FFN endpoint |
|`tools/build_overlap_pinned_ids.py` |Protect actual selected-ID root/view lifetime before shared graph expansion |
|`tools/finite_route_capacity.py` |`bind_route_capacity`: request/evidence capacity coupling and bounds-checked access |

Generated native providers, exact private source hashes, immutable parent
receipts, link maps, console journals and SELF readbacks remain on the data
disk. They are not committed with endpoints, run bindings or binaries. The
original patched scheduler provider8c6c91e1 is verified as the actual control
input. The overlap variant replaces that exact object with an audited derivative
retaining its callbacks; substituting the original archive member is refused.
Upstream llama.cpp remains0a1ef309.

Host fixtures cover actual generated source ownership and8MiB canaries, mixed
projections,1--4 bundles,60/96-job queues, depths2/3/4, admission/short-read/
consumer failure drains, numeric observation freshness, dependency/alias
refusal and route-capacity drift. Manual checks only; no CI.

DeliveryReadPool's legacy timing interface populates batch count and enclosing
wall time. Its dispatch-sum and tail-idle fields are not populated; their zeros
must not be interpreted as zero dispatch overhead or zero tail. Per-call
histograms and the producer wait interval are separately measured.
