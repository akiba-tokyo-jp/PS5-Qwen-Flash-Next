# Validation plan for remaining Flash Next proposals

## Final current-environment disposition

The owner's latest instruction is to execute available work and classify the rest
as execution unavailable. The [final 22-stage ledger](final-current-environment-dispositions-20261027.md)
now supersedes all current-status and prospective next-step wording below.
Every stage has a finite decision; no item is waiting for user action or reboot.
This current queue is closed with explicit execution-unavailable outcomes.
Missing code remains unimplemented and unrun native tests remain unrun; the
original all-implementation/native-validation speed objective is not achieved.
Earlier case records remain historical and must not be replayed unchanged.

Plan date: 2026-10-26. **This plan itself does not implement or validate proposals.**
Execution outcomes are tracked in the [progress record](remaining-validation-progress-20261026.md).
The owner's latest request is to review and replace the inefficient execution
sequence. The [current execution queue](#current-execution-queue-after-plan-review)
below supersedes earlier priority lists and prospective "next test" paragraphs.
The technical work packages and consumed cases retain their original scope and
results. The [memory-first PLE sequence](PLE-memory-first-plan-20261026.md)
remains a reference for that later comparison, not a prerequisite for all work.
The regular prelaunch margin is not an established PLE hardware minimum.
Current dispositions
and historical results are in the [plan index](plan-index.md). Planning does not
start a console session or change the installed application.
The [status and constraint-origin classification](plan-index.md#verification-status-and-origin-of-execution-constraints)
separates not-run/not-implemented stages, revisable policy blocks and demonstrated
resource/API limits. The selected memory/cache budgets are not physical minima.

The objective is faster original-precision inference on the existing single PS5,
with independently reported TTFT, generated tokens/s and resource safety. Preserve
the exact [production artifact and rollback](production-installation-20261025.md),
[qualified profile](../config/qualified-performance.json), original BF16/F32,
F32 KV, every expert/PLE, driver `872cc126` / `cumulative-idle`, disabled persistent
caches. Preserve production budgets; explicitly scoped experimental budget
changes require actual accounting and fresh native admission. The old selected
caps are not hardware maxima. No second Flash-Next machine is required.

## Radiance references and applicability

Radiance-inspired candidates are integrated into the existing work packages,
with no new runtime dependency. The inspected source reference is the
[`magiccodingman/vllm-radiance` fork at `1d2e24849c9d8441b9614acade5252c9937a2bbf`](https://github.com/magiccodingman/vllm-radiance/tree/1d2e24849c9d8441b9614acade5252c9937a2bbf).
It is a continuation of the original vLLM fork, distinct from the author's newer
standalone Radiance engine. The original author records that transition in the
[vLLM image notice](https://hub.docker.com/r/stilldeadcode/vllm-radiance).
No standalone-engine source audit or PS5 performance result is implied here.

| Reference mechanism | Existing work package | Transfer decision and first gate |
| --- | --- | --- |
| [Metadata reuse](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/patch_gdn_metadata.py#L1-L29), `_radiance_arange` / `_radiance_empty_idx` | Order 1, CPU metadata audit | Cache only invariant data and omit unused work after proving an analogous native cost. The native C++ engine has no Python/Torch dispatch chain to remove |
| [Temporary lifetime and gate-parameter reuse](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/radiance_gdn.py), `_gate_params` / `forward_core_fused` | Order 2, allocation lifetimes | Audit repeated casts, copies and retained layer temporaries. Reuse original F32 constants; no extra converted weight corpus or claim of an existing native leak |
| [Dual-output input projection](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/radiance_gdnmerge.py#L1-L28), `_merge_one` / `merge_model` | Order 8, graph and kernel specialization | Reuse a shared activation across original projections without quantization or a second weight pack. The donor implementation merges MXFP4 rows; its packed layout is not a BF16 solution |
| [GDN fusion and strided gates](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/radiance_gdn.py), `_plan` / `conv_prep` / `recurrent_update` / `output_norm` | Order 8, graph and kernel specialization | Check original F32 intermediates, state and sigmoid output gate before a Vulkan design. RDNA4 HIP/WMMA kernels and device-wide barrier assumptions do not transfer directly |
| [Shape-specific small GEMM](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/radiance_gemm.py), `config_for` / `maybe_gemm` | Order 8, graph and kernel specialization | Measure actual one/two/four-token shapes against the adopted indexed-vector route. Donor BF16-input/output and `M>=6` eligibility do not match the current F32 path or its token widths |
| [Adaptive draft depth](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/radiance_draft.py), `_batch_ceil` / `_install_drafter_hooks` | Order 7, after complete checkpoint qualification | Adapt width using accepted-token benefit and discarded I/O; first keep the model-free draft. No borrowed MTP confidence thresholds or extra draft-model weights |

These are source-observed design references and proposed PS5 adaptations, not
measured PS5 improvements. Before any code reuse, check the exact donor/library
licenses and retain attribution. FP8/MXFP4/INT2, approximate verification heads,
multi-GPU all-reduce and reduced-precision KV are excluded from this plan.
Keep the existing application/driver and persistent-cache policy. Do not copy
the donor's speculative exactness claims: its current
[README qualification](https://github.com/magiccodingman/vllm-radiance/blob/1d2e24849c9d8441b9614acade5252c9937a2bbf/README.md#L6-L14)
still marks strict cross-mode output equivalence unpassed.

## Work order and dependencies

### Review findings, 2026-10-27

Reviewed against main `5887b1f39325502468ebb7b762a3367a43aa7315`. This revision
changes planning only: it executes no application, hardware test or CI and
changes no runtime margin, model, driver, precision or production selection.

| Planning failure | Evidence | Correction |
| --- | --- | --- |
| Work moved away from the nearest model comparison | Cache 128 already has native 120-case/360-graph geometry proof and a model-result reviewer. Work then expanded to independent buffers and a coordinator whose complete native/model runner is still unfinished | Finish the common startup prerequisite and cache comparison first; freeze new ready-expert implementation until its queue position |
| Diagnosis acquired new subprojects without an end condition | Metadata, reservation, quiet-start and controller-residency scopes completed; the proprietary kernel owner remains unresolved and allocator-zone nodes are unavailable | Reuse those results. A further diagnostic must name a specific code change or candidate decision it can resolve; full kernel-owner attribution is not a prerequisite for every candidate |
| Admission rules contradict each other in prose | A universal 10142-page sentence coexisted with separately scoped prefix/cache/PLE cases | Keep regular defaults and immutable case records, but give each future experiment one authoritative admission record, with phase, formula, evidence and failure action |
| More builds, checks and merges were treated as progress endpoints | PR 28 contains build-qualified components but no new physical overlap or model-speed result | Measure progress by the next model comparison or an evidence-based terminal decision; a build/merge alone does not close an execution package |

### Current execution queue after plan review

**One active native comparison at a time.** Keep one implementation deliverable
active, with no general research in parallel. A blocked native case may be
parked with its exact prerequisite while one already specified, independent
host deliverable proceeds. Do not switch to another console candidate that
shares the unresolved startup failure. Reboot is unavailable and is neither a
dependency nor a pending user action. Preserve all proposals in the backlog;
deferral is not rejection, completion or physical impossibility.

**Later owner instruction:** process each item to a finite decision. When a
supported reduction cannot be implemented or a stage cannot execute in the
current environment, record that exact unavailability and proceed to the next
independent item. Do not keep every package waiting on kernel-owner attribution.
The [current-round disposition table](plan-index.md#finite-current-round-dispositions-2026-10-27)
records those decisions. Unavailable implementation, unavailable native
validation and dependency-gated integration are separate outcomes; none is a
passing test or a declaration of permanent physical impossibility. The ordering
below remains a preference among executable items, not a global stop condition.

| Step | Work to perform | Evidence to reuse | Exit decision |
| --- | --- | --- | --- |
| 0. Make the existing model comparison executable | Review the completed production/control and refused startup traces offline. Map launch, SELF/receipt integrity, metadata and virtual-source phases to `native/app/native_main.cpp`, `direct_integrity.cpp` and `model_mapping.cpp`. Identify a concrete removable owned cost or a justified scope-specific admission change before editing/rebuilding | Production 2240; refusal 2860/restore 2865; metadata 2920; reservation 2950; quiet-start 2970; current-boot shader 2812 | One exact candidate executable/configuration, one complete memory ledger, and one finite admission decision for the model cohort. The 23.1 MB fixture's file size does not prove its kernel cost or make it an inference runner |
| 1. Compare 53 versus 128 cache slots | Use the implemented cache switch and reviewer; keep the same original model, context, precision, workload and other optimizations. Run A53/B128 then B128/A53 with complete output, route, resource and latency evidence | Native geometry 2840, 15-capacity route replay, allocation ledger and strict cache-128 reviewer | Adopt only a repeatable full-model winner after production placement/checks; otherwise record rejected or inconclusive and retain the fastest control |
| 2. Qualify and measure exact width two | Use the existing causal controller and complete-state checkpoint. First establish actual acceptance and forced rejection/restore correctness. Then run a separate same-model speed cohort with the 53-slot control, keeping cache-capacity changes separate | Native checkpoint continuation, 30 adapter controls, existing causal history screen and result reviewers | Native correctness, then speed/adoption decision. Width four/adaptive depth stays deferred until width two supplies a measured reason |
| 3. Close existing PLE/prefix comparisons | Complete their already specified finite comparisons after the shared model-startup path is established; retain their own metrics and exact configurations | Existing PLE numerical evidence, current-boot shader proof, complete checkpoint and implemented prefix consumer | A result for each tested scope; a PLE fixture win still needs model TTFT/decode verification |
| 4. Resume ready-expert overlap | Finish the missing native two-wave and model connections only at this point. Compare one-graph serial, split serial and split overlap, preserving whole-expert readiness and original-order reduction | PR 28 allocation owner, coordinator, serial graph and backing fixture; existing original packs | Physical backing/numerics and overlap benefit before model integration; reject a losing variant without further integration |
| 5. Follow measured evidence for the remaining backlog | Actual router observation/forecasting, further cache sizes, workload extensions and specialized kernels retain their package definitions | Existing traces, prototypes and eligibility screens | A measured profile must identify the target cost; keep each unimplemented/unrun item explicitly open until its own decision |

Cache 128 is first because implementation and native geometry are already
available, subject to current admission and the remaining work, not because
past implementation effort guarantees value or its speed is known. Its rounded
bank allocation increases from 510 to 1218 MiB, a 708 MiB increase. Price that
increment and all retained owners in the GPU/Direct ledger separately from
kernel free pages. Width two is not automatically cheaper: price its checkpoint
and width-two workspace from the existing evidence too. If cache capacity alone
cannot retain its required reserves and width two demonstrably can, width two
may move first with that reason recorded. A shared pre-GPU startup refusal is
not solved by changing candidates. Saved routes predict 4.8993% fewer
uploads across the recorded external requests and 6.9263% in one-token
processes; those are traffic estimates. Width two has only host causal proposal
matches, not measured native acceptance or speed. Ready-expert work requires
more missing integration, while the old 92.435% source-wait profile gives only
a conditional 1.082x ideal process-time ceiling for hiding unchanged compute.
These facts support the order; none promises a tokens/s gain.

For cache and speculation, the primary metric is decode tokens/s with identical
clock boundaries in control and candidate. Include all decode-side verification,
checkpoint, restore and I/O overhead. Also retain whole-request elapsed time,
TTFT and memory regressions so setup/first-capture costs cannot be hidden by
moving them outside the decode interval. Prefix reuse's
primary metric is TTFT/prefill cost and must not be reported as a decode speedup.
PLE and overlap fixtures first measure their complete read-to-consumer path;
production adoption still needs the relevant full-model metric. Historical
traffic reductions and the overlap ceiling are screening evidence, not speed
results. Later backlog order remains provisional where these costs are unpriced.

#### Step 0 boundaries and failure branch

Use the existing logs first, without another CPU diagnostic title or speculative
sysctl search. Case 2860 began at 8272 pages, observed 1544 before SELF integrity,
3285 afterward, 3259 before metadata and 1523 after the returned virtual rehearsal.
Those global observations do not assign the loss to the intervening operation.
Later metadata/reservation and quiet-start controls specifically prevent treating
the parser, journal or reservation API as a proven cause. New GPU-bank code cannot
by itself fix a refusal that occurs before GPU initialization.

Make one offline pass over the six named completed evidence sets and their
corresponding startup code. Its required output is: (1) the exact phase and
source/configuration to change, (2) the owned bytes/pages or policy margin being
changed with its evidence and uncertainty, (3) every retained reserve and owner,
and (4) the next finite admission's pass/fail action. A smaller executable or a
new page count alone is not this deliverable. Do not repeat that pass against
unchanged inputs. Then perform the changed checks and one candidate build,
reusing unchanged input proofs. Avoid a new diagnostic program
whose result would not select that delta. If no supported delta is identified,
record this common prerequisite as unresolved; do not fill the gap with another
unrelated fixture, assume recovery, or invent a physical limit.
Give the parked prerequisite a concrete required change and retain its status;
only a pre-existing independent host deliverable may proceed. This is not
completion of the shared prerequisite or permission for another blocked launch.

**Execution outcome, case 3014:** the bounded offline pass is complete. No
supported removable owned cost was identified: early display was already off,
and the observed 16--32 MiB CPU heap used Direct with zero libc fallbacks. The
previous 6207-page selection underpriced the observed 6749-page interval decline.
Repricing gives `6749 + 2974 + 256 = 9979` pages; retain the higher regular
10142-page policy for this unchanged full SELF. A single existing-shell screen
observed 6708 -> 6708, so no package staging, build, title or GPU run followed.
The common prerequisite remains unresolved, not physically impossible. Do not
repeat Step 0 or this screen unchanged. The already specified offline cache-cohort
reviewer is the independent host deliverable; other candidate integration stays
deferred. See the [execution record](remaining-validation-progress-20261026.md#bounded-startup-review-and-cache-cohort-reviewer-2026-10-27)
and [bounded public receipt](cache128-startup-review-20261027.json).

Before preparing a native cohort, take the required fresh cheap screen once.
A known refusal closes that attempt: record the phase, actual counters, chosen
rule and required change, perform ordinary close/restoration where applicable,
and do not retry the unchanged artifact/condition. A new attempt needs a material
source/scope/resource change and a reviewed rationale. Unknown completion keeps
all owners retained and prevents dependent work, with no forced reset or reboot.
This plan does not claim that a smaller SELF, a revised margin or one restart
would provide enough capacity.

#### Avoid repeating preparation and administration

- Reuse the exact original model/512 MiB parts, native shader proof within its
  valid boot/source scope, layout evidence, checkpoint proof, workload and route
  manifests. Do not reconvert, retransfer or rerun unchanged correctness fixtures.
- Check changed paths and dependencies only. Fresh owner, current memory/source
  identity and positive completion remain mandatory at native execution; they
  cannot be replaced by old host receipts.
- Prepare the full finite A/B/B/A cohort and adoption criteria before its first
  launch. Prefer the existing same-SELF switch. Reuse immutable package/rollback
  artifacts; do not create a framework or branch for every subcheck.
- Consider publishing one immutable candidate package for a whole bounded cohort
  only if existing ownership/restoration rules can be preserved. This transport
  consolidation is not implemented. Establish compatibility with those rules
  before using it. Preserve per-arm admission and never change a live title or
  assume that all arms can share a model context or one process.
- Expand to additional workload regressions only for a surviving speed candidate.
  Do not open another candidate while the active comparison lacks its decision.
- GitHub saving/merging is part of delivery, not the completion criterion. The
  active candidate ends with a measured decision and any required placement;
  the entire request stays incomplete while required backlog items remain open.

#### Research must resolve an active decision

The owner additionally requires removing unnecessary investigation. Before any
new investigation, state the exact unresolved question for the active step,
why existing evidence cannot answer it, and how either result changes the next
implementation or execution decision. Name a bounded set of sources/observations
and a stopping condition. If both outcomes lead to the same action, omit it.
Read the relevant existing source/receipt first. Consult an external source
only for a specific missing fact that blocks that decision; a general interest
in newer research is not sufficient.

| Remove from the current work queue | Retain or reopen only when |
| --- | --- |
| Broad new Strata/Maya/Radiance/PS5LM or SSD literature surveys | A concrete current implementation/API question is unanswered by the existing research and pinned sources |
| Repeated metadata, virtual-region, journal, quiet-start or closed-controller probes | A material change invalidates the exact earlier result or creates a different, stated decision; a desire for another memory count is insufficient |
| Repeating the three unavailable allocator sysctl names, guessing other names, or creating another general kernel census | A documented usable interface can resolve a named active blocker. Proprietary kernel-owner attribution stays unresolved, not silently completed or required before every model comparison |
| New standalone test titles or generic harnesses | Existing fixtures cannot check a required changed behavior, and the added test has a direct acceptance/failure decision |
| Further cache-capacity sweeps, model repacks, driver variants and extra workloads before the current comparison | The active result identifies their need. Existing model parts, profile and completed screens are reused |

Necessary numerical, ownership, current admission, monitoring and completion
checks stay in place. This restriction removes speculative/repeated work, not
the user's required validation. Research, documentation and GitHub updates are
batched into the active work package; do not make each small check a new project
or use its merge as an endpoint for the overall task.

### Reference work packages

The stable IDs below identify technical scope, not a competing execution order.
The current queue above governs actual work. Completed feasibility evidence is
reused; the package descriptions do not instruct repeating it.

| ID | Work package | Dependency and first useful result |
| --- | --- | --- |
| 1 | Bounded workload, CPU metadata and measurement contract | Reuse fixed-request evidence; define short workloads, baseline variability and any recurring native metadata cost before caching it |
| 2 | Allocation lifetimes and cache capacity | Existing ledgers and route replay; identify a concrete removable live allocation or close an impossible capacity variant before console allocation |
| 3 | Expert-major delivery without added copies | Existing physical source traces and owned-bank geometry; determine whether any calls or wait can actually be removed |
| 4 | Ready-expert execution | Existing real demand and slot ownership; measure an exact two-wave graph before model integration |
| 5 | Hidden-state router observation, then optional forecast reads | Real early input is required; first measure predictions without speculative I/O |
| 6 | One complete state checkpoint and prefix reuse | Allocation feasibility from order 2; complete KV/recurrent/PLE/logit continuation is required |
| 7 | Exact speculative verification | Qualified checkpoint from order 6; start width two and prompt lookup without a learned draft model |
| 8 | Additional graph and shader specialization | Screen Radiance-inspired GDN/dual-output/small-GEMM applicability offline; implement only if a completed profile identifies material cost |

Use one independent change per comparison. Later queue changes require an
explicit reason tied to a measured cost, implementation readiness or a concrete
blocker; they must not silently expand several active work packages.

## Shared benchmark and adoption contract

Keep the established arithmetic and identical 30-prompt-token / 22-output-token
requests as the regression control. Add one compact workload from each category:
short Japanese conversation, code/copying, short reasoning, and low-repetition
generation. Freeze template, tokenizer, thinking setting, greedy sampler, stop
conditions and token IDs. Initially fit each rendered prompt within 30 tokens
and retain the 22-token output cap and context 256. Tokenization is host metadata
work; no learned host inference is needed. Short requests do not qualify long
reasoning, arbitrary prompts or endurance service.

Use one workload's first and repeated request in a finite case, retaining the
existing arithmetic/lifecycle sequence. A first request after model load is not
proof of a physically cold SSD cache. Qualify a different workload manifest and
its exact bounds before using it; do not append arbitrary requests to a consumed
case or enlarge the observer allocation.

Record output bytes/token IDs, actual routes, logical/physical source bytes and
calls, source wait, consumer time, graph completion, TTFT, generated tokens/s,
per-token median/p95/maximum latency, CPU/Direct/Flexible/kernel peaks and positive
retirement. p95 from short requests is descriptive. Keep source, decode and
prefill intervals separate; overlapping counters are not additive.

For native delivery fixtures, compare identical bytes and destination geometry
in predeclared alternating or rotated orders. Include every new read, copy,
decode, graph submission and completion cost on the candidate's critical path.
For model qualification, first use an A/B then B/A sequence of four distinct
finite cases on the fixed regression workload. Use trace evidence to select the
most diagnostic additional workload for that mechanism; expand to the remaining
workload regressions only for a surviving candidate. Keep the same executable
with a frozen switch where feasible;
otherwise record each relink and isolate the intended source change. Reuse a
fresh A/A baseline pair only when the existing measurements cannot characterize
the new workload or observation overhead.

Do not run the remaining arms after a correctness, ownership, allocation or
known startup refusal invalidates the comparison. Record those arms as not run
and close that cohort under its failure branch. Conversely, a small or noisy
first A/B difference is not sufficient to claim a win or loss: retain reverse
confirmation for a valid adoption comparison. Avoid extra control cohorts and
administrative transfers before removing that necessary confirmation.

Before execution, declare the primary metric, workload and tolerance from control
variability. Require exactness, complete lifecycle, a repeatable primary-metric
improvement exceeding observed control drift, and no material regression in
first/repeated requests, other workload classes, tails or memory. Do not invent a
universal 5% threshold or alter the gates of already consumed experiments. If the
initial finite comparison cannot separate a small effect from drift, mark it
inconclusive and retain production; justify any additional bounded cohort with
the unresolved question before running it.

New source/GPU overlap and kernel mechanisms need their meaningful numerical
and performance fixture gates before model integration. Cache capacity, prefix
reuse and speculation can require full-model execution to measure their actual
benefit: reuse their qualified allocation/correctness gates, then perform the
model comparison without inventing a separate microbenchmark-speed prerequisite.
A full-model winner
then requires explicit profile selection, exact production placement, post-placement
inference/frame/lifecycle verification and full SELF/settings readback. Merge of
source alone does not establish adoption. Do not add gains from different controls.

## CPU metadata reuse

Audit `native/app/llama_engine.cpp::LlamaEngine/process_batch`,
`streaming_context_params`, the maintained cache overlay and upstream graph-input
setup. The engine already allocates its batch and greedy sampler once; do not
count that existing reuse as a new Radiance improvement. Use existing counters
first, then bounded timing/allocation counters for any unresolved host-only gap.
Never remove the required synchronization, current admission, failure checks,
completion journaling or monitor work to make the candidate appear faster.

For a measured repeated cost, distinguish immutable geometry from token positions,
sequence/reset state and actual expert selections. A reusable metadata record
must bind model, graph shape, dtype, strides and owner epoch; reset/invalidate it
on every changed binding. Cache constant index ranges, reuse bounded storage or
avoid unused transforms only when their native equivalents exist. Avoid adding
new GPU readbacks to save a smaller CPU operation.

Host tests compare exact masks, positions, offsets and output flags at widths
one/two/four, request reset, changed geometry and failure paths. Measure reduced
allocations and CPU duration with identical graph submissions, read bytes and
guard calls, then compare full-model TTFT/decode. If the analogous cost is absent
or smaller than the added lookup/invalidation overhead, close that subcandidate
without a native implementation or full-model replay.

## Allocation lifetimes and useful cache capacity

Start with `native/app/model_cpu_budget.h`, `native_allocator_budget.h`,
`device_buffer_budget.h`, `owned_mapped_backend.cpp` and
`patches/native-model-io/0002-llama-moe-cache.patch`, `0003-ggml-vulkan-buffers.patch`
and `0004-ggml-vulkan.patch`. Build one allocation ledger covering startup,
prefill, decode, observation retention and shutdown. Track aliases and shared UMA
ownership so CPU and GPU views are charged once physically, while retaining each
domain's independent guard. A budget ledger alone is not physical admission.

Current padded banks use `3 * 54 * 3293184 = 533495808` bytes against the
536870912-byte cache cap. The remaining 3375104 bytes cannot hold another expert's
three 3293184-byte planes. Adding a slot fails the selected production cap;
this is a policy result, not a physical capacity limit. The larger-capacity
screen uses `tools/check_cache_capacity.py --large-capacity-sweep` and
`tools/price_cache_capacity.py`, preserving the native layer-floor rule,
actual routes and separately rounded bank/CPU/platform allowances.
Keep the tested 53-slot LFU policy as control.

For any shorter lifetime, prove the last CPU and GPU consumer has positively
completed before release. Test alias retention, failure/unknown-completion
retention, peak-live accounting and unchanged shutdown. Compare recovered usable
headroom and actual payload saved, then source wait and decode if meaningful.
Do not resize kernel pools, count inactive pages as free or remove monitoring.
An experimental cap change is isolated from production and names its exact
geometry, context, lifetime assumptions, retained reserves and fresh allocator
checks. Record policy gaps separately from confirmed pool/API bounds. The ledger
remains useful to checkpoint and graph proposals.

Include the Radiance `_gate_params` and `forward_core_fused` lifetime patterns
in this audit: identify constants prepared repeatedly and layer-local temporary
references that outlive their last consumer. This is an analogy to inspect, not
evidence of the same bug here. Preserve original tensor types, avoid duplicate
F32 router/state copies, and release a temporary only after every CPU/GPU owner
has completed. Charge persistent replacement storage before claiming a saving.

## Expert-major delivery without added copies

Target `native/app/mapped_source.h::try_owned_bank_reads`,
`padded_cache.cpp::qwen_app_try_owned_bank_reads`, `paired_source_io.h` and the
cache overlay's miss loop. First replay current physical ranges, split joins,
coalescing, residues and descriptor use to count genuinely removable calls and
padding bytes. Compare against the current approximately 97% direct-bank path,
not a staged-copy control.

Do not assume that expert-major source contiguity creates contiguous destinations:
gate/up/down banks are distinct. Write down how each read reaches its owned bank
without a new gather copy. If the design requires vectored Direct I/O, qualify its
actual native ABI, alignment, bounded partial-completion semantics and ownership
in a separate CPU-only fixture first. Unsupported ABI or unrepresentable bank
destinations close that variant without trying an unqualified call.

Prepare only a small immutable sidecar from preserved originals. Include layer
0/23/47 and gate/up/down, all actual source residues, split/EOF edges, slot 52,
canaries, descriptor identity and complete SHA256. Compare complete read-to-bank
delivery, calls, bytes, p95 wait and returned resource ownership. If no delivery
win survives unchanged coalescing and fallback costs, stop before full repacking.
Only a winner may propose an independently recoverable in-place migration;
the current storage limit still forbids a complete second model pack.

## Ready expert execution

Implement in the maintained cache overlay around upstream
`src/llama-moe-cache.cpp::impl::copy`, and a new model-graph overlay for
`src/models/qwen4exp.cpp::graph::build_layer_ffn`. The upstream reference remains
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`. Reuse actual router selections;
introduce no predictions or extra read leases.

Represent each whole expert as filling, ready or GPU-pinned. Publish readiness
only when gate/up/down reads all return. Keep one synchronized GPU producer and
pin every consumed slot through positive GPU completion. A later fill cannot
overwrite a pinned slot. Compute selected ready experts/shared expert while
remaining actual reads continue, save contributions at original indices, and
perform the original final reduction order. Price all retained contributions
and graph metadata before allocation.

Host ownership and metadata tests cover empty/all/mixed-ready sets, top ten,
repeated IDs, one failed role, slot pressure and unknown I/O/GPU completion.
Then run a bounded original-shape two-wave GPU fixture with delayed returned
reads, F64 numerical references and the existing precision limits. Measure
graph/submission overhead and actual simultaneous read/compute intervals.
Exact greedy outputs and original route order must match the sequential graph.
If graph overhead consumes the overlap, stop before full-model integration.
The historical non-source fraction gives only a conditional 1.082x ideal
process-time ceiling for pure overlap; it is not a promised gain.

## Hidden state router observation and forecasts

First add a bounded, default-off observation path around the actual Qwen4Exp
`build_hc_combine`, `build_hc_mix` and `build_layer_ffn` input. The exact FFN input
after hyper-connections/PLE must remain authoritative. Use the original resident
F32 router with verified tensor ownership; add no BF16 cast or duplicated router
corpus. Maintain the graph change as an overlay. Slot protection later belongs
in `native/app/expert_policy.h`, the cache overlay and mapped-bank leases.

Start with observation only, no speculative reads. Charge a fixed selected-layer
observation buffer before graph execution; export compact scores/IDs and timing,
not full unbounded hidden tensors. Compare tap off/on to measure observation
cost. Verify unchanged actual selections, outputs and graph retirement. Score
missing-expert precision, ready-before-demand opportunities, useful lead time,
extra graph time, displaced hits and predicted wasted physical bytes. Saved
previous-token expert IDs cannot substitute for these hidden-state measurements.

Proceed only if conservative saved wait exceeds forecast, eviction and read
cost. Test zero, then one, then two reserved slots within the existing 53; never
increase outstanding reads above two. Actual demand has priority. A speculative
slot becomes eligible only after all three matrices return, and the actual
router still determines every contribution. Measure foreground p95/max read
wait and waste as well as decode. If prediction is late or slows demand, close
that configuration and retain the nonpredictive baseline.

## Complete checkpoints and prefix reuse

Share this implementation with speculative verification. Target
`native/app/llama_engine.cpp::prefill/process_batch/next`, `streaming_context_params`,
upstream `llama-memory-recurrent.cpp::seq_rm/state_read/state_write`, hybrid/KV
modules and Qwen4Exp PLE/logit state. A proposed application checkpoint wrapper
must explicitly bind model, sequence, positions, sampler and every state owner.
The wrapper has now passed the finite complete-model continuation comparison
recorded in the progress report; prefix and speculative consumers still need
their own qualification. `seq_rm` on KV alone is insufficient.

The measured host checkpoint minimum, 118038528 bytes before KV/logits, exceeds
the 83820544-byte CPU slack. Do not implement that rejected host allocation.
Price a device checkpoint, or bounded SSD checkpoint with all transfer costs,
using the shared ledger before native allocation. If neither fits current
physical floors, record checkpoint-dependent proposals as blocked by a concrete
budget, with no inference attempt. A numeric post-load device allowance does
not establish UMA/kernel headroom.

For an admissible design, test capture, restore, commit and discard at multiple
positions, including partial prefill and every draft rejection position. Check
complete continuation logits within fixed original-operation limits, exact
greedy tokens/routes, PLE history, recurrent state, KV positions and positive
copy/I/O completion. Keep snapshot resources pinned until their consumers finish.
Cross-model/prefix mismatches and incomplete snapshots must refuse before use.

Qualify prefix reuse first as a checkpoint consumer: compare exact cold prefill
with restoration of one matching completed prefix plus its suffix. Report
capture cost, storage, restore time and reuse count needed to repay capture.
Adopt only for a demonstrated repeated-prefix TTFT benefit without a cold-path
regression. Do not report it as a steady decode improvement.

## Exact speculative verification

After checkpoint qualification, add a default-off prompt-lookup or n-gram draft
path to `LlamaEngine::next/process_batch` and `streaming_context_params`. Validate
two target tokens first; width four follows only after its independent memory,
slot, rollback and numerical gates pass. Existing prefill four does not qualify
multi-token generated verification. No learned host/cloud or extra draft-model
weights are introduced.

Force zero acceptance, each partial acceptance and full acceptance. Check emitted
tokens occur once in order, rejected suffixes are fully rolled back, and every
subsequent token/route agrees with ordinary greedy decoding. Do not demand the
same intermediate speculative routes, since rejected drafts create extra work;
compare accepted continuation and account for all discarded work. Multi-token
arithmetic must meet the fixed reference limits without relaxed precision.

Measure accepted tokens per second, acceptance distribution, unique actual
experts, physical bytes per accepted token, draft/verification/rollback time and
tail latency across the bounded workloads. The earlier 13.354% / 32.529%
accepted-path duplicate-use estimates for widths two/four exclude rejected drafts
and are not measured savings. Low acceptance or checkpoint cost can close the
variant before production. Sampling requires a later distribution-correct
verification design; same-seed equality alone would not qualify it.

After fixed-width verification qualifies, test the Radiance-inspired adaptive
controller as a separate switch: ordinary single-token decoding versus width
two, and later width four. Use prior acceptance, n-gram availability, observed
verification/rollback cost and wasted source bytes to decide whether to draft.
Never peek at future target tokens or omit target verification. The current
model-free drafter has no MTP confidence; do not transplant a confidence-product
threshold or compute extra target logits just to emulate the donor controller.
Keep `load_mtp=false`; enabling native MTP or DFlash is separate model/state/I/O
qualification and is not required for this candidate.

Price the controller's CPU work, telemetry and any synchronization. Test abrupt
high-to-low acceptance, absent n-gram matches, request reset, each width change
and the full forced-rejection matrix. Retain the checkpoint and exact emitted-
continuation gates. Compare accepted tokens/s, wasted bytes/token and tails
against both ordinary decode and the qualified fixed-width control. If controller
overhead or extra SSD traffic erases its benefit, retain fixed or ordinary decode.

## Shader specialization after profiling

Use existing completed counters before adding profiling. If new profiling is
needed, verify supported timestamp/completion behavior with bounded overhead;
wall time around a fence is not isolated shader execution time. Continue only
if a completed model profile identifies a material kernel cost after source work.

Targets are the Vulkan overlay and upstream
`mul_mat_vec.comp::iter_aligned_nonquant`, its load helper and `ggml_vk_mul_mat_id`.
Keep original 2560x640 / 640x2560 shapes, top ten, BF16 loads, F32 activation and
accumulation, stride/residue/slot guards and one GPU producer. Test ordinary and
indexed paths, slot 52, repeated/boundary IDs, non-BF16-exact F32 inputs, canaries
and fixed F64 references before any model run. Compare total source-to-output
delivery and full-model decode, not just a faster shader interval. If no material
kernel target exists, retain an explicit deferred status rather than claim an
implemented optimization.

Radiance adds three specific subcandidates to this package. First screen their
actual graph shapes, dtypes and existing fused coverage using
[`qwen4exp.cpp` at the pinned upstream revision](https://github.com/ggml-org/llama.cpp/blob/0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/models/qwen4exp.cpp):

- **Shared-input projections:** `build_qkvz` and `build_layer_attn_linear` contain
  projections of the same activation. Check dual-destination BF16-weight/F32-input
  kernels for the original `wqkv`, `wqkv_gate`, `ssm_beta` and `ssm_alpha` tensors.
  Keep independent original weight views and F32 output/reduction semantics;
  do not copy the donor's MXFP4 concatenation or repack the full model. Prove
  identical source/role ownership, output strides and all original projection
  results before measuring activation bytes and launch count.
- **GDN and gated-normalization fusion:** inspect `build_recurrent_attn` and
  existing fused-GDN support before changing `build_layer_attn_linear` or
  `build_norm_gated`. Target only remaining redundant intermediates or contiguous
  copies. The pinned `build_norm_gated` uses **sigmoid**, which must not become
  SiLU. Current recurrent sources and intermediates stay F32; donor BF16 working
  buffers do not authorize downcasts. Prefer workgroup-local fusion or ordinary
  separate dispatches; do not transplant the donor's device-wide grid-counter
  barrier or assume RDNA4 resident-workgroup guarantees on PS5. Test state
  initialization/continuation, strides, tails, norm epsilon, softplus/sigmoid and
  extreme-decay inputs against the existing path and independent references.
- **Small dense projections:** apply shape-gated dispatch ideas to actual F32
  routers and BF16-weight/F32-input projections in the Vulkan overlay, retaining
  their original types. The donor's `config_for` table and BF16-only `maybe_gemm`
  are not a measured configuration for PS5. Start with actual M=1/2/4 token
  geometry, also checking expert-index expansion, and compare with the current
  vector/matrix route. No FP8 conversion, new reduction approximation or imported
  RDNA4 WMMA dependency is eligible.

Keep these switches independent of ready-expert scheduling and speculative
width. Each surviving subcandidate must pass host/layout checks, a bounded native
numerical fixture, full original-model comparison and the shared adoption gate.
Measure TTFT and decode separately; a long-prefill kernel win elsewhere does not
establish benefit at the current four-token prefill. No PS5 gain is yet measured.

## Case safety and completion records

Each native case needs fresh owner, source identity, kernel/Flexible/Direct and
completion admission. The regular full-model policy remains 10142 prelaunch
pages and the adopted native startup target remains 2974. These are not universal
hardware minima or automatic conditions for every fixture: separately scoped
experiments retain their exact recorded formulas and eligibility. A future
revision needs a stated scope, phase cost, retained reserves and failure branch;
this planning review changes no runtime predicate. CPU-only fixtures retain
their own allocation formulas and independent guards. Keep the operational floor
`minimum + max(reserved, 256)` unchanged. Old point
observations never authorize a new launch. Reuse the qualified driver, sealed
model lineage, shader evidence and returned integrity receipts only within their
exact unchanged scope; no routine reconversion or redundant full transfer.

### Owner-authorized reduced-headroom experiment

After disclosure of the 7036-page idle observation and regular 10142-page gate,
the owner explicitly permitted experiments while physical recovery is unavailable
until evening. This supersedes the earlier prohibition on changing the additional
prelaunch margin only for a separately recorded finite experimental cohort. It
does not establish that the reduced margin is safe or sufficient.

The exact-prefix A/B then B/A cohort uses the same packaged executable with a
frozen reuse switch. Its experimental gate requires ten fresh consecutive
observations at or above 6046 pages: the unchanged startup target 2974 plus
3072 pages (48 MiB) of additional prelaunch margin. The regular extra margin
remains 7168 pages (112 MiB), and the regular production gate remains 10142.
Both thresholds must be recorded in the experimental log. The native startup
target, operational floor, bounded backpressure, CPU/Direct/Flexible/device
allocation caps, positive completion, ordinary close and exact fastest-control
restoration requirements remain unchanged. There is no forced reset or
automatic retry. A returned refusal closes its case; unknown completion retains
all backing and prevents dependent console execution. Passing this experimental
gate does not qualify a changed production default.

Keep durable bounded progress/completion records and all existing deadlines.
Perform large transport/visual capture before required native Direct integrity
of positively closed artifacts, then fresh admission. Preserve monitoring. A
known returned refusal closes that case; uncertain completion retains backing,
prevents reuse and stops dependent execution. No automatic retry, forced kill,
service/GPU reset, file-backed model mmap, cache pressure or reduced reserve.

For every package, record implementation status, source/build revision, budget,
host checks, native fixture outcome, full-model result if admitted, adoption
decision, exact installed SELF/settings and final idle/restoration evidence.
Keep raw sessions, SDK/binaries, paths and traces outside Git. CI stays disabled.

Use explicit states: unimplemented, prototype, host-qualified, native-fixture-
qualified, full-model-qualified, production-adopted, rejected, inconclusive, or
blocked with a concrete unmet prerequisite. Deferred work remains incomplete.
For blocked work, state whether the blocker is a chosen application policy,
missing implementation, or a demonstrated device/OS/API constraint. Report
revisability, evidence and required changes; never call a selected guard refusal
physical impossibility. Unrun target arithmetic and a measured inconclusive
comparison are distinct results. Incomplete is an overall aggregate, not the
individual test's disposition.
A rejected fixture may close that tested variant without a full-model run; it
does not mean another unimplemented proposal was tested. Update the single
[plan index](plan-index.md) with each decision. The overall implementation and
validation request remains incomplete while any required package is unimplemented,
unvalidated, blocked or deferred. A terminal decision for one tested variant does
not complete the other proposals. Every selected winner must finish production
placement before its adoption is complete.

The later [ten-original-Expert/depth-two record](finite-execution-dispositions-20261027.md#ten-original-expertdepth-two-implementation-cases-3048-3062)
supersedes missing-source statements for that runner. It is implemented and
host/native-build-qualified; physical acceptance is pending. Numerical/timing
prerequisites constrain native execution/adoption, not writing and host-checking
the next default-off dependent implementation. No memory, ownership or completion
guard is lowered, and no unchanged refused launch/poll is authorized by this rule.
