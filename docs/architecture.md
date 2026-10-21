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

The current upstream loader requests prefetch for ordinary mapped tensors;
architecture-marked lazy tensors are excluded. Enabling mmap alone is therefore
insufficient for this checkpoint. Before full-model console loading, the runtime
must also exclude routed expert ranges from eager prefetch and measure resident
pages under sustained cache misses. That integration is not implemented yet.

Only the converted model needs to reside on the console SSD. Retain original
checkpoint shards on the host data disk; keeping both complete containers on the
console would exceed the currently observed free space. Storage capacity does
not establish a working RAM budget or a successful model load.

## Driver

Use the owner's PS5-Vulkan-Inference repository and explicit cumulative-idle
profile recorded in the lock file. The archive contains the current H1/H3
compiler and completion changes. It does not advertise native BF16 arithmetic
or matrix hardware. BF16 support in the application must use supported shader
operations or explicit exact widening, rather than enabling an unsupported
device feature. Keep accumulation and numerical validation explicit.

Persistent shader and pipeline caches remain disabled as required by the
current driver integration contract. A successful build or API feature query
does not prove numerical acceptance.

The static engine libraries do not contain a final linked PS5 application.
Selecting the RADV archive during configuration records the intended dependency;
the native application's final link and console admission must verify that same
archive before claiming driver integration.

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
