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

The owner subsequently authorized real-console validation after implementation,
and explicitly required avoiding hangs and uncertain completion. The native
build, actual module import audit, SELF integrity/segment roundtrip and focused
host checks must pass before console work. Initial console execution is limited
to `display-validation`: no model load, Vulkan initialization or compute. The
configuration's `allowed_modes` must reject later modes until their preceding
gates pass. Release deployment remains disabled. Temporary validation publication
is authorized with exact preservation and restoration of the original title.
A host build or application merge is separate from native execution and
full-model qualification.

Use one identified native GPU title. Close existing applications through the
ordinary OS path. Never force-kill, reset the GPU, change firmware, or release
uncertain in-flight resources. Record compilation, console execution and model
quality as separate outcomes. Do not present a fixture or model load as completed
full-model inference.

## Bounded display admission and next gate

The display/status admission at SELF
`03e40dc85f18fea0755cf766ac94e1de4a4b008000412b857977a23ad5084e3a`
completed its first native frame and two HTTP 200 responses from one verified
owner, with a reported clock advance of 22,175 ms and no model/Vulkan
initialization. See `docs/native-display-20261022.json`. CPU percentage and
wall-clock calibration remain unqualified; native CPU percentage is now disabled.

The policy may permit `monitor-validation` only for the reviewed BF16 32x16
matrix/F32 vector fixture after host API ownership checks, linked SPIR-V
validation and observed memory headroom. Initially run it without native display
to isolate compute from scanout. Its finite 16-output numerical gate is separate
from model quality and throughput. `inference` remains rejected. Preserve every
failed admission and the shared driver's failed LLM CPU-reference baseline.

The first no-display BF16 attempt at SELF
`64ecb3b6515b9263265a04474f11255e6cdc0e817639bc7a30e03b54f8da0dab`
persisted headroom/clock admission and then exited before owner admission or a
completed readback. See `docs/native-bf16-20261022.json`. Do not repeat this
artifact. `monitor-validation` is disabled pending initialization investigation;
the finer host phase diagnostics do not qualify another console launch by
themselves. Preserve the unresolved cause and every original restoration gate.
