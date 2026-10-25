# Original-precision GPU optimization results

This sequence keeps the original BF16 model, F32 KV, all experts and PLE,
512 MiB source parts, 53 expert slots, prefill four, context 256 and every
existing reserve and completion deadline. The driver remains
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, native
archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent caches and CI remain disabled. Physical qualification is in progress;
production publication follows the final exact-artifact qualification below.

| Technique | Application location | Evidence and disposition |
| --- | --- | --- |
| Completed decode profiling | `native/app/native_main.cpp::performance_snapshot`, `llama_engine.cpp`, patches `0003` / `0004` | Per-token completed snapshots distinguish source wait, consumer time, BF16 matrix/vector calls and mapped/staging uploads. No timestamp queries or additional GPU commands. |
| BF16 indexed-vector dispatch | `native/app/indexed_vector.h::bf16_indexed_vector_layout`, `llama_engine.cpp::process`, `0004-ggml-vulkan.patch` | Existing original shader; narrow decode-only predicate. Four real-shape fixtures passed with maximum error zero. The first full attempt completed one identical 22-token answer at 0.348609 tokens/s but refused kernel headroom during request two. It is not adopted. |
| Four source reads | `native/app/queued_source_io.h`, `native/qwen_flash_next/queued_source_probe*` | Exact trace CPU comparison: two 4 MiB windows versus four 2 MiB windows, unchanged total 8 MiB. Six rotated rounds: 0.959267 versus 0.969127 GB/s median. Approximately 1.03% is inconclusive; the paired time-saving interval includes zero. No production integration. |
| Eliminate upload staging | `0003-ggml-vulkan-buffers.patch`, upstream `ggml_vk_buffer_write_2d` | Actual decode uploaded 94.540 GB through mapped coherent writes and zero staging bytes across 21 processes. There is no staging copy to eliminate in this workload. |
| Direct reads into expert banks | `native/app/mapped_source.h::pipeline_windows`, `0002-llama-moe-cache.patch` | Existing logical GGUF payload offsets do not generally share the bank destination's 16 KiB alignment. Read padding cannot overwrite adjacent/live slots. Requires a separately admitted layout/gather design; no unsafe pointer import or bank overwrite is implemented. |
| Existing known-miss overlap | `PairedSourceIO::pipeline`, `MappedSourceReader::upload_pair`, `0002-llama-moe-cache.patch` | Already implemented and physically qualified before this sequence. Selected safe parallel/coalesced paths remain in use. Additional cross-pair scheduling remains a separate design, without a measured speed claim. |
| Flash Attention and GPU recurrent state | `native/app/llama_engine.cpp::streaming_context_params` | Current native diagnostics already report `resolve_fused_ops: Flash Attention enabled`, Vulkan KV and Vulkan recurrent state. Re-enabling an existing path is not a new optimization. |
| Host shared-prefix checkpoint | Upstream hybrid-state APIs, current `model_cpu_budget.h` | At least 118,038,528 recurrent/PLE bytes are needed before attention/logits. The split512 peak leaves only 83,820,544 bytes in the unchanged CPU budget. This host-buffer variant fails its capacity prerequisite. A streaming/device checkpoint remains separate work and would affect warm TTFT. |

The measured first-to-last decode interval of the first vector attempt contains
21 processes and 3,024 indexed-vector calls. Source wait is 50.028 seconds out
of 59.469 seconds of process time (84.12%). Consumer time is 5.707 seconds.
These counters are completed intervals; accumulated transfer bytes are not
resident memory or a measurement of SSD peak bandwidth. They do not establish
that shader tuning alone will materially improve whole-model speed.

## Frame evidence memory qualification

`native/app/direct_bmp.h::stream_direct_bmp` preserves the exact 1,920 x 1,080,
32-bit, bottom-up BMP: 8,294,454 logical bytes. It uses one aligned 1 MiB output
window, zero physical tail padding and an exact final length. The native sink
only opens a fresh process-owned file and releases its window only after
returned writes, durable commit, stable identity and returned close. A failed
operation retains backing for ordinary OS title close.

The CPU AB/BA comparison wrote four fresh synthetic files. All full SHA256
digests matched; every write/read/commit/close and Direct lifetime call returned;
fresh idle CPU/session checks passed. Original model and title were untouched.

| Order | Mode | Free pages before | After write | After independent Direct hash |
| --- | --- | ---: | ---: | ---: |
| 1 | Ordinary | 5,730 | 5,222 | 5,730 |
| 2 | Direct | 5,730 | 5,726 | 5,730 |
| 3 | Direct | 5,730 | 5,726 | 5,730 |
| 4 | Ordinary | 5,730 | 5,222 | 5,730 |

Ordinary persistence reduced free pages by 508 (7.9375 MiB), Direct by four
(64 KiB). This is reproducible CPU evidence for the persistence mechanism,
not proof that it was the sole cause of the loaded-model refusal. The app's
optional Direct capture preserves all monitoring, raster bytes, original
8-second persistence / 10-second capture bounds, CPU budget and kernel/Flexible
reserves. The display thread uses the read-only memory observer and does not
share the inference producer's mutable backpressure controller.

## Qualification status

The initial Direct-frame app passed its native link, actual module import audit,
SELF integrity and all six segment roundtrips. Its subsequent complete control
failed as described below. Neither partial inference nor CPU-only screening
qualifies production adoption.

The first integrated frame case also failed its complete qualification. Its
first 22-token answer exactly matched the control at 0.343747 tokens/s, but the
new frame metadata check refused before any image write. Positive device idle
and completed-epoch request reset preceded that CPU exception. Ordinary close,
exact restoration, fresh original numerical admission, ordinary shutdown and
final idle/full SELF checks passed. No second inference request was retried.

The native CPU-only isolation found that title `fstat` reports UID/link fields
as zero, unlike the independent physical filesystem observation (UID 1/link 1).
A path-based metadata variant then refused with `EPERM`, without any GPU work;
its original restoration/final checks also passed. The selected driver's
`benchmarks/llm_vulkan_qualification/main.c::run_llm` already documents that
native sandbox limitation and uses descriptor metadata.

The next candidate therefore explicitly selects a native descriptor profile:
the original UID 1 process creates a fresh single-component application filename
with `O_EXCL|O_NOFOLLOW|O_DIRECT`, retains the private descriptor, and verifies
stable device/inode/mode, exact writes/length, Direct flags, durable commit and
returned close. Unavailable UID/link fields are never presented as real owner
metadata. Its CPU qualification additionally requires an independent exact-owner
physical UID 1/link 1/length check. That CPU qualification subsequently passed:
all eight writes, durable commit, exact truncation/length, returned close,
independent complete BMP digest and physical UID 1/link 1 checks succeeded.
Ordinary close, exact original restoration, final idle CPU/full SELF readback
also passed. This is separate from full-model/display qualification.

The observed premature successful stream terminal before frame capture has
also been corrected. Final metrics update the passive monitor internally;
successful completion is published after frame persistence. The actual host
transport passed two normal requests, scope refusals and three failure cases,
including frame failure after final metrics: exactly one failed terminal is
returned, internal monitor progress is not streamed, and listener shutdown ends.

The subsequent complete vector-OFF control at SELF
`d6841015f8c7836cc26d5c688f7d968ca28b41065052952daa03b3eeec187d98`
passed arithmetic and external prefill/first sampling, then refused the next CPU
work boundary at 1,070 free kernel pages versus the unchanged 1,154-page floor.
Its 20-second bounded passive wait ended normally. No frame capture had started;
all preceding source windows and GPU completion/epoch records were positive.
Ordinary close, exact restoration, fresh original numerical readmission,
ordinary shutdown and final idle CPU/full SELF readback passed. This consumed
case is not replayed and supplies no completed decode-throughput result.

After-context free pages were 2,922 in that case versus 2,898 in the successful
512 MiB control. Therefore startup free-page count alone does not explain the
failure. A default-OFF, fixed 64-entry owner-thread observation ring now samples
the existing inference, CPU guard, token-report and publish boundaries. It uses
read-only memory counters and tracked-heap statistics, with no file writes while
sampling, allocation, reclamation, admission decisions or retries. Observation
failure preserves earlier samples without changing the real admission guard.
The trace is diagnostic; it does not establish a cause or a speedup.

The installed SDK revision `b83202be73e930050e00de0f1b4d9ec46c0391bf`
provides optional pthread wrappers in `platform/src/threads.c`. Inspection found
that they replace small default stacks with 2 MiB Direct allocations, keep up
to 32 cached stacks, and may fall back to library stacks. Those allocations are
outside the app's tracked malloc heap. Adding the link flags alone would not
establish memory savings or preserve complete budget accounting, so the wrappers
are not integrated or presented as a proven fix. Driver/profile/cache policy and
the SDK remain unchanged.

## Completed instrumented control

The distinct vector-OFF control at SELF
`9f6d582d1be3ec3376bbcf500fa68c70919a7ec07962ef949710c07c0b5872fb`
completed the complete finite physical sequence. Arithmetic and both 22-token
external outputs/token IDs matched the control. Decode was 0.343633 / 0.350158
tokens/s; TTFT was 57.629 / 56.714 seconds. Both actual native frames were
viewed. Source/GPU/model retirement, ordinary close, exact original restoration,
fresh original numerical readmission, ordinary shutdown and final idle/full
executable readback all passed. The 484 frozen inputs remained unchanged.

There were 146,461 admitted memory observations, zero pressure events and zero
passive wait time. The diagnostic's final 64 samples ranged from 1,402 to 3,118
free kernel pages; tracked CPU heap peak remained 453,050,368 bytes. This is a
completed short control, not proof of sustained stability or a sole explanation
for earlier failures. The same executable is selected for the policy-only
vector comparison; no archive rebuild, model conversion or retransfer is needed.

The trace payload was bound through its unique fresh evidence path and completed
owned native-plan report. It lacks duplicate owner/run fields in the payload
itself; preserve that limitation in diagnostic attribution. The inference and
retirement reports retain their independent exact owner/run checks.

## Repeated vector comparisons

Two completed vector cases first produced 0.348516 / 0.355333 and
0.348456 / 0.356073 tok/s. The second added four non-BF16-exact F32 input
checks; maximum absolute error was at most 2.51e-8 against the unchanged
1e-6 limit and independent F64 references. The original 24 timed graphs retain
identical dyadic inputs for both strategies; four extra vector graphs qualify
actual unrounded F32 activation handling. All source/GPU/model retirement,
frames, exact original restoration, numerical readmission and final idle/full
SELF checks passed. These short outputs do not establish broad model quality.

A subsequent control refused its CPU guard after the first external token:
1,044 free kernel pages versus 1,154 after the unchanged 20-second passive wait.
Every preceding source/GPU completion was positive; normal close, exact original
restoration, fresh numerical readmission and final idle/full readback passed.
The preserved refusal is not a throughput sample and was not replayed.

A dedicated CPU report-writing diagnostic then completed six closed files with
identical independently verified full JSON bytes and physical UID1/stable inode
checks. Its auxiliary trace was partial because verbose Direct labels exceeded
the ring's 63-character limit; that label bug was fixed separately. Initial
kernel-page loss also occurred during an idle interval; later heap, stack and
Direct writes each consumed about four pages. This does not support adopting
Direct JSON as a proven solution to the loaded-model refusal. The original
application was restored and the same-boot numerical admission preserved.

The final matched comparison used exactly the same SELF in both arms. Both
executed the same 28 fixture graphs and passed the same 2,974-page postfixture
startup target. Only decode dispatch differed:

| Request | Matrix control | Vector candidate | Observed gain |
| --- | ---: | ---: | ---: |
| Cold, 30 prompt / 22 output tokens | 0.343754 tok/s | 0.348566 tok/s | 1.400% |
| Warm, same workload | 0.350816 tok/s | 0.355464 tok/s | 1.325% |
| Mean | 0.347285 tok/s | 0.352015 tok/s | 1.36188% |

TTFT was 57.519 / 56.689 seconds for control and 57.595 / 56.666 for candidate.
Output bytes, token IDs and stop reasons matched. Both native frames were
actually viewed in both arms. Positive source/GPU/model retirement, ordinary
close, exact original restoration, fresh original numerical readmission,
original shutdown and final idle/full executable readback all passed. Earlier
completed repeats agree in direction. This supports the narrow vector route
as a small measured improvement; it does not imply statistical significance for
arbitrary prompts or a 100 tok/s opportunity.

Routing remains a material attribution limit. In the earlier comparison all
prefill routes matched, while 258 of 1,056 single-token records changed expert
sets, with 370 individual replacements. The vector path accepts F32 activations
without the matrix route's RHS preparation rounding. No weights/KV were reduced
in precision. Report the observed end-to-end result rather than assigning the
entire gain to a single shader or claiming identical intermediate logits.

The owner-authorized adoption decision is therefore conditional on a final
exact-artifact full sequence after the isolated transfer probe. Temporary
qualification does not switch the original MOSS executable or enable a general
unattended inference service.

## Isolated owned-mapping transfer gate

The next default-OFF fixture uses a real device-buffer allocation through the
same ggml allocator policy as expert banks. A small backend bridge uses the
exact pinned internal headers and holds the actual `vk_buffer` across a
synchronous callback. It checks ownership/type, complete allocation bounds,
DEVICE_LOCAL/HOST_VISIBLE/HOST_COHERENT flags and 16 KiB destination alignment.
It imports no arbitrary CPU pointer and changes no driver or engine archive.

One aligned 3,276,800-byte read at offset 131,072 of the sealed eighth logical
member's first physical part must match a separately verified host fragment
hash. Returned incompatibility can reject the candidate after stable identity
and close; unknown I/O retains backing without retry. A compatible result runs
the real 2560x640 BF16/F32 matvec against an independent F64 reference and six
rotated ordinary/non-temporal copy blocks, with full byte equality and positive
GPU completion after each block. The fixture never loads the model or starts
VideoOut. Eligibility, kernel numerics and whole-model speed remain separate.

See [the primary-source assessment](ps5lm-transfer-assessment-20261025.md) for
the external benchmark conditions, transfer table and exact source targets.

The first isolated probe completed all seven GPU references, full payload hash,
six copy-byte checks and positive device/epoch/probe-buffer retirement. Its
final CPU cleanup then correctly refused an unenabled post-load device ledger:
the new probe had skipped the model-load enable point. No model or display had
started. Independent current owner and stable driver logs admitted ordinary
close, exact original restoration, fresh original numerical readmission,
original shutdown and final idle/full executable readback. The missing timing
report was not reconstructed or counted as a performance result.

The corrected distinct artifact enables and checks the unchanged ledger before
allocation and preserves a preliminary report before final source shutdown.
Its complete isolated physical plan passed, including original restoration and
fresh numerical readmission. One Direct read returned all 3,276,800 expected
bytes with the exact host fragment SHA256. Actual buffer flags were
DEVICE_LOCAL | HOST_VISIBLE | HOST_COHERENT. All seven matvec references passed
with maximum absolute error 4.656612873077393e-10. The accounted device-ledger
peak was 272,629,760 bytes; final live bytes were zero. That ledger peak includes
its conservative workspace reservation and is not a measured resident payload.

| Copy block, five copies each | Ordinary memcpy | Non-temporal stores |
| --- | ---: | ---: |
| First sample | 1.123398 ms | 0.642125 ms |
| Second sample | 1.121072 ms | 0.640281 ms |
| Third sample | 1.124120 ms | 0.647497 ms |
| Mean | 1.122863 ms | 0.643301 ms |

The actual order was A, B, B, A, A, B. Every copied byte matched and each block
was followed by a completed GPU numerical check. The approximately 42.7% copy
time reduction is a warm small-buffer result, not SSD bandwidth or whole-model
speed. The next candidate preserves the existing read/coalescing schedule and
cache layout while changing only eligible decode copies from completed owned
source windows. It remains default OFF until a completed matched full-model
comparison supports adoption. The padded direct-bank inference path is still
separate, even though its first mapping/I/O prerequisite now passes.

## Complete non-temporal copy comparison: rejected

The matched full-model comparison used the same SELF in both arms, the same
28 original-shape fixture graphs and the qualified indexed-vector route. All
precision, source scheduling, cache sizes, driver and completion guards matched.

| Request | Ordinary copy | Non-temporal copy | Outcome |
| --- | ---: | ---: | --- |
| Cold, 30 prompt / 22 output tokens | 0.348004 tok/s | 0.335749 tok/s | Slower |
| Warm, same workload | 0.355322 tok/s | 0.342571 tok/s | Slower |
| Mean relative change | Control | -3.55552% | Reject; keep disabled |

TTFT was 57.612 / 56.700 seconds for control and 57.613 / 56.701 seconds for
candidate. Every prefill and decode route record, logical upload byte count and
physical read byte count matched. Output bytes and token IDs also matched.
Both cases passed viewed native frames, positive resource retirement, ordinary
close, exact original restoration, fresh original numerical admission, normal
original shutdown and final idle/full executable readback.

For the first 21 decode processes, 94,538,959,548 bytes used the coherent mapped
branch in each arm. The candidate actually streamed 94,538,956,800 bytes across
28,837 copies. Source consumer time rose from 5.728404 to 6.388436 seconds
(+11.5221%); source wait rose from 50.066032 to 50.784171 seconds, and total
process time from 59.521708 to 61.726819 seconds. This disproves adoption from
the warm copy microbenchmark alone. It does not identify a hardware cache cause.
No repeat or small tuning of this slower variant is planned.

The next candidate eliminates eligible copies with directly owned padded-bank
reads. Its host dispatch and extent controls cover all 30 actual offsets, four
original layouts and 53 active slots, within the unchanged 512 MiB cache cap.
At that point GPU layout eligibility and full-model speed were still separate
uncompleted gates. Both subsequent completed stages are recorded below.

## Padded bank layout: complete physical eligibility gate

A distinct isolated artifact completed one exact 3,293,184-byte Direct read
from the sealed original file and 360 Vulkan numerical graphs: two original
matrix shapes, one/ten F32 input vectors, all 30 actual source residues, and
matrix/vector/non-BF16-exact F32 strategies. Repeated/boundary IDs included
slot 52. All 120 layout records passed; maximum absolute error was
1.7171259969472885e-9 against the unchanged 1e-6 limit and F64 references.
All bank bytes and the spare-plane sentinel remained intact.

The actual descriptor alignment was four bytes and memory flags were
DEVICE_LOCAL | HOST_VISIBLE | HOST_COHERENT. The accounted device-ledger peak
was 450,887,680 bytes, including the conservative workspace reservation. All
eight ledger allocations retired to zero live bytes. Source workers stopped;
ordinary close, exact original restoration, fresh original numerical admission,
ordinary original shutdown and final idle/full executable readback all passed.
No model load or VideoOut occurred. This qualifies layout/ownership/numerics,
not full-model speed.

The subsequent default-OFF integration preserves 53 active slots, 54 physical
planes and the 512 MiB cap. Actual eligible reads target strongly owned mapped
bank slots. Consecutive Expert runs retain their coalesced original source
windows and scatter payloads into padded slots. Cross-part/EOF envelopes and
coalescible pairs select the qualified staged path before any I/O starts.
Unknown or failed reads quarantine backing without fallback or retry. The
actual-reader host controls cover exact writes, all original residues, last-slot
guards, selected parallel/serial/single reads and failure retention. Full-model
comparison subsequently passed as recorded below.

## Final same-SELF full-model comparison: selected

The final application SELF was
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`
(28,017,271 bytes). Both arms used that exact executable, P1 indexed-vector
decode, the same 28 fixture graphs and the unchanged startup target. Only the
owned padded-cache policy differed. Driver, precision, all experts/PLE, 512 MiB
physical model parts, 53 active slots, 512 MiB cache, 8 MiB source window,
30-token prompt, 22-token output, context 256 and prefill four were unchanged.

| Request | Qualified ordinary-copy control | Owned direct-bank candidate | Observed gain |
| --- | ---: | ---: | ---: |
| Cold | 0.348376 tok/s | 0.390685 tok/s | 12.1447% |
| Warm | 0.354832 tok/s | 0.398193 tok/s | 12.2204% |
| Mean | 0.351604 tok/s | 0.394439 tok/s | **12.1829%** |

TTFT fell from 57.650 / 56.676 seconds to 50.145 / 49.260 seconds; mean
57.163 -> 49.702 seconds. Every output byte, token ID and Expert route record
matched. Physical read bytes and call counts also matched exactly. This is a
completed two-request comparison on one console, not a broad quality/context
or sustained-service claim.

| Completed 21-step decode interval | Cold control -> candidate | Warm control -> candidate |
| --- | ---: | ---: |
| Logical source bytes | 94,539,171,840 -> same | 92,474,787,840 -> same |
| Physical source bytes | 95,012,347,200 -> same | 92,937,788,736 -> same |
| Physical read calls | 28,993 -> same | 28,372 -> same |
| Source consumer time | 5.726372 -> 0.176574 s | 5.598851 -> 0.171342 s |
| Source read wait | 50.027639 -> 48.938901 s | 49.062363 -> 47.980861 s |
| Process time | 59.473732 -> 52.929471 s | 58.381768 -> 51.921928 s |
| Direct-bank share of logical source bytes | 0 -> 96.9947% | 0 -> 96.9985% |

The whole-request counters independently satisfy direct-bank payload plus
staged scatter payload equals the actual cache-miss upload count. No
non-temporal copies ran. These measurements support copy elimination as the
main observed mechanism; they do not establish a proprietary hardware cache
cause for the smaller change in read wait. Source wait still dominates after
copy elimination, so further shader specialization remains deferred pending a
measured kernel bottleneck.

Both actual native frames were viewed in both arms. Positive source/GPU/model
retirement, ordinary candidate close, exact original restoration, fresh original
numerical readmission, ordinary original shutdown and final idle CPU/full SELF
readback all passed. The two finite controllers ended with all 525 / 527 frozen
inputs unchanged. No native owner, gateway or loaded model remains. There was
no CI, driver/shader rebuild, model conversion/retransfer, force kill, reset or
automatic retry.

The owner-authorized selection is the indexed-vector route plus owned direct
bank reads, with the qualified coalesced/scatter/split/EOF fallback. The slower
non-temporal path and inconclusive four-read proposal remain disabled. The
adopted exact-artifact policy is in
[`config/qualified-performance.json`](../config/qualified-performance.json);
its offline application was checked against the actual measured policy, with
all other bindings preserved and 11 invalid inputs refused. See
[sanitized machine-readable evidence](native-owned-bank-success-20261025.json)
and [usage](qualified-performance-20261025.md).
