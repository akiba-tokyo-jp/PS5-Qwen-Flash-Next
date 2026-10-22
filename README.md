# PS5 Qwen Flash Next

Experimental original-precision **Qwen3.8-Flash-Next on one PlayStation 5**.
The goal is to execute the complete text model with its original BF16 weights,
streaming weights from SSD into bounded shared memory. No quantized substitute,
expert pruning, or PC/cloud model execution is part of this goal.

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
Committed console/deployment flags remain disabled in
[development.json](config/development.json). A private frozen fixture policy
and guarded ordinary launch are required; full-model inference remains rejected.
The native allocator/lifecycle integration is implemented and host-verified. See
[native-validation.md](docs/native-validation.md) for the staged gates and exact
preservation/restoration requirements. Driver tests do not establish Qwen quality
or memory admission.

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
of browser polling. Its no-model validation mode never initializes Vulkan.
See [application.md](docs/application.md) for exact check coverage and remaining
work. The demo is not evidence of Qwen inference or console performance.

## Current state

Construction is in progress. Full-model PS5 inference has **not** been achieved.
The pinned original checkpoint has 131 shards and 1,658 tensors. Every shard
header was inspected through bounded HTTP ranges: 359,999,962,848 bytes of BF16
weights and 280 bytes of exact I64 constants. This is metadata verification,
not a full-shard checksum or an inference result.

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
six verified reconstructed SELF segments. Native CPU percentage and wall-clock
calibration remain unqualified; tokens/s stays unavailable without inference.
The exact original executable was restored, numerically admitted and normally
closed. Fresh observations confirmed no native owner and an unchanged boot.
Original shard acquisition and full checksumming remain incomplete. These
display results are separate from the later successful no-display BF16 fixture.

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
Combined native display/Vulkan execution, accurate UTC calibration and full-model
inference remain separate qualification stages.

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
policy. Full acquisition/conversion and physical PS5 memory admission remain
pending.
The native client requires the complete v2 conversion audit and exact original
footprint before backend initialization; legacy receipts are rejected.
[The native contract build](docs/native-model-contract-host-20261022.json)
passes 289 actual-module imports, SELF integrity and six segment roundtrips.
That artifact has not been installed on the console.

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
