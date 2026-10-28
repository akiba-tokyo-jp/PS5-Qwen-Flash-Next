# Width-two adoption conditions

Status: defined after the owner's numerical-review feedback; this additional
qualification has not been implemented or executed. It is not covered by the
completed three-request numerical/rejection closure. The installed production
image keeps speculation disabled.

## What the existing evidence establishes

Case 5620 completed one accepted width-two batch. The emitted greedy token IDs
matched the ordinary continuation, while the maximum absolute full-vocabulary
logit difference was 1.992569923400879. All values were finite and the 23 rows
had the expected 248,320 columns. The original elementwise tolerance was
`abs(candidate-reference) <= 1e-5 + 1e-5*abs(reference)`.

This fails that declared numerical-equivalence test. A maximum over the whole
vocabulary and all positions does not by itself prove a functional defect,
quality loss, or harmless rounding. Batch width changes the actual graph and
can change numerical results. The original diagnostic retained only aggregate
and first-mismatch information, not full candidate/reference arrays. Percentile
errors, centered-logit errors, top-k margins and probability divergences cannot
be reconstructed from the saved maximum. No universal absolute-logit cutoff of
zero, one or two is claimed.

The forced rejected draft restored every compared F32 value exactly. Positive
common model/source/device retirement, ordinary OS close and exact production
restoration passed. Those facts do not qualify the accepted path's speed or
broader output equivalence.

## Required qualification

Keep original BF16/F32 weights, F32 activations/accumulation/KV, all Experts and
PLE, the current pinned driver, disabled persistent caches, context 256 and
prefill four. Test the current deterministic greedy sampler; stochastic
sampling requires a separate acceptance algorithm and qualification. No second
machine, model conversion, reboot, CI or change to OS reserve counters is needed.

1. **Separate batching from speculative state handling.** From the same complete
   captured original state, run the same two causal tokens through ordinary
   `LlamaEngine::process_batch_once` and through the accepted
   `LlamaEngine::next_with_one_draft` path. Compare both full vocabulary rows,
   active attention KV, recurrent/GDN state, token position and the subsequent
   continuation. Use the existing elementwise tolerance for identical-width
   floating-point work and exact structural/token checks; do not compare unused
   allocation padding. Require zero nonfinite values and zero geometry errors.
   Verify the normal two-token control repeats within that same tolerance. A
   failed same-width repeat is an unresolved baseline, not permission to widen
   tolerance. Width-one versus width-two drift is recorded separately and is
   not automatically attributed to speculation.
2. **Check generated behavior with meaningful path coverage.** Freeze the eight
   inputs below before execution. Host tokenization must confirm each fits
   128 prompt tokens; context stays 256 and output limit stays 32. Compare every
   emitted token ID, EOG/limit reason and position against ordinary width-one
   greedy inference. All eight must agree exactly. Across these inputs require
   at least eight actual accepted batches, including the queued bonus emission,
   and four deliberately wrong drafts on four different inputs. Force those
   rejections at different committed positions, then compare the restored
   original F32 continuation for at least four more tokens. Record the actual
   acceptance count; a proposal or cost-model check is not an accepted batch.
   Insufficient accepted coverage cannot pass. Collect per-row error count,
   RMS and p50/p95/p99/maximum errors, mean-centered logit errors, top-1/top-5
   IDs and margins, and softmax divergence as diagnostics. A maximum near two
   alone is neither a pass nor a failure of this behavior gate.
3. **Demonstrate actual speed.** After correctness passes, use one unchanged
   application image with only the speculative option changing. Freeze the
   prompt/output limits, cache-reset procedure and causal draft/cost policy.
   Run ordinary/candidate/candidate/ordinary at identical Expert-cache starting
   conditions; distinguish Expert-cache reset from OS file-page coldness.
   Every candidate timing must contain actual accepted width-two work. Include
   drafting, cost selection, capture, verification, rejected work, restore,
   bonus handling, I/O and completion in total time. Both reverse pairs must
   improve total request time and decode throughput, with the candidate range
   outside the observed control range. If ranges overlap, allow at most one
   predeclared additional ABBA block; otherwise record no reproducible gain.
   Do not select a favorable partial arm, aggregate unlike cache conditions or
   infer tokens/s from source-read traffic.
4. **Complete the physical lifecycle and application check.** Retain current
   Direct/Flexible/CPU-heap/device caps and explicitly bound phase prices.
   Require positive request reset and GPU completion, source worker stop,
   model/source/device retirement and zero device ledger, then normal exact-owner
   OS close. After a winning engine comparison, qualify the actual passive
   VideoOut/API application and its full F32/routes under the correct batching
   reference. Preserve the exact installed production as rollback, verify full
   canonical/rollback/settings bytes natively and confirm idle. Fresh admission
   is required for every new case; old cases are never replayed unchanged.

| Input ID | Frozen prompt |
| --- | --- |
| ja-arithmetic | `Respond in Japanese. What is 17 plus 25? Give the number and one short sentence.` |
| ja-summary | `Respond in Japanese. Summarize in one sentence: A train left at noon, stopped for ten minutes, and arrived at one.` |
| en-explanation | `In one sentence, explain why a shadow moves when the light source moves.` |
| en-contrast | `Give one short sentence comparing a stack and a queue.` |
| arithmetic-sequence | `Continue the sequence 1, 2, 3, 4, 5, 6, 7, 8 with the next eight integers.` |
| code-python | `Write only a Python function add(a, b) that returns their sum.` |
| structured-json | `Return only JSON with keys count and label, values 3 and ready respectively.` |
| repeated-context | `Copy this sequence twice exactly: red blue red blue red blue.` |

Do not silently replace inputs, increase output/context/capture limits or force
oracle drafts into speed measurements to obtain path counts. If the unchanged
causal controller lacks the required coverage, report that concrete gap and
revise the mechanism as a separately identified candidate.

## Concrete implementation boundaries

| File / function | Required work before this qualification can run |
| --- | --- |
| `native/app/llama_engine.cpp::next_with_one_draft` | Add opt-in bounded observation of the two target rows, acceptance decision, pinned bonus and committed position; retain the original producer/completion owner |
| `native/app/llama_engine.cpp::process_batch_once` | Expose a diagnostic-only ordinary width-two reference from the identical captured state; do not enable speculative control on this reference |
| `native/app/llama_engine.cpp::capture_checkpoint_in_active_epoch` / `restore_checkpoint_in_active_epoch` | Bind the reference state, active recurrent/KV payload and position; verify both accepted state and forced-rejection continuation |
| `tools/build_speculative_closure.py::generate` | Derive a new separately bound entry with the eight frozen prompts and complete row statistics; retain the consumed original diagnostic unchanged |
| `tools/review_independent_resident.py` / `tools/resident_route_review.py` | Add an explicit same-width reference and per-position greedy review; do not silently relax the old width-one numerical validator or route geometry |
| `tools/build_prefix_delivery_monitor.py` | Use only as the passive-application integration reference after a winner; prefix and speculative snapshots share an owner and must not be enabled together without separate combination qualification |

If all four gates pass, adopt the exact qualified candidate and preserve its
control as rollback. A correctness failure means the current candidate needs a
specific repair; a completed slower candidate is not adopted. A returned
allocation/API refusal is classified with its actual resource or interface
cause. None of these outcomes proves universal physical implementation
impossibility. Missing qualification is explicitly missing and never counted as
completed by publishing these conditions.
