# Exact-byte physical file split control

The same original bytes read from distinct files avoid the demonstrated
same-file cross-region slowdown in the completed CPU control. Mean time for
two3,293,184-byte reads was50.687ms in parallel from the original file and
7.058ms in parallel from two physical fragments. Original-file serial time
was9.981ms. All192 pairs passed full SHA256 for both returned byte ranges;
hashing was outside the read interval. The actual application C++ executor,
two-read limit and8MiB source window were retained. See
[the aggregate result](source-split-cpu-20261024.json).

This isolates file placement for identical payloads. It copied only two16MiB
fragments and left the sealed model and original application unchanged. It does
not measure whole512MiB chunks or native inference tokens/s. Separate opens of
the original inode did not fix the earlier slowdown; logical subdivision alone
does not reproduce this physical-file intervention.

512MiB is a candidate layout size. In the32 sampled native read pairs it avoids
cross-chunk joins and satisfies the existing range margins for every pair.
Smaller chunks introduce more files and some boundary joins. The projected file
counts and alternative sizes are recorded in the JSON. A production comparison
must also include descriptor churn under the existing eight-handle limit,
sealed chunk identities and complete original-byte verification. Keep the
original GGUF metadata, all experts and PLE, BF16/F32 precision, memory budgets,
driver and disabled persistent-cache policy.

# Startup memory investigation

The stronger post-probe candidate stopped before Vulkan because free pages did
not recover to its existing startup target after the completed whole rehearsal.
Its normal close, exact restoration/readback and fresh idle CPU checks passed.
The preceding same-boot original numerical admission remains valid.

CPU controls using the unchanged virtual provider did not reproduce the large
native free-page decrease, either sequentially through102.4GB or while holding
all76 original spans concurrently. Root-path metadata checks and journal writes
also did not reproduce it. See
[the memory controls](source-memory-causal-controls-20261024.json). The native
namespace, allocator context and external monitoring remain confounders. The
next explicit CPU-only native diagnostic brackets actual durable stage writes
with bounded memory observations, completes the actual rehearsal and waits for
ordinary OS close before any source worker or Vulkan initialization.
