# Preserving completed conversion splits

The original host writer has a fixed six-hour controller deadline. Its observed
throughput projects slightly beyond that deadline. The running sources, deadline
and outputs are unchanged. A controller timeout is a failed attempt, never a
completed model receipt. On Windows the virtual-environment redirector and actual
writer are distinct processes: the actual writer may outlive its controller.
Require positive absence of every recorded process before any new writer.

`resume_conversion.py checkpoint` records the original completed 131-file SHA256
journal, frozen preparation sources, active process identities, pinned metadata
hashes and original file identities. Every source modification time must precede
the original verification phase. This reuses the recorded original SHA pass;
it does not claim another payload hash pass. The subsequent attempt holds
nonblocking preparation/download writer locks and Windows read-only source
handles that prohibit writes/deletion. Changed identity or metadata rejects it.

Only the specific positively failed timeout and terminated data continuation
may be resumed. New output and evidence directories are required. No previous
file is overwritten or removed. The unchanged pinned GGUF writer generates
bounded headers. A previous split with the exact final size and identical header
may be hard-linked into the new output; partial/missing/different splits are
written anew using the existing 8 MiB source-copy adapter. Each tensor belongs
to one complete retained/new partition. If an orphaned original writer finishes
all splits, all splits may be retained and no new copy reads are claimed.

Structural retention does not admit payload fidelity. The existing independent
audit still compares every expert, embedding and PLE byte with the original
sources, replays every dense transformation, validates all shapes/types and
64-bit constants, and hashes every final split. The explicit resumed adapter
schema records retained/new counts and bytes, sources and checkpoint evidence;
it never claims that retained tensors were freshly streamed. Partial failures
close host file handles and preserve evidence. There are no automatic retries.

The separate attempt declares a four-hour writer bound, a 24-hour complete
payload-audit bound and a 12-hour final-hash bound in its immutable intent.
These do not extend the old job. Console access and learned host inference
are absent. Transfer planning must explicitly accept the reviewed resumed
provenance after the old data continuation ends; old admission is unchanged.

Five synthetic writer tests passed, including incomplete writes and journal
failure. The actual pinned GGUF writer also reproduced byte-identical tiny
synthetic splits while retaining two complete files and regenerating one
partial file. Five provenance tests reject incomplete partitions, changed
records, source drift and invalid bounds, including the fully retained case.
These host checks are separate from original model auditing and PS5 execution.
