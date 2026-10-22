# Bounded original-model runtime

This describes application implementation, not a passed full-model console run.
Use the active execution plan for the complete task and physical exit criteria.

## Original data and source I/O

All original experts and required PLE remain in the BF16 containers. Registered
model addresses are source/offset keys for GPU uploads. The application reads
at most 8 MiB into one aligned CPU window and reuses that window only after the
existing synchronous upload or coherent CPU copy positively returns. Eight
read-only direct descriptors are cached by verified file identity. Partial
unmaps retire the matching address ranges before virtual addresses can be reused.

The native provider checks direct I/O on the first file before backend startup.
Unsupported direct reads, changed identities, short reads and failed closes
stop admission without buffered fallback or retry. Direct I/O is a request to
the kernel to minimize caching; this does not claim a hard global page-cache
bound. CPU PLE/input-row gathers remain mapped, and fresh OS reserve checks are
required at completed model boundaries.

## Memory admission

The historical MoE monitor reported 12,280,922,112 total driver bytes and
12,201,230,336 free bytes. These are prior observations, not current admission.
A 12,378,983,936-byte draft estimate exceeded even that reported total and was
rejected during host planning, before any additional console launch.

The current proposed worst-case total is 12,110,548,480 bytes:

| Allocation allowance | Bytes |
| --- | ---: |
| Resident original model weights | 8,755,105,280 |
| Expert cache | 536,870,912 |
| Context/state | 1,073,741,824 |
| Graph workspace | 268,435,456 |
| Transfer staging | 134,217,728 |
| CPU heap and explicitly addressed model pages | 536,870,912 |
| OS reserve | 268,435,456 |
| Direct reserve | 536,870,912 |

For 3 requests of at most 64 prompt and 32 output tokens, 16 PLE rows and one
input embedding row per token address at most 160,432,128 bytes of 16 KiB pages,
counting every row as straddling two pages. Original BF16 row widths are 160
and 2,560 columns, respectively, and are checked in the GGUF metadata. This is
an explicit-access bound, not a bound on kernel readahead. The remaining CPU
allowance limits the observed SDK heap peak; untracked libc fallback rejects
admission. The fixed source window and CPU workspace are included in heap use.

After model load, GPU matrix operations are mandatory. CPU graph workspace
above 16 MiB is rejected before allocation. GGML device buffers share an enforced
1,792 MiB post-load pool for expert cache, context/state and graph workspace;
individual buffers are limited to 512 MiB and conservatively charged in 2 MiB
units. Each allocation additionally needs fresh physical Direct headroom plus
512 MiB reserve before calling Vulkan. A failed/incomplete reservation cannot
be retried. All tracked buffers must be released before the terminal result.
The driver's independently owned BO lifetime and positive completion contract
are unchanged. Internal transfer staging and driver resources retain their
separate allowances; this is not a replacement device allocator.

Every actual launch still requires fresh driver/Direct/OS observations, aligned
tensor limits and positive full-model mapping/integrity. A budget declaration
does not establish actual resident memory or graph compatibility.

## One native session and passive demonstration

The private v2 policy runs one greedy arithmetic smoke request first. It requires
the expected answer and positive completed reset, then destroys that completed
context and creates a new bounded context while retaining the model. This gives
the first identical API benchmark an empty expert cache and the next benchmark
the retained cache. File pages and shader pipelines may already be warm; do not
call this a cold process/storage benchmark or assume the second request is faster.

The external native listener accepts exactly two fixed text requests on port
8086. HTTP threads transport data; all learned model work stays on the admitted
caller thread. The TV and browser have no chat/generation controls. CPU/GPU
identity, calibrated time, TTFT, generated-token count and actual token rates
are observable. Unqualified utilization percentages stay unavailable.

Each request persists its intent, exact token pieces/IDs, timings and terminal
result. A frame is copied from the same CPU raster only after its matching
VideoOut completion, with the request's final token count and metrics. This
proves scanout-source pixels plus reported flip completion, not the TV's optical
output. The independent observer checks the bitmap, served assets, status,
stream events, native journals and reconstructed rates.
The host observer also records POST-to-first-token and complete-response time,
including native queueing and network delay. Its streaming deadline covers
header waiting as well as token reads; a short connection timeout must not
silently become the model's first-token deadline.

The listener stops only after two positive requests, passive observations and
a delivered finish acknowledgement. An exception wakes/closes its pending
transport before joining the listener; it never joins an in-flight model thread
because model execution stays on the caller. GPU failures retain the resource
graph for the established ordinary OS close path. The original title must then
be restored, numerically readmitted, normally closed and fully read back before
the entire execution plan can be considered complete.

## Build provenance

Five isolated application engine objects replace the original mmap, expert
advice, Vulkan buffers, Vulkan backend and CPU backend archive members. The
active pinned upstream/converter sources and original engine archives are not
edited. The final link map must contain all five replacement objects and none
of their original archive members. Hook symbols, object/source/patch hashes,
native imports, SELF roundtrip and existing shader qualification remain required.

The selected driver remains revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. Committed execution,
deployment, release and CI controls stay disabled; only the exact reviewed
private physical case can admit execution.

`prepare_first_case.py` has no console client. After the exact package and
positive complete data transfer exist, it binds them to the preserved original
and generates the private policy through the actual native scope and validator.
The scope emitter passed with a synthetic binding, and the existing independent
153 malformed-field checks passed after extracting the shared scope function.
Fresh CPU/session/clock and ordinary-launch gates remain required afterward.
