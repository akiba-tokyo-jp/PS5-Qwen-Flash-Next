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
