# Staged Expert 2-bit qualification

The owner selected Gate/Up at 2-bit with Down retained at 4-bit, followed by
all-Expert 2-bit only if mixed-model quality holds. The first candidate uses
Q2_K Gate/Up and Q4_0 Down. All 49 layers, 512 Experts per layer, top-10 routing,
non-Expert BF16/F32 payloads, F32 activation inputs and F32 KV are retained.
The original BF16 and selected Q4 production files remain intact.

Full-model conversion, physical readback, metadata sealing and complete-source
host admission have completed. Generation qualification is in progress. Component
results below do not establish model quality or inference throughput. The
machine-readable measurements are in [the result record](expert-q2-results-20261029.json).

## Mixed counting model

Native case 8440 completed one model load and three independent requests on the
PS5. Every answer was `1, 2, 3, 4, 5, 6, 7, 8`. The two timed requests compared
all 23 full vocabulary rows and ordered Expert routes against the same-format
reference, with maximum absolute logit error zero. Source/device owners retired
positively, the device ledger returned to zero, and normal OS close plus exact
Q4/settings restoration completed.

| Request | Decode tok/s | TTFT seconds | Whole-request physical GB |
| --- | --- | --- | --- |
| 0, warmup | 0.907694 | 22.077 | 31.4160 |
| 1 | 0.914238 | 20.126 | 31.4160 |
| 2 | 0.912485 | 20.130 | 31.4160 |

Pooled timed decode was **0.913361 tok/s**, versus the earlier same-console
headless Q4 control's **0.871504 tok/s**, or **4.8028%** higher. The control
precedes this run; this is not a simultaneous matched speed comparison. Both
produce the same 22 output tokens and use 21 accepted decode transitions per
request. Physical bytes include prefill and decode. This successful counting
screen does not establish the additional quality criteria or production
adoption. The fixed Japanese instruction, arithmetic and JSON extraction
comparison is in progress before the conditional all-Expert 2-bit stage.

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

The first packed producer ended explicitly after 59 completed files when a
write returned `-1`; a subsequent FTP publication returned `ENOSPC`. Its CPU
Direct window retired positively and no GPU was started. The original write
errno was not recorded, so the FTP error and successful continuation after
capacity recovery support storage pressure as the cause. New writes record
errno and retain a two-GiB disk margin. This is a disk policy, not a change to
kernel-memory or GPU admission.

Capacity recovery removed one archived closed trial copy and a batch of 130
explicitly listed files, including trial/layout copies and the backed-up
incomplete output.
Every retained current/older rollback was verified with whole native SHA256
before and after the batch; each removed batch file passed whole native
SHA256 and stable identity checks against its complete host copy. Original
BF16 and Q4 model source files were untouched. Measured available space
recovered to 9,128,837,120 bytes. The 59 completed files / 79 physical parts
were retained by exact native identities, and only the remaining 15 logical
files were submitted to a fresh CPU continuation. That continuation completed:
all 74 replacement logical files and all 75,264 Expert matrices are accounted
for, and both producers positively retired their CPU workers and Direct owners.
Both producer journals are preserved separately; combined receipt rows are
explicitly marked as derived. The completed model receipt covers 76 logical
files, 1,256 tensors and all 147 Expert tensors. Actual completed metadata passed
the source parser with 74 composite plans and 405 physical source references.

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

Two preliminary title launches terminated before GPU initialization during
backing-metadata admission. The diagnostic launch read the full metadata with
the expected SHA256 and stable descriptor identity; its final `lstat` returned
`-1`. Native-title `lstat` had already returned `EPERM` in historical case 3474.
The corrected metadata reader uses the same independently reopened
`O_NOFOLLOW` descriptor plus `fstat` method as the qualified launch-integrity
reader. It retains all ten identity fields, the explicit 1 MiB CPU Direct
window, whole SHA256, EOF and positive close/unmap/release checks. Source-plan
admission and GPU math are unchanged. Both CPU-failed launches ended by normal
OS close and exact Q4/settings restoration; neither is model-quality evidence.

The next CPU-only return exposed an ordinary-source assumption in Direct GGUF
metadata registration: a shorter physical first part had to be exactly 512 MiB.
Packed composite file 2 has 275,252,832 physical bytes and a 1,632-byte header;
file 75 contains only its 832-byte header. Their complete logical tensor spans
are backed by the already validated composite ranges. The isolated metadata
extension therefore admits the exact complete first header prefix, independently
checks its first physical identity, retains the full logical tensor size for
GGUF span validation and bounds actual reads by physical bytes. It never pads
missing bytes, removes tensors or changes ordinary-source registration.
Focused host tests cover 832-byte and multiple-window prefixes, exact content,
aligned reads, malformed bounds, short-read quarantine and ordinary behavior.

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
- [Composite metadata window](../native/app/expert_q2_metadata_window.h) and
  [its isolated derivative](../tools/expert_q2_metadata_reader.py): separate
  physically readable header bounds from the complete logical tensor span.
- [Native relink](../tools/build_expert_q2_composite.py): replaces the comparison
  entry and qualified resident source-owner object, preserving GPU providers.
- [Model comparison](../tools/expert_q2_model_source.py): `entry_source` and
  `cache_source` preserve original guards and F32 inputs, select the compressed
  cache, and distinguish quality failure from GPU completion uncertainty.
- [Metadata sealing](../native/qwen_flash_next/expert_q2_seal.cpp): full Direct
  metadata hashes, identities, EOF, own-file permissions and positive release.
  Three new metadata files are staged outside the title, verified, and renamed
  into their owned destination without overwriting existing paths or changing
  production-directory permissions.
- [Upstream license](../third_party/notices/ggml-quantization/NOTICE.md).

Upstream llama.cpp is pinned to
[`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`](https://github.com/ggml-org/llama.cpp/tree/0a1ef309cdbb9f2024f58a38fb4c42352c5db569).
The driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, with persistent caches disabled. No CI or reboot was used.

The [fixed quality cohort builder](../tools/build_expert_quality_cohort.py)
uses three predeclared prompts, three independent requests per prompt, complete
same-format output rows/routes, and separate answer-quality predicates.

## Acceptance

Follow [the finite staged plan](expert-q2-plan-20261029.md). A completed mixed
counting regression is a tested quality failure and stops the conditional
all-2-bit stage. If counting passes, compare a fixed Japanese instruction,
arithmetic and extraction/JSON cohort against Q4, requiring retention of every
Q4-correct answer. Measure decode separately from prefill on the same console.
Adoption requires passing source, arithmetic, completion, quality and measured
speed criteria; otherwise the exact selected Q4 remains production.
