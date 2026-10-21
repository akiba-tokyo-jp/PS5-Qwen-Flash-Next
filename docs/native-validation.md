# Native monitoring and staged validation

The owner authorized console validation after implementation on 2026-10-22,
then explicitly required avoiding console hangs and uncertain completion.
Host compilation alone does not authorize skipping a runtime prerequisite.

The default application configuration selects `display-validation`. This mode
does not call the model loader, backend enumeration, Vulkan initialization or
compute submission. It presents a CPU-rendered read-only monitor through the
existing VideoOut API. Two fixed 16 MiB Direct buffers are retained until
ordinary OS title close. A buffer is reused only after its own flip marker is
shown and no flip remains pending. The first visible monitor frame must complete
before startup reports success. A failed display operation is never retried.

The host tests execute this display owner against API stubs, including a failed
first monitor flip. They also exhaustively check all 2,073,600 pixel addresses
for bounds and uniqueness. API stubs do not establish console success.

The `monitor-validation` mode separately checks a model-independent operation:
BF16 32x16 weights times a F32 32-vector, with 16 F32 outputs checked against
exactly representable CPU fixture inputs. The fixed gate is `abs(error) <=
1e-5 + 1e-5 * abs(reference)`, with all outputs finite. A fresh durable start
record precedes backend initialization. This mode requires observed Direct and
Flexible headroom, serialized submissions and disabled asynchronous transfers.
It does not establish full-model quality or BF16 support before execution.

Application blocking fence/semaphore waits are capped at ten seconds. Zero-time
polls retain their original semantics. Failed submits, device errors or an
expired long wait halt the calling thread before stack unwinding, retain the
resource graph, latch quarantine and attempt a fresh durable fault record.
The pinned driver's underlying wait implementation also has a stall bound;
none of these limits proves that arbitrary unqualified GPU work is safe.
The native entry point forces serialized one-node submissions and disables
asynchronous transfers. Its CRT return hook retains the process rather than
entering the launch context's documented unsafe `exit` path.

The full model remains a third stage. Original shards, lossless conversion,
transferred file hashes, address-space and resident-memory admission, required
operation coverage and successful bounded inference must be established before
reporting Qwen inference. No fixture is a substitute for that result.

Before any launch, audit imports against actual public module exports. Weak
convenience stubs are not runtime ABI evidence. Package the exact verified PIE,
check SELF integrity and compare its reconstructed headers and loadable segments.
Preserve exact source, driver profile, compile/link inputs and SELF hashes.

For console work, freshly identify the sole native owner and verify idle native
and gateway services. Preserve the original SELF and settings before replacing
application bytes. Use ordinary OS close and an existing registered title only.
One launch intent permits one launch; ambiguous outcomes never trigger a retry.
Do not advance a stage with unresolved allocation, instruction, synchronization
or completion behavior. No manual GPU release, reset or force termination is
part of this procedure. Restore the exact original SELF and validate its
numerical startup admission and idle services after the test.

The raster, date/time and status observer run independently of browser polling.
The screen contains no chat or operation controls. Tokens/s stays unavailable
until tokens are actually generated. Unknown hardware counters remain absent.
