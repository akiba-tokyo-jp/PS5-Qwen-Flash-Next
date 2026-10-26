# Remaining validation: execution progress

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

## Remaining package scope

The peak-live allocation review, broader tokenized workloads, ready-expert
execution, hidden-state observation/forecasts, prefix reuse, exact speculative
verification/adaptive width and eligible graph specializations remain incomplete.
The finite complete-state continuation comparison has passed. Device checkpoints
are not ruled out by the rejected CPU snapshot. The existing cache cap still
cannot hold an extra expert with the current qualified three-bank ownership and
dispatch geometry. A hypothetical byte-storage view passed host geometry only,
with a very small route-traffic benefit. See the plan for each remaining
prerequisite and adoption gate.
