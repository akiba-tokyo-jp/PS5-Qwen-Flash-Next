# Dependencies and licenses

[Project-authored source](../LICENSE) uses the MIT license. That does not
relicense models, separately supplied SDKs, driver dependencies or imported code.
Preserve original third-party notices when redistributing source or derivatives.

## Pinned external inputs

| Input | Source / terms |
| --- | --- |
| Qwen3.8-Flash-Next | [Model repository](https://huggingface.co/Qwen/Qwen3.8-Flash-Next); Qwen Community License 1.0 recorded in the lock file |
| llama.cpp / GGML | [Upstream](https://github.com/ggml-org/llama.cpp); MIT |
| PS5-Vulkan-Inference | [Selected source](https://github.com/akiba-tokyo-jp/PS5-Vulkan-Inference); its own component licenses and integration contract |
| PS5 Vulkan/Mesa lineage | [Driver notice](../third_party/notices/native-driver.md) |

The [dependency lock](../native/qwen_flash_next/dependencies.lock.json) records
model/engine/driver revisions and source identities. It pins original model
preparation; later weight/routing experiments are separately described in
[current status](project-status.md). Model data is not bundled here.

## Included notices and references

* [Strata](../third_party/notices/strata/LICENSE): cache, source and execution design references.
* [Project Maya](../third_party/notices/project-maya/LICENSE): cache-policy references.
* [GGML quantization](../third_party/notices/ggml-quantization/NOTICE.md) and
  [license](../third_party/notices/ggml-quantization/LICENSE).
* [Native boilerplate](../third_party/notices/native-boilerplate/NOTICE.md) and
  [license](../third_party/notices/native-boilerplate/LICENSE).
* [SHA-256 helper](../third_party/notices/sha256.md).
* [LZ4](../native/thirdparty/lz4/LICENSE) and [zlib](../native/thirdparty/zlib/README.md).

A reference or source review does not imply that upstream endorses this project
or that a CUDA feature is a qualified PS5 Vulkan implementation.

## Distribution boundary

This tree distributes research source, tests, documentation and small public
metadata. It does not include model weights, native executables, proprietary
SDK material or private device captures. The driver/toolchain/model must be
obtained separately with the access and terms each requires. Source publication
is not a binary release or a claim of a portable complete build environment.
