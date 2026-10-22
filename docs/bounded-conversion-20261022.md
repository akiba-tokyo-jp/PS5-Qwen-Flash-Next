# Bounded original-BF16 conversion copies

The pinned converter normally widens a fused expert projection to F32 before
splitting its gate/up outputs. Those temporaries can require several GiB even
though the final BF16 bytes are unchanged. Its PLE implementation already streams
original shards. The application now bounds all raw-copy outputs to smaller
row-aligned chunks, including experts, embeddings and PLE.

`tools/bounded_conversion.py` keeps all 237 upstream Python sources unchanged.
It calls the actual pinned Qwen `modify_tensors` method, preserving its metadata,
shape decisions and bookkeeping. For the 150 independently planned raw-copy
outputs, it substitutes the same upstream `LazyChunkedTensor` interface using
at most 8 MiB of original BF16 input per read. BF16 values widen exactly to F32
inside each chunk, and the unchanged upstream BF16 formatter/GGUF writer writes
them. The other 1,106 dense outputs retain the pinned transformations. No reduced
precision format, expert removal, PLE omission or learned forward pass is added.
The actual CLI factory is checked to select that exact Qwen text class.

The adapter must stream all 351,568,363,520 planned BF16-copy bytes once in order.
Out-of-order/repeated reads and truncation are rejected. Only one read-only input
descriptor per output is active at a time. Output shapes must match the original
plan. The source tree and adapter identity are checked again after writing.

The parent conversion command still verifies all original shard hashes first.
It requires the complete adapter record, then independently rechecks the entire
converted tensor set, original copy bytes, every dense transformation and final
GGUF file hashes. It records six application preparation-source digests and
rejects source changes before publishing the v2 receipt. Partial output and
explicit failure status are retained; an adapter record alone is not a model
receipt. Freeze those six preparation files once conversion begins.

Manual checks compared all 1,256 metadata outputs before/after the adapter with
zero learned payload reads. All 150 copy outputs were present. A real pinned
GGUF writer/reader fixture matched interleaved expert slices, embeddings and PLE
bytes exactly. A larger synthetic BF16 payload crossed the 8 MiB boundary and
matched byte-for-byte; truncation and repeat attempts were rejected. The actual
CLI selected the expected class. The Python suite passed 49 cases, including
failed adapter proof, conversion timeout and post-conversion audit failure.

These are format and bounded-I/O checks. Full checkpoint acquisition, conversion
and payload verification are not established by them, and no PS5 model inference
or tokens/s is claimed.
