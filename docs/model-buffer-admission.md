# Resident buffer planning before model loading

The pinned engine's `ggml_backend_vk_buffer_type_get_max_size` returns its
suballocation batching target. The default is 1 GiB. This is not a hard tensor
limit: the real GGML planner emits a standalone larger buffer when one tensor
exceeds that target. The original output tensor is 1,271,398,400 bytes, so the
client's earlier conservative comparison would reject it with default settings.
No physical full-model load was attempted under that comparison.

The future model-loading path now requests a 2 GiB batching target using
`GGML_VK_SUBALLOCATION_BLOCK_SIZE`. Upstream reduces this request to its queried
hard allocation/buffer limit. The client never sets the force-max allocation or
buffer overrides. It requires fresh positive alignment, a bounded power-of-two
alignment, and the aligned largest tensor to fit the reduced target. Under that
condition the actual planner cannot create an oversized group. Memory reporting
records the observed batching limit and alignment separately from resident bytes.

`tools/check_model_buffer_plan.py` checks the exact pinned source ZIP and the
byte-identical `ggml-backend.cpp`, then compiles its actual planning function with
storage-free API inputs. Thirteen cases cover the default oversized-tensor
behavior and every planned resident tensor under four insertion orders and three
alignments. All 1,078 resident tensors, totaling 8,755,105,280 bytes, fit the
requested target in these checks. They establish size/accounting invariants,
not the loader's exact runtime insertion order, buffer count or physical capacity.
The tool leaves the source tree and active model converter unchanged.

The complete 1,256-tensor native footprint replay also passed after adding
alignment guards, including rejection of unknown/invalid alignment and aligned
size overflow beyond the admitted limit. Its planned 11,976,330,752-byte total
remains a budget. Actual allocation overhead, available Direct/OS memory and
post-load headroom still require fresh physical admission.

The revised entry point compiled for `x86_64-sie-ps5` using the previous qualified
recipe. Its only additional undefined symbol is the existing static GGML API
`ggml_backend_buft_get_alignment`. This object has not been linked into a new
application, packaged or executed on the console. Full-model execution remains
independently rejected; this change does not replace model integrity/mapping,
resident load, context, quality or throughput qualification.
