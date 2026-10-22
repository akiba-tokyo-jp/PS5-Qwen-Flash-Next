# Original BF16 indexed expert diagnostic

`moe-validation` implements one bounded `GGML_OP_MUL_MAT_ID` graph with
512 original BF16 expert matrices, 2,560 columns, 16 diagnostic gate rows per
expert, one F32 input vector and ten I32 expert IDs. The output has 160 F32
values. The fixed ID order is `511, 0, 256, 17, 383, 1, 510, 127, 255, 42`.
This tests indexing, ID scatter order and input broadcasting across selected
experts. The diagnostic rows do not replace full-width model weights or qualify
expert pruning, complete routing, layer execution or inference throughput.

The 41,943,040-byte fixture preserves BF16 bytes from every expert in
`model.language_model.layers.0.mlp.experts.gate_up_proj`, original shape
`[512,1280,2560]`. The pinned checkpoint revision is
`de4b8e4d43b917e7706784d8bb445c9af86a3540`. Source shard
`model-00002-of-00131.safetensors` is 3,355,443,368 bytes with SHA256
`1da92de7cf72dcca86faf05007925389ceb24427609e8d3b478d53d97fd97a63`.
Each expert contributes its first 16 rows, starting at source offset 168 with
an expert stride of 6,553,600 bytes. One complete streaming source hash and
stable source identity precede the final fixture receipt. Fixture SHA256 is
`48ae4c3c1a34904384ad7349c2151dc551cad4ca3b3302e8ce73d1f90b4b39c8`.
Weights and private source receipts stay outside Git.

The app verifies the complete fixture hash and all BF16 values before native
GPU initialization. It calculates scalar double references on the PS5 before
creating the compute backend. Device support must pass before device allocation.
Five sequential 8 MiB weight uploads precede the vector and exact ID uploads.
One graph compute and synchronization precede the complete readback. Every
value must be finite and meet `abs(error) <= 1e-5 + 1e-5 * abs(reference)`;
aggregate NRMSE must not exceed 0.01. The measured diagnostic interval includes
CPU references, setup, transfers and readback; it is not GPU kernel time or
tokens/s. Failed or uncertain results retain their resource graph. Successful
numerical checks still require the native owner's positive device idle and
matching completion epoch before driver retirement.

The pinned llama.cpp revision is
`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`. Its BF16 `MUL_MAT_ID` path uses
expert-count/scatter and indexed matrix shaders even for one token: its
single-token vector selector excludes BF16. F32 diagnostic activations are exact
half-integer values and remain exact when its BF16 matrix path copies them to
BF16. No learned weight quantization is introduced. The app uses this existing
implementation without editing the upstream tree during active conversion.
`tools/check_moe_shaders.py` verifies actual linked indexed-matrix, expert-count
and activation-copy modules with `spirv-val --target-env vulkan1.3`, and rejects
native BF16, cooperative-matrix and integer-dot capability requirements.

Use the selected driver revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, native
archive SHA256 `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`,
with persistent caches disabled. The private policy binds the preceding
successful operator SELF, source/fixture digests, exact expert/ID counts, fixed
ID order, one graph and the upload bound. Native display and model loading are
disabled. Require at least 1 GiB largest available Direct range and 192 MiB
remaining Flexible capacity before compute. Host API refusal checks and PS5
object compilation are prerequisites; they do not establish physical success.

Before a distinct physical case, complete its native link, actual import,
six callback-table, SELF roundtrip and shader gates. The existing data-only
continuation must be positively stopped while still waiting with no console
access, preserving its immutable evidence, before changing its pinned reservation
or console context. Full-model conversion continues unchanged. Require a fresh
same-boot idle CPU observation, exact original preservation and one ordinary
title launch. Capture every numerical/completion result, normally close the
candidate, restore the exact original, repeat its numerical admission, normally
close it and verify final CPU metadata and complete SELF readback. A fresh
data-only continuation can then bind that new completed context. No automatic
retry follows uncertain execution or transfer.

Full-model receipt, disk transfer, native SHA/mapping, resident-memory admission,
all remaining operations, generation and quality gates remain separate.
Committed console, deployment, release and CI controls remain disabled.
