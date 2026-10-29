# Native routing and multi-token Expert sharing comparison

Status: the finite requested verification is complete. See the
[physical results](expert-routing-sharing-results-20261030.md) and
[sanitized evidence](expert-routing-sharing-results-20261030.json). The dated
sequence and two corrected integration failures below are preserved as history;
they do not reopen completed comparisons or leave pending cases in this scope.

The owner requested physical verification of cache-aware routing, fewer active
Experts and multi-token Expert reuse. Model-output equality is not an adoption
gate for the approximate routing arms. No production replacement is authorized
by this comparison record alone; the measured quality tradeoff must be reported.
The selected db542fa2 application and its settings remain the exact rollback.

Use one model lifetime with the selected 420 bundles, adjacency merging,
depth-four reads, original probation and the unchanged driver. Expert precision,
all stored weights, F32 inputs/KV and the current resource/owner/completion guards
remain fixed. No CI, reboot, pruning, conversion or new SSD payload is needed.

Modes: 0 ordinary Top-10; 1 decode-only cached ranking multiplier 1.5 with
original mixture probabilities; 2 decode-only Top-8; 3 decode-only Top-6;
4 up to eight causal width-two verifications from committed token history.
Prefill routing is unchanged. Mode 1's CPU metadata node is charged, with all
matrix operations left on the original GPU. Logical residency is updated on
actual deterministic fill/eviction, not asynchronous transfer timing.

Because graph topology changes across modes, this isolated comparison disables
graph reuse uniformly through the existing LLAMA_GRAPH_REUSE_DISABLE setting.
It must not be silently labelled an unchanged production-speed comparison.
Normal adoption would require a separate matching application qualification.

Counting order: warmup, A B B A C C A D D A E E A, with an empty Expert cache
before every request. A=0, B=1, C=2, D=3, E=4. Use the existing 30-token counting
prompt and at most 32 output tokens. Preserve complete finite vocabulary rows,
all actual variable-width routes, source bytes/calls/wait and per-token snapshots.
Only unchanged controls require exact F32 and emitted-token equality.

Then run three fixed quality prompts for every mode: translation, arithmetic
and raw JSON-only formatting. Keep answer contents and format separate; do not
normalize outputs or suppress regressions. Quality changes never terminate an
otherwise completed experiment. Report decode-only GB and calls per accepted
token separately from whole-request totals; rejected speculative work is charged.

Speculation retains complete KV/recurrent/position/logit/sampler/application
state capture, verification and rejection restoration. Only already completed
captures or complete request reset may establish reusable snapshot capacity.
No future reference tokens may supply draft proposals. A proposal that never
executes is not a tested multi-token path.

All cases need fresh run identities and once-only journals. Positive model,
source and GPU retirement precedes ordinary close and exact production/settings
restoration. Unknown completion retains owners; no retry or forced termination.

## Corrected continuation after the first integration failure

Case 9440 completed five requests (warmup and the cache-ranking ABBA). At the
first Top-8 decode, the process exited during CPU graph construction: the
upstream aggregation loop still used the configured ten Experts while the
actual tensor had eight. The corrected graph bounds aggregation by the actual
dimension; host regression checks cover six, eight and ten. No completed
request is discarded or replayed.

CPU-only observation confirms zero native owners, AppInfo idle, identical boot
and unchanged management services. Restore the exact production/settings using
that explicit self-exit proof; do not label this a normal native completion or
invent a positive GPU-retirement terminal. Preserve the five durable native
result and per-token source records separately from the aborted overall run.

The fresh corrected continuation has 26 requests: warmup plus the remaining
Top-8, Top-6 and repeated-verification ABBAs, followed by all 15 quality requests.
Counting order is `0,0,2,2,0,3,3,0,4,4,0`. Cache-ranking quality is measured in
the corrected run; its already completed speed comparison remains case 9440.
All new runs still require the original GPU fixture and admission/completion
guards. The collector now detects an unexpected owner exit at its 30-second
observation interval instead of waiting for the generic no-progress deadline.

## Final continuation after checkpoint accounting refusal

Case 9460 completed the eight warmup, Top-8 and Top-6 requests. The first
repeated-verification request completed one accepted width-two verification,
then the next checkpoint admission priced a changed-size replacement as a full
additional allocation. The pinned `llama-context.cpp` ON_DEVICE writer releases
its old buffer before allocating a changed-size replacement. This was an
application reservation calculation, not a kernel-floor failure. The native
failure terminal, ordinary OS close and exact production restoration are kept;
global positive GPU retirement is not invented for the failed run.

The experiment now credits only the raw payload of a positively completed
snapshot belonging to the same retained single-Vulkan-buffer context. Alignment
slack is never credited. A new size is rounded up by 2 MiB, and the original
device cap, Direct reserve, physical reserve and kernel floor still apply.
Each admission records payload, completed payload, additional upper bound,
device ledger and Direct availability. The builder pins and checks the exact
release-before-allocation writer source. Host regressions cover first capture,
same-size reuse, growth, shrinkage and rejection beyond the payload limit.

Case 9480 needs only 20 requests: counting order `0,0,4,4,0`, then the 15 quality
requests. The five completed requests from 9440 and eight from 9460 supply their
already completed speed ABBAs and are not replayed. Their partial evidence is
explicitly distinct from the final complete model/source retirement protocol.
