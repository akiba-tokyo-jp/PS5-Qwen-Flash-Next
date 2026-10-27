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

The later [connected dispatch and finite-disposition record](finite-execution-dispositions-20261027.md)
supersedes the host-runner pending statement above: the execution owner and real
GGML workspace/dispatch adapter now pass 40 host controls and native SDK
compilation. The complete physical fixture entry, backing/numerical acceptance
and model integration still remain unqualified/incomplete. No raw ready-bank
byte extent or smaller file is treated as current native admission.

No new generation tokens/s result or adopted acceleration follows from this
continuation. The wider cache, exact speculation, PLE, prefix, router and other
work packages remain individually tracked in the plan index. CI stayed disabled.

## Subsequent native numerical connection

The [connected native numerical entry and case 3046](finite-execution-dispositions-20261027.md#connected-native-numerical-entry-and-finite-decision-case-3046)
supersedes the missing numerical-entry statement above. It connects the existing
strong bank callbacks and twelve backing graphs to six serial/split/reverse
controls, real Direct reads, actual graph dispatch, F64 full-FFN references,
exact original contribution/output bytes and joined-source retirement. A separate
default-off route now admits the actual byte roots and partial Expert count to
the existing BF16/F32 vector shader; the production predicate is preserved.

The available pack provides only two unique original experts, so this gate uses
one distinct expert per group and I/O depth one. The representative ten-unique-
expert/two-call performance runner remains a later missing implementation,
dependent on this physical numerical prerequisite. Host/reference checks and
final native link/SELF integrity passed. One changed-scope screen observed 6630
pages against the staged CPU estimate 8159; no title or GPU ran. Backing/numerics,
representative timing and model adoption remain incomplete, with no reboot
dependency or unchanged retry.

## Subsequent original-source implementation

The [3048-3062 source/build record](finite-execution-dispositions-20261027.md#ten-original-expertdepth-two-implementation-cases-3048-3062)
supersedes the missing representative-runner statement above. Ten distinct sealed
original BF16 experts now feed the actual two-call reader and GGML serial/split/
reverse adapter. Manifest/identity/hash checks, bounded descriptor caching,
failure retention and independent review are host/build-qualified, default-off.
The extra fourteen graphs require all twelve backing and fourteen numerical
completions in the same title. None of the forty total graphs ran this continuation.
Native gates constrain execution/adoption, not writing disabled code. No new
PS5 operation/poll, kernel saving, tok/s result or production adoption exists.

## Later physical comparisons, 2026-10-27

The [physical source/ready and PLE results](finite-execution-dispositions-20261027.md#physical-original-source-and-ready-comparison-cases-3067-3106)
supersede earlier pending/unavailable statements for these precise fixture
scopes. The original-source CPU cohort completed eight reverse-controlled
cases; two calls gave a 1.06735x source-fixture ratio. The full forty-graph
ready comparison passed exact/F64 numerics, actual backing, all 180 original
reads and retirement, but overlap lost both reverse comparisons by about
0.9–1.4%. The PLE widths-one-through-four comparison completed all 208 graphs;
its -0.092% to +0.046% median effects and mixed per-pair wins supplied no
repeatable gain. Both variants are closed without model integration/adoption.
Neither fixture replaces a model tokens/s measurement.

Both titles were normally closed and the exact fastest SELF/settings fully
verified after restoration. No reboot or unknown completion occurred. Native
resource state changed: the post-ready screen observed 9160 pages and admitted
PLE under its original 8190-page requirement. The post-PLE screen observed 8874.
A separately scoped 8159-page CPU entry for the existing full-model comparison
is now being prepared, retaining the native 2974-page GPU gate and operational,
pool, precision and device limits. The regular 10142-page rule remains the
default. This new staged admission has not completed a model request, reduced
kernel consumption, qualified a winner or finished the overall plan.

The [subsequent original-model control](finite-execution-dispositions-20261027.md#original-model-control-and-remaining-current-environment-limit-cases-3130-3175)
actually completed warmup and both 30-prompt/22-output-token requests at 53
slots. Decode was 0.355716 / 0.398618 tok/s; TTFT was 50.056118 / 49.220898 s.
All native output/source/shader checks and positive retirement passed. Ordinary
close and exact fastest SELF/settings restoration completed. The next B128
screen observed 6583 pages against the CPU entry price 8159; no B title ran.
The A53/B128/B128/A53 cohort is incomplete and supplies no adoption decision.
Remaining full-model validation is currently unavailable; no supported reduction
of the earlier 6749-page initial CPU interval was established. This is neither
an assertion of permanent physical impossibility nor overall plan completion.
Do not repeat unchanged refusals or request reboot.
