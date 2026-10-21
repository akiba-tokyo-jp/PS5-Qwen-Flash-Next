# Original-precision streaming architecture

## Fixed objective

Run Qwen3.8-Flash-Next on a single PS5, retaining original BF16 model weights
and exact I64 PLE hash constants. Store the full checkpoint and converted
model on SSD. The host builds, transports, formats requests and inspects
results; the console performs learned inference.

The first execution target is text generation. The model's n-gram lookup is
required and must not be replaced with zeros or omitted. Vision input and
MTP acceleration are distinct later execution modes; retaining their original
checkpoint data does not imply that they have been executed.

## Existing upstream mechanisms

The pinned llama.cpp implements `qwen4exp`: gated delta attention, QSA,
hyper-connections, PLE hashing and lookup, and optional MTP. Its conversion
path supports BF16 output, preserves the I64 hash constants as metadata, and
handles the large PLE table through lazy chunks. Conversion is a layout and
container operation, not model quantization.

The model loader can map selected weights without eagerly faulting all pages.
The scheduler's expert-copy callback and `llama_moe_cache` provide bounded
device expert banks, slot remapping and hit/miss accounting. These are reused
before introducing a separate cache implementation. The large-batch path can
need substantially more temporary memory: start with one-token microbatches
and explicitly sized caches, then increase only after measured admission.

CPU and GPU memory share physical backing on PS5. Moving a weight to a CPU
buffer does not create capacity. Filesystem mappings, resident allocations,
staging, device caches and KV/state must be accounted for together.

The upstream loader requests prefetch for ordinary mapped tensors. The application
patch adds an explicit opt-out, `LLAMA_APP_NO_MMAP_PREFETCH=1`, which the native
entry point sets before backend initialization. A required link symbol prevents
using an older unpatched loader silently. The patch applies and compiles to a
target object on a separate source copy. This removes eager prefetch; it does
not prove a resident-memory bound or console support for the model's very large
virtual mapping. Physical residency under sustained cache misses is unqualified.

The [application expert policy](expert-policy.md) extends that same cache callback.
It keeps the selected IDs, coefficients, original tensor types and upload sources
unchanged. Its UMA admission limit is the minimum of requested cache size, driver
free memory and observed OS free memory after an explicit reserve. This admits
only the expert bank budget; it does not bound all context, page-cache or PLE
allocations. Native memory admission remains a separate qualification milestone.

Only the converted model needs to reside on the console SSD. Retain original
checkpoint shards on the host data disk; keeping both complete containers on the
console would exceed the currently observed free space. Storage capacity does
not establish a working RAM budget or a successful model load.

## Driver

Use the owner's PS5-Vulkan-Inference repository at the revision and explicit
`cumulative-idle` profile recorded in the lock file. The 2026-10-22 integration
is documented in [driver-integration.md](driver-integration.md). The archive
contains the current H1/H3 compiler and completion changes. It does not advertise native BF16 arithmetic
or matrix hardware. BF16 support in the application must use supported shader
operations or explicit exact widening, rather than enabling an unsupported
device feature. Keep accumulation and numerical validation explicit.

Persistent shader and pipeline caches remain disabled as required by the
current driver integration contract. A successful build or API feature query
does not prove numerical acceptance.

Static engine libraries alone do not establish application integration. The
2026-10-22 native build links the actual application and the exact selected RADV
archive into one intermediate PIE, with stable input digests and required
integration symbols. SELF conversion, runtime admission and console validation
remain separate from this host link.

## Milestones and evidence

1. Verify every original shard header, dtype, tensor span, index membership and
   total byte count. Verify full shard SHA256 digests during acquisition.
2. Cross-build the current model implementation and Vulkan backend with pinned
   sources and the owner's driver; record all archive identities.
3. Verify supported BF16 reads/math, mapped-file behavior, bounded memory and
   normal close with a standalone native fixture.
4. Load the complete text model with PLE enabled and emit finite logits and
   tokens on PS5. Record actual CPU/GPU placement and fallback operations.
5. Compare numerical results and tasks, then tune expert-cache size, microbatch,
   read sizes and overlap. Add MTP only with measured acceptance and memory.

Record TTFT, final-answer time, prefill and decode separately. Cold files,
filesystem cache and expert-cache warm state are different conditions. Model
size or theoretical SSD bandwidth alone cannot establish usable speed.
