# Getting started

This checkout is a research source release. You can inspect results and run
small host checks without a console, model weights or a PS5 SDK. A native
build needs separately supplied dependencies and operator-specific artifacts.
There is no supported one-command public install of the selected executable.

## 1. Inspect and run host checks

Use Git and Python 3.11+ from the repository root:

```powershell
python -B -m unittest discover -s tests -p test_development_policy.py -v
python -B -m unittest discover -s tests -p test_driver_inputs.py -v
```

The first checks guarded defaults and rejection before console IO. The second
uses temporary synthetic files/mocked source metadata to check driver-input
validation. Neither contacts a PS5 or performs model inference. Other test
families may need a compiler, SDK, upstream sources or private fixtures.

Read [status](project-status.md), [architecture](architecture.md) and
[performance](performance.md) before interpreting an experimental provider.

## 2. Acquire pinned sources and model metadata

Choose a separate data directory; examples below are placeholders:

```powershell
$QwenCache = "E:/ps5-qwen-cache"
python tools/fetch_engine.py --cache $QwenCache
python tools/qwen_flash_next.py prepare --cache $QwenCache --jobs 4
```

`fetch_engine.py` downloads/authenticates the pinned engine source archive.
`prepare` obtains model metadata, tokenizer and bounded shard-header ranges;
it does not fetch every weight or execute a model. The
[lock file](../native/qwen_flash_next/dependencies.lock.json) fixes revisions.

Full original weights are about 360 GB before conversion. Converted outputs,
temporary files and retained source data require additional space. Model terms
apply separately from this repository's MIT license. Only start the explicit
weight download when you intend that data transfer:

```powershell
python tools/qwen_flash_next.py download --cache $QwenCache --jobs 4
```

Acquisition resumes partial files and verifies the original whole-file hashes
before publication. [Original preparation evidence](model-preparation-20261022.md)
explains the BF16/I64 conversion/audit contract. It is distinct from subsequent
quantized deployment experiments. Model conversion is not console admission.

## 3. Supply the native build environment

The tracked builders expect a Windows workspace with the specific local layout
used by this project. Dependencies are not installed automatically:

| Input | Expected location under the supplied workspace |
| --- | --- |
| Cross compiler | `toolchain/llvm-mingw-20261006-ucrt-x86_64/bin` |
| Host compiler/runtime | `toolchain/msys-clang64/clang64/bin` |
| PS5 payload SDK | `toolchain/ps5-sdk-radv/ps5-payload-sdk` |
| CMake / Ninja | `toolchain/pydeps/cmake/data/bin` / `toolchain/pydeps/bin` |
| Shader compiler | `toolchain/shaderc-clang64/clang64/bin` |
| Vulkan headers | `toolchain/Vulkan-Headers/include` |
| Selected driver source | A separately available `PS5-Vulkan-Inference` checkout |
| Driver archive/manifest | Exact selected profile and authenticated private build manifest |

Inspect `tools/build.py`, `tools/build_preview.py` and
[driver integration](driver-integration.md) for the actual commands/contracts.
Some native helpers use additional historical workspace inputs; the table is
not a promise that all research scripts run with only these directories.
SDKs, native driver archives, private manifests and model weights are not
redistributed here. Access to this repository alone does not provide them.

With the correct inputs, the engine-library build is:

```powershell
$Ps5Workspace = "C:/ps5-workspace"
$DriverRoot = "$Ps5Workspace/driver-work/PS5-Vulkan-Inference"
$DriverManifest = "$DriverRoot/.local/selected-profile/manifest.private.json"
python tools/build.py --workspace $Ps5Workspace --driver-root $DriverRoot --driver-manifest $DriverManifest --cache $QwenCache --jobs 4
```

The driver must match the lock file's exact revision, profile, archive identity
and integration contract. Persistent caches remain off. This builds static
engine libraries; it does not reproduce, install or launch the selected native app.

## 4. Optional interface preview

`tools/build_preview.py --workspace ... --cache ...` builds an explicit demo
and also cross-compiles application objects, so it still needs the listed SDK.
It does not link the driver or run a model. After successful preparation/build:

```powershell
python tools/build_preview.py --workspace $Ps5Workspace --cache $QwenCache
& "$QwenCache/build/application-preview/app-demo.exe" --demo ./web "$QwenCache/model/chat_template.jinja" 41027
```

The preview listens on loopback. Its synthetic output and unknown hardware
counters are labelled; it is not evidence of PS5 inference. See
[application and monitor](application.md).

## Reproduction and deployment boundaries

The selected performance binary was linked from retained objects, generated
source overlays and private build/identity receipts. Those artifacts are not
all derivable from a clean checkout with the generic library-build command.
Dated JSON paths identify that campaign's evidence, not public download URLs.
Exact-binary reproduction and a packaged public runtime remain separate work.

Do not run a dated deployment/launch script as a quick-start command. The latest
console close/restoration is unresolved. Hardware execution requires current
identity, memory, source and completion observations and operator authorization.
All committed execution/deployment flags remain off; this guide starts no
console operation. Consult [native validation](native-validation.md).
