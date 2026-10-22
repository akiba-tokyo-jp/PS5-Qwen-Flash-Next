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

The owner subsequently authorized console validation and required careful
prevention of hangs and uncertain completion. [development.json](config/development.json)
permits only bounded `display-validation` after host checks; model loading and
GPU compute modes remain rejected. Release deployment is disabled. See
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
The subsequent native monitor build preserves 16 initializer slots and seven
runtime providers, passes 344 real-module import checks and produces an
integrity-checked SELF with six verified reconstructed segments. See
[the monitor host record](docs/native-monitor-20261022.json). Its first ordinary
console launch was accepted by the OS, but no native process or admission report
was observed. Startup is **not admitted**; see
[the startup record](docs/native-startup-20261022.json). The exact original SELF
was restored and read back, with no native application running and the same boot
still responding. Original numerical re-admission remains pending before final
console release. A distinct corrected build passes host verification with a
preinit journal, a static C++ ABI and 290 actual-module imports; see
[its host record](docs/native-monitor-corrected-20261022.json). This does not
establish corrected console startup. Original shard acquisition and full
checksumming remain incomplete.

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
