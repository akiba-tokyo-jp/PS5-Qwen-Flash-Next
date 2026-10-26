# Remaining validation: execution progress

This is an intermediate execution record for the
[remaining-proposal plan](remaining-validation-plan-20261026.md). The overall
implementation and validation request is incomplete. Fixture qualification
does not establish generation speed, full-model acceptance or production adoption.

The qualified production control is
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
Temporary native fixtures preserve that control and restore it after ordinary
closure; publication of a diagnostic SELF does not adopt it. The completed CPU
cases below made no title, GPU, model-file or application
changes. The driver selection remains `872cc126` / `cumulative-idle`, with
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

## Remaining package scope

The peak-live allocation review, broader tokenized workloads, ready-expert
execution, hidden-state observation/forecasts, prefix reuse, exact speculative
verification/adaptive width and eligible graph specializations remain incomplete.
The finite complete-state continuation comparison has passed. Device checkpoints
are not ruled out by the rejected CPU snapshot. The existing cache cap still
cannot hold an extra expert with the current three-bank geometry and spare
planes. See the plan for each remaining prerequisite and adoption gate.
