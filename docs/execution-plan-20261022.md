# Execution plan: first complete PS5 generation

This is the active forward plan, created from the required result on 2026-10-22.
Earlier milestone lists are historical evidence, not an additional work queue.

## Required result and starting point

One physical PS5 generates text with the pinned original BF16 model, all original
experts and required PLE. The passive TV/web monitor shows CPU/GPU identity,
date/time and measured TTFT/tokens per second; requests use the external API.
Strata UMA admission and Maya aged-frequency caching remain in the real engine.

All 131 original shards passed SHA256. Conversion is active; complete auditing,
final hashes and transfer are pending. The data-only continuation is waiting
without console access. The converted tensor payload is 359,235,922,432 bytes
before container overhead. Component/display evidence does not establish model
compatibility. Full inference is still rejected by `validation_policy.h`, and
the old 11,976,330,752-byte memory estimate is not observed residency. The
bounded application now plans 12,110,548,480 bytes, including a larger tracked
CPU allowance and a capped aggregate pool for post-load device buffers.

## Three deliverables

| Deliverable | Work | Exit evidence |
| --- | --- | --- |
| 1. Ready data and runtime | Continue conversion/audit/hash/transfer. In parallel, implement the missing bounded first-generation admission using existing integrity, mapping, memory and engine code. | Complete original-model receipt and positive transfer record; focused checks and exact candidate link/package proof. |
| 2. First real generation | One identified title launch executes ordered native integrity, mapping, memory, load and short-generation gates. | Actual token IDs/text, finite logits, expected arithmetic smoke answer, exact model/driver identity, measured timings and positive GPU completion. |
| 3. Working demonstration | In that same title session, retain the model and recreate only the completed context. Run two identical fixed external requests with initially empty and then retained expert cache. | Passive TV/web output, calibrated time, displayed-frame evidence, independently reconstructed TTFT/token rates, listener shutdown, ordinary title close and exact original restoration/readmission. |

Deliverable 1 has concurrent data and runtime work streams. Data preparation owns
bulk disk work; avoid competing large reads or repeated full builds. Change the
missing runtime controls, check affected paths, then link/package one coherent
candidate using unchanged engine/driver artifacts and recorded provenance.
Keep frozen preparation/transfer sources and the console context unchanged.
No new title/diagnostic runs while that continuation owns the data lease.

## First-generation implementation

Add a distinct private admission mode. Keep ordinary inference rejected and
committed execution/deployment/CI disabled. Bind the exact candidate, model
receipt, driver revision/profile/archive, session, request and resource limits.
A policy declaration never establishes a passed physical gate.

Within that one launch, verify all native SHA/metadata and read-only mappings
before backend initialization; each later action requires positive prior results.
Bind unchanged owned files across verification and loading. Do not add a separate
CPU-only title cycle or hash the same complete payload twice within this run.
Retain the existing CPU-only mode as an available diagnostic.

Before loading/submitting affected work, account for resident weights, aligned
allocation limits, expert cache, PLE access, context/state, graph workspace,
staging and OS reserve. Check actual graph shapes/backend support. Unknown or
insufficient headroom and unsupported placement reject the affected phase.
Fix that concrete blocker; never relax precision, numerical limits or feature
checks, or count CPU/GPU shared memory twice.

Start with one original-template greedy request: context at most 256 tokens,
rendered prompt at most 64 tokens, output at most 32 tokens, one-token
microbatches. Reject oversized prompts instead of truncating. These are proposed
implementation maxima, not qualified context capacity. Persist the exact request
before its single execution. No retry is permitted. Only after that smoke
request positively completes and returns the expected answer may the two fixed
API demonstration requests proceed. They each have the same context/prompt/
output bounds and a separate durable intent; the full model is never reloaded.
Distinguish end-of-generation, token limit, rejection and backend failure.
A partial reasoning trace is not a completed answer.

## Completion, safety and reuse

Completion means every implementation and physical verification required by all
three deliverables. A host check, component test, first token, model load or one
request is an intermediate result. Keep working through the remaining gates.

Persist phase progress and terminal outcomes under fixed deadlines with an
independent host observer. Check cancellation/deadlines at completed backend
boundaries. A host timeout cannot interrupt or safely release an in-flight GPU
call: mark missing completion uncertain, refuse more submissions and retain
backing for ordinary OS close. Never report success or retry automatically.
This plan cannot guarantee that the driver will never hang.

Preserve the original title once per candidate session; run its ordered gates,
then normally close and perform the established exact restoration/readmission
at session end. Do not repeat that sequence after every successful internal phase.
Reuse evidence for unchanged source/artifact/scope; check affected code and fresh
session/ownership/headroom at actual mutation boundaries. Add a targeted operator
diagnostic only when a concrete full-graph failure requires it.

## Scheduling and immediate work

Report the active deliverable, its blocking dependency and new evidence. Do not
restart acquisition/conversion/transfer because a timestamp is old. Inspect the
known process/output. Keep native display integration and performance tuning
after the first model result; do not add standalone GPU fixtures now.

The earlier 16 MiB transfer at about 11.50 MiB/s suggests roughly 8.3 hours for
the payload if sustained; this is not a full-transfer measurement. Synthetic
native hashing projects about 34 minutes of CPU work before file I/O. Existing
preparation and verification deadlines remain fixed. Inspect real progress
before forecasting completion; do not promise same-day operation or silently
extend a frozen job. Preserve partial/failure evidence on deadline expiry.

No quantization, pruning, host inference substitute, cache optimization or extra
benchmark is on the critical path.

## Implementation checkpoint

`first-generation-validation` now implements candidate/receipt binding, one
complete native model hash pass, unchanged-file identity checks, mapping before
backend initialization, the existing memory gate and one bounded original-template
request. Durable per-token records and independent result validation distinguish
actual completion from missing/failed evidence. Ordinary inference remains
rejected; committed execution/deployment/CI controls remain disabled.

Manual host control/adapter checks passed, including 90 malformed first-generation
policy fields and the existing 277 policy rejections. Five report fault-injection
tests passed. The actual shared Jinja renderer passed with the original template
(111 rendered bytes). All five changed native translation units compiled for
the PS5 ABI. Host renderer link failures were preserved and resolved without a
console request; completed interpreter objects were reused.

The preceding physical original indexed-MoE result used SELF
`0b187cac25c3e322bd4244474a935d191ce85b7bcbb3d2559ead26f05198d057`:
all 512 diagnostic expert matrices were retained, the ten selected IDs passed
the fixed numerical limits and positive completion/retirement passed. The exact
original was restored, numerically readmitted and normally closed. The current
data-only continuation is bound to that completed context. This is reusable
component evidence, not full-model generation.

The runtime now includes one 8 MiB direct-read window, at most eight direct
source descriptors, original mapping-identity tracking and positive unmap
retirement. CPU matrix fallback is rejected after model load; CPU workspace is
capped at 16 MiB. Post-load GGML device allocations are admitted before creation:
at most 512 MiB each and 1,792 MiB in aggregate, with fresh physical Direct
reserve checks. Their tracked peak and completed release must be reported.
See `bounded-runtime-20261022.md` for scope and limitations.

The finite API transports two exact requests onto the existing model producer
thread. It serves only the passive assets/status, streams durable token events,
requires positive observation/finish acknowledgement, and stops its listener
before model retirement. Native frame capture records the exact CPU raster
after a matching positive VideoOut flip; it is not a TV photograph.

The coherent final native link, SELF integrity/segment roundtrip, actual import
resolution and linked BF16/operator/MoE shader checks passed on the host at SELF
`b380e755daf7ecfa3b10a46ed3aefc867bca80d5917d831d1815262f18f4bfc0`.
Its five isolated overrides include the internal Vulkan workspace reservation.
See `native-first-generation-build-20261023.json`. It has not been launched.

Original conversion 001 reached its unchanged six-hour deadline. Its actual
writer, redirector, preparation and data waiter all ended; 351,317,227,759 partial
output bytes remain intact. The distinct resumed attempt reuses 72 complete
splits and writes the remaining four. It still requires the complete independent
payload audit and new final hashes. Data waiter 003 may then execute the reviewed
CPU-only directory/transfer sequence once. These host/data outcomes do not
establish physical model capacity, generated text or performance.

Remaining deliverable-1 work is complete data readiness. After positive transfer,
use fresh owner/ordinary-launch gates for deliverables 2 and 3 in one native
session. Ordinary close, exact original restoration/numerical readmission and
final idle/readback evidence remain part of completion.
