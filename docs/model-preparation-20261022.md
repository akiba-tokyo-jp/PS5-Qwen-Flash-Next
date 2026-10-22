# Original BF16 preparation and host audit

`tools/prepare_model.py --acquire` resumes original shard acquisition and then
performs sequential original SHA256 verification, pinned BF16 conversion,
converted structure/payload verification and final file hashing. Acquisition
and preparation have separate nonblocking OS leases. An exited process releases
its lease; a second writer cannot acquire an active lease. Fresh run records and
old failure records remain on the data disk. No console access is part of this
batch.

The acquisition deadline is 12 hours by default. Verification, converter,
payload-audit and final-hashing phases each have a six-hour deadline. Existing
complete files may be retained during acquisition without rereading them on the
shared USB disk. That state explicitly reports `original_shards_verified=false`;
every original shard must still pass SHA256 before converter execution. Newly
downloaded shards are verified before atomic publication. Interrupted partial
files remain resumable. Phase status is persisted with flush/fsync and replacement.

Acquisition now uses bounded 32 MiB ranges by default. Each worker retains only
its current immutable file's HTTPS redirect in memory; expired signed redirects
refresh from the pinned origin, preserving the requested range. No signed URL
is logged. A byte-checked host sample took 3.047 seconds for 8 MiB and 2.781
seconds for 32 MiB with redirect reuse. This sample informed acquisition only;
it does not predict complete-checkpoint or console throughput. Metadata headers
remain limited to 8 MiB, and every data response must honor its exact range.

## Complete metadata plan

`tools/audit_conversion.py` checks the pinned source ZIP and all 237 executed
Python sources, then subclasses the actual Qwen4Exp converter with storage-free
`meta` tensors. Its normal filtering and transformation methods determine every
converted tensor name, shape and precision. Learned tensors cannot be
materialized during this planning path; only 280 bytes of original integer
constants are read. This is format/metadata processing, not learned inference.

The original 48-layer trunk, all 512 experts, top-10 routing and required PLE
remain present. One MTP layer remains in the converted file but is not loaded
for this text inference path. The text converter excludes 333 vision tensors;
their original checkpoint data is retained separately. No expert or required
text component is pruned.

The derived layout has 1,256 tensors: 857 BF16 and 399 F32. F32 follows the pinned
converter's norm/router/SSM handling. No F16 or quantized tensor is accepted.
Layout SHA256 is
`8f558e3ad4114c6b733d2a871394187557c24d430f4b38352146c1082bddd260`.

| Native placement | Planned tensor bytes |
| --- | ---: |
| Device weights | 8,755,105,280 |
| Mapped trunk experts | 241,591,910,400 |
| Required lazy PLE | 102,400,491,520 |
| Mapped CPU token embeddings | 1,271,398,400 |
| MTP tensors not loaded by the text runtime | 5,217,016,832 |

The largest device tensor is 1,271,398,400 bytes. The existing cache, context,
workspace, staging, CPU and reserve budgets bring the planned requirement to
11,976,330,752 bytes (about 11.15 GiB). The actual native `ModelFootprint` and
`MemoryBudget` matched every tensor and this total in a host replay. Synthetic
limits one byte below each driver/Direct/OS/buffer boundary were rejected.
These values do not establish available PS5 memory, physical residency or
successful model loading. Fresh observations remain mandatory.

## Before a conversion receipt may be published

- Inspect every split with the pinned read-only GGUF reader. Require the complete
  tensor set, exact shapes and expected BF16/F32 types, correct split numbering,
  bounded aligned nonoverlapping spans and original architecture/routing keys.
- Compare PLE layer assignments and exact 64-bit hash constants to the originals.
  Compare all 128 concatenated PLE parts, totaling 102,400,491,520 BF16 bytes.
- Compare every original expert projection, including the retained MTP layer:
  147 output tensors and 246,625,075,200 bytes. Gate/up comparison follows each
  expert's original strided half, rather than treating the split as one contiguous
  source range. Comparisons use two buffers of at most 8 MiB each.
- Compare both original embedding matrices (2,542,796,800 bytes) directly. Replay
  the pinned weight-format transforms for 1,094 remaining source tensors and
  compare all 1,106 dense outputs (7,667,558,912 bytes). Each source is bounded to
  64 MiB; the actual largest input is 60 MiB, and each transformed F32 array is
  bounded to 256 MiB. No model forward pass or matrix inference is involved.
- Require exactly one completed payload check for every converted tensor. The
  total is 359,235,922,432 tensor bytes, including retained MTP tensors.
- Hash every final GGUF split and recheck converter-source identity. Publish the
  fsynced model receipt only after all checks pass. A failure or timeout retains
  partial output and a failed phase, without a model receipt.

The dense replay checks the saved weights against the pinned converter; it does
not independently validate that converter's arithmetic or model forward results.
Host format/copy checks do not establish console model quality or tokens/s. Full
checkpoint acquisition and the real conversion/payload checks are still pending;
the complete metadata plan and small fixture checks have passed.

## Manual checks

The Python suite passes 44 tests. Actual pinned GGUF fixtures accept BF16/F32 and
exact large integer constants, and reject F16, big endian files, truncation and
overlapping spans. The full 1,256-tensor plan passes the native memory replay.
The first metadata subclass attempt and initial generic integer-array fixture
failed during host development; they produced no accepted model receipt and
their evidence remains preserved. The corrected fixture uses the actual PLE
64-bit writer method.

Four retained original dense inputs exercise actual exp, norm, V-head reorder
and indexer-split transformations, producing five verified output tensors.
Changing one output bit or exceeding the source input bound is rejected.

Windows status replacement also tolerates transient scanner sharing conflicts
with at most five attempts and 0.75 seconds of delay. Persistent conflicts and
other disk errors still fail explicitly; this host metadata rule never retries
console work or GPU resource release.

```powershell
python tools/prepare_model.py --cache D:/PS5-AI/qwen-flash-next --out D:/PS5-AI/qwen-flash-next/converted-bf16-FRESH --state D:/PS5-AI/qwen-flash-next/model-preparation-FRESH.private.json --acquire --jobs 2
python tools/audit_conversion.py --cache D:/PS5-AI/qwen-flash-next --plan-out D:/PS5-AI/qwen-flash-next/audit/conversion-plan-FRESH.private.json
python tools/check_conversion_audit.py --cache D:/PS5-AI/qwen-flash-next --out D:/PS5-AI/qwen-flash-next/build/conversion-audit-check-FRESH
python tools/check_model_footprint.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next --plan D:/PS5-AI/qwen-flash-next/audit/conversion-plan-FRESH.private.json --out D:/PS5-AI/qwen-flash-next/build/model-footprint-FRESH
python tools/check_dense_replay.py --cache D:/PS5-AI/qwen-flash-next --out D:/PS5-AI/qwen-flash-next/build/dense-replay-FRESH
```

Use the CPU-only conversion virtual environment for conversion and metadata
planning. Outputs above require fresh names. GitHub Actions remain disabled.
The [current console hold](../AGENTS.md#current-console-hold-2026-10-22) is unchanged;
none of these commands deploys or launches console software.
