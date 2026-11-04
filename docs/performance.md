# Performance and validation

The latest completed selection is R1 + P1. Results come from short native
validation cohorts on one PS5, not general answer-quality, long-context or
sustained-service qualification.

## Metric and conditions

Decode rate is `(generated_tokens - 1) * 1000 / decode_ms`. The first generated
token is associated with prefill/TTFT and excluded from the decode numerator.
Prefill, TTFT, whole-request time and end-to-end throughput are separate metrics.
Build, deployment and result-transport time are not inference speed.

| Condition | Meaning |
| --- | --- |
| Cold | First request with an empty application expert cache |
| Retained | Expert weights remain cached; request/KV state is reset |
| Exact-prefix | The same prefix reuses explicitly qualified request state |

Cold does not mean a rebooted console or guaranteed empty OS file cache.
Cached files, expert weights and reusable request state are different conditions.
S1's third condition was retained2, not exact-prefix.

## Completed matched comparisons

| Change | Condition | Control tok/s | Candidate tok/s | Change |
| --- | --- | ---: | ---: | ---: |
| R1: completed-stage synchronization | Cold | 10.075792 | 10.214440 | +1.376% |
| R1 | Retained | 11.952293 | 12.142559 | +1.592% |
| R1 | Exact-prefix | 13.031378 | 13.255748 | +1.722% |
| P1: cold-prefill output refinement over R1 | Cold | 10.162065 | 10.436816 | +2.704% |
| P1 | Retained | 12.094066 | 12.172570 | +0.649% |
| P1 | Exact-prefix | 13.264824 | 13.217511 | -0.357% |

Each change has its own matched control. Multiplying their percentages would
invent an unmeasured cumulative comparison. P1 establishes no exact-prefix gain.
The README's selected-profile rates are the P1 candidate means in this table.

The [complete report](native-performance-comparisons-20261102.md) and
[JSON evidence](native-performance-comparisons-20261102.json) preserve cohort
identity, inputs, controls, numerical checks and ordinary restoration.

## Numerical and quality limits

R1 matches all 69 ordered full-vocabulary F32 rows, actual routes, tokens and
output bytes against its reference. P1 matches 68 of 69 rows; the first cold row
differs, with maximum absolute logit difference `0.1812725067138672`. Its
observed tokens and ordered routes match.

Finite outputs, identical greedy tokens or a counting-task pass do not prove
unchanged broad reasoning quality. A check against the same quantized model
also does not establish original-BF16 equivalence. Precision, routing, reduction
order and output-selection changes must be disclosed.

## Other completed candidates

| Family | Disposition |
| --- | --- |
| G1: GPU ranking/sort | Not adopted after tested refinements |
| Q1: shared-weight quantization | Not adopted |
| Q2: Up / Gate-Up IQ2 | Original and minimum-stream model profiles slower than recorded P1 in all three conditions |
| Q3: Down IQ2 | Full-plane, source-prefix and minimum-stream profiles slower than recorded P1 in all three conditions |
| I1: source prefetch | Not adopted after distinct refinements |
| S1: speculative/MTP execution | Not adopted; its second retained request is not exact-prefix |

See [source/stream follow-ups](source-capacity-and-stream-followups-20261104.md).
Component correctness is not a whole-model speedup. Single negative screens
are identified as screens, not ABBA means. No tested rejection proves every
future improvement impossible.

## Strata: incomplete speed evidence

ST1/ST2 have no eligible existing Q8_1 activation-conversion path under the
selected arithmetic policy. Both ST3 cache-wait refinements pass native
numerical/route equivalence, but neither has completed speed/adoption evidence.

The first control returns 10.401232 / 12.199695 / 13.349245 tok/s; the first
`group` refinement returns 10.446024 / 12.258107 / 13.373284 tok/s, ordered
cold / retained / exact-prefix. This pair is incomplete: the candidate's
ordinary close/restoration is unconfirmed, readback timing is pending and the
final control is missing. These rates are **not a confirmed improvement** and
are not combined with completed R1/P1 cohorts. See
[interrupted validation](strata-validation-20261105.md).

## New results

Keep configuration, source/profile provenance, precision, input, output count
and cache condition with every measurement. Collect qualification hashes
separately from observer-free timing. Require actual outputs/routes, positive
source/device retirement and ordinary exit/restoration. Reuse completed cases;
add a distinct refinement or a justified comparison instead of repeating an
unchanged benchmark as a check.
