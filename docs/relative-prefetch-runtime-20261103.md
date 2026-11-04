# Relative model-prefetch runtime

The new C++ predictor65045 reproduces the completed independent screen64827
on all4336 original PS5 calls:3449 eligible, six original producers, nine
predictions, two hits, seven unused,12943360 predicted bytes and2162688 matched
bytes. Its two512-entry LRU tables and64 full-identity histories use only
completed reads. Eight new native geometry refusals pass. Earlier Python
predictor tests and PS5 inference are not replayed.

The largest of those predictions is1540096 bytes. The new runtime therefore
owns one aligned2MiB CPU Direct scratch lease, one pending span and at most one
lazy persistent worker. It forwards the original producers concurrently and
shares their observed four-read limit with speculation. A new worker starts
only with spare capacity. This bound does not promise that the optimistic nine
per-producer predictions will all be submitted or hit in the actual shared
runtime. The reference trace is one prompt; broader coverage remains unknown.

Both original pread and close are wrapped. The original fd is kept until its
same pending speculative read positively returns; no duplicate or reopened
source fd is added. Actual before/after12-field descriptor identity, flags,
returned byte count and the original destination are checked before a cache
hit. A short or invalid speculative result falls back to the one original
demand call. Unknown completion retains the state, fd and actual scratch lease.

Concurrent controls65047 cover hits, short reads, identity changes, admission
decline, close waiting, the original four-read concurrency, request misuse and
retention after an opaque worker exception. Changed65048 adds a fresh read-only
worker admission immediately before speculative I/O: nine controls pass. Neither
the worker nor original source producers mutate the frontend admission/wait
state. The runtime uses fresh memory/heap observations and declines speculation
when the original reserve or actual CPU budget is unavailable. Actual worker
I/O calls, returned calls/bytes, completed jobs, hits, unused work and final
drain/retirement time are recorded separately.

The source provider65054 compiles for the actual PS5 ABI, with64-bit pread
offsets, both ownership wrappers and zero additional global C++ initializers.
It is not yet bound to the complete model entry. Actual whole-link source-fd
ownership, native numerical output, source contention and decode tok/s remain
unqualified. No production change or model-speed improvement follows from
these host controls. Complete-model measurements must retain the original
decode formula and separately include final speculative cleanup in the
additional complete-request observations.
