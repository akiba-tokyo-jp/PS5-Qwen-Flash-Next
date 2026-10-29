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
   same quality and speed criteria. Otherwise retain Q4 and record the tested
   failure explicitly. Components alone never establish quality or tok/s.

All current memory floors/caps and exact-owner ordinary close remain enforced.
Mixed payload per Expert triplet is 1,996,800 bytes versus Q4's 2,764,800 bytes,
a 27.78% reduction before alignment/cache effects. The candidate fits 581 active
slots plus one staging plane within the original 1,333,739,520-byte budget and
the unchanged 512 MiB maximum individual bank. An all-2-bit Q2_K/Q2_0 triplet
would use 1,536,000 bytes, 44.44% below Q4. Neither ratio is a promised
end-to-end speedup.
