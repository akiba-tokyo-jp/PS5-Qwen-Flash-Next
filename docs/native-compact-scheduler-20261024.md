# Completed native decode and compact scheduler arena

The one-output prefill artifact completed its first physical input-token decode.
The decode call returned, synchronization completed, positive device idle passed
and the matching worker checkpoint retired completed resources at epoch 2058.
The following CPU guard rejected mapped/peak 385,941,504 bytes against the unchanged
376,438,784-byte heap limit, with zero libc fallbacks. This is a completed input
decode, not completed prefill, a sampled output token, or a tokens/s result.

Both private logs were complete and stable from offset zero. The final native
stages prove that the heap refusal followed positive completion and retirement;
the driver log records successful completed-epoch unmap/release operations. The
owner was ordinarily closed, the exact original SELF restored and numerically
readmitted, normally closed, then checked by final CPU guards and a complete
original SELF readback. No force-kill, reset or manual GPU release was used.

The scheduler scratch arena is reduced from 192 MiB to 160 MiB, superseding the
earlier initial arena size. The unchanged CPU heap limit, Direct/Flexible/kernel
reserves, graph/hash capacity, node count and source-copy rejection remain in
force. This removes 33,554,432 actual scratch bytes instead of increasing the
heap allowance. The real GGML allocator still uses exactly 158,936,784 bytes for
the conservative 7,184-node metadata bound within the 167,772,160-byte arena.
An oversized complete graph remains rejected before scheduler copies.

The actual scheduler executed three complete 7,184-node synthetic CPU graphs;
all 48 values were exact. Protected-row selection, ordinary offload control and
uncached protected-source rejection still passed. Only one scheduler object
changed; six native overlays, application objects and the pinned driver archive
were reused. Native link, actual module imports and all six SELF segments passed.

The next complete physical case must still finish prefill, sampled generation,
two external requests, actual native-frame review, positive resource retirement,
ordinary close and the full original restoration/readmission sequence. No complete
model-generation or throughput claim is made at this checkpoint.
