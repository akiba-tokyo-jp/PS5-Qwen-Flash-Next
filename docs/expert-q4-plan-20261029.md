# Expert-only four-bit implementation and qualification

The seven steps below completed in their finite requested scope. See
[the final application and placement report](expert-q4-adoption-20261029.md)
and its [sanitized evidence](expert-q4-adoption-20261029.json).

- [x] Compatible pinned Q4_0 geometry, independent encoder and unchanged tensor inventory.
- [x] All 75,264 routed Expert matrices converted; complete source/output hashes and physical part readback.
- [x] Compressed 481-slot GPU cache, F32-input dispatch and strict metadata reset.
- [x] 27 actual-weight GPU cases / 324 graphs with independent F64 references and paired timing.
- [x] Complete mixed 76-split / 1,256-tensor model loaded and executed on PS5.
- [x] Repeated full same-Q4 vocabulary/routes, finite counting quality, decode/TTFT/I/O comparison.
- [x] Correctly labeled passive monitor/API, both actual native frames, normal close, verified production placement and BF16/older rollbacks.

No 8-bit comparison was performed. Scope is finite counting; it does not certify
general reasoning quality. The BF16-specific padded delivery, prefix and
speculative path is preserved in its rollback and is disabled in this Q4 profile.

The owner authorized Expert-only quantization and selected four-bit validation
only on 2026-10-29. Eight-bit conversion/comparison is outside this execution.
The BF16 production model, SELF and five settings remain the fallback.
Non-Expert weights, routers, attention, recurrent/PLE state, KV precision,
selected Expert count and model components remain unchanged. Quantization is
lossy and must not be represented as original-BF16 numerical equivalence.

## Format and bounded order

1. Select a pinned ggml four-bit format compatible with both 2560-column and
   640-column Expert matrices. Start with Q4_0: 32 values and a two-byte scale
   occupy 18 bytes, or 4.5 effective bits/value. Q4_K's 256-value row blocks
   do not divide the 640-column rows. Do not pad or reshape the model silently.
2. Convert representative original Expert gate/up/down matrices with bounded
   reads, record exact source/quantized hashes, check independent dequantization,
   numerical errors, all non-Expert preservation and explicit final status.
3. Implement typed compressed bank geometry and source/dispatch eligibility.
   Include quantization-block and Direct-read/descriptor alignment in stride
   calculations. Keep compressed bytes in cache; no full BF16 expansion on
   every token. Preserve source identity, range bounds and positive ownership.
4. Build one isolated actual-Expert GPU comparison at widths 1/2/4, checking
   quantized outputs against an independent dequantized reference. Measure
   complete read/delivery/compute separately from compute-only time. Check
   duplicate/edge IDs, padding, retirement and explicit normal close.
5. Connect selected Expert types and payloads to a separate full-model profile.
   Reuse existing non-Expert files/tensors where possible. Do not reconvert the
   original checkpoint or create a second copy of unchanged large PLE tables.
6. Compare the admitted candidate with BF16 using the same prompts and actual
   model source counters, TTFT, accepted decode throughput and peak allocations.
   Quantized quality is evaluated against BF16; identical full logits are not
   required. Keep component correctness and full-model answer quality separate.
7. Adopt only a repeatable whole-application gain with acceptable observed
   answer quality and complete normal shutdown/readback. Otherwise retain BF16
   and record the tested result. A policy refusal is not physical impossibility.

An original matrix is 3,276,800 bytes; Q4_0 payload is 921,600 bytes (28.125%).
Scales are included in this ratio, while file/bank alignment remains additional.
All 48 text layers' routed Experts require 67,947,724,800 Q4_0 payload bytes;
this does not imply that they fit in the console's RAM.

## Execution constraints and evidence

Reuse completed source/driver/CPU observations and finite operators. Do not
repeat old consumed cases, unrelated research, an unchanged failed launch or
8-bit work. No reboot, force kill, GPU reset, CI or uncertain resource release.
New native work needs fresh exact-owner/resource observations for its changed
scope. Driver source/profile stay at `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. Pin actual application
relink inputs, not only the driver repository reference.

Each stage records implementation, host/native validation, speed and production
adoption separately. A completed losing component does not require a full-model
rerun. A native refusal closes that case and does not stop independent host work.
