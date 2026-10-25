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

### Subsequent bounded reassessment

The owner's subsequent request to use the PS5 resumes examination of the
existing console under the previously authorized validation task. The earlier
host-only hold must not prevent a fresh bounded CPU-only state assessment.
Existing management GETs have responded with no native owner. Permit one
fresh-nonce copy of the reviewed metadata-only observer, preserving every
boot, process identity, process state and double-snapshot guard. This is not
permission to relax a failed guard or repeat an ambiguous execution. If the
fresh assessment passes, restore the exact preserved original SELF while its
title is inactive and verify a complete readback before considering an ordinary
original-title admission. Keep GPU validation, release deployment and full-model
execution disabled until separately admitted. Preserve the existing reservation
and failed records throughout.

The reassessment subsequently passed. The exact original SELF was restored,
numerically readmitted on the physical PS5, normally closed, and verified by
fresh idle CPU metadata and a complete post-shutdown readback. See
docs/console-reassessment-20261022.md and its JSON result. The reservation is
still held by this task. A distinct native-frontend artifact may now run the
single no-display BF16 32x16/F32-vector fixture after its host link, module,
SELF, SPIR-V, fresh session, exact original preservation and headroom gates.
Use the native validation policy's exact archive/profile and one-graph scope;
keep committed console/deployment flags disabled. This is separate from
full-model admission and never authorizes repeating an ambiguous launch.

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
Keep the native v2 receipt and complete original footprint gates before backend
initialization. A metadata fixture or legacy receipt must never bypass them.

## Latest physical-console result

The distinct corrected-link artifact at source
`f645d9303f105e363d00dc42fd72c4d3a25cb476` passed the one-graph no-display BF16
fixture: all 16 outputs exact, maximum absolute error 0, positive device idle
and matching completion-epoch retirement. Its passive monitor returned two
HTTP 200 responses. See docs/native-bf16-success-20261022.md and JSON.
The exact original SELF was restored, numerically readmitted, normally closed
and fully read back after shutdown. Fresh CPU guards passed with no native
owner and the same boot/services. The earlier hold and failures above are
historical checkpoints, superseded only by these explicit completed gates.
The reservation remains held. Keep committed console/deployment flags disabled.
Full-model inference, resident-memory admission and tokens/s are unqualified.
Native VideoOut combined with Vulkan and accurate UTC calibration remain
separate stages; an advancing device wall clock does not establish UTC accuracy.

A distinct combined validation artifact may now run the unchanged one-graph
fixture and start the fixed 32 MiB native display only after its own numerical,
positive completion and retirement gates pass. Require the exact preceding
successful SELF in the private policy, fresh session/original preservation and
fresh post-compute Direct headroom. App-local UTC calibration may use one
freshly guarded CPU observation and a bounded host interval; never set the
console system clock. Its source and uncertainty must remain visible. Preserve
and restore the exact original executable, then repeat its numerical admission,
ordinary shutdown, fresh CPU guards and complete final readback. Full-model
inference remains independently rejected. Host checks alone do not qualify
combined display/compute or calibrated UTC on the physical console.

The distinct combined artifact at source
`e60e947e0954618a05543ee8ecbc3d041e3e1ee2` subsequently passed its physical
one-graph BF16 gate, positive completion/retirement, native first-frame completion
and two passive HTTP/clock observations. Initial UTC uncertainty was 2,209 ms;
the console system clock was unchanged. The original app was restored,
numerically readmitted, normally closed and fully verified again with fresh
CPU guards. See docs/native-combined-success-20261022.md and JSON. No native
owner remains. Preserve this result separately from full-model admission;
committed console/deployment flags remain disabled and the reservation is held.

The next model CPU preflight is implemented as `model-validation`. Do not execute
it until the complete v2 model receipt and every transferred file are available.
It must verify all SHA256/metadata/footprint gates and read-only virtual mappings
before any backend initialization. Keep display and model loading disabled,
bounded whole-model verification and mapping deadlines, no mapped-payload reads,
and no automatic retry or cleanup after uncertain mapping results. A successful
terminal report precedes explicit idle ownership for ordinary OS close. See
docs/model-preflight.md. Host checks do not admit physical model mapping.

Use tools/bounded_conversion.py through tools/convert_model.py for current
original-precision conversion. It retains the pinned source tree and dense
transformations, while bounding all 150 expert/embedding/PLE copy outputs to
8 MiB input chunks. Require its complete copy provenance and the independent
full output audit. Once the active batch reaches conversion, do not edit
convert_model.py, bounded_conversion.py, audit_conversion.py, qwen_flash_next.py,
fetch_engine.py or prepare_model.py until its verification/audit/hashing ends;
their digests are frozen in the resulting receipt. See
docs/bounded-conversion-20261022.md. Acquisition may retain unverified files,
but every original shard still requires SHA256 before converter execution.

After the successful combined admission and completed original restoration,
a distinct `operator-validation` artifact may run the fixed original-weight
2560x16 BF16 matvec plus F32 RMS/SiLU diagnostic in one graph without display.
Require the pinned source-shard/slice hashes and unchanged numeric limits,
all host/import/SELF/callback/SPIR-V gates, fresh session/headroom and exact
ordinary-launch preservation/restoration. This small diagnostic is separate
from the complete v2 model receipt, model loading, full-model quality and tokens/s.
See docs/original-weight-operations.md. Never repeat an ambiguous launch or use
this mode to bypass the still-rejected full inference stage.

That distinct original-weight artifact subsequently passed on the physical PS5:
all 5,136 matvec/RMS/SiLU outputs met the fixed limits, positive device idle and
completion-epoch retirement passed, and two passive HTTP observations passed.
The exact original was restored, numerically readmitted, normally closed and
fully read back after fresh final CPU guards. See
docs/native-original-operations-20261022.md and JSON. The reservation remains
held, with no native owner. Full-model gates and disabled committed execution,
deployment, release and CI controls remain unchanged.

Model data preparation uses tools/plan_model_transfer.py, build_model_directory.py
and transfer_model.py. Do not execute a model-directory controller or start bulk
transfer before the complete original v2 receipt/plan, exact local build proof,
fresh unchanged CPU session, reservation and verified existing parent-owner
marker. Bulk transfer additionally requires positive new owned-directory evidence
after controller finalization; that evidence cannot precede directory preparation.
The CPU controller changes only the established task-directory ownership and
positively verified new model/marker modes; restore the parent ownership before
publishing its admission. Compile fixtures must never be executed on the PS5.
The transport never grants native model/GPU admission. Require independent
native SHA verification afterward, retain uncertain partials and immutable failed
records, and never automatically resend an uncertain file or receipt publication.

A bounded ordinary host continuation is now active for successful preparation
through CPU directory admission and data-only transfer. Its private
`model-data-continuation-001/intent.private.json` freezes the relevant preparation,
directory, transport, receipt and memory-header sources. Keep every recorded
input unchanged while that continuation is active. It waits for matching complete
conversion/audit/hash records, then requires new unchanged CPU observations and
separate exact directory/data admissions. Failed upstream preparation, changed
inputs/session/reservation or any uncertain step stops the sequence for review;
it never retries, launches a title, initializes Vulkan or loads the model.
Successful transfer still requires independent native SHA/mapping admission.
Documentation and unrelated runtime development may continue without mutating
those frozen inputs. Keep committed execution/deployment/CI controls disabled.

A separate bounded synthetic CPU hash timing probe may assess the cost of the
later full-file SHA stage during that no-console preparation wait. Require the
exact already-qualified native SHA object, unchanged credential-preserving CRT,
actual runtime-export audit, host timer/digest checks, fresh unchanged CPU session
and existing reservation. Use one new nonce and the model data writer lease;
require a fresh idle CPU guard afterward. Limit it to the 1 MiB synthetic RAM
buffer, 512 verified passes, a 10-second target and 15-second observation boundary.
No model/file payload, title, GPU, ownership change or execution retry is included.
Its compute-only extrapolation never qualifies disk I/O or full-model integrity.
See docs/cpu-hash-probe.md. Keep the active continuation's recorded sources frozen.

That CPU probe completed on the physical console with fresh unchanged guards:
512 MiB in 3.056937667 s, 167.4878770107418 MiB/s. The original SELF/app directories
were untouched. See docs/native-cpu-hash-20261022.md and JSON. Its approximately
34.09-minute compute-only full-payload projection supersedes the earlier native
preflight's 30-minute planning budget. Use the distinct v2 native model-validation
policy with one fixed 7,200-second whole-model deadline and structured progress;
do not execute the earlier 30-minute binary as full-model preflight. The revised
entry point has host policy/parser checks and PS5 object compilation, but requires
a fresh complete link/package/import/SELF gate before any physical execution.
This changes no receipt/data-transfer gate, mapping limit, GPU/model rejection
or active continuation source. Complete original files and independent native
SHA/mapping admission remain mandatory.

The owner's subsequent instruction to implement and run continues bounded
physical qualification. A distinct `moe-validation` case may test the original
BF16 indexed expert graph described in docs/original-moe-diagnostic.md after
its full host/link/import/callback/SELF/shader gates. Keep all 512 diagnostic
experts, ten fixed IDs, unchanged numerical thresholds and one compute graph;
native display and full-model loading remain disabled. Positively stop the
waiting data-only continuation before changing its frozen console context or
reservation, preserving evidence and leaving model conversion untouched.
Require fresh idle guards and complete exact original preservation, restoration,
numerical readmission, ordinary close and final readback before binding a fresh
data-only continuation. Host tests do not establish physical MoE success.

## Active forward plan

Use `docs/execution-plan-20261022.md` as the new forward work queue requested by
the owner. Continue frozen model preparation/data transfer unchanged; add no
standalone operator trial while it runs. Implement a distinct bounded
first-generation admission with complete native integrity/mapping gates before
backend initialization in the same ordered title session. Ordinary inference
stays rejected until separately qualified. Preserve existing failure evidence,
resource retention and exact original restoration. The bounded native path and
focused host checks are now implemented; full link/SELF/import, independent host
observation and complete model/resource admission remain pending. Host checks
never permit bypassing those gates or establish physical first generation.

The original indexed-MoE case subsequently passed at SELF
`0b187cac25c3e322bd4244474a935d191ce85b7bcbb3d2559ead26f05198d057`,
with all diagnostic experts, fixed numerical limits and positive retirement.
The exact original was restored, numerically readmitted, normally closed and
fully read back with fresh idle guards. The data-only continuation 002 was bound to that completed context; the earlier
001 continuation was positively stopped before the MoE case. Batch 002 then
failed while waiting when original host conversion 001 reached its fixed
six-hour deadline. All known original writer/controller processes ended, with
351,317,227,759 partial output bytes preserved and no console access.
The original SHA journal and all 131 source identities were rechecked before
a distinct resumed host attempt. Preserve every old failure and partial file.

The owner's completion criterion covers every implementation and physical check
in all three deliverables, including passive display/API measurements, ordinary
close, exact restoration and numerical readmission. Individual host/component
checks are intermediate results and must not end the overall work.

The private first-generation policy is now v2. It includes bounded direct source
reads, tracked CPU/post-load device budgets, one arithmetic smoke request, and
two fixed external requests on the same producer thread after recreating only
the positively completed context. The native display starts after the smoke
result and fresh model-resident headroom. The first benchmark has an empty expert
cache; file pages/pipelines may be warm. See docs/bounded-runtime-20261022.md.
Full link/package/import and complete model data remain mandatory before that
distinct physical case. Keep the active preparation/002 inputs unchanged and
retain every earlier failed admission. Host implementation does not establish
that the full model fits, computes correctly or reaches a particular token rate.


## Current bounded continuation (2026-10-23)

The final native candidate SELF is
`b380e755daf7ecfa3b10a46ed3aefc867bca80d5917d831d1815262f18f4bfc0`
(58,586,023 bytes), with six roundtrip segments, 289 resolved real-module imports
and no missing imports. The BF16/operator/MoE shader suites passed. It has not
been launched. The driver and cache policy remain the exact pinned 872cc126
cumulative-idle source/profile; the newer driver checkout commit changes only
documentation. Use the existing pinned Qwen source checkout and exact manifests.

Host conversion-resume-002 is active for converted-bf16-002, initially reusing
72 complete splits. Do not edit convert_model.py, bounded_conversion.py,
audit_conversion.py, qwen_flash_next.py, fetch_engine.py, prepare_model.py,
resume_conversion.py, resumable_gguf.py or resume_provenance.py while its
writer/audit/hash pass runs. Original source and converted output read-only OS
leases plus unchanged identity checks remain mandatory. Structural retention
never replaces the complete original payload audit and final file hashes.

The single data waiter 003 freezes its recorded data sources and the unchanged
completed MoE context/reservation. Only after resumed conversion completes may
it prepare/run data continuation 003: at most five reviewed CPU-only ELF
requests and one bounded data transfer; no native title, model load or GPU.
Keep all its recorded inputs unchanged until it ends. Physical first generation,
passive monitor/API measurements and exact final restoration remain pending.

The original audit/waiter processes were subsequently found absent, with their
last progress at 16:50 UTC and no model receipt, data batch or console access.
Their immutable records remain preserved. A distinct finite host-only
`finish_conversion.py` attempt reuses all 76 completed writer outputs and repeats
the complete audit and final hashes. It does not repeat conversion or accept the
interrupted partial audit as admission. The audit and its data-only waiter now
run detached from the interactive process job. Keep `finish_conversion.py`, all
nine preparation/resume sources above, and every source/context/reservation in
data waiter 004 unchanged while they run. The unchanged data continuation 003
may execute only after the new complete receipt/status; all physical first
generation and restoration requirements remain part of the unfinished plan.

The one finite full-plan continuation 019 may wait for positive data completion
and the identified data waiter's exit, then invoke the existing case preparer
and reviewed operator steps once, including final ordinary close, exact original
restoration and numerical readmission. Keep every source in its private intent
unchanged while it runs. A failure or uncertain step forbids subsequent actions;
it implements no retry, forced close, GPU reset or automatic recovery. See
`docs/host-audit-continuation-20261023.md`. Detached launch is process isolation,
not evidence of successful inference or completed physical validation.

Continuation 019 later ended before case preparation or console access because
of a local progress-file sharing conflict. Preserve its failure and absence of
execution intents. Continuation 020 uses bounded local progress observations
from `tools/local_progress.py` while retaining all prior execution gates and
deadlines. The original audit and data waiter remain unchanged and active. Keep
the sources recorded in continuation 020 unchanged while it runs. Only local
metadata observations/publication may repeat for a sharing conflict; physical
operations and exclusive execution intents must never be retried this way.

Data waiter 004 subsequently ended during its pre-console wait on progress-file
replacement; continuation 020 rejected that failure before any physical step.
The audit remained active. After preserving both terminal records and checking
absence of execution intents/processes, data waiter 005 and full-plan
continuation 021 were started with current source bindings. Local
`model_transport.atomic_progress` replacement is now bounded for sharing
conflicts; exclusive intents and remote uploads remain one-attempt operations.
Six actual Windows sharing tests and 14 existing transport tests passed. Keep
every input recorded by the active waiters unchanged until they end.

## Efficiency reassessment (2026-10-23)

Use the updated `docs/execution-plan-20261022.md` and its linked critical review
as the current forward queue. All 76 outputs and the independent content audit
are complete; the existing final hash pass remains active. Preserve that pass,
data waiter 005 and full-plan continuation 021 with their frozen inputs. The
proposed immediate switch to upload-time receipt finalization is not implemented
or admitted and is not current work: no evidence establishes a net schedule gain
over finishing the remaining hashes. Reuse the sealed native candidate and its
passed checks. Measure sustained throughput during the existing transfer rather
than adding a probe. Physical full-model memory/load/generation, passive display
measurements and exact final restoration remain pending. This updates scheduling
and status, not physical permissions, precision, verification or safety gates.

The audit and all 76 final container hashes subsequently completed, publishing
the full v2 receipt. Data batch 003 failed the CPU controller import subset gate
before any CPU observer, console action or transfer. Waiter 005 and full-plan
continuation 021 positively ended. Preserve their immutable failures and the
completed model. The corrected directory controller passed 37 API checks with a
4,096-byte marker, the actual PS5 object import subset gate and 11 focused Python
tests. See `docs/model-directory-import-fix-20261023.md`. One finite continuation
022 may now use the existing data operator with fresh batch 004, then the unused
physical case 019 and every original final restoration/readmission gate. No new
model audit/hash waiter or application rebuild is required. Keep its frozen
sources unchanged while it runs; retain every failed/uncertain attempt without
automatic retry, GPU reset or forced close.

Continuation 022 / batch 004 later passed the actual controller link and fresh
physical CPU admission. A private local provenance check rejected the qualified
recipe's two archived CRT objects before the directory controller or any data
mutation. Its exact-path correction retains the pinned recipe and both recorded
hashes; all local directory admissions passed in offline mode. Continuation 023
may use fresh batch 005 and the unchanged unused physical case 019, reusing the
completed model and candidate. Keep its frozen inputs unchanged. No failed or
uncertain physical directory operation is being repeated.

Batch 005 later completed CPU `prepare`, then rejected the FTP creation's
canonical-path comparison before marker upload/finalization. A read-only review
proved the exact empty root-owned directory. Reviewed continuation 006 did not
repeat `prepare` or `MKD`: one fresh CPU observation, the first marker upload and
the first `finalize` all passed, restoring parent ownership with exact readback.
See `docs/model-directory-reviewed-resume-20261023.md`. The original plan and
complete model are retained. Data continuation 006 is active with two CPU
observation requests and a bounded one-writer transfer; keep its frozen inputs
unchanged. Its distinct completion-v2 record binds the reviewed directory and
original plan. Full-plan continuation 024 may wait for the identified data
process's positive completion and exit, then perform the existing physical case
019 and every final restoration/readmission step. Ordinary execution/deployment/
release and CI remain disabled; native destination SHA is still mandatory.

Data continuation 006 published the first 3,508,767,456-byte split after its source
stream SHA and FTP 226 passed, then rejected the rename's normal nonliteral-250
return. Read-only review proved the exact published size/readability and positive
partial absence. No upload or rename was repeated; the unknown exact response is
retained honestly. File/receipt publication now records the raw reply and requires
2xx plus independent publication checks; 29 focused tests passed. See
`docs/model-rename-response-20261023.md`. Continuation 024 ended before case
creation when the failed data process was absent. Data continuation 007 may bind
the reviewed first-file completion and preserve the original whole-batch deadline
while transferring the remaining files. Keep its frozen sources unchanged.
Full-plan continuation 025 may wait for that exact process's positive completion
and exit before the unchanged case 019 and all original final gates.

At the next checkpoint, data 007 ended with Windows `0xc000013a` during file 35;
34 positive files (216,633,567,072 bytes) remain reused. The incomplete
3,341,876,428-byte partial was preserved outside the model directory with a
recorded positive rename, exact size/readability and independent directory
metadata, without repeating the successful move. See
`docs/model-transfer-interruption-20261023.md`. Failed child launch and
preservation checks remain retained; none launched a title or used the GPU.

The active data continuation is now 011, with 117 frozen source/proof records,
console-free child processes, the original batch deadline and one explicitly
reviewed new upload of incomplete file 35. No successful file is resent. Keep
all frozen inputs unchanged. Full-plan continuation 029 binds that exact process
and 207 source/proof records, then waits for positive data completion and exit
before the still-unused case 019 and every original final gate. No automatic
retry, forced close, reset or uncertain GPU recovery is permitted. Inspect the
actual saved display frames before declaring the entire plan complete.

Data 011 and full-plan 029 subsequently ended before case creation when the
transfer's pre-publication guard observed a native title. Read-only reassessment
found no remaining native owner and unchanged management services/reservation.
The owner explicitly prioritized inference and authorized ordinary application
close. No close request was needed because the observed title had already exited.
Preserve the failed attempts and do not attribute that transient title to the
unlaunched Qwen candidate.

All 67 published files were retained. File 68 had a durable positive source-stream
SHA/identity/FTP/size/readability journal and no attempted rename. After a fresh
CPU admission, its first rename returned `226 Path renamed`; exact destination
size/readability and partial absence passed without reupload. See
`docs/model-transfer-owner-conflict-20261023.md`. Data continuation 012 now reuses
68 files and freezes 200 sources/proofs; full-plan continuation 036 freezes 290
and waits for positive completion/process exit before the still-unused case 019
and every original final gate. Keep those recorded inputs unchanged. The original
whole-batch deadline, driver, candidate, precision and disabled release/CI policy
are unchanged. This checkpoint does not establish full-model inference.

## Native full-model admission in progress (2026-10-23)

All 76 files and the complete receipt subsequently transferred successfully.
The original whole-batch deadline and every interruption record were retained.
Case 019 initially encountered two local publication checks before its first
SELF rename. The exclusive state writer was corrected in a distinct private
controller. A guarded 128-byte CPU file-view diagnostic proved the raw SELF
sizes and seek endpoints; FTP metadata returned different sizes. Full raw
readbacks remained mandatory. The sealed native candidate was not rebuilt.

The first native launch then rejected the model files' FTP-created mode 0777
before backend initialization. Exact source/stage evidence and the owner-bound
ordinary OS close passed; this is a failed candidate admission, not inference.
The plan-bound CPU controller in `model_file_seal.c` subsequently sealed the
76 files plus receipt to root-owned 0644. Seven host checks, 14 actual runtime
imports, all 77 positive file records, independent directory metadata and fresh
unchanged CPU observations before/after passed. Model contents were not changed.
See `docs/model-file-sealing-20261023.md`.

Case 020 uses a new run identity and the same exact candidate/model. It reuses
the original preservation from case 019, with fresh complete candidate/backup
readbacks. The original SELF remains preserved in its backup; final restoration
and numerical readmission are pending. Native whole-model SHA verification is
now progressing before backend initialization. Do not repeat it or launch another
candidate while this run continues.

Full-plan continuation 047 freezes 177 source/proof records and owns the remaining
measurement, ordinary close, original restoration/readmission and final guards.
Its GET-only observer handoff preserved the original observation deadlines and
occurred before any external generation POST; the native title and integrity
work continued. The stage reader now admits the native journal's existing 8 MiB
bound. Keep all frozen inputs unchanged, including the sealing controller and
observer sources. See `docs/native-full-model-progress-20261023.md`. Full-model
generation, displayed metrics, positive final retirement and restoration remain
unqualified until their actual terminal evidence and visual review pass.

## Reviewed native mapping exit and distinct public provider (2026-10-24)

Case 020 subsequently completed all 76 native model SHA256 checks, then exited
without a mapping completion. No backend/GPU initialization or model load was
reached. Full-plan 047 positively ended, its failure retained. Fresh CPU guards
passed with no native owner and unchanged boot/services. No ordinary OS close
was sent for the already-absent process. The original SELF remains preserved in
the original case-019 backup; final restoration/readmission remains outstanding.

The distinct case 021 may use the corrected public-mmap SELF described in
`docs/native-public-mmap-20261024.md`. Require its real libkernel mmap provider,
six-segment SELF roundtrip, unchanged pinned driver/cache policy and fresh
session/clock admission. The prior complete native SHA report may be reused only
with the bound raw evidence and newly checked unchanged sealed identities of
all model files, receipt and directory. Hold the model writer lease throughout
the native sequence. Do not repeat conversion, transfer or the full payload hash
when that explicit reuse gate passes. If any identity changes, reject reuse.
Preserve every failure and reject automatic retries. All memory, precision,
mapping, generation, display, retirement and exact original restoration gates
remain required; committed execution/deployment/release/CI controls stay disabled.

Case 021 later rejected its directory/receipt identity comparison before mapping
or backend initialization. Its exact owner was ordinarily closed and fresh idle
CPU guards passed; zero external requests were sent. Case 022 uses a distinct
SELF with actual/expected identity diagnostics and the same canonical `/data/`
model path used by the sealed management snapshot. Keep every identity field
and the original precision/memory/completion/restoration gates. Do not describe
the suspected app0 namespace difference as measured until its native identity
report is read. See the follow-up in `docs/native-public-mmap-20261024.md`.

Case 022's canonical-path configuration subsequently failed its bound file
size/open check before mapping/backend initialization, then was normally closed
with fresh idle CPU guards. Case 023 returns to the exact original app0 model
path. Its explicit private device-translation policy binds one canonical/app0
device-ID pair only after SELF/receipt SHA admission, retaining exact inode,
permissions, owners, size and all timestamps for directory, receipt and every
model file. All ten mismatch checks passed on the host. Save and read the actual
native identity and namespace reports; do not assume that translation passed.
The complete prior native SHA, unchanged sealed data, pinned driver/cache,
writer lease and all remaining physical generation/restoration requirements
remain mandatory. No other identity mismatch is relaxed or retried automatically.

## Current console hold after public file mmap (2026-10-24)

Case 023 measured exactly the device-ID namespace difference and passed all 76
unchanged sealed identities in 346 ms, reusing the prior 5,370,082-ms complete
native SHA pass. The first real public file mmap did not return within its
60-second stage bound. No mapping completion or backend initialization was
observed. A management process-list GET then timed out before any close request.
The unchanged qualified normal-close helper was subsequently invoked once with
its internal double boot/service/exact-owner guards; its transport timed out
without a returned result. Execution/acceptance and native absence are unknown.
Do not repeat that helper, launch a title/ELF/GPU work, restore an active/unknown
title target, reset/reboot, force-kill, or manually unmap/release resources.
Preserve case 023, close intent 059, and the local console-hold record 060.
The exact original SELF remains in the case-019 backup, with final restoration
and numerical readmission outstanding. Do not claim a closed/restored console.

Continue host implementation and focused verification of reserved virtual source
ranges plus bounded direct CPU/GPU reads. File-backed mmap is not qualified and
must not be repeated. Any eventual physical qualification first requires a fresh
bounded read-only state reassessment and unchanged complete CPU admission; a
host build or elapsed time never lifts this hold. Preserve original precision,
all experts/PLE, native numerical/memory/retirement gates and every final original
restoration requirement. The overall plan is not complete.

The reserved-source host implementation now compiles seven isolated overlays,
reserves no-access virtual keys and routes original CPU gathers/buffer copies
through the bounded reader. It rejects unsupported CPU source operations. The
actual original-versus-bounded CPU kernels passed 245,952 BF16/F32 scalar values,
six three-thread graphs and twelve buffer checks at widths 8/2560/7680. The
v3 policy, source/range/deadline/result checks and distinct SELF
`5c2ac4c3b9045eda2ae74e67abb262b7e757a91311e3bae024388b0574d62d13`
passed host link, six-segment roundtrip and 291 real imports. See
`docs/reserved-source-20261024.md`. The earlier host-only candidate's CPU fast
copy defect was caught before deployment and is superseded. These results do
not lift the console hold. Two later read-only reassessments returned management
responses but still found the same original owner at the unreturned public mmap.
No additional close, native execution or original restoration was performed.

## Owner-confirmed freeze and postboot restoration (2026-10-24)

The owner then confirmed that the console had frozen and unplugged/restarted it.
Fresh CPU discovery measured a different boot and no native owner. The optional
native compatibility runtime is not loaded. The historical uncertain close
remains unknown; power cycling does not turn it into a successful normal close.

Recovery-only CPU guards in `native/qwen_flash_next/recovery_guard.c` passed before
and after exact original SELF restoration. They check boot, firmware, seven
current service/system identities and no native/foreground title twice. Their
scope is inactive data-title file repair, without requiring/loading compatibility,
title execution, GPU work, payload reads or mappings. This is distinct from the
unchanged complete runtime/model admission; it does not enable inference.

The exact original SELF is now back at the title target with full pre/post raw
readback SHA256 verification. The failed case-023 SELF is preserved under a
distinct name. Current native owner count is zero. Original numerical readmission
and normal shutdown in this boot remain pending. Preserve the private restoration
083 and after-restore CPU 082 records and the console reservation.

Saved native and additional-loader wait descriptions were `pfault`; the latter's
exact helper identity is not established. The first mapping requested
3,508,767,456 bytes before full model/OS memory admission, without a completed
tiny native mapping prerequisite. Free-page starvation is the leading mechanism,
not a proved firmware-level root cause. The frozen instruction pointer, stack,
fault address and memory counters are missing. Postboot error records predate
the affected native start, and the current kernel ring cannot replace the lost
old-boot log. See `docs/freeze-forensics-20261024.md`.

Do not repeat the failed artifact, uncertain close or file-backed model mmap.
Do not reuse old-boot SHA/session/service/owner bindings after the power cycle.
The reserved-source SELF remains unexecuted. Before any future full model case,
separately qualify its tiny model-independent native memory primitive, including
pre-call memory observations and explicit return/completed-release records.
Do not describe an outer deadline as cancellation of an opaque OS operation, or
management HTTP responses as proof that the UI and recovery path remain live.
Complete runtime admission, numerical/readback/retirement and final restoration
requirements remain in force. The full plan is not complete.

Bounded postboot scalar reads also confirmed that the application's
`vm.stats.vm.v_free_count` / `vm.stats.vm.v_page_size` names are unavailable.
The PS5 vm0 free/inactive counters and `hw.pagesize` are readable, but must not be
substituted as process-available or immediately reclaimable RAM without separate
native-context qualification. Preserve the strict rejection of unknown memory.
The existing CPU/OS budget gate now runs before the tiny virtual-source probe
and range admission. The earlier reserved-source SELF predates this safeguard
and remains withheld. This gate placement fixes the demonstrated admission
ordering defect; it does not establish the old kernel's exact root cause or
qualify the replacement memory primitive.

The added guard's host-only SELF is 58,628,631 bytes at SHA256
`82b73be97f0e7123b59e44e01ce6e79d04a59e15d92e88e720c34ffed2d8fada`.
Its six-segment roundtrip and 291 public-module imports passed, and both
committed-policy checks passed. This new artifact is not deployed or physically
qualified. It must continue rejecting unsupported OS memory telemetry before
source reservation. Do not treat its build as a resolution of the old freeze.

## Recovery-first memory qualification (2026-10-24)

The owner authorized the new recovery-first plan. The current boot's unchanged
compatibility runtime and missing existing title nullfs mount were restored with
positive terminal evidence. The exact original then passed numerical readmission,
ordinary shutdown, fresh complete CPU guards and a full raw SELF readback. Keep
the old uncertain close unknown. The missing mount's first launch refusal had
zero launch calls; all failed preparation records remain preserved.

The separate `native-memory-validation` mode starts before model receipt reads,
display or any Vulkan initialization. Qualify telemetry, 16 KiB reserve/query/
release and bounded direct I/O separately, with exact current-boot owner and
artifact binding, durable results, normal OS close and fresh CPU guards after
each phase. Do not overlap phases or skip the native telemetry review. The
private phase policy cannot admit full-model memory or old-boot integrity.
Keep unsupported OS memory rejection, original precision and all final original
restoration requirements. See `docs/native-memory-qualification-20261024.md`.

Telemetry, the 16 KiB reserve/protection/release and the fixed-fixture direct
reads through 8 MiB subsequently passed on the PS5, each followed by ordinary
close and fresh complete CPU guards. All four I/O prefix hashes matched. The
exact original was then restored, numerically readmitted, normally closed and
fully read back after final CPU guards. Keep cases 118, 121, 122, 123 and 125.

The application now separates Direct-backed CPU/cache storage from Flexible
quota and raw kernel counters. Preserve the unchanged conservative Direct
requirement, 256 MiB Flexible reserve, additional 8 MiB source metadata margin,
and kernel minimum plus the larger of its reserved count or 4 MiB. Required
PS5 counter names and exact sizes must be available; never sum inactive pages
or treat vm0 as process-available RAM. Initial low kernel pages permit only
20 seconds of read-only observation before admission/rejection. This does not
cancel syscalls or qualify large model allocations. See the scoped admission
section of the same report. Full-model execution still requires actual fresh
admission, new-boot complete integrity and every final restoration gate.

The new-boot complete native SHA subsequently passed all 76 files in 5,408,068 ms.
Automatic reservation returned an error for the 102,400,507,904-byte PLE span;
all attempted calls returned before backend/GPU initialization. Ordinary close,
exact original restoration, numerical readmission, ordinary shutdown, final CPU
and full readback passed. Preserve this returned rejection separately from the
older unreturned file mmap. A new sealed-identity snapshot preserves this boot's
SHA proof; require its matching boot and all unchanged sealed identities for reuse.

Native telemetry measured unchanged `RLIMIT_AS` 2^63-1 and `RLIMIT_DATA` 32 GiB.
The replacement reserves fixed/no-overwrite source keys in [512,896) GiB,
disjoint from the pinned driver and Direct heap. Its 16 KiB native exact-address,
zero-protection, completed-release and normal-close/CPU gates passed. Never
replace occupied mappings, retry a failed primitive, release unowned ranges or
continue after a poisoned address book. Full-model simultaneous reservation,
resident memory and generation are still unqualified. See
`docs/disjoint-source-addresses-20261024.md`. Keep all final restoration gates.

The later case passed all 76 disjoint reservations/protection checks and completed
releases, bounded source-reader preflight, Vulkan initialization and pre-load
memory admission. The loader then returned a partial virtual-release ownership
rejection. Stable complete logs proved the kick worker never initialized; the
exact owner was normally closed and the original restored, numerically readmitted,
normally closed and fully verified with final CPU guards. Keep that returned
loader failure separate from model generation and from the historical freeze.

Reserved source keys carry no resident file pages. Their mmap overlay must keep
the whole protected lease through intermediate trim requests and release it once
at owner destruction. Preserve ordinary mmap fragment behavior and the native
strict complete-range ownership check. The actual patched class passed 304 trim
requests over all 76 file sizes and 76 final releases; the previous implementation
failed the same control. Six unchanged overlays are reused; only mmap is rebuilt.
See `docs/reserved-source-lifetime-20261024.md`. The next full case must freeze
its seven patches and exact overlay sources/objects as well as application inputs.

The corrected lifetime artifact subsequently loaded the complete model and passed
positive device idle/completion checkpoint, then returned the post-load headroom
refusal before generation. Its owner normally closed; exact original restoration,
numerical readmission, normal close, final CPU and full readback passed. Preserve
this positive load separately from context/cache admission and tokens/s.

The pinned PS5 Mesa budget source duplicates driver bytes into two counters later
summed on the APU. Keep raw Vulkan estimates diagnostic. Client allocation
admission now requires the actual canary-validated native Direct allocator,
matching device/pool totals, two lower free samples, stable healthy known owner
snapshots and free<=pool-owned. Do not compute availability as nominal pool minus
use, subtract owned bytes twice, reduce the unchanged reserves or accept unknown
queries. No shared-driver/archive/kernel change was made. The actual observation
function passed 29 strict host cases. Save post-load native and raw Vulkan values.
See `docs/native-allocator-admission-20261024.md`; all final full-plan gates remain.

The next artifact positively loaded the model, admitted native Direct capacity,
and returned from context creation before the CPU/Flexible guard refused it.
The full stable driver log had no worker initialization. Normal close, exact
original restoration, numerical readmission, normal close, final CPU and full
readback passed. Its generic error did not preserve the exact rejecting value.
Keep the new separate post-load/post-context reports and numeric rejection values.

The nominal-capacity scheduler metadata allocation exceeds the unchanged CPU
heap limit. Its replacement uses a fixed 192 MiB arena and checks the complete
active graph with actual aligned tensor/graph overhead before constructing
copies. Keep the original graph/hash capacities and every model node. Require
one serialized copy; reject overflow/empty/oversized graphs without truncation.
The actual GGML metadata allocator and three complete 7,184-node CPU fixture
graphs passed; see `docs/native-scheduler-memory-20261024.md`. The diagnostic-only
case was superseded before launch. Real generation and all final gates remain.

The fixed-arena artifact subsequently admitted the real context/cache and CPU
memory, then returned its single-buffer-scope refusal during the first decode,
before any worker initialization or completed token. Exact ordinary shutdown,
original restoration, numerical readmission, normal close, final CPU/full readback
passed. See `docs/native-source-row-scheduling-20261024.md`. Keep detailed numeric
buffer failure messages and the unchanged 512 MiB/aggregate/workspace limits.

Protected model-source GET_ROWS must select the admitted bounded CPU row kernel
and compatible output buffer before ordinary GPU offload selection. The source
key is not a resident host table. Never copy the full embedding tensor to GPU or
dereference the protected source. Preserve ordinary resident-host offload and
GPU matrix placement. The actual scheduler's simulated-device control and
protected-source selection passed, without model payload reads/GPU execution;
real full-model generation and all final complete-plan gates remain required.

The row-selection artifact returned an exact 1,677,787,532-byte post-load request
against the unchanged 512 MiB per-buffer limit before first decode completion.
Complete stable logs show 48 cached layers/53 slots and no worker initialization.
Normal close, original restoration/numerical readmission/normal close and final
CPU/full readback passed. Keep cache construction separate from measured use.
See `docs/native-cache-copy-admission-20261024.md`.

The scheduler must reject complete copies of protected source tensors before
creating the copy, naming the source/consumer/operator/size. Required expert-cache
bindings must be present. Cache eligibility/backend-query records are once per
layer, bounded independently of request/token count. Preserve bounded row/expert
uploads, GPU matrix placement, every existing budget and all final full-plan gates.

The guard subsequently named final-layer `blk.47.ffn_gate_exps.weight` as the
1,677,721,600-byte complete source copy during the first prefill token. The
single-token adapter must request one output for each prompt batch. Zero output
crops the final Qwen layer to zero rows and bypasses cache eligibility, as
reproduced by actual GGML cropping and the actual cache method. Sample only the
last prompt token's logits. Keep the source-copy rejection and all budgets.
The corrected adapter regression passes; the previous adapter fails it. See
`docs/native-prefill-output-20261024.md`; full physical inference remains required.

The one-output artifact completed one physical input-token decode, synchronization,
positive device idle and completed-worker-epoch retirement at epoch 2058. Its following CPU
guard rejected 385941504 mapped/peak bytes against the unchanged 376438784 limit,
with zero libc fallbacks. Ordinary close, exact original restoration, numerical
readmission, normal close, final CPU and full original readback all passed.
This is not completed prefill, a sampled output token or a tokens/s qualification.

The qualified scheduler scratch arena is now 160 MiB, superseding the earlier
192 MiB initial size. Its actual GGML metadata bound remains 158936784 bytes inside
167772160; all complete graph/copy checks and original CPU/Direct/Flexible/kernel
reserves remain unchanged. Three complete 7184-node CPU graphs / 48 exact values and
protected-source controls passed. See `docs/native-compact-scheduler-20261024.md`.
Finish every full-plan physical gate before reporting completion.

The compact artifact completed physical arithmetic generation: output `4`, 26 prompt
tokens, TTFT 91023.55 ms, total 94619.27 ms and successful reset. This single output has
no decode-rate interval. Native model-resident display completed. External request 1
then failed CPU admission before its first GPU boundary; it was never retried.
Normal close, exact original restoration, numerical readmission, normal close,
final CPU and full original SELF readback passed.

Scope v4 supersedes the earlier 359 MiB derived heap allowance. The total planned
CPU budget remains 512 MiB and the full resident requirement remains 12110548480.
Protected source keys have zero extra resident file pages; the logical 160432128-byte
address allowance must not be subtracted again from the tracked physical heap.
The 512 MiB heap cap includes the 8 MiB Direct source window, whose native heap
ownership is now mandatory. Keep zero libc fallbacks, zero file-backed model mmap,
protected keys, every Direct/Flexible/kernel/platform/device reserve and limit.
The actual separate Flexible/kernel fields replace the retired OS_free_bytes
aggregate in host verification. See docs/native-physical-CPU-accounting-20261024.md.

Failed API execution must emit a bounded failed terminal event while retaining
uncertain GPU resources, stop its listener and propagate the original error.
The once-only client distinguishes that event from empty/disconnected uncertainty;
neither permits an automatic inference retry. Successful two-request and failure
transport/client controls passed without a model. Complete all physical gates.

## Complete physical plan: 2026-10-24

The scope-v4 artifact at source 701f474cb8ca94dae5c854f080f3ec972d0d0c26 and SELF
cb775555fd7423738cc6ef53efa760362c8b1c384ef2574b5b5797295bccbb3b passed the complete
plan. One physical PS5 generated arithmetic `4`, then two external counting
responses with 22 tokens each at 0.2845483641 / 0.2888186108 tokens/s. Actual native
frames were viewed. Positive GPU/resource retirement, ordinary close, exact
original restoration, numerical readmission, ordinary shutdown, final CPU guards
and full original SELF readback all passed; the finite parent ended normally.
No native owner or loaded model remains. See
docs/native-full-generation-success-20261024.md and its sanitized JSON.

This supersedes earlier pending full-plan status, without changing failed or
uncertain historical evidence. Do not rerun the completed sequence. General
inference/release deployment and CI remain disabled, persistent shader/pipeline
caches remain disabled, and the task's console reservation remains held.
The three short thinking-disabled requests qualify finite original-precision
generation, not broad answer quality, long context or sustained service. Keep
unknown CPU/GPU utilization unavailable and raw GPU memory estimates diagnostic.

## Performance continuation

The owner subsequently authorized speed improvement. Preserve the completed
original-precision result as the control and use distinct candidate identities;
never replay its completed launch or POST intents. Follow
docs/performance-20261024.md. Start with aggregate wall-time profiling of source
reads, consumers and decode boundaries, without new GPU operations, changed
precision, larger memory budgets or relaxed completion checks. The profile-only
session is intermediate evidence, not completion of the requested speed work.
Keep the qualified driver/archive and persistent-cache policy unchanged while
isolating application costs. Require actual matched outputs/performance and the
same positive retirement, normal-close and original-restoration boundary after
each physical candidate. No delegation was authorized.

The subsequent two-read candidate at source f74eddd completed arithmetic but
increased direct-read wall time from 81.865 to 237.555 seconds. Its first external
request explicitly failed the unchanged kernel headroom predicate. No request
was retried. Its ordinary OS close, exact original restoration, numerical
readmission, ordinary shutdown, final CPU and whole SELF checks passed. See
docs/source-concurrency-refusal-20261024.md. Never replay that candidate.
The next source pipeline must permit at most one outstanding read, overlap only
CPU I/O with synchronous producer consumption, and retain every uncertain
read/consumer lease. Preserve the 8 MiB source window, every reserve, original
precision and selected driver. Host overlap checks do not qualify speedup.

The first single-read candidate completed 26 prefill decodes and its first sample,
including positive device idle/worker completion, then refused kernel headroom
before the next work boundary. It did not finish a request or issue an external
POST. Exact original restoration/readmission/shutdown and all final checks passed.
See docs/source-pipeline-refusal-20261024.json. The next memory admission policy
may passively observe OS recovery only at completed producer/unissued-read
boundaries, with 100 ms polls, a 2 s boundary limit and a 10 s whole-process wait
limit. Every continuation must satisfy the unchanged original memory predicate.
No I/O/GPU/inference retry, reclamation or reserve reduction is allowed. Failed
admission remains quarantined; physical speed qualification is still pending.

A subsequent CPU-only refusal observed 1,064 kernel free pages before any source
reservation, I/O worker or Vulkan initialization; the required count was 1,154.
Its ordinary close, original restoration, fresh CPU and full SELF checks passed,
preserving the same-boot preceding numerical original admission. See
docs/pre-worker-memory-refusal-20261024.json. Enable bounded admission after the
once-only CPU runtime admission and before model metadata, and guard every
completed metadata-file read. Keep the original predicate/observer bodies and
the existing 2 s / 10 s limits unchanged. Do not replay the consumed attempt.

The early-admission artifact at df8c26c completed arithmetic and API1, then
refused kernel headroom after API2 prefill/first sampling. Two pressure events
recovered; the third exhausted the 2 s boundary allowance, with 3.302 s total
waited. Its normal close and full original restoration/readmission/shutdown/final
checks passed. See docs/bounded-memory-refusal-20261024.json. The subsequent v2
policy supersedes the earlier wait constants with 20 s per completed boundary
and 60 s cumulatively, keeping 100 ms observations and every original memory
predicate/reserve. This changes waiting time only. Never retry I/O, inference or
GPU work, release uncertain resources, or report speedup before all physical
gates complete. Preserve the failed artifact and its consumed intents.

## Completed bounded source-pipeline performance pass

The artifact at source 86b645623f3de13fd49ad6e2b295565219729be7 and SELF
24cd22bbba24223eab5be01412294c33a83a4d5a380cd028acd66dec1983e344 completed the
entire physical plan: exact arithmetic output 4, two identical counting answers/22 tokens,
actual native frame review, positive model/GPU/source/worker retirement, ordinary
close, exact original restoration, numerical readmission, ordinary shutdown,
fresh final CPU and whole original SELF readback. The finite parent ended
normally with all frozen inputs unchanged, zero native owners/models/fallbacks.
CPU/device peaks stayed 436273152 / 945815552 bytes. One pressure event recovered
after 0.400 s under the unchanged predicate and v2 wait bounds.

The two decode rates were 0.285184 / 0.289577 tokens/s. Mean observed gain is 0.82%
against the profile control and 0.24% against the older functional control. This
small fixed-request result does not establish statistical significance or a
general throughput improvement. See docs/source-pipeline-success-20261024.json
and docs/performance-20261024.md. This supersedes pending performance-plan status,
without erasing failed candidates. Never replay completed launches/POST intents.
Keep the reservation held, every memory/precision/driver/cache policy unchanged,
and release/CI disabled. Use tools/check_source_pipeline.py for reproducible
focused host checks; host checks alone never admit a console launch.

## Source-contention cause investigation

The owner subsequently requested identifying the internal cause of the rejected
two-read regression. Isolated physical CPU controls, including the application's
exact C++ executor, did not reproduce it. Supported PID sampling observed native
filesystem wait-channel names; those names alone do not prove the target cause.
The original title remains unchanged, restored and idle after these CPU controls.
See docs/source-contention-investigation-20261024.md. Preserve failed queries and
pre-read refusals separately from completed comparisons.

A distinct explicit private diagnostic may record 32 completed source pairs at
interval 512 across the real arithmetic request and replay that exact finite
trace after output 4 and fresh positive GPU completion. Reuse the existing 8 MiB
source lease, one persistent worker and at most eight reader descriptors. Only
this diagnostic permits two outstanding reads; production read_pair stays rejected
and the normal pipeline stays limited to one. Keep every original budget, memory
predicate/reserve, v2 passive-wait bound, precision, driver and cache policy.
Unknown reads retain their owner/backing; no retries or speculative release.
Native link/import/SELF and focused lease/failure controls must pass first. The
new case still requires the complete three-request/frame/positive-retirement and
ordinary-close/original-restoration/readmission/shutdown/final verification plan.
This is diagnosis, not permission to replay the rejected full-model candidate.

The completed trace diagnostic at native source de84978 and SELF
09d87b0ddb6c5bcff3072da5c72e857543fab5021275d5fde15298cb773e61bb passed the
whole physical plan, including both 22-token external responses, actual frames,
positive retirement, normal close, exact original restoration/readmission/close,
fresh final CPU and complete original SELF readback. Its parent positively ended
and all 194 frozen inputs were verified unchanged. Do not replay it.

Subsequent finite CPU-only interventions isolate same-file cross-region BFS I/O
waiting: about 49 ms parallel versus 10 ms serial across approximately 1 GiB
offset regions. Independent opens do not fix it; different files cost about
7 ms parallel. A second source file reproduces it. Completed loaded-native pairs
show the same trigger, with 7 of 32 pairs slow. The GPU is not required. Internal
mapping-state contention is an inference; proprietary lock/cache implementation
and exact boundary safety remain unproven. The metadata API returned zero wait
addresses, so it does not establish shared wait-object identity.

See docs/source-contention-investigation-20261024.md and
docs/ps5-source-io-workarounds-20261024.md. Original title remains restored/idle,
with no loaded model or native owner. Keep one production read, unchanged
precision/budgets/reserves/driver/cache policy and the held reservation. Selective
file/range scheduling is the next candidate, not an admitted production change.
Do not copy LVD image-only BFS batching or cache hints into ordinary pread by
analogy. Keep CI and general release/console flags disabled.

## File/range source candidate authorization

The owner subsequently instructed implementing and physically comparing the
proposed source-bandwidth improvements. A distinct private first-generation
candidate may enable the file/range schedule after the completed CPU-only
qualification and fresh pre-backend exact-byte controls. It may use two reads
only for complete aligned extents inset by 4 MiB from a 1 GiB region boundary;
same-inode pairs must remain in the same region and both files must share the
qualified device. All other pairs keep the one-read consumer pipeline. Adjacent
original bytes may share a single read inside the existing 8 MiB window, with
their original separate cache destinations and positive consumer completion.

The completed CPU qualification exercised sequential 4/8 MiB reads, the actual
C++ range selector, both inset edges, crossing extents and the second file.
Normal 8 MiB reads measured about 0.82 GB/s in the CPU helper; selected parallel
pairs about 0.94..0.96 GB/s. This is not a native-inference speed qualification.
Expert sorting already exists; do not claim reimplementing it as an improvement.
No file layout, model payload, driver, persistent-cache policy, memory budget or
reserve change is part of this candidate. Require the complete matched native
three-request/frame/retirement/ordinary-close/original-restoration/readmission/
shutdown/final verification sequence. Keep every consumed intent and failed
artifact; no automatic retry or release of uncertain work is permitted.

The first selected-source artifact at 2c7b39d / SELF
92f83670e9f8e110d6ad97aa452f095c3fc4ae1e13acc05ee7f53076263a34d0 refused
kernel headroom during sealed-file metadata checks, before source reservation,
worker creation, Vulkan or model load. It issued no generation POST. Initial
kernel free pages were 2140 and the final refusal reported 1089 versus the
unchanged 1154 requirement. Its known pre-GPU fatal state was normally closed;
exact original restoration, full readback and fresh idle CPU checks passed.
The same-boot preceding numerical original admission was preserved without a
new GPU launch. Keep this failed case and do not replay its artifact or intents.

A distinct candidate adds stronger startup admission at the observed kernel
free target before model metadata. It shares the existing 100 ms / 20 s boundary /
60 s process wait budget and leaves the original work-boundary predicate intact.
A finite metadata-only root gate must first observe target + 1024 free pages
for ten consecutive 100 ms observations before publication/launch. No allocation,
source read, reclamation, reserve reduction or GPU operation is part of that gate.

The stronger-startup artifact at 7eec254 / SELF
9c095fafa9fa2f0e836b0373153039279dadab8055d2e9da583154ecd2e2a939 also refused
before metadata/source/Vulkan: native free pages remained 1418 below target2974
despite root prelaunch observations5607..5608. Its parent ended with all202
inputs unchanged; normal close, exact original restoration/readback and fresh
idle CPU passed. Preserve the preceding original numerical421 proof and this
CPU-only refusal. Do not replay the consumed artifact or intents.

The next distinct candidate replaces only its startup SELF/receipt verification
with exact full-file SHA256 over a fixed aligned1MiB O_DIRECT tracked-heap buffer.
This tests whether the previous buffered107MB SELF scan consumes kernel cache;
that attribution is not yet measured. Preserve all bytes/digests, stable fd
identity before/after, exact EOF-tail counts, deadlines and no retry. Failed or
unknown reads retain fd/buffer; only positive SHA/identity/close releases them.
Record native memory before/after startup integrity. The original predicate,
stronger startup target, wait limits, model integrity reuse and driver remain.

The Direct-startup artifact at ff46289 refused its newly added startup file
permission test before any complete integrity scan, model or GPU work. Read-only
FTP metadata of the preserved candidate confirms a regular file with mode0777,
the existing publication mode. Its parent ended with all206 inputs unchanged;
normal close, exact original restoration/readback and fresh idle CPU passed.
See docs/source-schedule-startup-refusals-20261024.json. Do not replay it.
A distinct correction accepts the existing startup publication permissions while
preserving nonempty regular-file admission, the complete SHA256, stable descriptor
identity and exclusive writer lease. Model-source permission guards stay intact.
This fixes an introduced startup restriction; it does not qualify cache pressure
as the cause of the earlier headroom failures or establish an inference speedup.

The subsequent publication-mode correction was built and packaged, but its
prelaunch root high-water observation refused before publication or title launch:
free pages stayed1624..1626 below the additional3998 requirement. All206 parent
inputs remained unchanged; the original title was never modified and fresh idle
CPU guards passed. The unused native SELF has not consumed a title-launch intent.
Root target+1024 is an added experimental gate, separate from the original
minimum+reserve requirement and from the stronger in-title startup target.
Because root high-water observations did not predict native headroom in either
direction, the next distinct case uses the original qualified minimum+reserve
predicate for ten prelaunch observations. Keep the stronger actual native target
before metadata, every work-boundary predicate, all reserves and wait limits.
Native Direct integrity memory observations must precede any decision about
metadata/model/GPU execution. This supersedes only the experimental root3998
requirement; it does not permit a replay of a consumed launch or GPU operation.

The correction subsequently ran once and passed Direct full startup SHA256,
all76 sealed metadata checks and selected-source CPU qualification. The original
virtual rehearsal also completed all76 reservations/releases. Free pages were
2982 before that interval and1195 afterwards; the isolated OS allocation cause
is not proved. Model loading then cancelled on free1091 below the unchanged1154
predicate after20s. Driver allocation calls had returned; stable owned logs showed
the retained resource graph. No generation POST or inference completed. The parent
ended with all206 inputs unchanged. Normal close, exact original restoration,
fresh numerical admission, ordinary shutdown, final CPU and full SELF passed.
See docs/source-schedule-load-refusal-20261024.json. Never replay this native SELF.

Keep executing the actual whole virtual rehearsal in every next candidate.
Do not substitute historical mapping evidence for current reservation admission.
The next distinct candidate requires the existing native startup target again
after all rehearsal reservations/releases positively complete and before driver
initialization. Share the unchanged20s/60s passive wait budget, record the immediate
post-probe memory before waiting, and retain every original work predicate/reserve.
No eviction, reclamation, allocation retry or uncertain resource release is allowed.

The post-probe target candidate subsequently refused before Vulkan after the
completed16KiB qualification and all76 model reservations/releases. Immediate
free pages were1849 and the final20s observation1843 below target2974. Its parent
ended with all206 frozen inputs unchanged; normal close, exact original readback
and fresh idle CPU passed. Do not replay it. Root CPU controls did not reproduce
the large native decrease, including holding all original spans concurrently.
Keep the actual whole rehearsal; no historical substitution is admitted.

The owner's subsequent physical-file-splitting question prompted a bounded
exact-byte control. Two16MiB original fragments were copied outside the sealed
model directory and fully read back. All192 serial/parallel pairs passed complete
returned-byte SHA256 using the actual executor and unchanged8MiB window. Mean
original parallel/serial times were50.6867/9.9807ms; split parallel7.0580ms.
See docs/source-split-cpu-20261024.md and JSON. This is CPU I/O evidence, separate
from full512MiB layout qualification and native inference performance.

A distinct explicit native CPU diagnostic may record at most2048 memory/time
samples immediately before/after actual durable stage writes during the unchanged
whole reservation rehearsal. It must stop before source-worker or Vulkan setup,
publish an independently checked CPU report, then await ordinary OS close.
Require native link/import/SELF and actual-bootstrap overflow/counter/short-write
controls, fresh ownership guards, exact original restoration and final idle CPU.
Preserve the same-boot preceding original numerical admission after this CPU-only
case. Normal modes keep sampling disabled and retain every durable stage write.
This diagnostic is intermediate work, not completion of the performance plan.

The native CPU diagnostic subsequently completed all current model reservations
and releases,1227 valid stage samples, normal close, exact original readback and
fresh final idle CPU. Its parent ended with all191 frozen inputs unchanged.
Net free-page decrease was2113:2109 inside durable-stage intervals and4 between
them. The measured interval includes observation overhead; proprietary allocation
behavior is not identified. See docs/native-stage-memory-20261024.json.

The next distinct intervention preserves complete line content, the1024-byte
bound and fsync before returning from every durable stage, while copying the
line and newline to one fixed1025-byte stack buffer and issuing one write.
Actual-bootstrap controls must check exact output bytes, maximum line length,
short-write retention, counter failure and sample capacity. Repeat the CPU-only
native diagnostic before considering full-model performance qualification.

The single-stack-write intervention completed all76 current reservations/releases
and1227 valid observations, normal close, exact original restoration/readback and
fresh final idle CPU. Its parent ended with191 frozen inputs unchanged. Stage
interval time fell2.857803 ->1.984434s; net free-page decrease was1780 versus2113
in the preceding case. Final1481 pages remain below the stronger2974 target.
Do not treat this as a solved memory cause or native performance qualification.
See docs/native-stage-memory-single-write-20261024.json. A preceding host-only
context-binding refusal issued no console helper, publication or title launch;
preserve it separately from the completed native comparison.

The next distinct CPU-only diagnostic may separate the exact write and fsync
observations and add a fixed2ms idle observation before each unchanged durable
stage. This distinguishes time-correlated background effects from I/O intervals.
Keep the full current reservation rehearsal, every complete stage and fsync,
bounded2048 samples, no retries, ordinary close and exact restoration. Normal
modes keep the sampler and idle delay disabled. Require actual-bootstrap controls
for middle-counter, idle and fsync failures as well as existing bounds/retention.

The split-interval diagnostic completed all76 model reservations/releases and1227
valid observations, normal close, exact original restoration/readback and final
idle CPU. Its parent ended with191 unchanged inputs. Free pages4703 ->1633:
matched idle2783 decrease/2.581102s, write1020/0.948515s, fsync734 increase/0.921029s,
between intervals1 decrease. Journal I/O alone is not supported as the cause.
Read-only root VM metadata passed with free6031, target2974, minimum898,
reserved206, active29150, inactive72528, wired31030, total138739 and page16384.
See docs/native-stage-memory-split-20261024.json. Never count inactive pages as
available or lower any memory predicate/reserve based on these observations.

A distinct CPU-only diagnostic may add canary-checked free/active/inactive/wired
population snapshots before/after the unchanged whole rehearsal and after two
seconds of completed idle. These sequential counters classify page movement;
they never authorize reclaim, additional I/O/GPU work, or a reserve substitution.
Preserve all existing bounded samples, actual reservations, durable stages,
normal-close/restoration gates and the original numerical same-boot proof.

The native population diagnostic completed all76 current reservations/releases,
1227 valid stage samples and normal close/exact original restoration/final idle
CPU. Its parent ended with192 unchanged frozen inputs. During the rehearsal:
free3292 ->1580, inactive70735 ->72449, active28678 ->28610, wired36034 ->36100.
Two more idle seconds left free1580. These sequential categories support page
movement toward inactive memory, but do not identify the backing object or prove
GGUF read-ahead as its cause. See docs/native-VM-population-20261024.json.

A distinct CPU-only intervention may use the pinned original GGUF callback
parser over a fixed aligned1MiB Direct metadata cache, retaining exact original
file sizes and ten-field sealed identities. Keep every BF16/F32/PLE/tensor-span
check and full current reservation rehearsal. When the existing8MiB source
window is active, borrow that exclusively with its idle worker and descriptor
cache; do not add a second payload buffer or exceed eight source descriptors.
Failures retain descriptor/window/lease with no retry or buffered fallback.
Require all76 original GGUF serialized-metadata and GGML-context host parity,
window/EOF/failure/lease controls, actual PS5 compile/link/import/SELF checks and
the normal-close/exact-restoration/final CPU sequence before GPU qualification.
No model bytes, file layout, precision, driver/cache policy, heap budget, memory
predicate/reserve or passive wait bound is changed by this intervention.

The Direct metadata CPU intervention completed all76 sealed originals with86
physical reads/90177536 bytes, all76 current reservations/releases and1227 valid
samples. Normal close/exact original restoration/final CPU and positive parent
termination with195 unchanged inputs passed. Free3922 ->2227; inactive70220
->71937; wired36077 ->36106. The memory problem remains unresolved. Do not claim
buffered GGUF metadata alone as its cause or enable this path as a measured
performance improvement. See docs/native-direct-metadata-20261024.json.

A distinct CPU-only phase control may observe five seconds without journal
writes, then at most256 clearly labeled synthetic journal-only lines with2ms
idle and no source operations. Before each line retain the original predicate
plus512 extra kernel pages; stop only at a completed boundary. Save the finite
phase report, then require the unchanged stronger startup target before the
actual whole reservation rehearsal. A refusal there is pre-GPU evidence and
must normally close/restore; it never admits skipping or replacing the rehearsal.
The normal application keeps this optional control disabled. Keep every original
reserve/budget/precision/driver/cache policy and the existing20s/60s wait limits.

The CPU phase control subsequently lost3628 free pages during five seconds
without journal writes or reservations. Its next256 journal-only lines changed
none of the sampled populations. The unchanged2974-page target refused before
the actual rehearsal. The controller's failure-record collision bypassed cleanup;
separately reviewed ordinary close, exact original restoration/full readback and
fresh idle CPU subsequently passed, preserving same-boot numerical admission.
Never replay this case. Every next controller must bind all six actual cleanup
and four actual exception-path controls to its final source before execution.
See docs/native-CPU-phase-20261024.json.

A distinct application-footprint experiment may losslessly store all original
embedded SPIR-V resources. Require full source/compiled-archive byte parity,
complete lookup-table provenance, all-resource CPU SHA256/length and relocation
verification before Vulkan, bounded tracked Direct decoder storage, native ABI
qualification, actual linked CreateShaderModule input-copy lifetime evidence,
positive lease completion and quarantine without retry on uncertainty. Keep the
driver, model precision, all original memory predicates/reserves, real whole
rehearsal, wait limits and persistent caches unchanged. Host checks precede one
distinct CPU-only native case with ordinary close/exact restoration/final CPU;
full native inference remains a separate complete qualification. See
docs/lossless-shader-storage.md. This does not establish the memory cause or
authorize relaxing a failed guard.

The first lossless shader CPU case passed all1527 original byte checks and382
lookups on the physical PS5. Quiet free pages2954 ->2950 over five seconds;
next256 journal-only lines changed none of the VM populations. The unchanged
2974-page target refused at2930 before the actual rehearsal/Vulkan. Its hardened
controller normally closed/restored the exact original/full readback/final CPU;
parent exit and378 unchanged inputs passed. Never replay this SELF. See
docs/native-shader-storage-CPU-20261024.json. A distinct representation may add
reversible word-byte ordering and exact stored-byte aliases, preserving every
original SHA256/name/lookup and all prior guards. Charge its one extra maximum-
shader buffer to the existing tracked heap and repeat the actual-codec and
distinct native CPU gates before full inference qualification.

The reordered shader representation passed all1527 original byte checks and382
lookups on the PS5 at SELF1f027d73a095194f1de48ca55b7e96b863e77ed67f96cdfb81f776a8e1bde17b.
The unchanged target refused at2021 before the actual rehearsal. Its normal
close/exact restoration/full readback/final idle CPU and378 unchanged parent
inputs passed. This full shader-byte result is valid data evidence, separate
from the failed later memory admission. Never replay the consumed case. See
docs/native-shader-ordering-CPU-20261024.json.

A distinct optional CPU startup profile may reuse only those immutable shader
bytes after exact prior owner/run/report SHA, same-boot, same encoded resources
and unchanged per-use decoder/completion provenance. Keep complete current SELF
SHA256, every current lookup relocation check, and full original SHA256 of every
used compressed shader frame before CreateShaderModule. The CPU report must say
which assets were verified in this run and which came from prior data evidence.
This never permits reusing OS mappings or skipping the actual current whole
rehearsal, reducing2974/1154-page predicates/reserves, or enabling persistent
caches. Require actual-codec and prior-evidence refusal controls, native import/
SELF gates and a distinct bounded CPU case with ordinary close/exact restoration/
final CPU before considering a separate finite full inference case.

The prior-byte/on-demand CPU case passed current SELF/prior-report SHA and382
current lookups, without decoding unused shaders. It still lost1968 free pages
during five quiet seconds and refused at1401 before current virtual reservations.
Normal close/exact restoration/full readback/final CPU and382 unchanged inputs
passed. Do not replay the case or attribute the decrease to unused shader decode.
See docs/native-shader-JIT-CPU-20261024.json.

A distinct standalone CPU SELF-read control may stop before all shader/model
metadata, virtual reservations and Vulkan. Its explicit Direct/buffered modes
must preserve complete current SELF SHA256, stable descriptor identity, the
aligned1MiB tracked buffer, exact returned EOF bytes and fixed deadline. Require
the original memory predicate before every new read, paired durable native-read
markers, a bounded five-second VM observation, an explicit SELF-only completion
report, ordinary close/exact original restoration/final CPU and actual controller
unknown-read/failure controls. This does not admit model execution or bypass its
unchanged2974/1154-page gates, actual whole rehearsal, reserves or cache policy.

The standalone SELF Direct control completed all37 reads/full SHA and a five-
second quiet observation: free4728 ->2994, wired34406 ->36147. The buffered
control returned25 reads before the original predicate refused the next read,
with no pending read. Both normally closed/restored the exact original/full
readback/final CPU and ended with382 unchanged inputs. Do not retry buffered
reads or count its SELF hash complete. See docs/native-SELF-read-controls-20261024.json.

A distinct Direct SELF control may compare the optional streamed binary readback
transport using the exact positively completed native binary. Preserve complete
raw byte-count/SHA verification, observed absence before fresh upload, positive
FTP completion, exact full readback before publication, no overwrite of retained
partials and no retry/fallback after uncertainty. The transport changes no native
I/O mode, model/GPU guard or source reservation. Require its host fault controls,
new finite case, frozen inputs and normal-close/exact-restoration/final CPU gates;
do not claim memory or tokens/s benefit from host tests.

The first optional FTP readback was refused before publication/title launch
because the returned length exceeded the raw SELF bound. ftpsrv enables per-
connection SELF-to-ELF extraction by default. Preserve that failed pending file;
do not retry its operation or accept extracted ELF bytes. Every new raw RETR
connection must send SELF once and require the exact disabled acknowledgement
before any RETR. Refuse unknown mode responses, preserve transfer exceptions,
retain partials and require unchanged complete raw byte-count/SHA checks. The
untouched original/full readback/fresh final CPU passed after parent termination.
This is transport correctness evidence, not native memory or throughput evidence.

The corrected raw FTP control subsequently completed full binary publication and
ordinary title launch, but the original memory predicate refused before the first
SELF read (the preceding sample had1064 free pages versus1154 required). No model
metadata, source reservations, worker or Vulkan call began. Ordinary close, full
raw original restoration/final idle CPU and385 unchanged parent inputs passed.
Do not adopt FTP binary readbacks as a memory or performance improvement.

A distinct full inference qualification may use the same standalone-Direct-
qualified native binary with the previously qualified HTTP binary transport.
Retain current SELF/receipt SHA, same-boot all1527 shader-byte evidence, current
382 lookups and per-used-module full original SHA256. The original2974-page
startup predicates before metadata and after the actual whole current reservation
rehearsal remain mandatory, as does1154 before work. CPU-only controls must be
disabled explicitly in this full policy. Require all three fixed requests, two
actual native frames, positive module/GPU/model retirement, ordinary close,
exact original restoration/fresh numerical readmission/close/final idle CPU and
full readback before claiming completion or throughput improvement. A pre-GPU
refusal requires the final-source known-idle/exception controls and ordinary
restoration; unknown calls or any unretired GPU work must remain retained.

Production Direct startup integrity now promotes the existing physically
qualified CPU-control predicate to every read. Exact source comparison confirms
this is the sole provider change: SHA256, stable identity, aligned1MiB window,
EOF, deadlines and retained failures are unchanged. Full inference must relink
this stricter provider and pass its focused stream/native compile plus normal
link/import/SELF checks. The shader decoder, model I/O and pinned driver objects
remain unchanged; their existing positive evidence remains data evidence.

That complete candidate subsequently refused before Vulkan at2898 free pages
against2974 after all76 current reservations/releases. Normal close, exact
original restoration/full readback/final idle CPU and392 unchanged inputs passed.
Do not replay the consumed case or lower its memory target.

A distinct bounded lossless resource representation may group instruction headers
and the first16 operand columns, retain long literal tails verbatim, and encode
column differences reversibly. Require all original bytes/SHA256/lookups and the
actual-codec malformed-span, length, heap-canary, ownership and native ABI gates.
Charge its additional four ordering-buffer bytes to the existing tracked heap.
Repeat a distinct CPU-only all-resource native qualification with ordinary close,
exact restoration and final idle CPU before separate complete inference work.
Keep every current rehearsal, memory predicate/reserve, wait, precision, pinned
driver and disabled persistent-cache policy. Host storage savings do not prove
native free-page headroom, proprietary cache behavior or inference throughput.

The first column case refused the original minimum/reserve predicate after
complete current SELF/receipt integrity and before shader initialization. Normal
close/exact original restoration/full readback/final idle CPU and381 unchanged
inputs passed. No current shader-byte or whole-rehearsal qualification resulted.
The next distinct binary may connect only shader initialization's completed
startup boundary to the existing passive admission controller. Keep its exact
predicate,20s/60s bounds,100ms polls and failed-admission quarantine, and allocate
no codec storage while waiting. Require actual codec recovery, persistent refusal,
invalid-counter and native compile checks. This is no authorization to lower the
stronger2974-page targets, skip current reservations or repeat a consumed case.

The corrected initialization case passed all1527 current original shader bytes
and382 lookups, then refused the unchanged stronger target at1412 before model
metadata/current reservations. Exact original restoration/full readback/final CPU
and381 unchanged inputs passed. See docs/native-shader-columns-CPU-20261024.json.
Keep that positive data gate separate from full native memory/performance
qualification; do not replay the consumed case.

The bounded descriptor read-ahead control passed384 complete returned-byte hashes,
exact status changes, worker/Direct retirement and fresh idle guards. The accepted
hint did not improve the measured source path; do not enable it as an optimization.
See docs/source-read-hint-cpu-20261024.json. The read-only vm.objects API was
unavailable, so it supplies no backing-object diagnosis. Safe link folding saved
only503432 bytes offline and was not adopted. Preserve all original guards.

A distinct application may move the unchanged compressed original SPIR-V pool
to one immutable, SHA256-named application resource. Its24-byte descriptors must
retain every original shader name, length, digest and lookup relocation. Charge
the single49152-byte aligned input window to the existing tracked Direct CPU
heap and use one read-only resource descriptor, separate from the unchanged
8MiB model-source window and eight model-source descriptors. Require current
full resource SHA256, stable identity, exact EOF/read bounds, paired durable read
markers and quarantine without retries on unknown or failed reads. This resource
contains original SPIR-V bytes; persistent compiled caches remain disabled.

Publication must preserve the original executable and configuration until exact
resource readback succeeds. Use a fresh transaction, observed absence before a
new pending upload, positive rename acknowledgement and complete raw byte-count/
SHA256 readback; reuse existing data only after the same complete verification.
Retain mismatches, partials and unknown acknowledgements without overwrite,
deletion or retry. Require actual publication fault controls and final-source
cleanup controls that distinguish pending shader reads from completed CPU idle.
After host/native link/import/SELF gates, a distinct CPU-only case must verify
all1527 current shaders,382 lookups and all76 current reservations/releases with
normal close/exact restoration/final idle CPU. A separate complete native run
must still pass both2974-page startup gates and every numerical, frame, retirement
and original-app restoration gate before reporting a throughput improvement.

The first external-resource CPU launch refused the original minimum/reserve
predicate before its first startup integrity read. Its preceding sample had1066
free pages versus1154 required. No current shader-byte or whole-rehearsal result
was produced. Normal close/exact restoration/full readback/final idle CPU and397
unchanged parent inputs passed. Preserve this consumed case and its failures.

A distinct binary may enable the existing bounded admission controller once
before selected-source startup integrity, retain its20s boundary/60s process
budget across all later boundaries, and use it before each new integrity read.
This changes neither the predicate nor any reserve, allocation, SHA256, stable
identity, EOF, read-call lifetime or stronger2974-page gate. Require actual native
provider-class fault controls for transient recovery, persistent refusal without
a read, invalid counters, failed-admission quarantine and a shared process budget,
plus real PS5 provider compile/link/import/SELF gates. Repeat the distinct current
all-resource CPU/whole-rehearsal gate before separate complete native inference.

The distinct bounded-startup launch passed current SELF/receipt and complete
external resource SHA256. All235 native shader-file reads returned before an
original read-only memory guard refused during the CPU shader phase. No complete
all-resource or current whole-rehearsal report resulted. Normal close/exact
restoration/full readback/final idle CPU and401 unchanged parent inputs passed.
Preserve this consumed case. Its last qualified shared-gate sample is not a
measurement of the later independent guard's failure count.

The serial CPU all-resource verifier may check the same shared admission
controller before each next shader lease. Keep compiler-thread per-use guards
read-only, all decoder/file/ownership code and budgets unchanged, the existing
20s/60s shared bounds, and quarantine on failure before starting another read or
decode. Require actual-codec controls for initial and middle recovery, persistent
refusal and invalid counters, plus current native link/import/SELF gates and a
distinct current all-resource/whole-rehearsal CPU case before full inference.

The serial-boundary case passed all1527 current original shaders,382 lookups and
complete current external resource SHA256. The later2974-page pre-metadata target
refused at1503 after its unchanged20s boundary wait. No model metadata/current
reservations/GPU began. Normal close/exact restoration/full readback/final idle
CPU and401 unchanged parent inputs passed. Preserve the positive immutable-byte
evidence separately from the failed model-memory gate.

A distinct external profile may reuse only that complete same-boot v3 shader
report after exact report SHA256/owner/run, unchanged encoded resource manifest,
current full external resource SHA256, current382 lookup checks and unchanged
per-use decoder/completion provenance. Require direct prior evidence with1527
current checks and zero inherited checks; reject evidence chains, pending/failed
files and mismatched resource bounds. Its report must say current0/prior1527.
Every actually used shader still requires current full original SHA256 before
module creation. The actual current whole rehearsal and both2974-page targets
remain mandatory; no OS mapping/ownership/available-memory state is reused.
Require actual legacy/external validator refusal controls and native link/import/
SELF gates, then a distinct bounded CPU whole-rehearsal case with normal close/
exact restoration/final CPU before separate full inference qualification.

The external prior-byte CPU case completed all76 current reservations/releases
with current file SHA256/current382 lookups and direct prior1527-byte evidence.
Normal close/exact restoration/full readback/final idle CPU and404 unchanged
inputs passed. Its settled diagnostic free count1574 is not full startup admission.
The subsequent distinct full case refused before model metadata at1580 versus
2974 required. No model/current virtual/GPU work began; all169 resource reads
returned, and normal close/exact restoration/full readback/final CPU plus411
unchanged inputs passed. Do not replay that consumed case or lower its target.

A distinct CPU-only diagnostic may read the positively identified idle title's
SDK `KERN_PROC_VMMAP` metadata. Require exact PID/start/application/title/boot
before and after, no process memory reads or mapping changes, at most one size
query/one data query,1MiB/4096-record bounds and canaries. Validate the actual
packed parser/query and native imports first. Unknown metadata completion blocks
ordinary close and retains backing; positive completion and unchanged ownership
must precede normal close/exact restoration/final CPU. VM sizes and resident0
are not reclaimable capacity or permission to alter any reserve. Keep raw maps,
addresses and identities private. See docs/native-VM-map-diagnostic.md.


The CPU-only VM diagnostic subsequently completed two returned kernel metadata
queries and parsed 188 bounded records with exact owner checks before and after.
Ordinary close, exact original restoration/full readback and fresh idle CPU
passed. Require the qualified process ABI overlay and a 1,096-byte compile-time
process-size assertion; a permission-only SDK recipe produces 1,088 bytes and is
not usable for process identity. Keep the full compiler/CRT/header/provider
input receipt and the allowed `moss-` transport namespace. Preserve every refused
helper; zero-query terminal refusal is separate from unknown query completion.
The same CPU title completed all 76 current reservations/releases; settled free
pages 3,155 do not replace either full-startup 2,974-page admission. No new GPU or
throughput result follows from these CPU measurements. A distinct full sequence
may reuse the unchanged candidate and positive immutable-byte evidence, with
fresh sessions, current reservations, both startup guards, all requests/frames,
positive retirement and exact original restoration/fresh numerical admission.
Allow the ordinary title transition to settle for one bounded 30-second quiet
interval before the unchanged owner observer; never retry or relax a failed
service/owner guard. Strengthen the prelaunch metadata gate to the native kernel
target as well as the original minimum/reserve to avoid a cold launch under an
already-insufficient observation.


The next full case refused before model metadata/Vulkan at 2,338 versus 2,974
pages and completed ordinary close/exact original restoration/full readback/
final idle CPU with all 412 frozen inputs unchanged. Preserve that consumed case.
A separate Direct-integrity CPU helper then verified the complete 107,911,351-byte
original SELF in 1,040,491,313 ns, with the Direct flag set, all 108 reads returned
and fresh same-boot idle guards before/after. No title or GPU ran. Its immediate
free-page observations 7,151 -> 13,738 do not prove stable memory admission or
specific proprietary cache behavior.

A distinct full sequence may replace only launch/preservation digest input with
this qualified serial Direct stream. Keep one aligned 1 MiB window, exact full
SHA256/stable path+descriptor identity/EOF/deadlines, per-read original kernel
minimum/reserve, durable call markers and quarantine without retry. Preserve all
other service/title/owner/registration/mounted-inode/claim/done guards. The fresh
session may be staged once before original preservation and reused only with
its unchanged current full SHA256 checks. Native complete original integrity
must finish before rename; candidate full raw readback remains mandatory.
Unknown helper completion prevents publication/launch and retains backing.
Application/driver/precision/budgets/both native startup targets and the complete
inference/frames/retirement/original numerical readmission plan are unchanged.
See docs/launch-integrity-20261024.md.

## Completed source-schedule physical plan (2026-10-25)

The unchanged candidate SELF
`c354b82c75a4e60f783c80e16485c4132bcd40cb35fb34a62d92e528f57debf7`
completed the full physical plan with the selected file/range schedule. Arithmetic
returned `4`; both 22-token external outputs/token IDs matched the completed
single-read control. Rates were 0.332877 / 0.337782 tokens/s, mean 0.335329 versus
0.287381, an observed 16.68% gain. Logical source bytes matched. This is one
complete short-request comparison of the candidate bundle, not isolated causality,
nominal-bandwidth admission, broad quality or sustained-service qualification.
See docs/native-source-schedule-success-20261025.md and its sanitized JSON.

Both actual native frames were viewed. Positive source/GPU/model retirement,
ordinary candidate close, exact original restoration, fresh original numerical
readmission, ordinary original shutdown and final same-boot/service/idle-CPU/full
raw readback all passed. The finite continuation positively ended with all 428
frozen inputs unchanged. It retained the already-running model and original
deadlines after a separately reviewed fresh owner admission; no app/model or
generation request was retried. No native owner, gateway or loaded model remains.
Preserve every historical refusal and consumed intent; do not rerun this sequence.

The original BF16/F32 model, all experts/PLE, actual current 76-file rehearsal,
both startup targets, all budgets/reserves/wait limits, pinned 872cc126
cumulative-idle driver and disabled persistent caches remain unchanged. The
reservation stays held. Committed general execution/deployment/release and CI
remain disabled. Configuration status now records the passed finite qualification;
it does not authorize automatically starting ordinary inference or another test.

## Completed in-place 512 MiB physical plan (2026-10-25)

All 76 original logical files (359,246,956,672 bytes) were replaced in place by
711 physical parts of at most 512 MiB. Every reassembled logical SHA256 and
physical part SHA256 passed; freshly verified host originals remain intact.
No second complete original console model is retained. Preserve the sealed
layout, positive migration journals, refused attempts and unpublished forensic
fragments. Never repeat a consumed publication/truncation or infer completion
from a partial pending file. See docs/native-split512-success-20261025.md/.json.

Candidate SELF
`9727228738d6ffb3f153a4bd0e6cac3375c50d02c9eae56e1c0d68fe3042e31f`
completed arithmetic `4` and both 22-token external answers with exact control
bytes/token IDs. Both actual frames were viewed. Decode was
0.344610/0.351360 tokens/s, mean +1.50% versus the unsplit compact-observer
control; TTFT was 57.555/56.589s. This does not establish significance, broad
quality, reasoning, sustained service or a global optimum. CPU heap peak rose
16 MiB to 453,050,368 bytes within the unchanged 512 MiB budget.

The actual startup inspection must distinguish first-part physical size from
original logical GGUF bounds/footprint. All 76 real metadata-prefix checks and
four invalid-size controls passed. The saved-result collector's unsplit physical
read equality was repaired only after positive native retirement. Split serial
boundary pairs add one or two physical reads outside pipeline batches; enforce
the bounded counts and alignment overhead only after independent split-layout
admission. Default unsplit accounting remains exact. No generation, model load,
finish POST or candidate launch was repeated for the host repair.

All adopted Maya LFU4096/53-slot cache, known-miss overlap, selected reads and
coalescing, prefill four, compact completed-route observation and byte-identical
shader/Direct metadata paths remain implemented and exercised. Alternative
unselected proposals retain their recorded dispositions. Positive source/GPU/
model retirement, ordinary candidate close, exact original restoration, fresh
original numerical readmission, ordinary original shutdown and final idle
CPU/full executable readback passed. The finite host continuation positively
ended with 456 frozen inputs unchanged. No native owner, gateway or loaded
model remains. Preserve the same pinned 872cc126 cumulative-idle driver,
disabled persistent caches, every budget/reserve/startup/wait limit and held
reservation. General execution/deployment/release and CI remain disabled.


## Authorized production placement (2026-10-25)

The owner explicitly authorized production placement after the qualified profile.
The exact `ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`
SELF now occupies the registered title's actual startup path. Post-placement
arithmetic, both 22-token external requests, native frame review, positive
source/GPU/model retirement, ordinary close and final full readback passed.
The original remains verified as rollback; do not restore it merely because the
successful production verification finished. No native owner, gateway or loaded
model remains. See docs/production-installation-20261025.md and
config/production-installation.json for the sanitized current state.

Preserve the earlier zero-launch headroom refusal and every consumed case. This
production placement does not authorize replaying the completed run binding or
an unrestricted service. Another launch requires a distinct fresh case and all
unchanged memory, session, source, owner and completion guards. Keep the same
pinned driver, original precision, budgets/reserves and disabled persistent caches.
Committed global execution defaults and CI remain disabled.

## Bounded SSD CPU screen (2026-10-25)

The codec/native-delivery/continuous-refill/packing initial gates are recorded in
docs/ssd-io-validation-results-20261025.md/.json. Cases 2255, 2258, 2267 and 2269
positively completed all original-byte hashes, reads, worker joins where used,
Direct retirement, fresh idle guards and unchanged production SELF readback.
No title/GPU/model operation or production executable change was made.
Lossless CPU restoration/overlap and the tested packed-copy paths lost; the
roughly 4% raw refill signal failed the predeclared small-fixture adoption gate.
The new codec/queue/probe files are experimental and are not linked into the
qualified production application. Do not replay any consumed case.

Case 2261 returned a positive zero-allocation/zero-payload-read preallocation
refusal for a 40 MiB CPU fixture. Its allocation-free metadata review and later
distinct smaller cohorts completed. It is not an unknown in-flight GPU call.
The smaller fixtures separately charged 8 MiB I/O and 10 MiB destinations;
their 18 MiB total is not the production scratch budget or admitted GPU memory.
Keep all original floors/reserves, exact completion ownership and held reservation.

Actual model metadata has 49 F32 router matrices, including the unused MTP
router; current inference loads 48 text layers with top-10 experts. Do not
automatically charge another BF16-to-F32 router copy. Literal upstream staging
and victim margins fail current capacity, while a two-slot smaller forecast is
only a design/capacity result. No hidden-state forecast, speculative read or
native forecast speed has been implemented or qualified. Saved route IDs alone
cannot validate router reuse. The installed fastest production SELF and rollback
remain as recorded by config/production-installation.json.

## BF16 system validation and current headroom (2026-10-25)

The new exact-palette CPU cohort completed 108 original-byte deliveries and
positive Direct retirement, but lost at 0.488x paired delivery throughput.
Its GPU shader has host integer-bit/SPIR-V checks only. The one-worker demand
queue passed host ownership controls; physical cases 2285 and 2288 positively
refused before allocation at the unchanged 20/10 MiB admission gates. Preserve
both failures and their explicit zero-work completion reviews; never replay them.

The subsequent allocation-free same-owner snapshot observed 1767 free kernel
pages versus native startup target 2974 and full prelaunch requirement 10142.
This is a point observation, separate from Flexible/Direct capacity and the
later canonical SELF readback. No GPU/title/model was started. Additional native
work requires a distinct fresh case passing all unchanged memory and lifecycle
gates; do not lower floors or deliberately reclaim/pressure memory to force a
test. See docs/bf16-system-validation-20261025.md/.json.

No new candidate is adopted or linked into the qualified production app.
The exact installed fastest SELF and preserved rollback remain unchanged.
Router forecasts, ready-expert execution and speculative verification remain
unimplemented/unqualified; do not infer their completion from codec/queue tests.
