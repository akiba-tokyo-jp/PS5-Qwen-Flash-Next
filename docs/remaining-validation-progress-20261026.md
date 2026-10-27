# Remaining validation: execution progress

## Final current-environment disposition

The owner's latest instruction is to execute available work and classify the rest
as execution unavailable. The [final 22-stage ledger](final-current-environment-dispositions-20261027.md)
now supersedes all current-status and prospective next-step wording below.
Every stage has a finite decision; no item is waiting for user action or reboot.
This current queue is closed with explicit execution-unavailable outcomes.
Missing code remains unimplemented and unrun native tests remain unrun; the
original all-implementation/native-validation speed objective is not achieved.
Earlier case records remain historical and must not be replayed unchanged.

This is an intermediate execution record for the
[remaining-proposal plan](remaining-validation-plan-20261026.md). The overall
implementation and validation request is incomplete. Fixture qualification
does not establish generation speed, full-model acceptance or production adoption.

The qualified production control is
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
Temporary native fixtures preserve that control and restore it after ordinary
closure; publication of a diagnostic SELF does not adopt it. The initial
standalone CPU cases made no title, GPU, model-file or application changes.
Later title-based CPU diagnostics are recorded separately with exact restoration.
The driver selection remains `872cc126` / `cumulative-idle`, with
persistent caches disabled. Raw private evidence, SDK inputs, binaries and
original weight fragments remain outside Git.

The [later memory controls](PLE-memory-first-plan-20261026.md#subsequent-physical-controls-and-reduction)
completed actual small-title CPU shader attribution and reduced an observed
closed-file cache component. Registry/decoder initialization changed free pages
by zero; the entire shader interval lost 22 pages. Normal close, exact fastest
restoration and native integrity of 15 closed sources passed. Post-close free
pages were 9,079–9,080. No GPU was initialized and no new decode speed is claimed.
The subsequent four-graph PLE smoke passed exact physical GPU checks (2741).
The finite timing comparison and other outstanding packages remain incomplete;
see the [latest physical record](PLE-smoke-startup-20261026.md).

## CPU batch metadata

`native/app/batch_metadata_reuse.h` is an experimental adapter, not linked into
`LlamaEngine`. It retains initialized single-sequence batches at widths one,
two and four, updates tokens and positions, and checks context/vocabulary,
owner epoch, pending use and quarantine. It preserves every output-logit flag.
`tools/check_batch_metadata.py` compares actual pinned `llama_batch_ext` methods
at upstream `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`; it does no model arithmetic.

Host case 2476 and native CPU case 2479 passed 2,277 exact metadata comparisons.
The native median nanoseconds per batch over 12 rounds of 100,000 iterations were:

| Width | Clear/add/set control | Initialized reuse |
| --- | ---: | ---: |
| 1 | 1119.468265 | 11.099265 |
| 2 | 2247.357180 | 17.748645 |
| 4 | 4446.675290 | 26.688915 |

Reuse made zero additional allocations; the tracked C++ metadata peak was 1,688
bytes. These are metadata times, not graph or token times. Their small absolute
size must be included when deciding whether engine integration is worthwhile.
No full-model benefit has been measured. Native workers and CPU resources
positively completed; no GPU was initialized.

## Vectored original-byte delivery

Native ABI case 2481 verified the existing `readv`/`preadv` runtime exports with
returned invalid-descriptor controls. Native case 2483 then scattered a generated
48 KiB file into three disjoint Direct destinations, checking all bytes,
intervening canaries, identity, EOF and positive unmap/release. This qualified
the bounded native ABI separately from original-model delivery.

The original-BF16 cohorts use unchanged 3,276,800-byte matrices inside aligned
3,293,184-byte envelopes. Padding retains each matrix's original source residue.
Both arms read the same physical file, bytes and destinations. No extra gather
or reconstruction copy is included in either arm. Timed delivery includes the
required read/return journal; identical post-delivery SHA checks are outside both
timed arms. Groups rotate and arm order alternates over eight rounds. The
predeclared fixture screen requires median control/candidate time above one and
every round above one, plus all exactness and ownership checks.

| Native CPU case | Geometry | Exact original-matrix deliveries | Scalar / vector calls | Median paired delivery ratio | Faster rounds |
| --- | --- | ---: | ---: | ---: | ---: |
| 2488 | One expert, three roles; two scalar waves versus one `preadv` | 144 | 72 / 24 | 1.216448426x | 8 / 8 |
| 2493 | Two experts, six roles; three scalar-pair waves versus two concurrent `preadv` calls | 288 | 144 / 48 | 1.308267449x | 8 / 8 |

Case 2493 retains the same one persistent worker plus caller in both arms. The
original samples cover layers 0, 23 and 47, experts 0 and 257, and gate/up/down.
All complete pack and original/envelope SHA256, file identity, EOF, tail-canary,
returned-read, joined-worker and Direct retirement gates passed. There was no
unknown completion. The 24 MiB CPU fixture is separate from the production
scratch allowance and GPU admission.

`native/app/vectored_source_batch.h` owns at most two actual requests. Each
request charges every byte of one or three disjoint aligned destinations; a
three-plane request is not disguised as a single-matrix read. Host case 2490
passed 23 invalid-request controls, exact six-destination delivery, reentrant/
wrong-producer refusal, two known-failure joins and isolated uncertain-completion
retention. Host case 2491 checked expert-major input to role-major output mapping,
short reads, canaries and exact delivery with the actual pair backend.

These results qualify CPU delivery only. Current production source is role-major;
`preadv` needs physically contiguous expert records. The real Vulkan-bank lease,
coalescing, split/EOF fallback, descriptor and full-model costs remain separate
gates. Do not multiply these ratios by production tokens/s or start complete
repacking from this result.

## GPU-bank implementation and preserved refusals

The default-off `vector-bank-validation` mode and
`native/app/vector_bank_admission.cpp` are experimental. They retain all three
actual padded-bank owners through each returned read and positive graph
completion, using the existing indexed BF16/F32 shader. The test design includes
slots 0/52, repeated selected IDs, F32 inputs that are not BF16-exact, F64
references, bank canaries and the unchanged device budget.

Assets case 2494 contains the authentic two-expert sample pack and a second
bounded placement pack. The latter places unchanged original matrices at every
one of the 30 known source residues; it repeats the same expert payload into
both selected slots and tests padding/descriptor correctness only. These
synthetic placements are excluded from the speed comparison. They are not a
claim that the original model has those new tensor/file bindings.

Host case 2496 passed the valid policy and 22 invalid-policy controls. The final
prelaunch source, case 2498, passed 25 invalid-policy controls, actual headless
startup parsing and compilation with the native ABI. Earlier case 2495 stopped
at a missing host JSON include before any console work. These host gates preceded
the native cases recorded below.

Native case 2500 passed SELF/import/segment checks, staged-file whole integrity,
all ten unchanged 10,142-page prelaunch observations, ordinary OS launch and
exact owner observation. It then positively refused a nested owned-bank lease
before creating the comparison worker or issuing a comparison read/GPU graph.
One device initialization and its positive idle/checkpoint completed. The
failure was `Nested vector bank lease refused`; no unknown completion occurred.

The fixture had created each bank followed by its smaller input/output tensors
in one context. GGML allocates root tensors in creation order, so those smaller
extents interrupt the banks' required 16 KiB alignment. The existing owned-bank
guard correctly refused the next unaligned root. This is a fixture allocation
problem, not a measured `preadv` failure or a throughput result. The proposed
correction creates all three page-sized bank roots before auxiliary tensors and
defers bank initialization until all three real leases pass. Host case 2508
mechanically extracted both fixture construction sequences and the pinned actual
GGML tensor-size/planning/allocation functions. Metadata API stubs reproduced the
failed second-root alignment and verified the corrected layout for descriptor
alignments 1/2/4/8/16/32. At the previously measured native alignment of four,
bank offsets changed from `[0, 178250792, 356501584]` to
`[0, 177815552, 355631104]`; total payload remained 535,673,976 bytes. Only
inaccessible host virtual addresses were reserved, with zero physical weight
allocation, learned inference or GPU work. The first host attempt, 2507, stopped
at a duplicate macro definition before execution. Case 2510 also passed the
updated native unit compile and 25 policy/startup controls. A distinct native
case is still required; case 2500 is consumed.

The failed case was reviewed before exact-owner ordinary OS close. The exact
fastest SELF and prior settings were restored and fully read back, and a fresh
same-boot/service CPU observation confirmed idle native/gateway/model state.
No original MOSS executable was substituted. During staging, a missing host
`session_remote` field had separately refused before session/SELF publication;
its saved review bound the missing fields from the actual launcher and continued
only the two unperformed transfers. Completed data/configuration transfers were
not repeated. Preserve both failures and the immutable source-at-execution
snapshot of build 2499. Final closed-artifact preservation, case 2509, verified
four complete sources and observed 15,127 free kernel pages. That point value
does not authorize a later launch.

## Completed GPU-bank fixture and attribution limit

Case 2512 admitted all three corrected bank mappings and returned its first six
scalar reads, then refused the first shader acquisition because the isolated
mode had bypassed the existing CPU shader-storage admission. No GPU graph was
submitted. Its known returned refusal was reviewed before ordinary OS close,
exact fastest/settings restoration, full readbacks and fresh idle CPU checks.
Closed-artifact preservation 2517 passed. The case is consumed.

The existing shader CPU-admission body is now shared by ordinary inference and
the isolated mode, preserving its guards and verification except for explicit
parameters. The new mode requires all original assets in the current process;
the existing ordinary path retains its original prior-proof option. Host 2522
checked the actual extracted helper's order, nine CPU refusal paths and placement
before the GPU boundary. Host 2523 passed 34 policy/startup refusals and native
unit compilation. Failed host extraction/include checks remain preserved.

Native case 2525, build 2524, completed the finite bank fixture:

- 1,527 original shaders CPU-verified before Vulkan; every later shader input
  SHA256-checked and its input lease returned.
- 68 batches, 408 original-matrix deliveries and 204 GPU graphs; all 30 residue
  layouts, slot 52, repeated IDs and non-BF16-exact F32 inputs passed.
- Scalar/vector F32 outputs were bit-exact. Maximum absolute F64-reference error
  was `1.1917939551908674e-10` under the unchanged per-element limits.
- All 272 read IDs and returned byte counts conserved 1,343,619,072 physical
  bytes. All workers joined, all three bank leases returned and the device ledger
  ended at zero; its conservative peak was 805,306,368 bytes.
- Positive device/epoch completion, exact-owner ordinary close, fastest/settings
  restoration, full readbacks and fresh idle CPU checks passed. Final preservation
  2531 verified five complete closed artifacts and observed 14,634 free pages,
  not a future admission. No model was loaded or generated tokens measured.

The 48 authentic-layout timed batches produced these delivery wall times; the
20 synthetic-padding correctness batches are excluded:

| Arm | Median batch ms | Descriptive p95 ms | Maximum ms |
| --- | ---: | ---: | ---: |
| Three scalar-pair waves | 23.695674 | 25.099079 | 26.865163 |
| Two concurrent three-vector reads | 13.034020 | 13.848824 | 16.023532 |

The paired eight-round median was **1.820924911x**, all rounds faster, so the
predeclared **logged fixture** gate passed. It is not a production qualification.
Per-call durable read/return journals are part of this interval. Grouping three
planes reduces those journal operations too, and production adds no such
per-read hot-path logs. The prior two-expert CPU case's paired median ratio of
the sum of pure syscall times was **0.945693350x**, despite faster logged wall
delivery. A sum of overlapping reads is not producer wait, but this difference
prevents attributing the logged wall gain to SSD service alone.

The distinct compact-journal comparison below resolves that tracing question
before testing the actual original-file layout. Neither fixture authorizes
model migration or a tokens/s prediction.

## Compact records and actual production-source layout

`native/app/batch_io_journal.h` predeclares at most six real calls in one durable
record, then captures every begin/return in bounded owned memory. The returned
snapshot is persisted before GPU work. It retains unknown completion even after
a late callback. Host 2532 passed 18 refusals, foreign-producer checks, known
short reads and uncertain retention. Host 2534 passed 37 policy/startup controls
and actual native compilation; ten result-test groups also passed.

Build 2535 and native GPU case 2536 preserve the preceding bank/shader/numerical
scope, including all 68 batches, 408 original matrices and 204 graphs. All 272
I/O events matched 68 durable plans and 68 returned records. Both predeclared
timing gates passed: median paired **1.251869484x** for source service and
**1.183166212x** including batch safety persistence; all eight rounds were faster
on both metrics. This isolates the earlier per-call tracing effect but still
compares two ways of reading the same expert-major source file. Ordinary close,
exact fastest/settings restoration, full readbacks and fresh idle checks passed.
Preservation 2542 verified five closed artifacts; 14,401 free pages was only its
terminal observation, not a future launch admission.

The next CPU case, 2547, used actual unchanged production 512 MiB physical parts
for its scalar control and the same sealed expert-major sample for its candidate.
`native/qwen_flash_next/vector_layout_probe.c` checked sealed identities, every
one of 18 used original envelopes and BF16-slice SHA256 values, and original-file
EOF. Unused original-file payload was not reread. The complete sample pack was
SHA256/identity/EOF checked. Both arms used one worker plus caller, two actual
requests maximum, the same destination geometry, zero copies and compact safety
records. Host 2545 checked the actual executor, mapping, canaries, invalid ranges
and known short-read joins; three result-test groups checked finite evidence.

| Native comparison | Source paired median | Total paired median | Faster rounds | Decision |
| --- | ---: | ---: | ---: | --- |
| 2536: same expert-major file, actual GPU banks | 1.251869484x | 1.183166212x | 8/8 on both | Fixture qualified; original production layout still excluded |
| 2547: actual original physical files versus expert-major pack | 1.039768653x | 1.036605631x | 7/8 on both | Inconclusive; original every-round-positive gate failed |

Case 2547 completed all 288 original matrix deliveries, 192 I/O events and
948,436,992 physical bytes, with joined workers and positive Direct retirement.
One round regressed to 0.979137x source and 0.986618x total. The measured source
advantage is substantially smaller than in the same-file control. Original
descriptor opens were outside both timed arms; production coalescing, fallback,
partial-pack coverage and engine metadata remain unpriced. No whole-model
repacking, engine integration or production adoption follows from this failed
screen. No GPU/title/model load or production mutation occurred in case 2547.

## Bounded workload metadata

Host metadata case 2543 froze arithmetic/counting controls and four new workload
classes. Original rendered arithmetic/counting strings and their 26/30 token
counts matched the completed native evidence. Japanese, code/copying, reasoning
and low-repetition prompts fit within 19/25/25/17 tokens respectively. Tokenizer
and template identities, token IDs, greedy sampling, disabled thinking, context
256 and the 22-output-token cap are frozen privately. No model payload or learned
host inference was used. New native workload/token-ID qualification remains open.

## Device-state copy prerequisite

The pinned engine already implements `LLAMA_STATE_SEQ_FLAGS_ON_DEVICE` in
`src/llama-context.cpp::state_seq_get_data/state_seq_set_data`. Its device-copy
classes keep tensor payload in context-owned backend buffers; only serialized
metadata needs CPU storage. This avoids the rejected whole-state CPU allocation.
The sequence API covers hybrid memory, but does not by itself preserve application
positions, pending tokens, prompt ownership, sampler and effective last logits.

Host 2550 exercised the exact extracted `llama_io_write_device` and
`llama_io_read_device` classes with explicit metadata-only byte-copy stubs:
eight partition/reuse/resize/discard/buffer-type cases, two metadata-bound refusals
and positive owner retirement. The earlier 2549 compile refusal is preserved.
Native input receipt 2551 puts the unchanged extracted classes in a private
fixture namespace, without replacing engine symbols. Host 2554 passed 23
policy/startup controls and native unit compilation; shared shader admission
2555 retained the original helper body and all nine refusal checks.

The default-off `device-state-validation` mode is compiled only with an explicit
checked extraction manifest. Otherwise its implementation refuses before GPU
initialization. Build 2556 passed link, module-import, SELF and segment-roundtrip
checks using the unchanged driver/engine/shader archives. Native case 2557 then
passed all ten fresh 10,142-page prelaunch observations and eight actual Vulkan
copy cases over **142,606,336 bytes (136 MiB)** of generated original-F32 patterns:

- Capture with one/two partitions and restore with one/two/three partitions,
  including changed chunking, same-size saved-buffer reuse and a discarded restore.
- Every checked F32 bit and both source-view canaries matched. The CPU transfer
  window was 2 MiB; no complete state payload was allocated on the CPU.
- All source/copy owners returned, the source worker stopped and positive
  device/epoch retirement passed. Device ledger peak was 287,309,824 bytes
  (274 MiB), with zero live bytes afterward.
- All 1,527 shader assets were CPU-verified; the copy path used zero GPU shader
  modules. Queue-submission counts are not inferred from copy calls.

Ordinary exact-owner close, fastest/settings restoration, full readbacks and fresh
idle CPU checks passed. Preservation 2563 verified five complete closed artifacts;
13,983 free pages was its terminal point observation only. The installed production
SELF is unchanged. This establishes the state-copy prerequisite on this console,
not complete-model checkpoints, prefix reuse, speculative exactness or speed.

## Complete-model continuation

`native/app/model_checkpoint.h/.cpp` owns one bounded CPU metadata/logit record
and uses the pinned context-owned device state storage. The adapter explicitly
preserves request/model/context binding, positions, pending token, prompt, ready
state and effective F32 logits. It restores the existing greedy sampler path.
Pinned PLE predecessors come from KV `ext.tok`; the state reader restores those
IDs before `get_prev_tokens`. Hybrid state includes recurrent/PLE and QSA state.
These source observations were followed by actual continuation comparisons.

Host 2572 passed checkpoint ownership, bounds and uncertain-completion controls;
2573 passed six adapter scenarios using opaque state/API stubs and the actual
greedy implementation. Native host check 2575 passed 25 policy refusals and
compiled the actual adapter, checkpoint and application units. Build 2576 passed
link, module imports, SELF integrity and six-segment roundtrip with unchanged
driver, engine and shader archives. The temporary diagnostic SELF was
`b10752c83004a13f4941f5503b1557e5fe72c841057f29ec7553937918ebd1f0`.

Physical case 2577 passed all ten fresh 10,142-page observations. It executed the
unchanged arithmetic smoke, one normal counting request and one counting request
with deliberately repeated calculations:

- Capture/replay at original prefill positions 4 and 28, then every generated
  state and EOG: **25 captures and 25 restores**. Both requests emitted the same
  22 original tokens and bytes as the qualified production control, exactly once.
- All **1,152 compared layer-route records** matched, and the maximum absolute
  error across every compared F32 continuation logit was **0**.
- Actual maximum saved tensor payload was **121,171,968 bytes**; CPU serialized
  metadata was **3,828 bytes**. Effective logits and reference/candidate arrays
  retain their separate bounded CPU charge.
- Device ledger peak was **1,069,547,520 bytes (1,020 MiB)**, ending at zero.
  CPU heap peak was **453,050,368 bytes**, with zero untracked libc fallbacks.
  Source worker, GPU, context, model and checkpoint owners positively retired.

The normal request measured 0.391058 tokens/s and TTFT 50.149955s. The validation
request measured 0.195901 tokens/s and TTFT 59.165222s, including 24 deliberate
extra model-process calls: 54 total versus the ordinary 30. Those validation
numbers are **not** an optimization comparison or evidence of a production
regression. No prefix-reuse or speculative-throughput qualification follows.

The first host collector rejected its expected-position list after positive
native completion. Initial `next()` samples existing prompt logits without
advancing position, so the saved positions correctly begin `4,28,30,30,31...51`.
Review 2586 retained the original refusal and sources, corrected only the host
expectation, and revalidated saved native quality, performance accounting,
memory and routes. No POST, inference or GPU operation was repeated. The
maintained validator and adapter regression now explicitly check both position-30
states; host 2588 passed all six updated adapter controls.

Both actual native frames were viewed and showed the passive hardware/time/token
monitor. Ordinary exact-owner closure, exact fastest/settings restoration, full
readbacks, fresh idle CPU checks and reservation return passed. Preservation
2585 checked **12 complete closed artifacts**, including both frames and restored
settings. Its final **7,038 free pages** was below the unchanged 10,142-page
prelaunch requirement and does not admit another title. Metadata-only follow-up
2587 observed 93 files for this closed case; apart from two 8,294,454-byte frames,
each was below 1 MiB. This does not explain the entire kernel-memory change.
Further attribution and host implementation continue before another publication.

Complete-model checkpoint correctness is now qualified within this finite scope.
The next consumers remain exact repeated-prefix reuse and width-two verification,
each with its own admission, comparison and adoption gates. The production
executable and prior settings are restored; no new optimization is adopted.

## Exact-prefix consumer and reduced-headroom experiment

`ModelCheckpoint::matches_complete_prompt/rebind_complete_prompt` and
`LlamaEngine::prefill` now implement default-off exact complete-prompt reuse on
the same context/producer. Partial, generated, older, other-model and mismatched
prompts refuse; prefix reuse and checkpoint replay are mutually exclusive.
The original complete device snapshot is preserved across request cleanup and
retired with its context. The adapter observes the existing full F32 CPU logits
without adding a GPU download. The two requests' 23 original arrays, including
EOG, must have identical SHA256 values, exact tokens/bytes and original routes.
The enabled warm request has 22 original decode processes instead of 30 including
prefill; result collectors require the explicitly bound prefix proof before
accepting this accounting.

Host 2592/2593 passed ownership/refusal/retention and 13 adapter scenarios.
Host 2594 passed 27 policy refusals, original F32 bit-hash comparison and actual
native compilation. The device executable passed linking, actual imports and
six-segment SELF roundtrip as
`ff2ef965e52386f04c44b763bc3bb0484e26761dfb44381f1190ebcb708d2c05`.
These are implementation/host results, not a measured prefix benefit.

After the owner explicitly authorized reduced-headroom experiments while
physical recovery was unavailable until evening, case 2601 attempted the A1
control of the planned A/B then B/A cohort. All ten observations passed the
separately recorded experimental 6046-page gate at 6363–6364 pages. The regular
10142-page production gate, native startup target 2974 and operational floor
`minimum + max(reserved,256)` were recorded separately and preserved as specified
in the [experimental exception](remaining-validation-plan-20261026.md#owner-authorized-reduced-headroom-experiment).

The application returned a **known pre-backend memory refusal**. All original
76-file metadata/footprint checks completed. The 77 virtual reserve/protection/
release calls, including the small prerequisite, all returned, and all 76 model
ranges were released. No model was loaded, GPU initialized, source worker
started or external generation POST issued. The application waited within its
original backpressure bound but did not regain the unchanged startup target.

| Observed native interval | Free 16 KiB kernel pages |
| --- | ---: |
| After current SELF/receipt Direct integrity | 3401 |
| Before original model metadata/integrity inspection | 3361 |
| Before virtual-source rehearsal | 2102 |
| After all virtual ranges were released | 2089 |
| Last failed startup admission | 2077 |

The large observed decline occurs **before** the virtual rehearsal: 1259 pages
in the metadata/integrity interval, compared with 13 pages around the completed
virtual operations. The tracked CPU heap grew from 16 to 32 MiB. These phase
observations do not identify the allocator or establish that the heap caused
the kernel-page decline. Original GGUF Direct metadata completed 86 reads /
90177536 physical bytes, maximum logical prefix 10946389 bytes, with its window
retired. No extra readback or inference repeats were used to repair this refusal.

Review 2607 proved the returned CPU-only terminal and allowed ordinary exact-owner
closure. Restoration 2608 returned the exact fastest SELF/settings, full
readbacks, fresh idle CPU and the held reservation. Preservation 2609 verified
18 closed artifacts and observed 6709 free pages. This point is not a future
launch admission. The fastest production executable remains unchanged; no prefix
timing or speed result exists. The cohort is incomplete and case 2601 is consumed.

Metadata-only case 2611 inspected first and last 1 MiB of each sealed first part:
152 regions, all resident/modified/referenced counts zero, with matching owned
map/query/unmap completion and no payload reads, cache advice, title or GPU calls.
This is a post-close observation in the payload's source namespace, not proof
about every page or the application's mounted-file cache while it was running.
The earlier case 2597 similarly found zero residency in 32 actual last-layer
expert ranges and three positively closed executable controls.

`metadata_memory_probe.h` and `native_main.cpp::inspect_container` now provide a
separate default-off CPU-only attribution prototype: five observations per file
around size access, GGUF parsing, tensor inspection and container retirement.
Its fixed 27376-byte record store preserves all 380 observations. The dedicated
policy disallows prefix/checkpoint/stage diagnostics and terminates before any
virtual-source operation, worker or GPU initialization. Host 2614 passed all
380 records and 31 refusal cases; 2613 compiled the actual native units. Build
2615 passed actual imports/link and SELF roundtrip as
`dbe2f323e1f2af917b95312731111c74069db757110281d4acfb22e3426bf4c8`.

Distinct CPU-only case 2616 passed ten experimental observations at 6606 pages
but refused **before the metadata loop**. Free pages were 1411 before current
SELF/receipt integrity, 3139 after it and 1688 at failed startup readmission
after shader CPU admission. No original container was parsed and no virtual
source, worker, GPU or generation request started. The same 2974-page startup
target and bounded wait remained unchanged. This earlier refusal shows that
the metadata interval from case 2601 is not a unique explanation for all of the
current title's pressure or system variation. The CPU probe remains physically
unqualified; do not attribute its missing measurements to a specific parser or
reduce the runtime floor to complete them.

Review 2624 proved the returned pre-metadata terminal and ordinarily closed the
exact owner. Restore 2625 returned the exact fastest/settings and fresh idle
reservation; preservation 2626 verified 13 closed artifacts, ending at 6451 free
pages. No unknown completion remains. Neither consumed case is eligible for
replay; dependent physical comparisons need a materially improved fresh memory
condition. Physical attribution and any resulting code optimization remain open.

## Cache capacity feasibility

Host 2599 used actual GGML allocation-free tensor metadata, 60 residue/role views
and 3240 read envelopes. A 1D BF16 byte-storage root could represent 54 useful
slots within the same 533495808-byte three-bank allocation; 55 cannot fit. The
current 3D ownership/dispatch predicates reject that representation. No existing
53-slot guard was relaxed and no 54-slot application was built or executed.

Host 2600 replayed the actual `ExpertPolicy` and independent Python policy on
the frozen production routes. Both capacities matched. Across the two external
requests, misses changed from 38781 to 38762: only 19 experts / 186777600 bytes,
or 0.048993% of baseline uploaded traffic. This is a traffic screen, not a speed
measurement or a hard bound on critical-path latency. The actual soft layer floor
is zero for both capacities at the recorded top-10 through top-40 selections;
do not assume a one-expert-per-layer floor. Cache expansion remains unpromoted
and requires new ownership/dispatch qualification plus the wider lifetime audit.

The finite research expansion screen 2630 replayed 53, 54, 64, 80, 96, 112, 128,
144 and 160 slots through the actual C++ policy and an independent Python replay
with the native layer floor. All nine matched, and the 53-slot control matched
the native counters. This prices the existing **3D root plus one spare plane**;
the 54-slot row here is a different representation from the preceding packed
byte-storage hypothesis. No extra allocation was made.

| Hypothetical slots | Three banks, MiB | Extra banks versus control, MiB | External logical upload reduction |
| --- | ---: | ---: | ---: |
| 53 | 508.781 | 0 | 0 |
| 64 | 612.422 | 103.641 | 0.436% |
| 96 | 913.922 | 405.141 | 3.200% |
| 128 | 1215.422 | 706.641 | 4.899% |
| 160 | 1516.922 | 1008.141 | 6.740% |

Every expanded 3D candidate exceeds the existing 512 MiB cache cap. Adding the
bank delta to the observed checkpoint device peak is only an arithmetic envelope
under unchanged-other-lifetimes assumptions: 128 slots would be 1726.641 MiB,
while 144/160 already exceed the 1792 MiB ledger cap. No geometry, UMA/kernel
headroom, peak lifetime or native speed admission follows. The modest traffic
reduction at a large extra footprint lowers this candidate's present priority.

Screen 2631 separately kept all 53 slots and tested two causal cyclic-order
eviction prototypes in `cyclic_expert_policy.h`, using the actual aged-frequency
observer and an independent Python replay. Layer-distance eviction increased
external misses from 38781 to 39286 (+1.302% traffic). Frequency divided by next
layer distance reduced aggregate misses to 38726 (0.142%), but the repeated
request worsened from 19244 to 19282. Both failed the declared requirement for
fewer misses in each external request. These variants are rejected at the
metadata screen and need no native integration/speed run. No future expert IDs,
speculative reads, bank changes or production policy changes were used.

## Model-free draft and width-two adapter prototypes

`model_free_draft.h::propose_model_free_token` now implements a bounded pure
metadata prototype. It accepts only the prompt and already committed generated
IDs, prefers generated-history suffixes of length one through four, and requires
at least two suffix tokens for prompt lookup. It introduces no weights, logits,
learned host inference or speculative reads. Its second exploratory mode requires
at least two historical matching successors with no conflicting successor; this
is a recurrence rule, not a calibrated confidence estimate.

Host 2628 passed 12 input refusals, suffix/recency/provenance controls and future
suffix mutation controls. On each of the **same two saved counting traces**, 21
positions were eligible: latest-match proposed 12 times and matched six saved
next tokens; the consistent-pair screen proposed five times and matched all five.
The latter rule was explored after inspecting this workload and is **not** an
independent accuracy or throughput evaluation. Prompt lookup on actual model
traces was not evaluated because those saved traces contain generated IDs only.
EOG targets, target width-two arithmetic, rejected-draft traffic and new workloads
remain necessary before any speed claim or adoption.

`LlamaEngine::enable_speculative_step_prototype/next_with_one_draft` adds an
independent default-off adapter prototype. No `native_main` policy or automatic
draft controller enables it. Verification width two means the original pending
token **plus one draft**. It captures the qualified complete state, runs both
original target positions with the existing matrix route, and checks both full
finite F32 CPU logit rows with the original greedy sampler. Acceptance samples
the first target once and pins the second target row for the next ordinary
`next()` call. Rejection, including an EOG target, restores the entire checkpoint
and computes the original pending token before emitting anything. The expert
cache's observed work is not rolled back or omitted from future cost accounting.

All snapshot, model, sequence, request and producer guards remain. The prototype
caps attempts at 32 and vocabulary at 262144, rejects a second verification or
prefill while its bonus is pending, and discards a queued row on successful
request cleanup. Unknown processing/synchronization, missing logits, incomplete
restore or corrupted PLE retain the failed owner and block subsequent work.
These are transaction/API controls, not physical arithmetic qualification. The
current matrix and staging behavior must be priced; a saved route match does
not establish that this path beats two optimized single-token decodes.

Host 2633 passed **25 actual-adapter/API-stub scenarios**, including the original
checkpoint/prefix controls and width-two acceptance, zero acceptance, queued-row
discard, EOG, invalid draft/duplicate prefill, incomplete restore, missing PLE,
missing row, failed process, unknown synchronization, wrong model and refused
budget. All three emitted/EOG F32 arrays matched the opaque ordinary reference
in successful two-output cases. Accepted cases used nine process calls, versus
ten ordinary calls for that stub prompt; rejected cases used eleven. These
counts are API behavior only, not throughput or learned-model inference. Native
host check 2634 passed the original 27 policy refusals, F32 bit hash and actual
compilation of all four native units. The prototype has no full native package,
physical width-two fixture, full-model comparison, automatic controller or
production adoption.

## Bounded workload metadata

`config/bounded-workloads.json` remains execution-disabled. Host 2629 used the
actual `chat_prompt.cpp` C++ renderer, unchanged original template and original
tokenizer metadata through the existing conversion environment. No weights were
read or evaluated and no new dependency was installed. Rendered prompt counts
were arithmetic control 26, counting control 30, Japanese dialogue 20, code/copy
21, short reasoning 27 and low-repetition 17. Both control counts matched their
completed native controls. The four added cases fit the planned 30-token prompt,
22-token output cap and context 256. Exact native token-ID equality, native
execution, output quality and the surviving candidate's broader comparisons
remain unqualified.

## Ready-wave and graph feasibility follow-up

See the [source, ownership and case report](remaining-feasibility-20261026.md).
Host 2640 passed the top-ten ready-wave ownership and split byte-root geometry
prototype: 64 refusals, ten failed/unknown retention cases, 120 actual GGML views
and 3,180 bounded envelopes. Native metadata is 432 bytes; raw bank extent and
53 slots are unchanged. Actual independent backing, graph integration and GPU/I/O
overlap remain unqualified.

Saved-route screen 2643 preserved the current read packet choices and matched
all native cache counters plus 12,471 actual C++ physical eligibility/schedule
queries. Its narrow last-serial-read variant has opportunities in 194/1056 and
183/1056 external decode layer steps. These counts are not saved time or tok/s.
Existing parallel pairs must not be silently serialized for this experiment.

Audit 2644 limits the initialized-batch loop's measured opportunity to about
0.1334 ms per fixed request even when pricing every process at width four.
A full-model run solely for this small loop is not justified. Original GDN
constants are already F32; repeated conversion of those constants is absent.
The one BF16 PLE convolution does have recurring tap copies and casts.

The new isolated PLE graph prototype retains casts, data and arithmetic order,
with separate coefficient-copy and shifted-input-copy switches. Host 2646 passed
64 GGML graphs, 64 refusals and 1,638,400 exact deterministic F32 comparisons;
all four actual PS5 model unity variants compiled. This is not backend arithmetic
or speed qualification. Strided MUL requires verified Vulkan placement because
the current CPU fallback rejects that stride. Production overlays are unchanged.

No new physical headroom was proven. ELF zero fill is only about 1.5 MB and
external shaders already use Direct I/O. Passive regular-gate 2641 refused at
6577 free pages with zero launches/payload operations. Earlier restored cases
and the exact fastest app remain preserved; no new candidate is adopted.

## Native PLE fixture prepared; physical gate refused

The [bounded native fixture](PLE-slice-fixture-20261026.md) now has an independent
headless policy and startup path, full four-tap graphs, explicit Vulkan placement,
guarded readbacks, original-order F32/F64 checks and durable width/mode/ordinal
bindings. The finite future cohort is 208 graphs, with construction measured
separately from complete graph/fence/readback time. It reuses the existing source
guard and reports its two preflight reads; no source-free ledger exception exists.

Host 2653 passed 16 complete GGML graphs / 409,600 exact deterministic F32 outputs;
root-tensor metadata peaks at 8,643,328 bytes and 64,000 bytes of metadata. These
are not physical allocation results. Admission 2652 passed 52 refusals and three
actual native units. Shared shader check 2655 retained the original helper and
passed nine refusal controls. Eight result-review tests passed.

Full app/package 2654 passed the actual link/import audit and six SELF segment
roundtrips at SELF `21dd6eae31e97440814403d86de0a087151aad9cf665c4317f30bce57943a25c`.
Driver/profile/native archive and engine/shader inputs are unchanged. No new SELF
or settings were published to the PS5 and no candidate was adopted.

After that preparation, new read-only CPU case 2656 returned the regular memory
refusal at 6257 free pages versus 10142 required, with zero title/GPU launches,
payload reads and explicit allocations. Owner/idle checks returned normally.
The physical PLE numerical/speed comparison remains outstanding; neither this
host package nor a prelaunch refusal completes the overall plan.

## Remaining package scope

The owner subsequently made [memory attribution before PLE](PLE-memory-first-plan-20261026.md)
the current priority. Cases 2662/2664 completed CPU-only physical process/category
and file-residency diagnosis. There were 89 processes with no native owner or
stopped/zombie accumulation; all seven selected executable/frame/shader files
had zero resident pages and all 132 query windows retired. Free pages were 6274
in the process census. This is not a new launch admission or recovered capacity.

Saved case 2616 localizes a 1406-page decline to 717.446223 ms in CPU shader
preparation with unchanged 16 MiB Direct heap, zero model metadata and zero GPU.
Its individual cause remains unproven. The new independent shader-startup CPU
diagnostic reuses the original stage/idle/write/fsync probe and returns before
model metadata or Vulkan. Host 2667 passed 35 scope refusals and actual native
main compilation; 2668 passed the extracted original shader orchestration and
nine refusals, with only read-only diagnostic observations added. Five focused
reviewer tests passed. These are host/SDK checks, not physical attribution.
The earlier 2666 host test used a one-asset synthetic policy against a harness
expecting 1527 assets; its failed control is retained. The separately corrected
2668 used the real qualified 1527-asset policy, with zero console operations.

Full app/package 2670 then passed actual linking, zero missing imports and six
SELF roundtrips at `8dddba9df84629a5e12a74152b0bee17c00da6a6b81809798ee9218b4b1c54f5`
(28258439 bytes). Driver/engine/shader archives stayed unchanged; no PS5
publication or execution occurred. Earlier SELF-only quiet controls also showed
a decline without shader/model work, so this localized interval is not proof
of a shader leak. The physical attribution and PLE-specific launch qualification
remain open; production is unchanged.

Before this reprioritization, host 2660 implemented partial ready-expert graphs
at widths one through ten, original-order reduction and actual-router shadow
graph/observer/callback prototypes. It passed 20 actual GGML partial graphs,
138 invalid-shape/ordinal refusals, 2560 cancellation-sensitive F32 reduction
values, four shadow graphs and 384 bounded observation records / 17 refusals.
The callback/graph headers and actual isolated model shadow-off/layer23 unity
variants compiled with the PS5 SDK. This did not execute BF16 expert matrices,
read real hidden states, qualify buffer independence/overlap, integrate a native
controller or change the production engine. The fixed host observer is 34600
bytes; native physical cost and runtime integration remain open. These candidates
are paused behind memory attribution, not completed by this metadata checkpoint.

The peak-live allocation review, broader tokenized workloads, ready-expert
execution, hidden-state observation/forecasts, prefix reuse, exact speculative
verification/adaptive width and eligible graph specializations remain incomplete.
The finite complete-state continuation comparison has passed. Device checkpoints
are not ruled out by the rejected CPU snapshot. The existing cache cap still
cannot hold an extra expert with the current qualified three-bank ownership and
dispatch geometry. A hypothetical byte-storage view passed host geometry only,
with a very small route-traffic benefit. See the plan for each remaining
prerequisite and adoption gate.

## PLE source owner qualified before Vulkan

The [four-graph/source-owner record](PLE-smoke-startup-20261026.md) preserves the
full-title startup refusal, a subsequent pre-driver source-identity refusal and
their exact restoration. Native CPU-only case 2738 now completes current source
SHA256, read-only identity and the original two-read prerequisite using the same
bounded window. It confirms shader-resource mode 0777 is unsuitable for that
owner while the explicitly qualified source is 0644; no guard or permission was
relaxed. Four CPU phase observations retain the operational/startup reserves,
16 MiB heap and zero libc fallbacks. Normal close and exact fastest/settings
restoration completed. Controller-upload residency is another measured
contributor and is now included in post-use integrity.

Ninety-one policy/identity refusals, three SDK units, ten result-review tests,
actual native imports/dispatch and six SELF roundtrips passed. The v2 four-graph
and 208-graph scopes remain experimental. The subsequent four-graph physical
case 2741 passed exact F32/F64 numerical, canary and positive retirement checks;
ordinary close and exact fastest/settings restoration passed. See the linked
record for phase observations and preservation evidence. The paired speed comparison,
original-model acceptance and production adoption are still outstanding, as are
the other remaining packages above. Source qualification is not overall plan
completion or a new generation-speed result.

The paired-v2 preparation (2748) reused the same isolated SELF. Two distinct
prelaunch metadata controls returned 7858 / 7883 pages versus 8108; the latter
followed measured completed-controller residency and whole-file integrity.
No title or GPU launched, and no timing result exists. Exact fastest/settings
restoration (2754) and complete post-readback integrity of 15 sources (2755)
passed. The full-model gate remains 10142; the PLE startup target remains 2974
and operational floor 1154. The remaining uncontrolled VM component is still
an attribution task, not a reason to assume recovery or lower those floors.

## Phase pricing and new-boot prerequisite

See the [phase/backing/postboot record](PLE-postboot-continuation-20261026.md).
The offline calculator 2760 uses both completed same-SELF cases, taking separate
phase maxima: CPU 7701 pages, pre-GPU 8190, with operational/startup floors and
256 variation pages retained. Six manual test groups passed; no launch is
admitted. Historical consumed thresholds/results are unchanged.

The experimental split-bank borrower now exposes actual VkDeviceMemory identity
through a synchronous guarded callback. Host/API-mock check 2763 and actual SDK
compilation passed, including shared-allocation refusal. Production root guards,
cache geometry, source scheduler and GPU model graphs are unchanged; actual
independent backing and overlap still require their native fixture.

The owner confirmed restart completion. New-boot discovery 2764 and read-only
category/process observations 2766/2767 passed. The new census had 88 processes,
zero native owners and 3499 free pages, so no recovery is claimed. The absent
compatibility runtime has not been restored: the temporary kernel/ShellCore
operation was rejected by automated approval pending explicit authorization.
Current-boot shader requalification is implemented as a strict isolated CPU-only
bootstrap; 104 admission refusals and three SDK units passed (2768). Physical
shader bootstrap, PLE timing, original-model checks and adoption remain open.

## Runtime restored; new cases screened before staging

The [2026-10-27 runtime/memory record](postboot-runtime-memory-20261027.md)
supersedes the earlier pending authorization. Following the owner's instruction,
the exact existing runtime completed one entry. New-boot discovery 2771 and full
CPU admission 2772 passed. Process-memory helper 2773 returned a known refusal
at 1060 free pages before its inventory; no unknown completion remains. Passive
screen 2776 used the existing shell, matched both boot observations and refused
at 1017 -> 1012 free pages, below unchanged operational floor 1154. It made zero
new ELF requests/title/GPU launches or kernel changes.

New reusable pre-staging and current-CPU-header tools passed eight focused host
test groups, actual completed-evidence authentication and two real native ABI
compilations. They preserve all native admission and production requirements.
No current-boot shader bootstrap, PLE timing, model comparison or adoption ran.
All outstanding packages retain their incomplete status; CI remains disabled.

## Expanded cache and causal controller implementation, 2026-10-27

The owner approved the revised execution order in the existing plan. PLE timing
and the separate prefix speed comparison no longer block independent cache or
width-two implementation. The earlier 512 MiB / 1792 MiB choices are policy
budgets; their refusals are not universal physical limits.

Saved-route screen 2777 independently matched the actual `ExpertPolicy` and a
Python replay at 15 capacities, 53 through 1024. The 53-slot counters match the
completed native control. These are logical upload estimates on the saved
30-prompt/22-output-token routes, not new SSD timings or native speed results.

| Active slots | Rounded three-bank allocation, MiB | Full external-request upload reduction | One-token-process upload reduction | Historical after-load allowance slack, MiB |
| --- | ---: | ---: | ---: | ---: |
| 53 | 510 | 0% | 0% | 995.859375 |
| 96 | 918 | 3.2000% | 4.3164% | 587.859375 |
| 128 | 1218 | 4.8993% | 6.9263% | 287.859375 |
| 160 | 1518 | 6.7404% | 8.9089% | -12.140625 |
| 192 | 1824 | 8.4887% | 11.0671% | -318.140625 |
| 256 | 2424 | 11.3561% | 14.8063% | -918.140625 |
| 384 | 3630 | 16.5442% | 20.3272% | -2124.140625 |

The envelope uses completed production control 2240, retrieved read-only in
2778. Its native pool was 12,280,922,112 bytes and after-load availability
3,401,433,088 bytes. The 904 MiB device peak already contains context/workspace;
the 96 MiB CPU heap is already absent from the available query. The calculator
replaces only the rounded baseline bank allocation and separately retains CPU
growth to 512 MiB, staging 128 MiB, Direct reserve 512 MiB, platform 256 MiB and
display 32 MiB. Four focused test groups cover rounding, double accounting,
identity/completion and policy-gap versus pool arithmetic. No current admission
follows from historical headroom.

128 slots is the first implementation target. Its raw cache request is
1,274,462,208 bytes; each bank rounds to 406 MiB. The historical peak substitution
is 1612 MiB, below the retained 1792 MiB ledger cap. The 160-slot shortfall is a
revisable allowance gap. At 384 slots, banks plus unchanged already-owned memory
alone exceed the recorded native pool: that arithmetic excludes this historical
resident layout, not every alternative PS5 residency design.

The default remains the qualified 53-slot path. `padded_cache_geometry.h`, the
MoE overlay, mapped source reader, actual backend lease and vector eligibility
support a separately selected 128-slot scope. The one-way process binding is
selected before backend/model initialization. The original 53-slot geometry and contiguous-vector
predicate remain unchanged. Direct reads, coalescing, split/EOF fallback,
descriptor checks and unknown-completion retention remain required.

Source review identified a necessary allocation correction: upstream could group
all three expanded banks into one allocation above the selected 512 MiB limit.
The experimental post-load batching hook splits them at that unchanged limit;
resident pre-load tensors retain their actual device limit. The verbatim pinned
upstream planner now passes both the original one-buffer and expanded three-buffer
host controls, including view ownership. No increased single-buffer cap is used.
The isolated layout fixture prices one bank and its working reserves (2070 MiB),
not an unloaded complete model. Model execution separately retains full-footprint
admission, a scoped context-256 allowance, CPU cap and original device ledger.

Host 2795 passed both geometries, all 30 source residues, final-slot canaries,
pre-I/O fallback/quarantine, actual planner checks and 71 policy/resource/
identity/numerical refusals. The expanded native fixture must still execute all
360 graphs / 120 shape-residue cases. Its complete hashed v2 report is mandatory
before the expanded model path. Host checks are not native geometry qualification.

The causal width-two controller is also implemented, default off and independent
of the cache experiment. It uses two consistent matches in committed past tokens,
the original pending token plus one draft, complete-state restore on rejection,
one emitted token per caller step and a bounded queued bonus. It retains the
53-slot control, context 256, prefill four, original BF16/F32/F32 KV and at most
32 verification attempts. A separate policy binds the already completed full
checkpoint proof; prefix speed qualification is not required again.

The first native controller cohort keeps external request one single-token and
enables the candidate only for request two. It checks exact token IDs and output
bytes against its own original target control. Different cache conditions mean
this is not speed adoption. Performance v6 explicitly includes extra operations
and records rejected verification calls and saved bonus steps; ordinary v1-v5
validation is preserved. A zero-attempt cohort cannot establish width-two math,
and native rejection coverage remains a separate reported result.

Host 2793 passed 30 actual-adapter/greedy tests, including automatic acceptance,
rejection, no proposal, request reset and attempt saturation, plus 42 policy/
native-proof refusals. Eleven existing performance-review groups and three new
controller/result groups passed. These use API/state stubs, not learned host
inference or native arithmetic. GPU validation, native speed, A/B then B/A,
production adoption and the other remaining work packages are still outstanding.

The corrected seven native I/O objects (2787), original 1527 shader resources
(2791) and external-location objects (2794) compiled manually. All retain driver
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925` and disabled
persistent caches. No console publication or production replacement occurred.

CPU-only case 2780 positively completed two inventories of 89 processes with
no native owner or stopped/zombie accumulation, unchanged boot/services and zero
explicit allocations/payload reads/GPU calls. Free pages were 2939, active 18627,
inactive 87211 and wired 29962. RSS remains non-additive shared-memory evidence.
The separately priced CPU bootstrap screen 2779 observed 2929 -> 2929 against
provisional 7989; it refused before staging. Neither count proves physical
impossibility or future recovery. A title, current-boot complete shader proof,
expanded geometry, PLE timing and new model generations had not run at that checkpoint.

## Current-boot CPU bootstrap and restored title alias (2026-10-27)

Full native application build 2796 and package 2797 passed the native module,
dispatch, input-hash, link and six-segment SELF roundtrip checks. Candidate SELF
`3e96076034170a38dfd0f1fa0e92168f72a56896b2384f72d27fccd50f320cb8`
is 28,324,551 bytes. Its default remains the qualified 53-slot path; experimental
128-slot cache and causal speculation require independent exact policies.
The matching source inputs were preserved before physical candidate work.

The first small CPU attempt (2804) returned an explicit launcher refusal with
zero native title-launch calls because the post-restart title nullfs alias was
absent. The host's initial requested-call counter is not the actual native count.
No GPU or model work started. A separately guarded helper restored the existing
alias once, checking the exact source executable, idle registered title, boot,
services and empty underlying mount directory. There were no unmount, system
volume remount, registration or title-launch calls. The native SDK wrapper uses
static syscall 378; an earlier host-only dynamic-symbol audit refusal was retained.
The refused case was not replayed.

Fresh CPU-only case 2812 then launched normally once (PID 278), fully verified
all 1,527 original shaders and all 382 lookup entries, and positively completed
with GPU calls and model loads both zero. Its CPU-only SELF was
`b2945e3aee2251db8be392104d2498ca9e13a2b1a206f22b5a64198ecac412b3`
(1,178,694 bytes), with a 16 MiB CPU cap and no linked driver or inference engine.
The current-run native shader v3 report is 1,144 bytes, SHA256
`e4b465cc6d8249c2df54ff65e24cb2d2a4a4b31678fa0059553a8b37f62eea22`.
Whole encoded-file verification and each decoded module's original SHA256 remain
required when a later candidate reuses this current-boot CPU proof.

The selected CPU prelaunch margin was 1,410 pages (unchanged operational formula
1,154 plus 256 variation); ten native observations passed. This succeeded below
the previous provisional 7,989 and full-model 10,142 prelaunch policies. It does
not establish the startup cost of a different executable or waive the native GPU
startup target of 2,974 pages. Inactive pages were never credited as free.
During the complete shader-verification interval, free pages were 2,996 -> 1,409
and wired pages 33,414 -> 34,836. These interval changes do not isolate one
proprietary kernel consumer or establish a universal leak rate.

The CPU app was normally closed. Restoration 2816 verified the exact production
SELF, all five prior settings and retained candidate through native complete
byte-count/SHA256/stable-identity/EOF checks. A fresh idle observer passed, and
the reservation returned to the existing production context. No extra raw large
SELF transport copy was claimed. No new model throughput or production adoption
was established by this CPU prerequisite.

Fresh passive screen 2821 observed 4,832 -> 4,831 free pages. Independent layout
case 2820 retains the existing native GPU startup and inner allocation guards,
the 512 MiB CPU/single-buffer caps and 1,792 MiB device ledger. It prices its
one-bank fixture plus reserves at 2,070 MiB; the retained 128 MiB I/O allowance
also covers graph inputs/outputs and allocation rounding, without charging an
unloaded full model. Its required 120 cases / 360 graphs, final slot 127,
non-dyadic F32 inputs, F64 reference and positive retirement are a prerequisite
to an expanded-cache model run. Preparation/publication alone are not a pass.

Case 2820 returned a known CPU refusal after complete SELF/receipt integrity and
current-boot shader-proof binding, before the whole-model metadata loop, source
workers, driver initialization or GPU work. Free pages were 2,190 at the first
CPU boundary and 2,293 after the bounded 20-second wait, below the selected
2,974 startup target. All shader reads returned; the terminal was explicit.
The app normally closed, and restoration 2825 returned the exact fastest SELF,
five settings and fresh idle reservation. GPU/model calls were zero, with no
hang or unknown completion. This is a policy refusal, not failed 128-slot math
or evidence of physical inability to allocate its bank.

### Independent single-slice layout path

The revised default-off layout path enters after unchanged SELF, receipt and
current-boot shader admission. It validates the pinned receipt, owns only the
selected first physical part, reads the original authenticated slice and starts
no whole-model GGUF loop, protected virtual-source rehearsal or source worker.
This removes unrelated model preparation from a model-free numerical fixture.
The actual expanded bank, all 30 residues / four shapes / 360 graphs, F64
reference, non-dyadic F32 inputs, final-plane canaries, original heap/device caps,
Direct/Flexible reserves and positive completion remain required.

Its exact `native_cache_layout_phase_memory` policy retains the operational
formula and adds 512 kernel pages (8 MiB) immediately before GPU initialization;
with the recorded 898 minimum / 206 reserved / 256 selected extra pages this is
1,666 pages. The completed small-GPU case 2741 observed a 32-page free decline
and 32-page wired increase across GPU initialization/work/retirement. That
different fixture does not bound this larger allocation; the 512-page addition
is an explicitly provisional experimental allowance, not a physical minimum or
a measured sufficient margin for 128 slots. Fresh pool/allocation admission and
operational checks before each shape and graph still apply. Full-model startup
continues to require its original target; no model execution can reach this path.

Manual host case 2828 passed both geometries, original source/fallback/planner
controls and 111 scope/resource/identity/numerical refusals, including the exact
single-slice scope, denied model-stage combinations and invalid kernel counters.
The new native build and its physical result are recorded below.

Native link 2830 and SELF 2831 passed imports/dispatch and six-segment roundtrip.
Fresh physical case 2840 then passed all 120 cases / 360 GPU graphs, including
slot 127, every original residue, both matrix/vector paths, non-dyadic F32 inputs
and padding canaries. Maximum absolute error was `1.7171259969472885e-9` against
the F64 reference and `1e-6` limit. The device ledger peaked at 666 MiB and returned
to zero. Native C++ qualification and independent Python stage/numeric/ownership
reviews both passed. No model, protected source probe, worker or display started.

GPU-interval free pages were 3,736 -> 3,633 and wired pages 34,719 -> 34,911.
The original 2,974 startup target was also satisfied: this run does not demonstrate
that the lower 1,666 threshold would suffice. Population samples classify the
whole interval and do not isolate one kernel allocation's cost. Ordinary close,
exact fastest SELF/five-setting restoration and fresh idle observation completed
(2845); there is no unknown completion. See the [public bounded result](cache128-layout-20261027.json).

The next native gate is the predeclared same-SELF original-model order A53 ->
B128 -> B128 -> A53. Each arm retains context 256, prefill four, one internal
warmup and two fixed external requests. The selected prelaunch policy is 6,207
pages: current-SELF observed CPU-prefix decline 2,977 + unchanged model startup
target 2,974 + variation 256. A small fixture does not price all model preparation;
the full path still independently applies both startup targets and every original
operational/heap/Direct/Flexible/device guard. Initial passive observation was
8,396 -> 8,396 pages, with no title launch. Exact outputs, both orderings and a
gain above control variation are required before adoption. No new model speed or
production winner is yet established.

### Full-model preparation refusal and small CPU attribution

First control A (2860) passed ten native observations beginning at 8,272 pages,
then returned a known CPU startup refusal after all 76 protected source ranges
had positively reserved, checked and unmapped. Free pages were 1,544 before
SELF integrity, 3,285 afterward, 3,259 before metadata and 1,523 after the
completed virtual rehearsal; the bounded wait ended at 1,540 versus the selected
2,974 startup target. GPU/model loads and external generation POSTs were zero.
Normal close and exact fastest/settings restoration passed (2865). The A/B/B/A
comparison is interrupted; it is not an unsuccessful cache-speed measurement.
The observed initial decline of 6,728 pages supersedes the earlier 2,977-page
prefix estimate for pricing a future full-application cohort. A CPU-only
8,138-page passive policy refused at 6,226 without a title launch; that selected
cross-executable price did not establish CPU metadata's physical impossibility.

The separate 1,082,438-byte CPU metadata SELF (2913) links the original GGUF
metadata utility, not a driver, Vulkan backend or learned inference engine.
Its inspector and 380-sample collector are extracted verbatim from native main;
the original source seal, exact receipt, all physical identities before/after,
BF16/F32 tensor spans, 48-layer/512-expert dimensions and PLE checks remain.
Thirty-four host scope refusals, actual strong imports and six-segment SELF
roundtrip passed. The first host-only footprint constant was corrected against
the existing native control before physical execution; the corrected final build
and package are separately preserved.

Physical case 2920 then passed all 76 containers / 380 observations, 86 returned
Direct reads / 90,177,536 bytes and the complete original footprint. Tracked CPU
heap peaked at 32 MiB under its 64 MiB observational allowance. Metadata-interval
free pages increased 2,582 -> 2,595; wired pages changed 33,966 -> 33,970. Size
queries showed zero free-page decline, parser intervals -8, tensor scans +1,
container retirement -4, between-file intervals -2, and the surrounding complete
identity checks zero. Negative declines mean more free pages. These whole-interval
observations are not exclusive kernel-owner attribution. Earlier files may have
warmed filesystem state; this does not disprove cold metadata cost. It does show
that metadata alone has not explained the earlier 1,736-page preparation decline.

Two additional ELF owner observers positively refused before their metadata read;
the smaller one reported 981 pages versus the selected 1,154 floor. A subsequent
resident shell observation reported 2,807. Different observation times do not
isolate the observer's exact cost. No CPU application was rerun. Normal shutdown
instead consolidated live owner-start admission in the exact recorded OS launch
window with the original two native boot/service/parent/UID/no-tracer/AppInfo/title
checks. Every original native guard remained; one ordinary OS close returned zero
and owner absence was verified. Exact fastest/five-setting restoration and fresh
idle/full native readback then passed (2931). No forced signal, kernel change,
GPU call or unknown completion occurred.

See the [bounded public measurements](source-memory-attribution-20261027.json).
The next default-off CPU fixture compares eight original-size protected source
regions with one equal-size arena, in A/B then B/A order, capped at 32 GiB of
virtual address space and zero model payload/GPU work. Both paths emit 72 native
or matched journal markers per round; VM snapshots separate native reservation,
matched log writes, logical protection queries and positive retirement. The
existing address allocator is already compact; the proposed difference is OS
reservation count. This representative fixture cannot qualify whole-model
virtual capacity, inference speed or production adoption.


### Representative virtual source comparison and quiet-start control

CPU case 2950 completed A/B/B/A for eight original-sized logical regions
(27,624,914,944 virtual bytes). All 18 native reservation/protection/release
sets and 32 additional logical protection checks returned; every range retired.
Both modes emitted 72 actual or matched journal markers per round. Reservation
API intervals declined by only 2, 0, 0 and 0 free pages. A 1,409-page decline
occurred after reservation, during a matched journal interval in the second
arena round. This does not identify logging as the cause: asynchronous title
startup is still confounded with that interval. Round times were 197.941,
103.976, 106.176 and 103.423 ms. Warm per-file was as fast as the arena rounds;
there is no qualified speed benefit and no shared-arena production adoption.
Normal close, exact fastest/five-setting restoration, complete native readback
and fresh idle admission passed (2955). GPU calls/model payload reads were zero.

The next bounded CPU case adds five seconds with no journal writes, allocations,
virtual calls or payload reads between VM snapshots before the same comparison.
Its purpose is startup attribution, not another cache-speed or capacity claim.
No global kernel pool, operational reserve or model GPU gate changes.


CPU quiet-start case 2970 then completed on SELF `e98327d1c436e5814b89c1b1375bbae6513fb8f7c2fbc605be02902bcc1e6336`
(847,942 bytes). During 5.000481353 seconds with no application journal writes,
allocations, virtual-source calls or payload reads, free pages fell 3,455 ->
2,048 and wired rose 34,147 -> 35,568. The later four complete reserve/query/
release rounds each declined by zero pages, including matched journal intervals;
times were 102.747, 102.776, 102.786 and 102.844 ms. All 18 ranges retired. Normal
close and exact fastest/five-setting restoration with complete native readback
and fresh idle observation passed (2975). This isolates the large decline from
the suspected application operations, but does not identify a proprietary kernel
allocator or exclude unrelated OS activity. No shared-arena winner was adopted.

### Independent model-capacity review and causal workload screen

`tools/cache128_result.py` binds the exact 128/129 geometry and prior complete
native layout report by SHA256. Full-model review now requires all 120 layout
cases, the actual 1,274,462,208-byte model cache request, retained after-load
Direct reserves and all three complete 128-slot route sidecars. The scoped
resident allowance is 12,042,833,408 bytes; the original 53-slot predicate stays
12,110,548,480. A native claim alone cannot select the smaller allowance. Five
new fault-injection groups passed; 21 affected first-generation, routes,
checkpoint, prefix and speculative-result regression tests passed. No new native
model comparison or production speed follows from these host checks.

The actual current C++ causal draft function was also replayed against the two
completed production 22-token outputs using committed generated history only.
Each produced five proposals; all five matched the subsequently recorded token.
No future target was passed to the proposer, no prompt lookup was required and
no learned host inference ran. This supports using the original counting request
for the first width-two test; it does not qualify target arithmetic, rejection,
checkpoint overhead or a speed gain on the console.


The subsequent current-boot controller cohort (2990) inspected 46 positively
completed owned ELF uploads, excluding old zero-residency model/SELF resources.
PROT_NONE/mincore reported 319 resident pages / 4.984375 MiB and zero modified
pages; all windows positively unmapped. Complete original SHA256/identity/EOF
verification of those 46 originals then passed (2991), with all reads returned
and no cache advice, pressure, deletion, title or GPU work. The separate passive
screen after this material state change observed 6,942 -> 6,942 pages, below the
existing same-SELF PLE price of 8,108 (2992). No exclusive amount of recovery is
established. Do not repeat this cohort, claim inactive pages as free or use a
policy refusal as proof of physical impossibility. The console remains idle on
the exact fastest SELF and prior five settings while independent implementation
continues; there is no pending native completion.

## Standing no-reboot constraint and independent backing, 2026-10-27

The owner made reboot unavailable for future planning. Workspace and repository
instructions now retain that constraint. No new launch, GPU work or native
comparison ran in this continuation. The exact fastest executable remains
inactive. Current work is summarized in
[the independent-backing report](ready-bank-no-reboot-20261027.md).

The actual allocation owner now prices two buffers with three contiguous roles
each before either allocation. It preserves 512 MiB conservative charging and
rejects shared actual VkDeviceMemory across groups. Fourteen planner/owner
controls and native SDK compilation passed (3001). Complete serial controls
retain every original contribution and the original left-fold reduction: twenty
partial graphs, nine serial controls, 174 refusals and 2,560 F32 reduction values
passed with native SDK compilation (3003). No matrix arithmetic ran on the host.

The source coordinator preserves two I/O calls while the original GPU producer
owns wave zero. Nineteen actual scheduler/controller controls passed, including
both deadline paths, wrong-wave release, exceptions and retention, with native
SDK compilation (3013). This does not qualify physical I/O/GPU interval overlap.

The default-off backing fixture uses six original matrices from the already
qualified existing pack. Its 57 scope controls passed; the final native link,
module imports, dispatch and six-segment SELF checks passed (3010/3011/3012).
Candidate SELF: 23,086,730 bytes, SHA256
`7ef8ab1a3d5d14f7823a11058d7881645bd347156fdff02ca7eb6e79a319b4b2`.
The changed CPU/GPU boundary is accurately reported. Seven independent report
fault-injection groups passed. Actual backing/numerical execution remains not
run; the full overlap runner and model integration remain unfinished.

Read-only allocator snapshot 3009 used the existing shell, matching the same
boot before and after. Free was 6,927 -> 6,927 pages and wired 30,279 -> 30,279.
The three requested allocator nodes returned No such file or directory. This
closes that bounded observation without assigning a proprietary owner or
claiming recovery. Four parser/scope test groups passed. No ELF, title, GPU,
pressure allocation, advice, setter or reboot occurred. Native stage budgets
and current production selection were not changed, and no speed was adopted.

## Execution-plan review at the owner's request, 2026-10-27

The owner interrupted implementation and requested an efficient plan review,
including removal of unnecessary investigation. This entry records planning
only: no application source, binary, runtime guard, console state or CI changed.
The revised current queue in the existing plan is authoritative: resolve the
common startup prerequisite from saved evidence, compare cache 53/128, qualify
and measure exact width two, then close PLE/prefix before new ready-expert
integration and the remaining measured backlog. One candidate is active at a
time. Earlier prospective "next test" paragraphs are historical.

The review identified premature branching away from the prepared cache test,
open-ended attribution, contradictory universal/individual admission prose,
and build/merge milestones being treated as stopping points. The revised plan
reuses completed geometry, checkpoint and CPU proofs, removes an artificial
microbenchmark-speed prerequisite for model-dependent mechanisms, and requires
a finite decision/failure branch before each cohort. General new surveys,
repeated CPU diagnostics and searches for unavailable allocator nodes are
excluded unless a specific unanswered active decision requires them. A merge
does not qualify model speed, adoption or completion of the entire request.

The owner's subsequent critical review found further execution gaps. Step zero
now has a one-pass, four-part deliverable and cannot be repeated on unchanged
inputs. Cache-first is conditional on actual resource eligibility: its 708 MiB
rounded GPU-bank increment is distinct from kernel free pages, and width two's
own checkpoint/workspace must also be priced. Native comparisons remain serial,
while a parked case may permit one pre-existing independent host deliverable.
Primary metrics are explicit per mechanism. Correctness/resource refusals close
the remaining arms; valid speed adoption still requires reverse confirmation.
These are plan corrections only, with no app, hardware, runtime-guard or CI work.

## Bounded startup review and cache-cohort reviewer, 2026-10-27

The one-pass review required by Step 0 is complete. This completes the review,
not the common model-startup prerequisite or any model-speed comparison. Saved
production 2240, refusal 2860, shader 2812, metadata 2920, reservation 2950 and
quiet-start 2970 were reused. No new diagnostic title or external survey ran.

The full model had early display disabled already. Before SELF integrity its
CPU heap was 16 MiB, rising to 32 MiB after metadata/reservations, all tracked
Direct and with zero libc fallbacks. The startup integrity window is 1 MiB;
the separate source window is 8 MiB. Removing the screen or treating these
Direct bytes as reclaimed kernel pages would not be a supported fix. The
metadata/reservation/quiet controls prevent claiming an exclusive app cause
for the large global decline. Its proprietary/asynchronous owner is unresolved.

The concrete scope correction is the pre-title refusal screen/prelaunch price:
the old selected 6207 pages did not cover case 2860's maximum observed
`8272 - 1523 = 6749` decline. Adding the unchanged startup target and variation
gives `6749 + 2974 + 256 = 9979`; the selected price retains the higher regular
10142 policy. This is a revisable estimate, not an irreducible hardware cost.
No native predicate was reduced and the unchanged full package 2831 was reused
without rebuilding. The ledger retains the 1154-page operational floor, 2974
startup target, 512 MiB Direct CPU heap cap, 256 MiB Flexible reserve, workspace,
staging, platform/Direct reserves and 1792 MiB aggregate device cap. Cache 128's
708 MiB rounded increment is priced separately, with its explicit context
allowance and fresh postload pool proof required. No unknown owner was freed.

One fixed existing-shell screen (3014) observed **6708 -> 6708 free pages**,
30296 wired, with matching boot before/after. It refused preparation under the
reviewed price. There were zero ELF requests, title launches, GPU calls, setters,
recovery attempts, retries or CI runs. The exact fastest production SELF/settings
remain inactive. The prerequisite is **unresolved under revisable resource
policy**, not demonstrated physical impossibility. A new attempt needs a supported
material reduction of the full startup envelope or sufficient actual headroom
under a reviewed scope. Reboot is unavailable. Do not repeat the same screen,
probe or offline pass to fill this gap. The [public receipt](cache128-startup-review-20261027.json)
binds the private ledger, screen and completion without publishing endpoints.

The independent existing cache-comparison deliverable now has an offline
implementation in `tools/cache_cohort_result.py`. It consumes four raw evidence
sets in A53/B128/B128/A53 order, each with independently captured binding,
published policy/app and complete sidecar path/size/SHA256. It reuses the native
generation, layout, routes, resource, backpressure and performance reviewers.
Only the priced cache geometry/proof and per-arm run/clock/report fields can
differ. Exact outputs, rendered prompts, token counts and every selected expert
route must match. Calibrated frame epochs must establish the declared order.

For both external cache conditions, both ordered gains must exceed the larger
observed control/candidate decode spread. The warmup is excluded from primary
speed but retained in latency checks. TTFT, prefill and whole-request time are
reported separately; candidate variability cannot enlarge tolerated latency
regression. One fast arm or traffic reduction alone never qualifies adoption.
Mixed/noisy speed results remain inconclusive. A speed candidate still needs
ordinary-close/restoration and production-placement proof; the tool never sets
production adopted or claims statistical significance.

Run the offline review with:

```text
python -B tools/cache_cohort_result.py --manifest PRIVATE_COHORT_MANIFEST.json
```

The manifest schema is `ps5-qwen-cache-capacity-cohort-v1`, with the documented
`timing_boundary` constant and four `arms`. Each arm contains `active_slots`,
captures named `result`, `binding`, `policy`, `app`, and an `evidence` array for
every result sidecar. Each capture has `path`, `bytes`, and `sha256`. The binding
is the existing independent native binding, including `cache128` only for B.
The native operator still owns fresh same-boot/owner/source admission and the
frozen predeclared experiment; this offline tool cannot authorize an execution.

Focused manual checks passed: eight cohort/capture/policy fault groups, five
expanded-cache native-result groups and eleven performance groups. These are
synthetic metadata tests, not GPU arithmetic or measured model acceleration.
No native app/driver change or new speed adoption follows. The full cache,
width-two, PLE/prefix and later native work remain incomplete.

## Finite dispositions and connected ready-expert dispatch, 2026-10-27

The owner's latest instruction changes the handling of an unavailable item:
make its finite implementation/execution decision and proceed to the next
independent work package. The [complete current-round table](finite-execution-dispositions-20261027.md)
distinguishes implementation unavailable, native validation unavailable,
dependency-gated integration and existing completed/inconclusive scopes. These
labels do not qualify unrun tests or erase missing implementation.

The bounded formatter question is closed. The actual original converted ELF
2831 was SHA-verified unchanged and its process/libc relative relocations were
resolved offline: heap-size `0xffffffffffffffff`, extension `1`. Formatter
`sce_module_writer.cpp::build_parameter_blocks` has source SHA256
`7d218781ec1bc077476bcf49685a9c230e5ade1b032d909ae7f883ad80c99ab5`.
No established evidence makes those libc fields a kernel-reclamation interface.
Changing them would be a different unqualified allocation experiment, so no
package/driver/OS setting was changed and no kernel reduction is claimed.

The next independent implementation connects the actual ready source coordinator
to real GGML serial/split graphs through `ReadyExpertExecution` and
`ReadyExpertNativeGraphs`. It adds a correct joint lease for one physical serial
graph, original-ordinal masks, scoped prepriced workspace, positive native
sync/checkpoint boundaries and completed-only release. The source coordinator
owns the mutable backpressure gate; GPU dispatch uses a pure fresh predicate.
Forty execution/native-adapter host controls and PS5 SDK compilation passed
(3029). Nineteen coordinator regressions (3024), the original role-retention and
120-view/3180-envelope controls (3025) passed. These execute metadata/mock-device
calls, not learned host inference or real GPU arithmetic. The complete native
fixture entry and production model integration are still unqualified/incomplete.

The PLE decision was evaluated independently of the full-model gate. Reusing
closed primary cases 2738/2741 reproduces 7701 CPU-phase and 8190 GPU-continuation
pages (3028). The CPU maximum is `6291 + 1154 + 256`, so removing the selected
GPU target alone cannot cover the earlier CPU interval. One finite next-item
screen (3031) observed 6709 -> 6709 against 8190, with matching boot, zero
ELF/title/GPU operations and no retry/reboot. That closes current-round native
PLE eligibility as unavailable; it does not prove permanent physical failure.
No further identical polling or already completed diagnostic follows. The exact
fastest production artifact/settings remain unchanged; CI stays disabled.

Remaining full-model and dependency-gated native stages are explicitly
unavailable in the present environment, with their actual implementation states
preserved in the table. No new tok/s result or production candidate was adopted.

## Connected ready-expert numerical entry, 2026-10-27

The owner again required continuing through the complete plan. The independent
native-entry work proceeded, rather than repeating completed CPU diagnostics.
`ready_expert_fixture.cpp` now connects the original backing fixture, Direct
source callbacks, ready-wave owner and real native graph adapter. It preserves
the six strong leases through the serial/split/overlap/reverse numerical cohort.
The source and GPU paths record exact read plans and positive graph epochs;
all ten original contribution positions and output bytes must match the serial
control and the fixed F64 full-FFN reference. Failed/unknown work retains owners.

Source inspection found a concrete missing dispatch connection: the old
production padded predicate rejects the independent byte roots and partial
top-k widths. `split_bank_route.h` adds a separate default-off eligibility path
to the existing parameterized BF16/F32 shader. Eighty actual GGML shapes, 1600
layout refusals, 80 default-off refusals and unchanged production routing passed.
Eighty-five policy refusals, fourteen independent result-review groups and strict
native SDK compilation passed. Offline original-byte matrix verification found
maximum F32/F64 error 4.389794464043639e-8 with the fixed limits; this is not host
model generation or native shader proof. Native link 3042 and SELF 3044 passed
actual imports/dispatch, integrity and all six segment comparisons. The preferred
driver/profile is unchanged; no persistent caches were enabled.

The numerical pack has only the two original layer-zero experts 0/257. This
entry uses those repeated IDs, all ten interleaved contributions, source depth
one, six runs and 14 additional graphs after the twelve backing graphs. It does
not implement or qualify representative ten-unique-expert/depth-two timing.
The [finite decision record](finite-execution-dispositions-20261027.md#connected-native-numerical-entry-and-finite-decision-case-3046)
binds the exact source, binary and checks and keeps representative/model work
unimplemented and dependent on physical backing/numerical acceptance.

Changed-scope case 3046 retained a staged CPU estimate `6749 + 1154 + 256 = 8159`
pages, followed by the unchanged actual 2974-page GPU-startup predicate. This
different-SELF estimate is expressly revisable and is not a hardware minimum
or measured new-SELF cost. The single existing-shell screen observed 6630 ->
6630 with matching boot. No package upload, ELF/title/GPU execution or retry
followed. The new native numerical stage is unavailable under present conditions;
it is not passed or physically impossible. No production files/settings were
changed. Overall implementation/native validation remains incomplete.

## Original-source depth-two runner, 2026-10-27

The previously missing ten-distinct-original-Expert source/cohort runner is now
implemented, default-off, and host/native-build-qualified. The [3048-3062 record](finite-execution-dispositions-20261027.md#ten-original-expertdepth-two-implementation-cases-3048-3062)
binds thirty original BF16 ranges, the actual paired source controller, native
GGML adapter and independent result/journal review. Eleven host scenarios, 110
policy refusals, 21 reviewer groups, original-byte F64/staged-F32 reference,
strict SDK compile, native link and SELF six-segment roundtrip passed. Final SELF
is `99009bc81063bb1447c5f3c8a73c62471bada4cf498bf92fff3742e9079f8c00`.
Driver/profile/archive and disabled persistent caches are unchanged.

No PS5 operation, startup retry or memory poll occurred. Forty connected graphs
(12 backing + 14 numerical + 14 original-source) remain physically unrun. The
eight-descriptor limit is per new reader; no title-wide/kernel reduction is
claimed. Native timing, model integration and adoption remain incomplete.

## Later physical comparisons, 2026-10-27

The [physical source/ready and PLE results](finite-execution-dispositions-20261027.md#physical-original-source-and-ready-comparison-cases-3067-3106)
supersede earlier pending/unavailable statements for these precise fixture
scopes. The original-source CPU cohort completed eight reverse-controlled
cases; two calls gave a 1.06735x source-fixture ratio. The full forty-graph
ready comparison passed exact/F64 numerics, actual backing, all 180 original
reads and retirement, but overlap lost both reverse comparisons by about
0.9–1.4%. The PLE widths-one-through-four comparison completed all 208 graphs;
its -0.092% to +0.046% median effects and mixed per-pair wins supplied no
repeatable gain. Both variants are closed without model integration/adoption.
Neither fixture replaces a model tokens/s measurement.

Both titles were normally closed and the exact fastest SELF/settings fully
verified after restoration. No reboot or unknown completion occurred. Native
resource state changed: the post-ready screen observed 9160 pages and admitted
PLE under its original 8190-page requirement. The post-PLE screen observed 8874.
A separately scoped 8159-page CPU entry for the existing full-model comparison
is now being prepared, retaining the native 2974-page GPU gate and operational,
pool, precision and device limits. The regular 10142-page rule remains the
default. This new staged admission has not completed a model request, reduced
kernel consumption, qualified a winner or finished the overall plan.

The [subsequent original-model control](finite-execution-dispositions-20261027.md#original-model-control-and-remaining-current-environment-limit-cases-3130-3175)
actually completed warmup and both 30-prompt/22-output-token requests at 53
slots. Decode was 0.355716 / 0.398618 tok/s; TTFT was 50.056118 / 49.220898 s.
All native output/source/shader checks and positive retirement passed. Ordinary
close and exact fastest SELF/settings restoration completed. The next B128
screen observed 6583 pages against the CPU entry price 8159; no B title ran.
The A53/B128/B128/A53 cohort is incomplete and supplies no adoption decision.
Remaining full-model validation is currently unavailable; no supported reduction
of the earlier 6749-page initial CPU interval was established. This is neither
an assertion of permanent physical impossibility nor overall plan completion.
Do not repeat unchanged refusals or request reboot.
