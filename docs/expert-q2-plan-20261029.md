# Staged Expert 2-bit comparison

Current disposition (2026-10-30): **all eight proposed families have a final
comparison or observed execution-unavailable classification**. Qualified winners
are installed after normal case 9290 and verified placement 9310. See the
[complete results and implementation references](expert-q2-optimization-results-20261030.md)
and [sanitized evidence](expert-q2-optimization-results-20261030.json).
The staged order below is historical; the owner's later acceptance of expected
Q2 loss and the completed optimized installation supersede its earlier holds.


The owner authorized Gate/Up at 2-bit while retaining Down at Q4 on 2026-10-29.
Only after that candidate preserves measured quality may all routed Experts
move to 2-bit. This supersedes the earlier 4-bit-only experiment limit.

Use pinned Q2_K for Gate/Up (256 values / 84 bytes, 2.625 effective bits including
its scales and minima). Original Gate/Up rows contain 2560 values and divide
256 exactly. Down rows contain 640 values and remain Q4_0 (32 values / 18 bytes)
in the first model candidate. Quantize original BF16, never Q4 reconversion.
Q2_0 (64 values / 18 bytes) was independently qualified as a component control:
sampled weight NRMSE was 0.717–0.735, compared with 0.296–0.311 for Q2_K.
These are weight errors, not language-quality scores. If mixed-model quality
passes, the conditional all-2-bit candidate can retain Gate/Up Q2_K and use
Q2_0 for Down without shape padding or Expert removal.

The mixed candidate subsequently passed counting, three fixed quality tasks
with three independent requests each, and the normal passive/API application.
It is installed as production in case 8580; see the result record. This admits
the conditional all-Expert stage. For that stage use the separately qualified
signed-scale MSE Q2_0 encoder, not the earlier high-error upstream encoder.
Retain the existing Q2_K Gate/Up bytes and convert only Down from original BF16.
Preserve the exact mixed production, Q4 and BF16 programs, settings and weights.

Preserve all 147 Expert tensors, all 512 Experts and top-10 routing, unchanged
non-Expert BF16/F32 payloads, F32 activation inputs and F32 KV. Keep the selected
Q4 SELF, settings, source files and original BF16 rollback intact. Reuse driver
872cc1264ad8ba5d6b888b092968fa5858a38c58, cumulative-idle, with persistent
caches disabled. Record exact compile/link ancestry and separate format guards.
No CI, reboot, force close, ambiguous dispatch replay or driver modification.

## Finite qualification order

1. Cross-check 27 original matrices against pinned Q2_0 encode/decode bytes.
2. Validate actual PS5 indexed GPU arithmetic against independent per-format
   F64 references, repeated IDs and widths 1/2/4 before full model execution.
3. Convert into a new owned directory on the console CPU, preserving every
   original logical hash and completely reading back each new 512 MiB part.
   Store only new Q2_K Gate/Up payloads and complete GGUF headers/padding.
   Composite source ranges reuse sealed existing Q4 Down and non-Expert
   payloads, with exact payload hashes, offsets and native identities. This
   retains complete logical GGUF files without duplicating 59 GB. Every byte
   of the approximately 27 GB of new packed storage is written and read back;
   sparse zero holes are not used. All original BF16 and Q4 files remain intact.
4. Run the mixed model against Q4 with identical prompts and greedy policy.
   A counting regression or nonfinite/broken output is a terminal quality
   failure and prevents the conditional full-2-bit stage. If counting passes,
   add a small fixed Japanese instruction, arithmetic, extraction and structured
   output cohort, requiring every previously correct Q4 answer to remain correct.
   Report this finite scope; do not call it broad reasoning certification.
5. Adopt only with passing arithmetic/completion/source guards, passing quality
   and a measured decode improvement. Then test the all-2-bit candidate with the
   same quality and speed criteria, subject to the owner's later clarification
   accepting expected all-Q2 quality loss below. Otherwise retain the fastest already
   qualified production and record the tested
   failure explicitly. Components alone never establish quality or tok/s.

All current memory floors/caps and exact-owner ordinary close remain enforced.
Mixed payload per Expert triplet is 1,996,800 bytes versus Q4's 2,764,800 bytes,
a 27.78% reduction before alignment/cache effects. The candidate fits 581 active
slots plus one staging plane within the original 1,333,739,520-byte budget and
the unchanged 512 MiB maximum individual bank. An all-2-bit Q2_K/Q2_0 triplet
would use 1,536,000 bytes, 44.44% below Q4. Neither ratio is a promised
end-to-end speedup.

## Owner clarification and remaining normal qualification

The mixed candidate remains installed. The all-Q2 candidate completed original
BF16 Down conversion, full native logical hashing, actual sealed-source admission,
three counting requests and all nine fixed quality requests. It measured
1.031136 headless decode tok/s against earlier mixed 0.913361, but added Markdown
fences to all three JSON-only responses. Extracted values were correct; the raw
format instruction failed. Preserve that strict result, including its initial
rejection under the assistant-defined rule. The owner subsequently clarified
that expected Expert 2-bit quality loss is understood and did not require
continued exact quality retention. Correct answer contents passed 9/9; strict
format passed 6/9. No output normalization is added to the application.

Continue the prepared fresh normal-display/API case 8720. Require two matching
native frames, exact same-format complete F32 rows/routes, positive ownership
retirement, ordinary close/restoration and both decode rates above the earlier
mixed normal control. On success, place the exact tested SELF and settings,
verify canonical and all retained rollback hashes, and record the quality
tradeoff in the selected installation. Do not repeat conversion, source hashing,
counting or the completed quality cohort. Every executed case normally closed
and restored the exact mixed control; audit 8790 verified seven programs and
five settings. Normal validation and final selection remain pending.

## Post-quantization optimization validation

The owner authorized all eight proposed optimization comparisons, incorporation
of measured winners, and explicitly accepted the remaining console freeze risk.
Preserve current memory, identity, ownership and positive-completion guards;
reboot, CI and ambiguous-operation retries remain disabled.

| Candidate | Final evidence | Disposition |
| --- | --- | --- |
| Expert replacement | 8900 same-model ABBA +9.507%; normal 8940 and placement 8950. | Adopted; retained in 9290/9310. |
| Gate/Up/Down bundle reads | Actual model 9180 +1.469%; exact F32/routes/misses; 336 immutable bundles, originals fallback. | Adopted after normal 9290 and placement 9310. |
| I/O serialization and GPU overlap | Composite 9040 -0.0609%; genuine overlap 9250 is slower than unsplit (36.388 -> 57.442 ms), despite overlap intervals. | Tested losers for these implementations; retain unsplit scheduling. |
| Expert-sharing speculative decode | 9160 +1.384%, same-width equality and forced rejection. Final normal consumer accepts once in 9290. | Adopted only on the final exact-prefix consumer. |
| Resident non-Expert compression | Exact Q8 host/reference controls; FTP and native pwrite both fail ENOSPC. No GPU/model execution. | Execution unavailable under current filesystem allocation; unadopted, originals preserved. |
| Intermediate-copy reduction | Operative 9080 streaming-copy comparison -0.530%, exact F32/routes/bytes. | Tested loser; threshold-only unexercised 8990 is superseded. |
| Prefix/full-state reuse | 9100 capture-charged pair throughput +30.611%; final repeat TTFT 63.117 ms and exact emitted sequence in 9290. | Adopted after complete-state and final-consumer qualification. |
| CPU management overhead | 9040 atomic immutable-range hint +0.164%; exact concurrent bytes/metadata controls. Actual counters positive in 9290. | Adopted in the qualified combination. |

The single-load 8900 experiment also completes the requested exact Q2 decode
I/O measurement. Original-policy arms 1 and 4 give 0.492914 GB/token, 944.429
calls/token and 1.418164 ms mean individual pread wall time. Probation arms 2
and 3 give 0.432558 GB/token and 831.524 calls/token. Token counter differences
exclude prefill and final EOS and reconcile with independent per-call counters.
Never average different policies into one baseline. Unstarted diagnostic 8880
is superseded, not replayed.

Independent component percentages are not added. The final normal first
request measures 1.143314 decode tok/s; the retained exact repeat measures
1.106472 tok/s with 63.117 ms TTFT. Capture-charged two-request throughput is
0.773582 generated tok/s. All executable comparisons are complete; output Q8
is explicitly execution unavailable. Qualified winners are verified in
production, with all rollback/settings hashes and fresh idle passed.
