# Validation plan for remaining Flash Next proposals

Plan date: 2026-10-26. **The remaining proposals are not implemented or validated
by this plan.** It defines their work and terminal decisions. Current dispositions
and historical results are in the [plan index](plan-index.md). Planning does not
start a console session or change the installed application.

The objective is faster original-precision inference on the existing single PS5,
with independently reported TTFT, generated tokens/s and resource safety. Preserve
the exact [production artifact and rollback](production-installation-20261025.md),
[qualified profile](../config/qualified-performance.json), original BF16/F32,
F32 KV, every expert/PLE, driver `872cc126` / `cumulative-idle`, disabled persistent
caches and all current budgets. No second Flash-Next machine is required.

## Work order and dependencies

Perform cheap feasibility work before native implementations. Share the allocation
ledger, workload traces and complete-state checkpoint work across proposals;
do not build a separate framework for each. Native cases run sequentially.

| Order | Work package | Dependency and first useful result |
| --- | --- | --- |
| 1 | Bounded workload and measurement contract | Reuse existing fixed-request evidence; define additional short workloads and measure baseline variability |
| 2 | Allocation lifetimes and cache capacity | Existing ledgers and route replay; identify a concrete removable live allocation or close an impossible capacity variant before console allocation |
| 3 | Expert-major delivery without added copies | Existing physical source traces and owned-bank geometry; determine whether any calls or wait can actually be removed |
| 4 | Ready-expert execution | Existing real demand and slot ownership; measure an exact two-wave graph before model integration |
| 5 | Hidden-state router observation, then optional forecast reads | Real early input is required; first measure predictions without speculative I/O |
| 6 | One complete state checkpoint and prefix reuse | Allocation feasibility from order 2; complete KV/recurrent/PLE/logit continuation is required |
| 7 | Exact speculative verification | Qualified checkpoint from order 6; start width two and prompt lookup without a learned draft model |
| 8 | Additional shader specialization | Only if a completed post-streaming profile identifies a material kernel cost |

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
three 3293184-byte planes. Thus adding a slot with unchanged geometry already
fails the current cap; do not launch an allocation probe for that configuration.
Replay different capacities with `tools/replay_expert_routes.py` only after
checking the native layer-floor rule and identifying a concrete admissible layout.
Keep the tested 53-slot LFU policy as control.

For any shorter lifetime, prove the last CPU and GPU consumer has positively
completed before release. Test alias retention, failure/unknown-completion
retention, peak-live accounting and unchanged shutdown. Compare recovered usable
headroom and actual payload saved, then source wait and decode if meaningful.
Do not resize kernel pools, count inactive pages as free, increase caps or remove
monitoring. If no admissible extra capacity or transient release exists, record
that variant as ruled out under current limits; the ledger remains useful to
the checkpoint and graph proposals.

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
must explicitly bind model, sequence, positions, sampler and every state owner;
it does not exist yet. `seq_rm` on KV alone is insufficient.

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

## Case safety and completion records

Each native case needs fresh owner, source identity, kernel/Flexible/Direct and
completion admission. Title/GPU cases keep the 10142-page prelaunch requirement
and 2974-page startup target. CPU-only fixtures retain their original allocation
formula and independent guards. Keep the operational floor
`minimum + max(reserved, 256)` unchanged. Old point
observations never authorize a new launch. Reuse the qualified driver, sealed
model lineage, shader evidence and returned integrity receipts only within their
exact unchanged scope; no routine reconversion or redundant full transfer.

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
A rejected fixture may close that tested variant without a full-model run; it
does not mean another unimplemented proposal was tested. Update the single
[plan index](plan-index.md) with each decision. The overall implementation and
validation request remains incomplete while any required package is unimplemented,
unvalidated, blocked or deferred. A terminal decision for one tested variant does
not complete the other proposals. Every selected winner must finish production
placement before its adoption is complete.
