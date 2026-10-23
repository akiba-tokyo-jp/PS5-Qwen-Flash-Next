# Reserved virtual sources and bounded original-byte CPU reads

The file-backed model mapping attempt remains unqualified. The console is held
at the uncertain ordinary-close boundary described in
[the physical record](public-mapping-hold-20261024.md). The following results are
host implementation and synthetic CPU checks, not completed PS5 inference.

## Runtime change

The native model path no longer uses file-backed mmap. It reserves inaccessible
virtual ranges with `sceKernelReserveVirtualRange`, checks their complete
no-access protection and uses their addresses only as file/offset keys. A
16 KiB reserve/query/completed-release probe precedes full source admission.
No payload is read through these pointers. The new kernel API remains physically
unqualified; the small probe cannot run until the console hold is resolved.

The original 8 MiB aligned direct-read window and eight-handle cache now serve
CPU embedding/PLE row gathers and CPU buffer copies as well as GPU/expert
uploads. BF16 conversion uses the original GGML conversion routine; F32 rows
copy their original bytes. All experts and required F32 PLE parts remain intact.
CPU row reads are limited to 1 MiB each. Only graph task zero uses the producer's
window; other workers inspect immutable range metadata. CPU operations that
could dereference a reserved source outside the supported gather/metadata path
are rejected. Writes and clears of reserved source storage are rejected.

The generic CPU-to-CPU fast copy uses `set_tensor`, bypassing the destination's
`cpy_tensor` callback. A protected-memory host fixture exposed that path before
any PS5 execution of the new implementation. Both input and output CPU buffer
routes now use bounded I/O where required. Five unchanged native source objects
were retained; only the two affected CPU objects were recompiled for that fix.
The superseded host-only SELF was never deployed.

The v3 first-generation policy requires reserved virtual sources, forbids
file-backed model mmap and requires the bounded CPU row path. Native result
reconstruction requires the new virtual-source admission schema and explicit
zero file-mmap/no CPU source-dereference records. The independent observer
rejects the old public-mmap stage and bounds virtual-source admission to 65
seconds even when the process remains alive. This detects an opaque-call stall;
it does not cancel a kernel call or establish ordinary-close completion.

The original driver revision/profile/archive, disabled persistent caches,
12,110,548,480-byte conservative model budget, request limits, arithmetic smoke,
external requests, passive TV/web monitor and GPU completion/retirement gates
remain unchanged. Exact original restoration/readmission is still required.

## Host evidence

| Check | Measured result |
| --- | --- |
| Virtual source policy | Exact rounded spans, no-access protection, failed-reservation retention and one-attempt release passed with API stubs |
| Source reader | Exact bytes, 8 MiB windows, eight handles, graph-worker metadata lookup, retirement and failure quarantine passed |
| Real CPU reference comparison | 245,952 scalar outputs exact for BF16/F32 widths 8, 2,560 and 7,680 |
| Real CPU execution | Six three-thread GGML graphs and twelve buffer get/copy checks passed |
| Inaccessible source proof | Windows source pages were reserved with no committed backing; row/copy code had to use the bounded reader |
| Combined reference output | 2,705,472 identical bytes; SHA256 `4073327af1bb61e160d6815e0a2cc041db5ab4be80f15904d3d2a3e12ddc30c3` |
| Unsupported CPU source operation | Actual backend capability query rejected the unsafe copy operation |
| First-generation scope | Limits, persistence, single-attempt behavior, timing/startup and 165 malformed policy fields passed |
| Independent virtual-source deadline | Four clock/phase fault tests passed |
| Result reconstruction | Seven focused tests passed, including forbidden mmap, protection and CPU-pointer records |

These fixtures execute CPU kernels on synthetic data only. They read no model
payload, run no learned host model, contact no console and establish no GPU
quality or token rate. The seven native source overlays compile against the
unchanged engine archives. The actual native link and callback audit passed.
The 58,628,503-byte SELF has SHA256
`5c2ac4c3b9045eda2ae74e67abb262b7e757a91311e3bae024388b0574d62d13`.
All six segments roundtrip and all 291 real-module imports resolve, including
the reserve/query/release APIs from `libkernel.sprx`.

The unchanged engine shaders retain their existing qualification; this I/O
change does not modify shader source, model precision or driver mechanisms.
Committed execution/deployment/release and CI controls remain disabled.

## Remaining physical work

Preserve the uncertain close and current native owner; do not retry the close or
file-backed mapping. Only a new admitted read-only/CPU reassessment can resolve
that boundary. Recover exact original restoration and numerical admission before
qualifying another native implementation after the unstable mapping attempt.
Then the distinct candidate must pass its tiny virtual-reservation probe, all
original-file and fresh memory gates, full load and generation, two external
requests, actual frame review, positive retirement, ordinary close and final
exact original restoration/readmission/shutdown. No part of this host record
marks those remaining physical requirements complete.
