# Preserve bounded source-row scheduling

The bounded scheduler artifact passed physical model loading, context/cache
construction, CPU/Flexible admission and the producer's positive device-idle
completion. After context construction, the actual Direct CPU heap mapped/peak
was 352,387,072 bytes with zero libc fallbacks; Flexible availability remained
404,750,336 bytes. The unchanged heap limit is 376,438,784 bytes. Native Direct
availability after context/cache construction was 2,472,001,536 bytes.

Tokenization passed. The first prefill entered its first decode call and returned
the post-load single-buffer-scope exception before any decode completion. No
external generation request was sent. The complete, stable driver log still
contained no worker initialization. Ordinary close, exact original restoration,
numerical readmission, normal close, final CPU guards and complete original SELF
readback subsequently passed. No generated token or throughput is claimed.

The combined buffer exception did not retain requested/pending bytes. New messages
distinguish an incomplete reservation from zero/oversized requests and include
the requested size, limit/pending amount and live accounting. All capacity and
reserve limits are unchanged.

Source inspection and the pinned conversion plan expose a concrete incompatible
selection path. `token_embd.weight` is a 1,271,398,400-byte original BF16 tensor
with `mapped_embeddings` placement. Its protected source key is not a resident
host table. GGML's ordinary automatic offload can select GPU GET_ROWS and create
a copy of the entire table, exceeding the 512 MiB post-load single-buffer limit.
The context's mixed-input reservation also differs from a real token-only input.
The previous exception did not numerically prove which request reached the guard;
keep that limit explicit instead of presenting a source inference as a recorded
request size.

The scheduler now recognizes GET_ROWS from an owned protected model source and
requires the admitted CPU row kernel/buffer. That existing kernel reads only
addressed original rows through the aligned 8 MiB Direct source window. It never
dereferences the protected source key or transfers the complete embedding table.
Resident-host offload and matrix placement remain unchanged; matrix work stays
on the GPU. Unsupported CPU kernels or incompatible preallocated output storage
are rejected.

The actual patched scheduler was tested with a simulated offloading device and
the full 1.27 GB tensor shape, with no payload allocation/read. Its ordinary
resident-host control selected the offloading device; the protected-source case
selected CPU. Three complete 7,184-node synthetic CPU graphs and all 48 output
values still passed. The device/workspace ledger and native provider compiled
and passed their existing bounded-source/failure tests. Only one scheduler
object was rebuilt; six unchanged source overlays and the pinned driver archive
were reused. These host results do not establish physical model generation.

The next distinct physical artifact retains all complete-plan generation,
external-request, actual native-frame review, positive retirement, ordinary-close
and final original restoration/readmission gates.
