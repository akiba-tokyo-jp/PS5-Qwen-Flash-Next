# Submission measurements and resident slot-map outcome

The requested measurements and prototype implementation were performed. The
full-model numerical cohort57500 did not complete and the prototype is rejected
for production; no new speedup is established. Console recovery and requested
SSD cleanup are now complete in `SSD-cleanup-20261101.md` / `.json`.

## Measured results

Two complete14-request model cohorts were collected and ordinarily closed with
exact9824 restoration:56400 and56900. Independent monotonic platform counters
and bounded GPU timestamps are qualified in56900. Its query pool was created
and destroyed once,111315 role ranges were measured, and no range remained.

| Retained diagnostic quantity | First request | Independent repeat |
|---|---:|---:|
| Whole request |2300.016 ms|2288.112 ms|
| Accepted decode wall |1809.835 ms|1796.529 ms|
| Selected GPU role ranges during accepted decode |212.941 ms|209.547 ms|
| Source wait, whole request |427.890 ms|423.356 ms|
| Sequence wait, whole request |653.785 ms|650.621 ms|
| Actual thread sleep |8.861 ms|7.758 ms|
| Submit lock wait |4.062 ms|4.074 ms|
| Command copying |6.335 ms|6.334 ms|
| Pure native AGC syscall |25.396 ms|25.189 ms|
| Nonempty submissions |4423|4423|
| Dedicated claims / ring overlap waits |0 /0|0 /0|

The scopes overlap. Sequence waiting includes useful GPU execution and must
not be labeled entirely removable CPU overhead. The selected GPU roles do not
cover every GPU operation; the remaining wall time is not automatically CPU
compute. Diagnostic overhead is99.705 ms,4.544%, so these rates are not new
production performance. Sleep, lock and command-copy costs do not justify a
whole new driver ABI or aggressive wait-policy changes from these measurements.

Initial56400 platform fields40..42 are withdrawn: the legacy getter resets its
logging counters. The corrected observer uses independent monotonic counters
while preserving the original logger, syscall, allocator and wait policy.
The other initial driver counters remain valid. Do not combine the withdrawn
fields with the corrected measurements.

The base driver is872cc1264ad8ba5d6b888b092968fa5858a38c58, cumulative-idle,
Mesa1ba9874f478657ccf6da72ce55f0260164cc0bd0. The original application's cold-table
archive isa325dcd4584b1f1fccc6b46e90faa081ca86d18544aca610efea9e3ca3774f32.
Diagnostic overlays and timestamp instrumentation are isolated from the
performance prototype. Persistent shader/pipeline caches remain disabled.

## Implemented and tested prototype

`native/app/resident_slot_maps.h` retains one512-entry I32 map per layer and
compares all authoritative CPU bytes before omitting an unchanged upload.
The original selected-ID download/synchronization, cache planning, required
Expert loading, routing, precision, capacity and completion controls remain.
`tools/build_resident_slot_maps.py` modifies the actual cache provider's
`llama_moe_cache::impl::copy`, rather than a historical unused cache source.

Initial57100 encountered a metadata assertion: `ggml_set_input` was called on
a VIEW tensor. This happened before this map buffer's device allocation. The
preceding startup work had a positive checkpoint. The owner was ordinarily
closed and exact9824 restored. The fix leaves the owning NONE tensor as input
and preserves each view's VIEW operation.

Corrected standalone57400 passed36 GPU I32 lookups across unchanged reuse,
changed maps and cross-layer destination rebinding. All lookup values, complete
maps and surrounding guards were exact. Device live bytes reached zero; owner
retirement, ordinary close and exact9824 restoration passed. This is a
standalone result, not proof that scheduler-owned model tensors can be rebound.

Full-model57500 was launched once. The last readable phase was
`inference_before_decode_call`; no complete model result was obtained.
Subsequent file HTTP reads, a separate read-only FTP attempt and a read-only
shell capability observation did not respond. Process inventory did respond
and still contained the native owner. This establishes loss of usable
observability, not a proven whole-console freeze or an identified GPU fault.
No additional GPU execution, ordinary-close call, forced signal, reboot or
manual GPU release was issued after this loss of observability.

Neither speedup nor full-model output equivalence is established. The failed
candidate cannot enter production. The model builder now refuses this
prototype; `prepare_first_case.py` also refuses its full-model receipts.
The unused normal-composition draft was discarded without building it.
Actual original normal and standalone receipts remain admissible. The existing
frozen57500 collection/close/restore inputs are unchanged and still validate.

## Required architectural change before reconsideration

The copy callback currently rewrites an already allocated destination's
`buffer` and `data`. That is not a qualified GGML scheduler allocation contract.
The standalone oracle does not exercise scheduler allocation, prefill-to-decode
graph changes, cached graphs or all view/descriptor relationships. This is an
identified design gap; it is **not** a confirmed explanation of57500.

A replacement must register cache-owned GPU input storage before graph
allocation, through the scheduler's input-copy creation path and
`ggml_gallocr_init_tensor`. `ggml_backend_sched_copy_input` must still invoke
the authoritative MoE callback. `llama_moe_cache::impl::copy` may then update
the already bound storage and omit identical bytes without changing any live
tensor address. View initialization and backend descriptors must see that
storage from their first construction. Preserve original ID synchronization
and one producer; never infer safe reuse from an address/content match alone
when the graph allocator can reuse that address for other values.

Required proof is a real CPU/Vulkan scheduler fixture with graph rebuilds,
prefill30 to decode1 transitions, graph reuse, view descendants, cross-layer
updates/evictions and complete guards. Then require matched model full-F32,
routes, tokens and source-demand equality; repeated whole-time improvements
must exceed control A/A spread. Finally compare the actual normal/API/display
app against the original9824 program, including cold, retained and prefix cases.
These are new-design admission criteria, not pending tests of a selected winner.

## Current installed state and outstanding recovery

The qualified production selection remains exact9824, sourcec60c1ab8, with
normal56100 rates9.759321 cold,11.574572 retained and12.801323 prefix tok/s.
Those are the last qualified rates, not a measurement of57500.

At the time of the interruption the test executable was483ee6d8. After an
externally observed new boot, exact9824 and all five settings were restored.
PS5 itself verified11 complete file SHA256/identity/EOF checks and518 complete
source metadata identities. The rejected trial executable and old copies were
removed from the console. The old cohort is not declared numerically complete.

File/control transports are responsive and native/gateway/model are inactive.
The current optional compatibility runtime is not loaded and fresh shader CPU/
model admission is pending. No new inference was run as part of recovery or
cleanup. Do not replay57500 or use its previous boot's launch/close bindings.
Reboot remains unavailable for planning; none was executed by this agent.
