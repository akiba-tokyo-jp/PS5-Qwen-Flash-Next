# PS5 Qwen Flash Next

Experimental **Qwen3.8-Flash-Next inference on a single PlayStation 5**, using
SSD-streamed experts and a bounded cache in shared CPU/GPU memory. Learned
inference runs on the console; the PC prepares data, builds the application
and collects results.

This research source repository includes a native Vulkan integration, a
read-only monitor, a streaming HTTP interface and validation tools. Model
weights, native executables, SDKs and private hardware captures are supplied
separately. Start with the [documentation guide](docs/README.md).

## Project status

As of **2026-11-05**, the completed performance campaign selected **R1 + P1**:
completed-stage synchronization reuse and a cold-prefill output refinement.
The later Strata investigation has no adopted optimization. Its two cache-wait
refinements pass numerical and routing checks; their speed comparison is incomplete.

**The latest console session is unresolved.** Model and GPU resource retirement
completed, but ordinary application exit and restoration of the selected
application were not confirmed after communication was lost. This repository
does not establish that a usable service is currently running. See
[current status and limitations](docs/project-status.md).

## Measured performance

The latest completed selected-profile comparison reports:

| Request condition | Selected R1 + P1 decode rate |
| --- | ---: |
| Cold application cache | **10.437 tok/s** |
| Retained expert weights, reset request state | **12.173 tok/s** |
| Exact-prefix reuse | **13.218 tok/s** |

These are matched means from short native validation requests, not a general
benchmark or sustained-service guarantee. The primary metric is
`(generated_tokens - 1) * 1000 / decode_ms`; prefill, TTFT and whole-request time
are separate. The three cache conditions are not interchangeable.

P1 improves cold decode by **2.704%** and retained decode by **0.649%** against
its own R1 control. Exact-prefix changes by **-0.357%**, with no established
prefix gain. R1 has a separate matched comparison; its percentages must not be
multiplied into P1's. See [performance and validation](docs/performance.md) for
controls, numerical differences and rejected candidates.

## How it works

1. Authenticate and convert the pinned checkpoint on the PC.
2. Keep complete text-model data on the console SSD and read actual expert
   misses into bounded, owned staging windows.
3. Upload demanded experts to a bounded cache and execute the model through the
   pinned llama.cpp/GGML Vulkan backend and PS5 driver.
4. Preserve request ownership, output durability and positive resource
   completion before ordinary application close.

The original BF16 checkpoint remains the reference. The selected optimized
profile uses quantized expert/resident weights and an application routing
policy; it must not be described as unchanged original-precision inference.
Activations and KV/recurrent state remain floating point. Read the
[architecture](docs/architecture.md) for model, cache and ownership boundaries.

## Getting started

For a fresh checkout, begin with the host-only policy checks. They use Python
3.11+ and do not contact a console:

```powershell
git clone https://github.com/akiba-tokyo-jp/PS5-Qwen-Flash-Next.git
cd PS5-Qwen-Flash-Next
python -B -m unittest discover -s tests -p test_development_policy.py -v
python -B -m unittest discover -s tests -p test_driver_inputs.py -v
```

[Getting started](docs/getting-started.md) describes checkpoint acquisition,
engine sources, the Windows toolchain layout, the preview and native build
boundaries. Tracked tools are not a one-command reproduction of the privately
retained selected executable. Console execution requires its own current
prerequisites; committed deployment and execution flags remain off.

## Source and dependency pins

| Component | Selected reference |
| --- | --- |
| Model | `Qwen/Qwen3.8-Flash-Next` at `de4b8e4d43b917e7706784d8bb445c9af86a3540` |
| llama.cpp / GGML | `0a1ef309cdbb9f2024f58a38fb4c42352c5db569` |
| PS5 Vulkan driver | `akiba-tokyo-jp/PS5-Vulkan-Inference` at `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle` |
| Persistent shader/pipeline caches | Disabled |

Full identities are in the [dependency lock](native/qwen_flash_next/dependencies.lock.json).
Original BF16 preparation and the optimized runtime profile are distinct.
Read [driver provenance](docs/driver-integration.md) before building a driver;
a newer driver revision is not automatically qualified.

## Repository map

| Path | Purpose |
| --- | --- |
| [`native/app/`](native/app/) | Session, engine, cache, monitor and experimental providers |
| [`native/qwen_flash_next/`](native/qwen_flash_next/) | Startup, identity, source and lifecycle contracts |
| [`patches/llama/`](patches/llama/) | Patches to the pinned engine |
| [`tools/`](tools/) | Preparation, build, analysis and scoped validation tools |
| [`tests/`](tests/) | Host checks, API stubs and native test sources |
| [`config/`](config/) | Guarded defaults and recorded profile metadata |
| [`web/`](web/) | Read-only browser monitor |
| [`docs/`](docs/README.md) | Guides, results and dated research records |

`main` is the maintained source/documentation baseline. Remaining Strata work
is tracked separately; see the [branch policy](docs/repository-maintenance.md).
Experimental providers are not enabled merely by being present in the tree.

## License and acknowledgments

Project-authored code is [MIT licensed](LICENSE). Model weights have separate
Qwen model terms. llama.cpp/GGML, the PS5 driver lineage, Strata, Project Maya
and bundled helpers retain their notices. See
[dependencies and licenses](docs/dependencies-and-licenses.md).

This is an unofficial community project, unaffiliated with Sony or Qwen.
Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md), particularly the
separation between host checks, native evidence and adoption claims.
