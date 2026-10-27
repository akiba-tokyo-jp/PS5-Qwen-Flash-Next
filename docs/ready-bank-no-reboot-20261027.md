# Independent ready banks without a reboot dependency

The owner made reboot unavailable as a standing constraint. This applies to
the remaining plan, not just the current evening. The implementation below is
saved work toward ready-expert execution. **Actual split backing, physical
source/GPU overlap and full-model speed remain unqualified.** Production is
unchanged and inactive; no new title or GPU work ran in this continuation.

## Implemented ownership and execution pieces

| Source | Concrete behavior | Validation |
| --- | --- | --- |
| `native/app/split_bank_allocation.cpp`, `SplitBankAllocation::prepare` | Plan both allocations with the pinned GGML allocator before either allocation; put three consecutive BF16 byte roots in each of two real buffers | 14 actual-owner/planner harness scenarios and PS5 SDK compilation, check 3001 |
| `split_bank_allocation.h`, `validate_split_bank_backings` | Require device-local/host-visible/coherent mapped roots, contiguous roles within each group, disjoint CPU spans and distinct actual VkDeviceMemory between groups | Aliased owners, overlapping spans, changed producer, missing coherency, bad alignment, allocation failure and unknown use all refuse |
| `native/app/ready_expert_graph.h`, `build_serial_ready_expert_graph` | Expand both groups and the original ten-contribution left-fold reduction into one serial control graph | 20 partial graphs, nine serial controls, 174 refusals and 2,560 cancellation-sensitive F32 reduction values; check 3003 |
| `native/app/ready_source_coordinator.h` | Move source coordination off the sole GPU producer; retain the existing inner two-call I/O controller while the GPU producer runs wave zero | 19 concurrent scheduler/exception/deadline controls and native SDK compilation, check 3013 |
| `native/app/split_bank_admission.cpp`, `admit_split_bank_backing` | A separately linked, default-off native backing/numerical fixture using six original BF16 matrices in the existing pack | Exact-source comparison and 57 scope refusals, check 3010; actual GPU execution not run |
| `tools/split_bank_result.py` | Independent finite-count, identity, numerical, canary and retirement review | Seven fault-injection test groups; a passing report still requires independent ordinary close/restoration review |

Six independently rounded buffers would charge 516 MiB. Three roles per actual
group charge 256 MiB twice, preserving the selected 512 MiB cache allowance.
The actual payload is 533,495,808 bytes. Distinct tensor roots alone are never
accepted as proof of distinct memory. Six nested strong borrower callbacks
retain all roots throughout synchronous use. Failure/unknown completion retains
the allocation graph; there is no CPU fallback, retry or implicit buffer free.

The coordinator admits its second source group only after acquiring group
zero's ready-wave lease on the original GPU producer. This avoids losing I/O
depth two when that producer enters a GPU call. Host tests exercise the actual
`VectoredSourceBatch` and `ReadyExpertWave` with metadata-only read callbacks:
30 callbacks, peak depth two, and 15 callbacks during the first GPU lease in
the overlap control, versus zero in the serial control. They read no weights,
dereference no fake address and execute no GPU arithmetic. Early release,
wrong active wave, both deadline paths and late returned work cannot qualify
successful retirement.

## Native fixture and unchanged driver

The fixture reuses original vector-bank pack zero (63,488,000 bytes, SHA256
`4d6247378c577a586d8cc552b14c771f63a732f8b9762ead8405612aea2d371d`).
Its six matrix/envelope hashes were independently compared with the qualified
original pack plan. No new model conversion or weight corpus is required.

It intends six direct reads into the actual roots, then twelve indexed BF16/F32
GPU graphs: two repeats for each original gate/up/down matrix, across global
slots 0 and 52. F32 inputs include values not exactly representable as BF16.
Each output must pass an F64 reference with absolute/relative tolerances 1e-5
and match its repeated F32 result in bits. Normalized errors must be finite and
at most one. Canaries stay within actual root boundaries; the last slot instead
also requires the entire original envelope to remain unchanged after GPU work.
This fixture qualifies neither a complete MoE graph nor source/GPU overlap.

Build 3011/package 3012 passed actual module imports, native dispatch and SELF
integrity plus all six segment comparisons. The final candidate is 23,086,730
bytes, SHA256
`7ef8ab1a3d5d14f7823a11058d7881645bd347156fdff02ca7eb6e79a319b4b2`.
The model/service entry points are absent. Against the 28,358,119-byte full
diagnostic SELF 2831, the file is about 5.03 MiB smaller. **This is a file-size
measurement, not a measured kernel-memory reduction.** The new startup cost
has not been established by console execution.

The application relinks the unchanged preferred driver revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, archive
SHA256 `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent caches remain disabled. Original startup target 2,974 pages,
operational observation, Direct/Flexible checks and device/CPU budgets remain
in force. GPU-started failure reporting now begins at the actual GPU boundary;
a returned CPU-source refusal is not mislabeled as GPU initialization.

## Read-only allocator attribution

Case 3009 used the already running shell for fixed, bounded read-only sysctl
queries. The complete boot identity matched before and after. Free memory was
6,927 -> 6,927 pages; wired memory was 30,279 -> 30,279. No ELF, title, GPU,
setter, pressure allocation, cache advice or recovery operation was issued.

`vm.zone`, `vm.uma_zones` and `kern.ipc.nmbclusters` each returned
`sysctl: No such file or directory`. This establishes unavailable nodes through
the current interface, not an exhaustive PS5 kernel capability limit. These
queries do not identify a network buffer or other proprietary owner. Do not
repeat them unchanged or claim memory recovery. Four parser/scope test groups
passed. Earlier metadata/reservation/quiet-start results remain preserved.

## Remaining work and next evidence

1. Finish the native two-wave source/graph runner using these owners and the
   existing paired reader. The coordinator is implemented and SDK-compiled;
   it is not yet connected to a physical source/GPU comparison.
2. Price the changed small-title CPU phase from an explicitly scoped native
   admission. Do not transfer an old SELF's phase price as a hardware minimum,
   lower guards solely to force a launch, or depend on reboot. The current
   snapshot is not launch admission. Preserve normal close and exact rollback.
3. Qualify actual independent backing and all twelve numerical graphs before
   a physical overlap comparison. Reuse current-boot shader proof and existing
   pack/source identities; avoid a new full-model preparation for this gate.
4. Compare one-graph serial, split serial and split overlap with identical
   source bytes, original-order reduction and durable per-batch plans. Include
   added submissions/worker overhead and prove actual I/O/GPU interval overlap.
5. Integrate only a fixture winner into the model, then require same-model
   A/B and B/A, exact continuation, TTFT/decode and production-placement checks.

No new generation tokens/s result or adopted acceleration follows from this
continuation. The wider cache, exact speculation, PLE, prefix, router and other
work packages remain individually tracked in the plan index. CI stayed disabled.
