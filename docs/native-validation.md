# Native monitoring and staged validation

Committed console/deployment flags remain disabled. The earlier
[failed initialization](native-bf16-fixed-20261022.json) and shell-state refusal
are preserved. A subsequent guarded reassessment restored and numerically
readmitted the original application. The distinct corrected-link artifact then
[passed the physical BF16 fixture](native-bf16-success-20261022.md), followed by
complete original restoration, numerical readmission, ordinary shutdown and
fresh CPU guards. The task retains its reservation for staged validation.

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

After the successful no-display fixture, a distinct combined validation artifact
may present the monitor only after its own unchanged one-graph numerical gate,
positive device completion and retirement have passed. The private frozen
policy must name the preceding successful SELF and fixed 32 MiB display limit.
A fresh post-compute Direct observation must admit at least 128 MiB before
allocating display backing. Record first-frame completion separately. This
implementation is not combined console qualification until measured on-device.
The distinct source subsequently passed that physical gate and bounded local
UTC checks; see [the combined result](native-combined-success-20261022.md).
Full-model qualification remains pending.

The device wall clock was observed to differ from the host by about 11 minutes.
An optional app-local calibration uses one freshly guarded CPU observer's
second-resolution epoch and a bounded host observation interval. Reject
intervals wider than 8 seconds, discontinuous host clocks, uncertainty above
5 seconds, offsets beyond one day and startup observations older than 15 minutes.
Once initialized, both HTTP and native display advance the same UTC anchor with
the monotonic clock. This never sets the console system clock. Status identifies
the clock source and initial uncertainty; without calibration, the display
explicitly labels device time. Long-term clock drift is not qualified.

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
The C++ runtime, RTTI, exception personality and allocation operators must resolve
to the matching static SDK libraries; an exported native-module symbol alone does
not prove C++ ABI compatibility. Numeric IPv4 resolution is application-owned:
the SDK resolver placeholder rejects even loopback. Native configuration/assets
live beneath `/app0/qwen-runtime`, the existing title's application sandbox.

An exclusive raw-fd preinit journal records fixed startup stages before C++
constructors. Application diagnostics use a bounded owner-only raw-fd log;
inherited stdout/stderr descriptors are left unchanged. Missing or
unwritable journals retain the process before display/model work. An external
observer must distinguish OS launch acceptance, a live process, first-frame
completion and advancing HTTP timestamps. A deadline without the required
evidence is an explicit failed admission, never an implicit success or a reason
to resubmit the same launch.

For console work, freshly identify the sole native owner and verify idle native
and gateway services. Preserve the original SELF and settings before replacing
application bytes. Use ordinary OS close and an existing registered title only.
One launch intent permits one launch; ambiguous outcomes never trigger a retry.
Do not advance a stage with unresolved allocation, instruction, synchronization
or completion behavior. No manual GPU release, reset or force termination is
part of this procedure. Restore the exact original SELF and validate its
numerical startup admission and idle services after the test.

The first console attempt is recorded in
[native-startup-20261022.json](native-startup-20261022.json). The OS accepted one
ordinary launch, but a bounded observation found no native owner or admission
report. No repeat launch followed. The original SELF was restored byte-for-byte;
fresh CPU-only observations confirmed no native owner, no running big application
and an unchanged boot. That attempt did not pass display or GPU/model admission.
The startup cause is unresolved. Host review found incorrect sandbox paths,
mixed C++ runtime imports and the failing resolver placeholder; correcting those
issues does not by itself establish which one caused the observed startup failure.

The corrected SELF subsequently produced one exact native owner and the fixed
`preinit_entered` journal, but no main-entry or first-frame completion evidence.
Display admission remained failed. The title closed through the ordinary OS API;
the original executable was restored. This attempt did not establish whether the
remaining startup interval was bootstrap descriptor setup or a C++ initializer.
The next host diagnostic adds durable operation-specific failures and paired
enter/return records for each initializer, retaining the original CRT startup
order. The subsequent attempts and completed display/status admission are
preserved in [native-display-20261022.json](native-display-20261022.json).
The stdout descriptor-duplication failure was removed without replacing inherited
stdio. All 16 initializers and the first frame then completed; bounded explicit
asset routes and HTTP-only plain acceptance resolved the subsequent HTTP failures.
The accepted display artifact returned two HTTP 200 status samples from the same
owner, with an advancing console timestamp. CPU percentage and clock calibration
remain unqualified. The exact original SELF was restored, numerically admitted
and normally closed; fresh metadata confirmed no native owner on the same boot.

The next `monitor-validation` fixture was separately attempted. It disabled
native display, retained the fixed finite-output tolerance, validated
linked BF16 SPIR-V and requires at least 1 GiB Direct/64 MiB Flexible headroom.
A 250 ms sleep/monotonic interval check preceded backend initialization.
The [BF16 attempt record](native-bf16-20261022.json) preserves the observed
250.085196 ms interval and memory headroom. The native process then exited before
owner admission and without a terminal readback or fault report. Its termination
cause remains unresolved; initialization completion and dispatch count are unknown.
It was not retried. Policy again rejects `monitor-validation` and `inference`.
The host follow-up adds finer durable phases; it has no console qualification.
An absent process is recorded as an exit, without claiming an ordinary close call.

The raster, date/time and status observer run independently of browser polling.
The screen contains no chat or operation controls. Tokens/s stays unavailable
until tokens are actually generated. Unknown hardware counters remain absent.
