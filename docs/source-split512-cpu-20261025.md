# Representative 512 MiB physical-file comparison

One finite CPU-only PS5 comparison used the application's actual C++ executor,
the same 8 MiB Direct window, two outstanding reads and three source descriptors.
All 192 pairs passed SHA256 of every returned byte. Hashing was outside the read
interval. Both fresh idle CPU/service guards and positive worker/Direct retirement
passed. The original model directory and original executable were not modified;
no title, model or GPU ran. See [allowlisted results](source-split512-cpu-20261025.json).

| Mode | Mean pair time |
| --- | --- |
| Original file, serial | 9.9635 ms |
| Original file, parallel across the problematic region | 48.5788 ms |
| Separate 512 MiB files, serial | 8.8736 ms |
| Separate 512 MiB files, parallel | 6.9222 ms |

Split parallel reads are 1.439x as fast as the safe original serial path in this
control. Production already excludes the slow cross-region parallel path, so
the 48.58 ms result is not the appropriate native improvement baseline.
The current four-token candidate serializes about 12.06% / 12.33% of its pair
batches. Those counts are not time or byte fractions. No full-layout native
inference speedup was measured.

Only two representative files, 512 MiB each, were uploaded and completely streamed
back with exact SHA256, using at most 64 KiB for readback and 1 MiB for upload.
They represent original offsets 512 / 1024 MiB. The timed relative offsets are
504 / 8 MiB, matching the original 1016 / 1032 MiB ranges. Each read is 3,293,184
bytes with a 16,384-byte pair stride and 16 pairs per mode in each of three rounds.
No complete model copy or reconversion was performed.

A fresh completed filesystem-capacity observation gave a conservative free-space
lower bound of 126,400,000,000 bytes. A complete second layout while retaining
the sealed original and the unchanged 32 GiB storage reserve needs at least
393,606,790,108 bytes. The existing storage admission function rejects it.
Full-model splitting is therefore not admitted on the current storage. This is
a capacity constraint, not evidence that physical splitting has no effect.
No original files were deleted or overwritten to manufacture capacity. A bounded
selective mirror would need its own mapping/integrity/cost qualification.
