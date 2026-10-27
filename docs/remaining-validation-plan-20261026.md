# Validation plan for remaining Flash Next proposals

Plan date: 2026-10-26. **This plan itself does not implement or validate proposals.**
Execution outcomes are tracked in the [progress record](remaining-validation-progress-20261026.md).
The earlier [memory-first PLE sequence](PLE-memory-first-plan-20261026.md)
continues to govern PLE comparisons. The owner-approved 2026-10-27 execution
order below governs the broader acceleration work; PLE timing does not block
independent cache, speculation or ready-expert implementation.
The regular prelaunch margin is not an established PLE hardware minimum.
It defines their work and terminal decisions. Current dispositions
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

### Owner-approved execution order, 2026-10-27

1. Price CPU-only, backend initialization, small graph and model stages separately.
   Attribute current consumption using completed observations. A historical
   cross-executable margin is provisional policy, not measured cost of a new SELF.
2. Replay saved actual routes at larger capacities. Price rounded allocations
   without double-counting shared Direct/CPU owners, then implement the useful
   affordable candidate. The first target is 128 active slots / 129 physical
   planes. The 160-slot allowance gap remains a lifetime-accounting question.
3. Implement native exact width-two verification using the already qualified
   complete-state checkpoint. Prefix speed comparison is not its prerequisite.
   Keep the 53-slot cache as its independent control.
4. Establish actual independent backing and two-wave ready-expert GPU/source
   overlap. Integrate only a fixture winner into the model.
5. Close PLE timing and prefix reuse comparisons when separately priced native
   stages admit them. Continue the router, workload and profiled specialization
   packages with their individual dependency and adoption checks.

For each surviving candidate, require same-model A/B then B/A, original-token
and lifecycle regression, exact production placement and post-placement checks.
Offline traffic reduction does not qualify generation speed or adoption.
The work packages below retain stable reference IDs; independent work need not
wait for every earlier speed comparison.

Perform cheap feasibility work before native implementations. Share the allocation
ledger, workload traces and complete-state checkpoint work across proposals;
do not build a separate framework for each. Native cases run sequentially.

| Order | Work package | Dependency and first useful result |
| --- | --- | --- |
| 1 | Bounded workload, CPU metadata and measurement contract | Reuse fixed-request evidence; define short workloads, baseline variability and any recurring native metadata cost before caching it |
| 2 | Allocation lifetimes and cache capacity | Existing ledgers and route replay; identify a concrete removable live allocation or close an impossible capacity variant before console allocation |
| 3 | Expert-major delivery without added copies | Existing physical source traces and owned-bank geometry; determine whether any calls or wait can actually be removed |
| 4 | Ready-expert execution | Existing real demand and slot ownership; measure an exact two-wave graph before model integration |
| 5 | Hidden-state router observation, then optional forecast reads | Real early input is required; first measure predictions without speculative I/O |
| 6 | One complete state checkpoint and prefix reuse | Allocation feasibility from order 2; complete KV/recurrent/PLE/logit continuation is required |
| 7 | Exact speculative verification | Qualified checkpoint from order 6; start width two and prompt lookup without a learned draft model |
| 8 | Additional graph and shader specialization | Screen Radiance-inspired GDN/dual-output/small-GEMM applicability offline; implement only if a completed profile identifies material cost |

Orders 2 and 3 begin with existing host metadata, not fresh full-model runs.
Reorder later native candidates only when those feasibility results supply a
better supported critical-path opportunity. Keep one independent change per
comparison. A blocked checkpoint does not prevent unrelated ready-expert or
router-observation work.

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

Before execution, declare the primary metric, workload and tolerance from control
variability. Require exactness, complete lifecycle, a repeatable primary-metric
improvement exceeding observed control drift, and no material regression in
first/repeated requests, other workload classes, tails or memory. Do not invent a
universal 5% threshold or alter the gates of already consumed experiments. If the
initial finite comparison cannot separate a small effect from drift, mark it
inconclusive and retain production; justify any additional bounded cohort with
the unresolved question before running it.

Only a fixture winner proceeds to full-model integration. A full-model winner
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
completion admission. Title/GPU cases keep the 10142-page prelaunch requirement
and 2974-page startup target. CPU-only fixtures retain their original allocation
formula and independent guards. Keep the operational floor
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
