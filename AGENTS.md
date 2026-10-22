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

The next initialization investigation separates `runtime-validation`: CPU time
initialization, a bounded 32 KiB GGML metadata context, release of that completed
CPU context and a C++ exception roundtrip. It must never access the backend
registry or initialize Vulkan. It is an implementation prerequisite, separate
from permission to repeat the failed GPU artifact.
After this CPU prerequisite passes, a distinct runtime-validation artifact may
query static Vulkan global version/extension metadata and verify required global
entry points without creating an instance/device or submitting GPU work. Keep
that discovery separate from Vulkan initialization and numerical admission.

Both CPU prerequisites have now passed on the console. The corrected backend
adds mandatory dispatch checks and removes an unenabled layer-settings pNext
chain, in addition to bounded staging and pre-load memory admission. A distinct
SELF may run the same fixed no-display 32x16 BF16 fixture after native import,
SELF, linked SPIR-V, ownership and headroom checks. This does not authorize
repeating the earlier failed SELF or skipping full-model qualification.

## Current console hold (2026-10-22)

The corrected BF16 artifact exited after Vulkan instance dispatch initialization,
before physical-device discovery returned. The subsequent CPU observer did not
admit the shell process state. No completed BF16 readback exists. The original
SELF remains preserved on the host and in the remote backup, but restoration
and fresh numerical admission have not completed for this attempt.

The owner cannot physically operate the console. Continue implementation and
manual verification on the host only. This supersedes all earlier permissions
above for additional console execution: do not launch a title, ELF observer,
GPU fixture or original application, attempt recovery/restart/force-close, or
request physical console interaction. Do not automatically resume after a
timeout or a successful host build. Keep console operations and all validation
deployment disabled in config/development.json. Preserve the reservation and
all failed evidence; do not report a normal or restored console state.

## Native frontend implementation

The subsequent host implementation follows actual PS5LM static RADV dispatch,
PS5 Mesa platform initialization and the preserved MIT native MOSS per-BO
lifetime code. See docs/native-driver-examples-20261022.md and the native source
provenance. Keep one explicit AGC8 owner, a Qwen-owned exclusive bounded journal,
one frontend producer, externally synchronized queue access and positive device
idle plus a matching worker completion epoch before deferred retirement.
Unknown or failed completion retains the resource graph. Qwen owns no optional
import-only heap; do not invent its capacity or import unowned CPU pointers.

Use tools/build_native_platform.py and --native-platform-manifest for native
frontend integration. The generic selected archive remains the exact shared
compiler/winsys donor, not an allocator substitute. Preserve all other native
member occurrences and immutable source/header/link receipts. Host native
integration and SELF checks do not lift the current console hold. Do not remove
the native GPU execution rejection merely because the host link succeeds.

## Original BF16 preparation

Use one bounded host preparation batch with OS writer leases. Retained files
may skip redundant acquisition rereads, but every original shard must pass
SHA256 before conversion. Require the complete pinned-converter tensor plan,
exact BF16/F32 shapes, every expert and PLE part, exact 64-bit PLE constants,
byte comparison of all expert/PLE/embedding copies, complete dense transformation
replay and final GGUF hashes before publishing
a model receipt. Keep failed/partial outputs; do not infer success from a stale
status file. The 11,976,330,752-byte planned memory requirement is not measured
available PS5 capacity. See docs/model-preparation-20261022.md.
