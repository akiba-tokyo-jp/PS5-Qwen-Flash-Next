# Staged Expert 2-bit comparison

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

| Candidate | Current evidence | Required next gate |
| --- | --- | --- |
| Expert replacement policy | Twelve closed all-Q2 traces replay exactly, including every control fill/slot. Two-touch probation reduces counting misses 7.250% and held-out quality misses 5.306%. Same-model case 8900 ABBA improves decode 1.029182 to 1.127026 tok/s (+9.507%), with zero full-F32 difference and identical ordered routes. Normal passive/API 8940 measures 1.126481/1.125980; both frames viewed. Placement 8950 verifies the canonical app, all five settings, every retained rollback and fresh idle. | Adopted in the finite qualified scope. |
| Gate/Up/Down bundle reads | Compact geometry and 25,088 positions pass host checks. CPU-only actual-weight 8914 compares the same bytes: one request versus three improves read-wall throughput 44.298% (time reduction 30.699%). | Integrate a bounded immutable bundle source; compare actual model decode before adoption. |
| I/O serialization and GPU overlap | Case 8900 records the existing two lanes and 540/553 selected serial batches in the control/candidate whole requests. | Distinguish composite-gather fallback from deliberate serial selection; qualify Q2 owner geometry before model comparison. |
| Expert-sharing speculative decode | Earlier BF16 results and current quantized component widths are preserved. They do not qualify Q2 complete-state handling. | Port complete-state and causal verification to Q2, charging rejected work and snapshot costs. |
| Resident non-Expert compression | Output projection Q8_0 would save 595,968,000 payload bytes. This is arithmetic, not a native memory/speed result. | Original-BF16 conversion, own-format arithmetic, complete memory accounting and bounded cache quota transfer. |
| Intermediate-copy reduction | The helper excludes single transfers below 1 MiB; individual Q2 roles are smaller. | Compare GPU-visible destinations at compressed sizes, retaining visibility and completion. |
| Prefix/full-state reuse | Exact-prefix implementation exists, but is disabled in Q2. | Q2 full-state restoration and a separate TTFT/prefill comparison; charge snapshot memory. |
| CPU management overhead | Default behavior remains unchanged; new policy selection requires empty observation history and adds no heap arrays. | Prove unchanged fills/guards and measure actual process benefit for duplicated immutable work. |

The single-load 8900 experiment also completes the requested exact Q2 decode
I/O measurement. Original-policy arms 1 and 4 give 0.492914 GB/token, 944.429
calls/token and 1.418164 ms mean individual pread wall time. Probation arms 2
and 3 give 0.432558 GB/token and 831.524 calls/token. Token counter differences
exclude prefill and final EOS and reconcile with independent per-call counters.
Never average different policies into one baseline. Unstarted diagnostic 8880
is superseded, not replayed.

Neither a bundle CPU comparison nor an offline miss reduction is a measured
whole-model speedup. Production now uses the normally qualified all-Q2
probation app. Open gates above remain open; this checkpoint does not
close the owner's complete eight-candidate task.
