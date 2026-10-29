# Staged Expert 2-bit qualification

The owner selected Gate/Up at 2-bit with Down retained at 4-bit, followed by
all-Expert 2-bit only if mixed-model quality holds. The first candidate uses
Q2_K Gate/Up and Q4_0 Down. All 49 layers, 512 Experts per layer, top-10 routing,
non-Expert BF16/F32 payloads, F32 activation inputs and F32 KV are retained.
The original BF16 and selected Q4 production files remain intact.

Full-model conversion and generation qualification are in progress. Component
results below do not establish model quality or inference throughput. The
machine-readable measurements are in [the result record](expert-q2-results-20261029.json).

## Component results

| Format | Original matrices sampled | Weight NRMSE range | Native GPU cases / graphs | Maximum GPU vs own-format F64 error |
| --- | --- | --- | --- | --- |
| Q2_0 | 27 | 0.717013–0.735435 | 27 / 324 | 1.766e-9 |
| Q2_K | 27 | 0.296395–0.311307 | 18 / 216 | 3.580e-9 |

Both formats passed independent decoded-value references, canaries, repeated
Expert IDs and indexed widths 1/2/4, with positive backend retirement and zero
live device ledger bytes. Q2_K native encoding also reproduced all 27 host
reference SHA256 values. These finite matrix cases do not measure language
quality. Q2_K has 2.625 effective bits including block metadata; Q2_0 has 2.25.
Original Gate/Up rows divide Q2_K's 256-value block. Original Down rows of 640
values do not, so the first candidate keeps Down at Q4_0.

## Storage and source integration

The complete mixed model has 98 Q2_K Gate/Up tensors and 49 Q4_0 Down tensors.
The Expert triplet shrinks from 2,764,800 to 1,996,800 bytes, or 27.78%, before
alignment and cache effects. This is a byte ratio, not a promised speedup.
The original cache budget admits 581 active slots plus one staging plane under
the unchanged 512 MiB individual-bank cap.

The new physical files contain only Q2_K Gate/Up data and complete GGUF headers
and alignment padding. Composite logical ranges reuse exact sealed Q4 Down and
non-Expert payloads. Original BF16 is the quantization source; Q4 is never
requantized. Complete logical GGUF tensor coverage and offsets are retained.
Every new physical byte is densely written and fully read back in 512 MiB parts.
The retained payload SHA256, original whole-file hashes and native identities
remain independently bound by the source admission metadata.

A sparse prototype was rejected before GPU work when readback exposed five
16 KiB zero-tail blocks within partly written 64 KiB filesystem allocation
units. Independently regenerated quantized weight bytes matched. The selected
packed representation avoids sparse holes entirely. No production data was
deleted or changed to make room for the candidate.

The isolated source derivative retains the qualified resident reader. Ordinary
single-range paired I/O stays on its existing path. Cross-range pairs use a
bounded Direct gather that handles different logical and physical alignment
residues, preserves already assembled bytes and retains completion ownership.
Host cases cover single reads, paired reads, upload callbacks, part/alias/EOF
boundaries, alignment and positive retirement. Eight malformed range plans and
nine malformed complete-source metadata plans were rejected.

## Implementation references

- [Q2_K encoder](../tools/expert_q2k_quantize.c): pinned `nearest_int`,
  `make_qkx2_quants`, `quantize_row_q2_K_ref` and original-BF16 wrapper.
- [Native CPU conversion](../native/qwen_flash_next/expert_q2_local_convert.cpp):
  `Source`, `Writer`, four-worker encoding, full source hashes and physical readback.
- [Composite source admission](../native/app/expert_q2_composite_source.h):
  `expert_q2_composite_source_integrity` validates complete logical regions
  against the retained Q4 receipt, proof, layout and exact payload hashes.
- [Reader derivative](../tools/expert_q2_sparse_reader.py): `reader_header` and
  `reader_source` derive isolated views; the original reader is unchanged.
- [Native relink](../tools/build_expert_q2_composite.py): replaces the comparison
  entry and qualified resident source-owner object, preserving GPU providers.
- [Model comparison](../tools/expert_q2_model_source.py): `entry_source` and
  `cache_source` preserve original guards and F32 inputs, select the compressed
  cache, and distinguish quality failure from GPU completion uncertainty.
- [Metadata sealing](../native/qwen_flash_next/expert_q2_seal.cpp): full Direct
  metadata hashes, identities, EOF, own-file permissions and positive release.
- [Upstream license](../third_party/notices/ggml-quantization/NOTICE.md).

Upstream llama.cpp is pinned to
[`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`](https://github.com/ggml-org/llama.cpp/tree/0a1ef309cdbb9f2024f58a38fb4c42352c5db569).
The driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, with persistent caches disabled. No CI or reboot was used.

## Acceptance

Follow [the finite staged plan](expert-q2-plan-20261029.md). A completed mixed
counting regression is a tested quality failure and stops the conditional
all-2-bit stage. If counting passes, compare a fixed Japanese instruction,
arithmetic and extraction/JSON cohort against Q4, requiring retention of every
Q4-correct answer. Measure decode separately from prefill on the same console.
Adoption requires passing source, arithmetic, completion, quality and measured
speed criteria; otherwise the exact selected Q4 remains production.
