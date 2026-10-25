# PS5 Qwen Flash Next

Experimental original-precision **Qwen3.8-Flash-Next on one PlayStation 5**.
The goal is to execute the complete text model with its original BF16 weights,
streaming weights from SSD into bounded shared memory. No quantized substitute,
expert pruning, or PC/cloud model execution is part of this goal.

The latest [qualified performance profile](config/qualified-performance.json)
selects BF16 indexed-vector decode and owned padded-bank Expert reads.
The complete same-SELF PS5 comparison measured **0.39068 / 0.39819 tokens/s**
versus **0.34838 / 0.35483**, an observed mean **12.18% gain**, with identical
outputs, token IDs, Expert routes and physical source reads. TTFT fell from
**57.65 / 56.68 s** to **50.14 / 49.26 s**. Both complete restoration and fresh
original numerical-admission plans passed; the console ended idle.
See [results](docs/gpu-optimization-results-20261025.md),
[sanitized counters](docs/native-owned-bank-success-20261025.json),
[profile usage](docs/qualified-performance-20261025.md) and the
[PS5LM source assessment](docs/ps5lm-transfer-assessment-20261025.md).
These are fixed short requests with original precision and unchanged budgets.
General execution/deployment and CI remain disabled.

The [complete implementation and physical validation plan](docs/execution-plan-20261022.md)
passed on 2026-10-24. One PS5 generated `4` for the arithmetic smoke request and
completed two external API requests, each returning `1, 2, 3, 4, 5, 6, 7, 8`.
Each external response generated 22 tokens at **0.28455 / 0.28882 tokens/s**;
time to first token was **104.62 / 102.14 seconds**. See the
[full-model result](docs/native-full-generation-success-20261024.md) and
[sanitized measurements](docs/native-full-generation-success-20261024.json).

The subsequent [source-I/O performance work](docs/performance-20261024.md) also
completed all physical/restoration gates. Bounded read/upload overlap measured
**0.28518 / 0.28958 tokens/s**, an observed mean **0.82%** above its profile
control and **0.24%** above the earlier functional control. This is a small
two-request result, not a general speedup claim. The implementation preserves
the 8 MiB window, original precision, every memory reserve and the selected driver.

The [contention investigation](docs/source-contention-investigation-20261024.md)
subsequently reproduced the rejected parallel-read slowdown in the loaded model
and isolated it without GPU work: same-file reads across approximately 1 GiB
offset regions cost about 49 ms per pair, versus 10 ms serial and 7 ms parallel
across distinct files. Independent opens do not help. Production retains one
read by default; [PS5-specific research](docs/ps5-source-io-workarounds-20261024.md)
selected file/range-aware scheduling for separate qualification. The proprietary
internal lock/cache implementation remains unproven.

The selected schedule subsequently completed the entire physical plan on
2026-10-25. Both fixed external answers/token IDs matched the single-read control
at **0.33288 / 0.33778 tokens/s**, a mean observed gain of **16.68%**. TTFT was
**89.44 / 87.38 seconds**. Qualified file/range pairs use at most two reads;
excluded pairs keep the single-read pipeline. Logical source bytes were unchanged.
This is one matched short-request result for the candidate bundle, which also
includes startup and lossless shader-storage changes. See the
[completed source-schedule report](docs/native-source-schedule-success-20261025.md)
and [sanitized counters](docs/native-source-schedule-success-20261025.json).

The [bounded prefill comparisons](docs/native-bounded-prefill-20261025.md)
qualified widths 2 and 4. Width 4 measured **57.64 / 56.77 seconds** TTFT,
a mean **35.30% reduction**, and **0.33927 / 0.34591 tokens/s** decode.
Generation remains single-token, with all validation and monitoring retained.
The [completed eight-proposal screen and selected implementation results](docs/performance-results-20261025.md)
retain current Maya LFU after exact actual-demand replay found no better tested
policy. The representative 512 MiB CPU read comparison improved 1.439x over
safe serial; its subsequent complete-layout inference result is recorded below.
The compact observer also completed all physical/restoration gates with an
unchanged CPU heap peak and zero memory-pressure events. Small decode changes
do not establish significance; state reuse and speculative drafts remain unimplemented.

The subsequent [matched 512 / 256 / 128 MiB physical-file comparison](docs/source-layout-size-comparison-20261025.md)
completed 576 exact-byte pairs on the PS5. Parallel means were **6.807 / 6.869 /
6.896 ms**; smaller files showed no material benefit in this representative
region. This CPU-only comparison does not establish a global file-size optimum.

The authorized [in-place 512 MiB replacement and full physical plan](docs/native-split512-success-20261025.md)
subsequently completed: 76 original logical files now use 711 physical files,
with every original logical and physical SHA256 verified. Arithmetic and both
22-token answers/token IDs matched the unsplit control. Decode measured
**0.34461 / 0.35136 tokens/s**, an observed mean **1.50% gain**; TTFT was
**57.56 / 56.59 seconds**. CPU heap peak increased 16 MiB within the unchanged
512 MiB budget. All previously adopted improvements remain implemented.
No complete second original model is kept on the PS5; verified host originals
remain intact. All actual frames, positive retirement, ordinary close, exact
original restoration, fresh numerical readmission, ordinary original shutdown
and final idle CPU/full executable readback passed. This small two-request gain
does not establish statistical significance or sustained throughput.

The model stayed loaded across the three requests. The actual native passive
frames were visually reviewed. Positive GPU/resource retirement, ordinary title
close, exact original SELF restoration, original numerical readmission, ordinary
shutdown, final CPU guards and complete original SELF readback all passed.
No native application remains running. Committed execution/deployment controls
and CI remain disabled; this result covers the finite validation session.

The complete original BF16/F32 text model retains all experts and required PLE.
Strata-style UMA admission and Maya aged-frequency eviction execute in the real
cache. Source reads use protected virtual keys and one bounded 8 MiB window;
model weights are not file-mapped. CPU heap peak was about 416 MiB inside its unchanged
512 MiB budget. CPU/GPU utilization remains unavailable, and displayed raw GPU
memory estimates are diagnostic. These short, thinking-disabled requests do not
qualify broad answer quality, reasoning performance or sustained service.

The earlier freeze and intermediate refusals remain documented in the
[forensic record](docs/freeze-forensics-20261024.md),
[native memory qualification](docs/native-memory-qualification-20261024.md),
[full-model progress](docs/native-full-model-progress-20261024.md),
[compact scheduler](docs/native-compact-scheduler-20261024.md) and
[physical CPU accounting](docs/native-physical-CPU-accounting-20261024.md).
The successful session supersedes their pending-generation status while
preserving every failed result.

## Native driver integration

The owner authorized integration of the updated driver on 2026-10-22. The source
is PS5-Vulkan-Inference at `872cc1264ad8ba5d6b888b092968fa5858a38c58`, explicitly
selecting `cumulative-idle`. Persistent shader/pipeline caches remain disabled.
The new profile is rebuilt from this source; older artifacts remain historical
controls. See [driver-integration.md](docs/driver-integration.md) for provenance,
manual build commands and the remaining native runtime/model gates.

The corrected application [passed the BF16 Vulkan fixture on the physical PS5](docs/native-bf16-success-20261022.md):
one 32x16 graph, 16 finite outputs, maximum absolute error 0. The passive monitor
also returned two HTTP 200 responses. The exact original SELF was restored,
numerically readmitted, normally closed and fully read back again. Fresh CPU
metadata confirmed no native owner. The task retains the console reservation.
The subsequent [combined admission](docs/native-combined-success-20261022.md)
also passed: completed BF16 computation and retirement, the first native TV
monitor frame, two passive HTTP responses and app-local UTC calibration.
The original app was again restored, numerically readmitted and normally closed.
The later [original-weight operation admission](docs/native-original-operations-20261022.md)
passed a 2560x16 BF16 matvec plus F32 RMS/SiLU: all 5,136 outputs met the fixed
numeric limits, followed by positive completion/retirement and complete original
restoration/readmission. These were component admissions; the later complete
model result and measured tokens/s are recorded above.
Committed console/deployment flags remain disabled in
[development.json](config/development.json). A private frozen fixture policy
and guarded ordinary launch are required. General `inference` mode remains
rejected; the completed session used a separate, frozen validation policy.
The native allocator/lifecycle integration is implemented and host-verified. See
[native-validation.md](docs/native-validation.md) for the staged gates and exact
preservation/restoration requirements. Driver tests do not establish Qwen quality
or memory admission. The [required-operation inventory](docs/qwen-operation-coverage.md)
keeps specialized Qwen graph paths separate from completed small-fixture coverage.

## Application development

The application includes session control, a Qwen/llama.cpp adapter, a read-only
inference monitor and a streaming HTTP API for external requests. The monitor
shows CPU/GPU information, date/time, generation tokens/s, TTFT and expert-cache
counters. It contains no chat input or operation controls. The host preview uses
an explicit demo backend; unknown hardware counters remain unavailable.
The real model adapter has API-stub tests and PS5 object compilation.
A guarded native entry point and BF16 conversion tool are implemented. The
native integration build and full-model qualification are recorded separately.
The native TV monitor uses two fixed VideoOut buffers and updates independently
of browser polling. Its display-only validation mode never initializes Vulkan.
See [application.md](docs/application.md) for exact check coverage and remaining
work. The demo is not evidence of Qwen inference or console performance.

## Earlier implementation checkpoints

At these earlier checkpoints, full-model PS5 inference had not been achieved.
The completed physical result above supersedes that historical status.
The pinned original checkpoint has 131 shards and 1,658 tensors. Every shard
header was inspected through bounded HTTP ranges: 359,999,962,848 bytes of BF16
weights and 280 bytes of exact I64 constants. All 131 original files have now
also passed their complete SHA256 checks. Conversion, independent output auditing,
all 76 final hashes, transfer and native model hashing subsequently completed;
the dated records below preserve earlier intermediate results.

The engine was rebuilt with the latest selected driver source on 2026-10-22.
The real application, original-BF16 adapter, HTTP service, Strata/Maya cache
patches and selected RADV archive now link into one intermediate native PIE.
The earlier host link is retained in [the integration record](docs/driver-integration-20261022.json).
Historical host builds and the first failed startup are preserved in
[the monitor host record](docs/native-monitor-20261022.json),
[the initial startup record](docs/native-startup-20261022.json) and
[the corrected host record](docs/native-monitor-corrected-20261022.json).
The subsequent [display/status admission](docs/native-display-20261022.json)
completed all 16 initializers, the first native frame and two HTTP 200 status
responses from the same verified owner. It initialized no model or Vulkan.
This artifact has six runtime providers, 289 verified actual-module imports and
six verified reconstructed SELF segments. At that display-only checkpoint,
native CPU percentage and wall-clock calibration were unqualified; tokens/s
stays unavailable without inference.
The exact original executable was restored, numerically admitted and normally
closed. Fresh observations confirmed no native owner and an unchanged boot.
At that display-only checkpoint, original acquisition and full checksumming
were incomplete. These display results are separate from the later successful
no-display BF16 fixture and the subsequent host model-preparation progress.

The separate no-display [BF16 fixture attempt](docs/native-bf16-20261022.json)
persisted its headroom and clock checks, then exited before owner admission or a
completed GPU readback. Its cause is unresolved. It was not retried; the exact
original SELF was restored. This is a failed admission, not a compute result.

The later [corrected initialization attempt](docs/native-bf16-fixed-20261022.json)
completed instance creation and checked instance dispatch, then exited before
physical-device enumeration returned. No BF16 compute or completed readback was
observed. The shell-state check then failed. The later
[reassessment and restoration](docs/console-reassessment-20261022.json) completed
on the physical PS5 without changing that failed result. The original bytes
and failed evidence remain preserved.

Host implementation now adds streaming model SHA256 checks before loading,
original-dimension/PLE verification, checked memory budgets, 64 MiB completed
transfer chunks, loader progress and separate inference phase records.
[Runtime implementation](docs/runtime-initialization-20261022.md) records their
scope. A host-only driver composition tool preserves the native allocator and
three native compatibility objects while applying the exact two selected
shared-driver members. The frontend now implements own-log initialization,
sole AGC8 ownership and retirement after device idle plus matching completion
epochs. [The source review](docs/native-driver-examples-20261022.md) records the
actual PS5LM/RADV and native MOSS examples and the implementation decisions.
Host integration does not establish Qwen console compatibility or numerical quality.

The distinct native-frontend trial subsequently passed explicit AGC8 and owner
initialization but exited during enumeration. The
[physical-console discovery record](docs/native-dispatch-discovery-20261022.md)
identifies a missing weakly referenced static Vulkan callback. Native linking
now retains the selected driver archive as the admitted original does, and
packaging requires an audit of the actual callback-table targets. The distinct
[corrected artifact](docs/native-bf16-success-20261022.json) subsequently passed
the physical BF16 fixture and positive completion/retirement checks. Its
117.013471 ms fixture interval is not model throughput. Native BF16 arithmetic
units were not advertised; the shader widens original BF16 storage to F32.
The later combined artifact passed native first-frame presentation and bounded
app-local UTC calibration. Long-term clock drift, original-model mapping/residency,
full-model quality and tokens/s remain unqualified.
The next [CPU model preflight](docs/model-preflight.md) independently verifies
complete model hashes/metadata and read-only virtual mappings before Vulkan.
The [physical CPU hash probe](docs/native-cpu-hash-20261022.md) measured 512 MiB
at 167.49 MiB/s with the production SHA object. Its compute-only projection led
to a fixed two-hour verification budget and structured progress; full-file disk
performance and integrity remain separate admissions.
The [resident buffer admission](docs/model-buffer-admission.md) now distinguishes
the upstream batching target from hard limits and checks aligned tensor sizes.
Host conversion now [bounds original BF16 copies](docs/bounded-conversion-20261022.md)
while retaining the pinned dense transformations and complete output audit.

The upstream llama.cpp model implementation is `qwen4exp`. Its PLE lookup,
hybrid attention, hyper-connections, expert-cache and scheduler paths are the
starting point. Strata/Maya principles are now wired into the actual engine cache:
UMA budget admission, aged-frequency eviction with recency ties, feasible layer
floors, active-expert protection and bounded miss read-ahead advice. See
[expert-policy.md](docs/expert-policy.md) for pinned sources, adaptations and
manual checks. Host fixtures preserve BF16 bits; they do not predict console speed.

## Dependencies

- [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next),
  pinned in [dependencies.lock.json](native/qwen_flash_next/dependencies.lock.json).
  Its Qwen Community License applies to the model, separately from this code.
- [llama.cpp / GGML](https://github.com/ggml-org/llama.cpp), MIT.
- The owner's private [PS5-Vulkan-Inference](https://github.com/akiba-tokyo-jp/PS5-Vulkan-Inference),
  an unofficial derivative of [PS5_Vulkan](https://github.com/mihawk-99/PS5_Vulkan)
  and [PS5_Mesa](https://github.com/mihawk-99/PS5_Mesa). Imported notices apply.
- Design references: [Strata](https://github.com/Niko1221/Strata) and
  [Project Maya](https://github.com/mw00/project-maya).

No models, native binaries, proprietary SDK material or private device captures
are distributed in this repository. GitHub Actions and other CI are disabled.

## Inspect and acquire the original checkpoint

Python 3.11+ is sufficient for metadata and acquisition. Point `--cache` at a
data disk with room for the original model and subsequent lossless GGUF output.

```powershell
python tools/qwen_flash_next.py prepare --cache D:/PS5-AI/qwen-flash-next --jobs 6
python tools/qwen_flash_next.py download --cache D:/PS5-AI/qwen-flash-next --jobs 4
```

`prepare` fetches metadata, tokenizer and shard headers. `download` explicitly
fetches all original shards, resumes partial files, verifies their original
SHA256 digests and publishes each shard only after verification. It performs
no inference or console operations.

`tools/prepare_model.py --acquire` runs resumable acquisition and bounded BF16
conversion as one host batch with OS writer leases and durable phase records.
The [complete conversion audit](docs/model-preparation-20261022.md) derives all
1,256 expected tensors from the pinned converter, checks split metadata and exact
precision, compares all original PLE/expert/embedding copies and replays every
dense weight-format transform, then publishes final
file digests. The derived memory footprint also matches the native admission
policy. All 131 original files have now been acquired and independently SHA256
verified. Conversion, output auditing, final hashes, transfer and physical PS5
memory admission subsequently completed before the generation result above.
The native client requires the complete v2 conversion audit and exact original
footprint before backend initialization; legacy receipts are rejected.
[The native contract build](docs/native-model-contract-host-20261022.json)
passes 289 actual-module imports, SELF integrity and six segment roundtrips.
That artifact has not been installed on the console.

[Offline transfer planning and per-file transport](docs/model-transfer.md) now
require the complete original receipt and preserve ambiguous transfer outcomes
without retry or deletion. Full-model console transfer subsequently completed;
the successful session reused its sealed files and same-boot native integrity.

## Manual PS5 build

The build uses the owner's local PS5 SDK, compiler, Vulkan headers and selected
driver archive. These dependencies are not redistributed. Keep the model cache
and build directory on the data disk.

```powershell
python tools/fetch_engine.py --cache D:/PS5-AI/qwen-flash-next
python tools/build.py --workspace C:/Users/User/ps5-ai --driver-root C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference --driver-manifest C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference/.local/qwen-cumulative-872cc126-001/manifest.private.json --cache D:/PS5-AI/qwen-flash-next --jobs 4
python -m unittest discover -s tests -v
```

This cross-builds static engine libraries and records local archive digests.
It does not install or launch an application. Console execution and numerical
acceptance remain separate milestones in [architecture.md](docs/architecture.md).
The tracked source patch links the required SPIRV-Headers include dependency;
the build receipt records its digest separately from the pinned upstream source.

`tools/console.py` inspects a native application before an explicitly requested
ordinary OS close. It records the PID, process start time, application ID and
title identity locally. It never sends force-kill signals or resets the GPU.
