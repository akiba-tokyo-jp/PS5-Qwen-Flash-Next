# Project instructions

Write project documentation, diagrams, code comments and program messages in English.
Keep conversation in the owner's preferred language.

The objective is original-precision Qwen3.8-Flash-Next inference on one PS5.
Use the pinned original BF16 weights. Do not substitute a quantized checkpoint,
prune experts, omit required model components, or use learned PC/cloud inference
as a substitute for console inference. Host builds, metadata processing, format
conversion preserving precision, and offline numerical verification are allowed.

Use the owner's current PS5-Vulkan-Inference driver, with an explicit profile,
source revision and archive digest. Preserve the upstream licenses and notices.
Keep weights, runtime binaries, private console evidence, endpoints, credentials
and credential hashes outside commits. Build and model data belong on the data disk.

GitHub Actions and other CI must remain disabled. Use focused manual checks.
Do not spawn agents or delegate without the owner's explicit authorization.

## Current integration phase

On 2026-10-22 the owner supplied the updated driver and authorized acquisition
and application integration. Use the current PS5-Vulkan-Inference source and
its integration contract. Pin the exact source revision, explicit profile,
artifact and application link provenance. Existing bounded driver evidence
does not establish this Qwen client's numerical quality or memory admission.
Persistent shader/pipeline caches remain disabled before backend initialization.

Implement and verify the native build/link path manually on the host. Console
operations and release remain disabled in config/development.json while this
integration is prepared. This phase does not require accessing the PS5 or
replacing another running application. A host build or application merge is
separate from native execution and full-model qualification.

Use one identified native GPU title. Close existing applications through the
ordinary OS path. Never force-kill, reset the GPU, change firmware, or release
uncertain in-flight resources. Record compilation, console execution and model
quality as separate outcomes. Do not present a fixture or model load as completed
full-model inference.
