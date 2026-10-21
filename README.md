# PS5 Qwen Flash Next

Experimental original-precision **Qwen3.8-Flash-Next on one PlayStation 5**.
The goal is to execute the complete text model with its original BF16 weights,
streaming weights from SSD into bounded shared memory. No quantized substitute,
expert pruning, or PC/cloud model execution is part of this goal.

## Development restriction

The owner has deferred console release and validation until driver qualification
is complete. Current work is application development in this private GitHub
repository with manual host checks. Do not access the PS5, upload, install,
launch, close applications, deploy, or run console tests during this phase.
The driver repository and dependency pin remain unchanged. The previously
selected driver is not a qualified release dependency.

[development.json](config/development.json) records this restriction. The
existing console tool rejects commands before network access or local writes.
An application PR or passing host check does not authorize console work.

## Application development

The application includes session control, a Qwen/llama.cpp adapter, a chat web
interface and streaming HTTP API. The interface runs on the host with an explicit
demo backend; the real model adapter has API-stub tests and PS5 object compilation.
A guarded native entry point and BF16 conversion tool are implemented, but a
complete native application link and full-model execution are still pending.
See [application.md](docs/application.md) for exact check coverage and remaining
work. The demo is not evidence of Qwen inference or console performance.

## Current state

Construction is in progress. Full-model PS5 inference has **not** been achieved.
The pinned original checkpoint has 131 shards and 1,658 tensors. Every shard
header was inspected through bounded HTTP ranges: 359,999,962,848 bytes of BF16
weights and 280 bytes of exact I64 constants. This is metadata verification,
not a full-shard checksum or an inference result.

The manual PS5 cross-build completed on 2026-10-21: `libllama.a`, `libggml.a`,
`libggml-base.a`, `libggml-cpu.a` and `libggml-vulkan.a` were generated. The build
selects the owner's pinned cumulative-idle driver archive for the eventual
application link. These static libraries are not a linked, deployed or validated
inference application. Nine acquisition checks pass; original shard download
and full checksumming are still in progress.

The upstream llama.cpp model implementation is `qwen4exp`. Its PLE lookup,
hybrid attention, hyper-connections, expert-cache and scheduler paths are the
starting point. Strata and Project Maya inform the tiering design; their
quantized PC performance figures do not predict this project's console speed.

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
python tools/build.py --workspace C:/Users/User/ps5-ai --driver-root C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference --driver-manifest C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference/.local/profile-cumulative-idle-001/manifest.private.json --cache D:/PS5-AI/qwen-flash-next --jobs 4
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
