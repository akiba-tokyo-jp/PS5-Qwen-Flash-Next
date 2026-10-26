# Bounded native PLE copy fixture

The current order and phase-specific admission design are in the
[memory-first plan](PLE-memory-first-plan-20261026.md). It supersedes treating
the regular 10,142-page gate as the sole outstanding issue. No replacement
launch threshold is activated by this documentation.

This is preparation for a physical numerical/placement comparison, not a measured
optimization. The overall remaining plan is incomplete. The installed fastest
SELF remains `ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`;
the new package was **not published, launched or adopted**. Persistent caches,
CI and committed execution/deployment flags remain disabled.

## Implementation and independent gate

The candidate and its source/type screen are described in
[the feasibility report](remaining-feasibility-20261026.md#a-bounded-ple-graph-copy-elision-candidate).
`ple_convolution_graph.h::build_PLE_convolution_fixture` now constructs the full
original-shape four-tap convolution, original left-to-right tap sum and SiLU,
followed by an identical final output copy for guarded readback in every arm.
Inputs are deterministic finite BF16/F32 data, not model weights or host model
inference. Keep that scope separate from original-model quality.

`ple_slice_admission.cpp::admit_PLE_slice_fixture` prepares four modes at each
width 1/2/3/4. Each width uses four warmup graphs and three eight-round alternating
control/candidate pairs: 52 graphs per width, **208 total**. Each mode's CONT count
is respectively 8/4/4/0. The existing BF16 -> F32 conversion is preserved.

Every operation must be supported by the actual single Vulkan backend before
allocation. Direct graph execution on that backend provides no CPU arithmetic
fallback. Inputs and output views have 64-byte guards. Every result must meet
the existing F64 `1e-5 + 1e-5*abs(reference)` limit, and every candidate's complete
F32 output must match the original control in bits. Source/input guards and
read-only data are checked again before release.

The raw GGML buffer cap is 16 MiB per width. This is not a cap on all driver
memory: the existing device ledger, internal-workspace guard, allocation rounding
and system/Direct/Flexible admission remain. Widths retire sequentially after
positive graph completion, synchronization and driver checkpoints. A failed or
unknown call retains its raw fixture/backend ownership until ordinary OS close.
There is no retry, forced release, reset, extra queue or asynchronous mode.

The existing device ledger requires a healthy source owner. The fixture reuses
the already CPU-verified external shader file for that prerequisite, with its
fresh descriptor identity and the existing 8 MiB scratch window. It performs
only the existing first/last aligned preflight reads (two calls), starts no
source worker and loads no model. These reads/bytes are reported, not hidden as
zero I/O. No source-free exception to the existing guards was introduced.

`PLE-slice-validation` is a separate headless mode in `startup.cpp` and
`native_main.cpp`. `require_PLE_slice_policy` binds the driver/profile/archive,
four widths/modes, graph count, eight rounds, deterministic data and all current
CPU shader verification. It rejects display and unused monitor calibration.
Native startup memory and CPU/global/shader admission precede driver execution.
The caller completes the final device/epoch retirement before publishing success.
The committed `allowed_modes` remains empty and console operations remain false.

## Measurements and result review

Graph construction is measured separately. Timed graph intervals include compute,
synchronization, required driver checkpoints and full guarded output readback.
Initial allocation/upload, startup verification, safety-journal writes and CPU
reference checking are outside those intervals. The common final output copy is
inside every arm. These timings alone do not measure the full application cost.

`tools/ple_slice_result.py::validate` checks the exact owner, all finite counts,
placement, dtypes, memory completion, alternating order and warmup/timed records.
Each of the 208 durable before/returned pairs binds width, mode, ordinal and
elapsed time. The final caller-retirement marker is mandatory. It reports paired
ratios and slow rounds without declaring model qualification or adoption.
Do not hide separate graph construction, startup or allocation costs in a later
full-model comparison.

## Completed host checks

| Check | Completed evidence | Limit |
| --- | --- | --- |
| Complete graph/address fixture, 2653 | 16 actual GGML graphs, 409,600 exact F32 outputs, independent F64 checks and guarded output-view COPY | Deterministic address interpreter; no backend execution |
| Resource metadata | Maximum root-tensor total 8,643,328 bytes; metadata used 64,000 bytes | No physical allocation or kernel-headroom claim |
| Admission, 2652 | 52 invalid-scope refusals; startup, fixture and native-main units compiled | No console admission |
| Existing shared shader admission, 2655 | Original CPU helper preserved; exact orchestration and nine refusal controls passed | Metadata API stubs; no actual shader/GPU execution |
| Result review | Eight focused Python tests reject missing completion, wrong placement/order/types, incomplete counts, altered durable records and changed owner; preserve slow rounds | Synthetic records are not benchmark results |
| Full native package, 2654 | Actual app link, module import audit and six SELF segment roundtrips passed with frozen inputs | Not installed or executed |

Exact package provenance:

- Driver: `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`.
- Native archive: `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
- Linked PIE SHA256: `976201d7740104e50954e82c7403b5f7c1878de39cc0da5bf781d054e958c641`.
- Converted ELF SHA256: `f2e961786a6cf275b2754c59e6060d8f638bc5954720b4967d79b0a8947d9d5b`.
- SELF SHA256: `21dd6eae31e97440814403d86de0a087151aad9cf665c4317f30bce57943a25c`,
  28,242,599 bytes. Real missing module imports: zero; segment roundtrips: six.
- Original driver, engine and shader archives were unchanged. The experimental
  model overlay is not substituted into the linked production model graph;
  these four modes are used by the bounded fixture only.

Raw receipts, source snapshots, SDK content and binaries remain private and
outside Git. No CI or learned host inference was run.

## Fresh physical prerequisite and remaining work

After package completion, new CPU-only case 2656 positively returned the regular
prelaunch refusal at **6,257 free pages**, versus **10,142 required**. Title
launches, GPU calls, payload reads and explicit allocations were zero. No SELF,
configuration, driver or model was published. Fresh ownership checks found the
existing production reservation and no native/gateway/model owner. The console
responded; this is a memory-admission failure, not evidence of another GPU hang.

This observation does not authorize a later launch. The earlier reduced-headroom
prefix cases are consumed and cannot be reused for this fixture. Keep the startup
target, runtime floor, regular prelaunch gate, budgets and retirement checks.
Do not repeatedly launch under unchanged insufficient conditions.

The next physical stage needs a new finite frozen case, exact original
preservation, fresh admitted memory/ownership and the unchanged regular gates.
Then run this numerical/placement fixture and review its complete records before
ordinary close and exact fastest/settings restoration. A surviving mechanism
still needs matched full-model A/B then B/A comparisons, broader workload
regressions and exact production placement/readback before adoption. Prefix reuse,
ready-expert backing/graphs, real hidden-state observation and speculative
verification remain independently incomplete.
