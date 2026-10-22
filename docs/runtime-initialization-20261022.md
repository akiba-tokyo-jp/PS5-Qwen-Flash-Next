# Runtime initialization implementation

All further console execution is disabled. The owner cannot physically operate
the console. The native GPU entry paths also fail before backend initialization
throughout the console hold. The native lifecycle is now implemented for host
verification. Host builds
and tests below do not lift this restriction.

The CPU prerequisite completed on the console with SELF
`86d425e61006525dd22bdde3fc1c7f91121593c251892a15c58676fa6348986d`:
time initialization, a 32 KiB GGML metadata context, its completed release and a
C++ exception roundtrip. Two HTTP 200 samples came from the same verified owner.
No backend registry, Vulkan instance/device, model or compute was initialized.

A distinct SELF
`4eb78c3c0d2f65935775f439f407dc9d5c2a26afe03a9169b39f3050a8cd9bf8`
also completed the checked static Vulkan global version and extension queries.
These CPU-side queries do not create an instance/device or submit work. The
earlier BF16 exit remains a failed numerical admission with an unresolved cause;
these prerequisites narrow its failing interval without replacing that record.

The distinct corrected BF16 SELF
`dfb9c1c5361634bc5ac15dac8c9d26cc712c45f9aa7ad137f018b0bd13da11a1`
completed instance creation and checked instance dispatch, then exited before
physical-device enumeration returned. No device, compute or BF16 result was
admitted. The subsequent CPU observer failed the shell-state gate. No additional
console helper or application is being executed, and original restoration and
fresh numerical admission remain pending. See
[the preserved record](native-bf16-fixed-20261022.json).

The selected generic driver archive did not retain the required native
application allocator and compatibility objects. Host tooling now composes the
exact shared-driver pair into a pinned native base while retaining its other
702 member occurrences. At that checkpoint native frontend integration remained
incomplete; the source/allocator omission is not established as the exit's root
cause. The subsequent [implementation from actual Vulkan examples](native-driver-examples-20261022.md)
adds the frontend lifecycle and native links without console execution.

The application implementation now validates required static dispatch pointers
before use and omits `VkLayerSettingsCreateInfoEXT` when its extension is not
enabled. Backend phases precede global dispatch, extension enumeration, instance
creation, instance dispatch and device creation. Feature advertisement and
arithmetic remain the selected driver's responsibility.

Before model loading, every transferred file is streamed through the pinned
engine's public-domain SHA256 implementation with a 1 MiB buffer, a per-file
deadline and progress records. Hash mismatch, size change, unexpected EOF or
file growth rejects the load. A successful integrity report is saved before
backend initialization. An independently computed Python SHA256 agrees on a
65 MiB host fixture; digest corruption and growth are rejected.

GGUF metadata is checked for original dimensions, all 512
experts, top-10 routing, the 48-layer trunk and required PLE. Tensor/file spans,
duplicate names and byte arithmetic are checked. Memory accounting separates
device weights, mapped experts, lazy PLE, CPU embeddings and unused MTP tensors.
Fresh driver, Direct and OS observations must admit the planned context,
workspace, cache, two bounded staging banks and reserves before loading starts.
This is a preflight requirement, not a qualified resident-set or mapping result.

The actual Vulkan buffer implementation copies contiguous original bytes in
completed chunks of at most 64 MiB when `GGML_VK_BOUNDED_STAGING=1`. Each chunk
retains the existing visibility, submission, fence and cleanup sequence. Both
staging allocators reject larger requests. Host checks extract the actual patched
transfer functions and verify byte preservation, boundary offsets, default
behavior and no continuation/retry after a failed chunk. No quantization or
expert selection changes are involved.

Model loading has a 20-minute deadline checked at completed loader progress
boundaries. The adapter records tokenization, prefill, decode return,
synchronization, sampling, token readiness and successful reset separately.
A failed decode cannot emit its synchronization-completed phase. Public phases
contain no prompts or generated text; the journal fails explicitly before
exceeding its bounded capacity. Backend wait failure still retains resources
before unwinding for ordinary OS close.

`tools/prepare_model.py` is a bounded host batch command which waits for the
existing downloader, then invokes original-shard verification and BF16
conversion. It does not start another writer or perform console actions.
Conversion publishes durable verification/conversion/hashing/completed/failed
states and has a process deadline. A corrupt shard or timed-out converter cannot
publish a model receipt. Full checkpoint acquisition, console mapping/residency,
model output and measured tokens/s remain separate requirements.

The converter also checks all 237 Python files in its source tree against the
original pinned ZIP before execution and again before receipt publication.
Changed or additional Python modules are rejected. The latest host-only native
build, local SELF checks, 24 Python tests, API-stub checks and native-driver
composition are recorded in [the host result](host-only-implementation-20261022.json).
The composed archive retains all 702 native member occurrences outside the
selected pair. At that earlier checkpoint it was not linked into the application.
The subsequent native frontend is implemented and host-linked separately; see
[the actual Vulkan examples](native-driver-examples-20261022.md). No artifact
from these host results has been sent to the PS5.
