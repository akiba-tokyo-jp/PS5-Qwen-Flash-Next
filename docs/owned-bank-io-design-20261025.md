# Owned mapped-bank source I/O candidate

Status: implemented, physically qualified and selected in the
[adopted profile](../config/qualified-performance.json). The small mapping gate,
360 padded-layout GPU graphs and complete same-SELF full-model comparison all
passed, including original restoration and fresh numerical readmission. Mean
decode improved 12.1829%; see [results](gpu-optimization-results-20261025.md).
The design and ordered gates below explain the implemented constraints. A small
mapping probe or arithmetic layout screen alone never admits whole inference.
No model repack or precision change was required.

The completed 21-step decode observation attributed 84.12% of process time to
source wait and approximately 9.6% to the upload consumer. All observed uploads
already used mapped coherent memory; staging traffic was zero. Removing the
consumer's entire interval would give about 1.106x in a simplified unchanged-I/O
model, before added I/O, synchronization or lost coalescing. Overlapped accumulated
timings do not establish an unconditional ceiling or a measured gain.

## Layout and source changes

Each original expert matrix contains 3,276,800 BF16 bytes. With a 16,384-byte
Direct-read alignment, use a conservative 3,293,184-byte slot stride. Each
layer/role's cached tensor view starts at its own original source-offset residue.
The 512 MiB split preserves those residues. Source offset, aligned read envelope
and destination-slot bounds must be checked independently, including a physical
split crossing. Never infer alignment from an allocation's nominal type.

Three banks including 54 slots consume at most 533,495,808 bytes under the
536,870,912-byte cache budget. This does not prove actual allocation admission.
In particular, `ggml_nbytes` excludes trailing padding of the last tensor plane;
the source lease must check the actual allocated buffer bounds, not just this
conservative arithmetic. Policy-visible active slots must remain 53.

| Source | Functions / responsibilities |
| --- | --- |
| `patches/native-model-io/0002-llama-moe-cache.patch` -> `src/llama-moe-cache.cpp` | Change `alloc_size`, bank construction, per-layer `ggml_view_3d` offsets, `copy` and `copy_experts` together. Keep slot protection/LFU policy. Every fill/hit/fallback must use the padded stride and the correct layer view. |
| `patches/native-model-io/0004-ggml-vulkan.patch` -> `ggml-vulkan.cpp` | Add a narrow bank-lease export beside `ggml_backend_vk_buffer_set_tensor`; inspect real owned `dev_buffer`, memory flags, mapping, offset and complete range. Verify `ggml_vk_mul_mat_id_q_f16` batch stride, descriptor alignment and actual shader indexing. |
| `patches/native-model-io/0003-ggml-vulkan-buffers.patch` -> `ggml-vulkan-buffers.cpp` | Preserve allocation ownership and completion. Count successful direct-bank bytes separately from `ggml_vk_buffer_write` mapped memcpy and staging bytes. No imported host pointers. |
| `native/app/mapped_source_bridge.h`, `mapped_source.cpp` | Define a typed, bounded lease and a source-I/O completion handshake; arbitrary destination pointers are insufficient authority. |
| `native/app/mapped_source.h` -> `MappedSourceReader::upload_pair` and native `SourceReadOps` | Keep source identity/descriptor leases, owner thread, existing worker limit, original headroom checks and unknown-completion retention. Add an aligned bank-target route only after both source and destination plans pass. |
| `native/app/moe_admission.cpp` | Add original-shape padded/offset indexed numerical fixtures and a separately bounded known-file Direct-read/coherence fixture before any full model use. |

The existing fill loop merges consecutive source experts and consecutive slots.
After padding, adjacent payloads are no longer adjacent destination bytes.
Passing `n * expert_size` to the old upload would corrupt later slots. Preserve
coalesced source reads through an explicit per-slot scatter fallback, and screen
whether direct-bank I/O loses enough coalescing to outweigh the saved copy.
Likewise, `copy_experts` must handle noncontiguous multi-expert views explicitly;
the Vulkan host-visible noncontiguous asynchronous write path currently aborts.

The current decode-vector predicate requires contiguous plane strides. Keep it
OFF for the padded variant until a separate layout/shader qualification admits
that combination. Verify descriptor alignment against real device limits;
generic misalignment helpers do not establish that the indexed matmul path
supports every source residue.

## Ordered admission

1. Validate every actual layer/role, source residue, slot and read envelope on
   the host. Exercise split boundaries, last active/spare slot, padding, overflow,
   descriptor alignment, fallback scatter and CPU/cache budget refusals.
2. Build/audit/package a distinct fixture artifact with unchanged pinned driver,
   exact source provenance and persistent caches OFF. First prove bounded CPU
   Direct reads into the specific owned mapping. A valid Vulkan host mapping is
   not proof that a filesystem Direct read may target it.
3. Prove payload plus padding sentinels and GPU results for both original matrix
   shapes, repeated/boundary expert IDs, nonzero residues and padded strides.
   Do not reuse/free an uncertain I/O or GPU lease or retry its operation.
4. Only then compare a full same-model sequence with unchanged context, prompt,
   output, cache, source-worker and memory budgets. Measure actual direct-bank,
   fallback/scatter, source-wait, physical-byte and copy counts separately.
5. Require both displayed frames, source/GPU retirement, ordinary close, exact
   original restoration/readmission/shutdown and final idle/full executable
   verification. Adopt only a completed, beneficial comparison; otherwise leave
   the candidate disabled with its measured disposition.

## Cheap first implementation gate

Screen filesystem I/O into an owned mapped allocation before implementing the
large cache-layout change. Add a narrow lease export beside
`ggml_backend_vk_buffer_set_tensor` for a fixture-owned buffer allocated through
the same device-local/host-visible/coherent policy as the real cache. Validate
the actual mapping, memory flags, allocation/tensor bounds, alignment, owner and
lease generation. Use offsets in the source planner; arbitrary host pointers
must never become destination authority. An opaque lease stays owned until the
read and every later GPU use have positively completed.

Use a single small known-file Direct read into that mapping without submitting
compute during the read. Confirm exact returned bytes and a known digest, then
qualify CPU/GPU coherence separately. A known incompatible mapping can reject
this candidate before the padded bank implementation or another model launch.
A small compatible mapping alone does not qualify the complete cache.

The host metadata screen covered all 144 trunk matrices, 73,728 experts and 53
active slots. It found 432 aligned read envelopes crossing a 512 MiB physical
part boundary. The three retained optional MTP expert tensors were inventoried
separately; their files and the existing `load_mtp=false` setting were untouched.
This screen establishes arithmetic fit, not I/O eligibility or performance.

The native source planner must also handle a final non-page-aligned EOF. A
Direct request may have an aligned capacity greater than its expected returned
EOF bytes. Require the exact qualified EOF count, the entire payload inside
that count, stable source identity and the full requested destination capacity
inside the lease. Do not reject a valid EOF as an arbitrary short read, pad or
rewrite model files, retry an unknown call, or treat unwritten padding as payload.
