# Staged Expert 2-bit qualification

The owner selected Gate/Up at 2-bit with Down retained at 4-bit, followed by
all-Expert 2-bit only if mixed-model quality holds. The first candidate uses
Q2_K Gate/Up and Q4_0 Down. All 49 layers, 512 Experts per layer, top-10 routing,
non-Expert BF16/F32 payloads, F32 activation inputs and F32 KV are retained.
The original BF16 and selected Q4 production files remain intact.

Full-model conversion, physical readback, metadata sealing and complete-source
host admission have completed. Mixed generation, fixed quality and normal-app
qualification and production placement have passed. The all-Expert candidate
ran faster and retained all tested answer values, with a strict JSON-only format
regression. The owner subsequently clarified that expected quantization quality
loss is accepted. Normal monitor/API qualification is therefore continuing;
the mixed model remains installed until verified placement. Component results alone do not
establish model quality or inference throughput. The
machine-readable measurements are in [the result record](expert-q2-results-20261029.json).
The [all-Q2 bottleneck verification](expert-q2-bottleneck-20261029.md) reconciles
the completed native counters and Expert routes without another console launch.
The [requested I/O and compute measurements](expert-q2-requested-measurements-20261029.md)
separate completed historical measurements from the additional blocked diagnostic.

## Mixed counting model

Native case 8440 completed one model load and three independent requests on the
PS5. Every answer was `1, 2, 3, 4, 5, 6, 7, 8`. The two timed requests compared
all 23 full vocabulary rows and ordered Expert routes against the same-format
reference, with maximum absolute logit error zero. Source/device owners retired
positively, the device ledger returned to zero, and normal OS close plus exact
Q4/settings restoration completed.

| Request | Decode tok/s | TTFT seconds | Whole-request physical GB |
| --- | --- | --- | --- |
| 0, warmup | 0.907694 | 22.077 | 31.4160 |
| 1 | 0.914238 | 20.126 | 31.4160 |
| 2 | 0.912485 | 20.130 | 31.4160 |

Pooled timed decode was **0.913361 tok/s**, versus the earlier same-console
headless Q4 control's **0.871504 tok/s**, or **4.8028%** higher. The control
precedes this run; this is not a simultaneous matched speed comparison. Both
produce the same 22 output tokens and use 21 accepted decode transitions per
request. Physical bytes include prefill and decode. This successful counting
screen does not establish the additional quality criteria or production
adoption. The fixed Japanese instruction, arithmetic and JSON extraction
comparison below also passed before the conditional all-Expert 2-bit stage.

## Fixed quality and normal application

Cases 8500 (Q4) and 8520 (mixed) completed all nine requests, positively retired
their model/source/device owners and normally closed/restored exact Q4 settings.
Both formats returned `cat`'s Japanese translation as `猫` and `19 + 23` as `42`.
Both extracted the correct city `Tokyo` and integer count `3`; JSON whitespace
differs across formats. All same-format repeated vocabulary rows and routes
matched exactly. All three Q4-correct tasks remained correct in the mixed model,
meeting the predeclared finite acceptance rule. This is three fixed tasks,
not broad reasoning, perplexity or arbitrary-context quality certification.

The earlier Q4 quality attempt 8460 returned before GPU initialization when its
measured free pages were 1,168 against the next-phase requirement of 1,185.
After positive close/restoration, a passive sample observed 5,847 pages versus
the earlier 5,567 prelaunch minimum. Fresh case 8500 used a 5,585-page entry
screen derived from the observed 4,400-page CPU decline plus the unchanged
1,185-page next-phase requirement. It completed actual GPU inference. No floor
was reduced, no inactive memory was counted as free, and no reboot was used.

Normal passive application 8560 then passed warmup and two API requests,
all same-format output/route checks, two positively completed native frames,
positive resource retirement, ordinary close and exact Q4/settings restoration.
Both 1920 x 1080 frames were inspected: CPU/GPU information, synchronized date,
token rate and `Gate/Up Q2_K / Down Q4_0` labels are legible; there are no chat
controls. Unavailable utilization counters remain `--`.

The API requests measured **0.911676** and **0.913507 decode tok/s**,
pooled **0.912591 tok/s**. Earlier same-console Q4 normal API was
**0.869808 tok/s**, a **4.9187%** improvement in this finite counting comparison.
Both use 22 generated tokens / 21 decode transitions and exclude prefill from
decode speed. The older control is not a simultaneous ABBA run. The selected
mixed SELF is `e64cd9a49851eec0e3062651f2cac91c925ddbdeca78eebb93c78586ec017730`;
production placement completed in case 8580. Whole native hashes of the selected
program and every specified older rollback, all five settings and fresh idle
passed. The exact Q4 and BF16 programs/settings remain available. The title,
gateway and model are inactive; this finite execution binding is consumed.

## Conditional all-Expert 2-bit work

The mixed model passed the required finite quality screen, authorizing the
second stage. Gate/Up retain their existing Q2_K bytes. Down uses Q2_0 storage
with fitted signed FP16 scales, preserving its original 640-column rows. The
decoder remains `(q - 1) * d`; this encoder intentionally differs from the
pinned upstream maximum-absolute-value encoder. It chooses a signed scale by
block MSE and refines it by least squares, with explicit F32-to-F16 rounding.

All 27 original-matrix component samples matched the independent and pinned
Q2_0 decoders. Their sampled weight NRMSE was 0.351013–0.374749; the nine Down
samples were 0.351013–0.361091. Native CPU case 8574 reproduced the exact nine
host Down hashes, averaging 684.919 ms per matrix. GPU case 8600 passed 27 cases
and 324 graphs, including widths 1/2/4, repeated IDs, canaries and negative
fitted scales. Maximum own-format F64 error was 1.766e-9. Device/source owners
retired positively and ordinary close restored the exact mixed production.
These component errors do not establish language quality or model throughput.

The isolated full-model candidate keeps all 49 layers, all 512 Experts/top-10,
non-Expert BF16/F32 weights and F32 inputs/KV. Its planned 867 active cache slots
plus one staging plane fit the existing 1,333,739,520-byte budget and 512 MiB
bank cap. It reuses Gate/Up and non-Expert payloads, requiring only 11,560,550,400
new Down bytes and 11,033,888 header bytes. Down is converted directly from
82,208,358,400 bytes of original BF16 payloads; each original tensor hash is
bound to the completed native Q4 conversion's original-input proof. It never
requantizes Q4. Dense new Down files avoid sparse filesystem tail behavior.

Host native metadata controls passed complete coverage of 76 logical files,
502 physical references and 1,389 source ranges; 13 malformed plans were
refused. These controls use explicitly non-deployable synthetic new identities
and hashes. They do not attest converted all-Q2 weights or a console model run.
Actual original-BF16 Down conversion has completed all 49 tensors / 25,088
matrices, including MTP. Every new file passed whole Direct readback, all nine
independent host sample hashes matched, and workers/Direct retired positively.
The console then hashed all 151,157,049,472 logical model bytes and all 1,330
payload/header spans. Actual sealed metadata passed complete host admission
with 502 physical sources and 1,389 ranges.

Case 8680 returned before GPU initialization because the existing source
schedule self-test assumed physical source zero contained at least 16 MiB;
the all-Q2 representation uses header-only files. The isolated correction
selects the first already sealed physical payload meeting the same minimum.
Its original reference offsets, exact-byte comparisons, parallel/coalesced
counter checks, completion and memory guards remain intact. Four malformed or
duplicate host admissions were refused. The CPU-only title normally closed
and exact mixed production/settings were restored before fresh case 8780.
Completed conversion and whole-model hashing were reused.

Corrected counting case 8780 passed all three answers and complete same-format
F32 rows/routes, with zero repeated logit error. Timed decode was 1.030974 and
1.031299 tok/s, pooled **1.031136**, versus earlier same-console mixed 0.913361
(approximately 12.9% higher). Both formats generated the same 22 tokens / 21 transitions
for the same 30-token prompt. This is a historical control, not simultaneous
ABBA. All model/source/device owners retired positively, ledger live bytes
returned to zero, and normal close restored the exact mixed production.
Fixed quality case 8700 completed all nine independent requests. Translation
returned `猫` three times and arithmetic returned `42` three times. Extraction
returned the correct `city=Tokyo` and integer `count=3` three times, but wrapped
the object in Markdown code fences despite the unchanged JSON-only instruction.
Raw JSON parsing therefore failed all three extraction requests. This is a
specific instruction/format regression, not an incorrect extracted value or a
GPU arithmetic failure. Same-format complete F32 rows/routes still matched
exactly: two, three and 25 rows per repeated task, with maximum logit error zero.
All source/device owners retired positively; normal close restored exact mixed
production and settings.

The original assistant-defined rule required retention of every previously
correct raw response, including JSON format, and initially rejected this
candidate. That original result remains recorded: **6/9 strict passes and 9/9
correct answer contents**. The owner then clarified that expected quantization
quality loss is accepted and did not request continued exact quality retention.
The observed Markdown fences are recorded as an accepted tradeoff; the runtime
does not strip them or change the original strict test result. Continue the
fresh normal monitor/API case and select the faster qualified application after
positive arithmetic, source, resource, frame, shutdown and speed checks. This
finite three-task cohort does not bound broader reasoning quality loss.

The three native candidates (counting, fixed quality and correctly labeled
passive monitor) passed real runtime/driver audits and six-segment SELF
round-trip checks. Counting and fixed quality executed on the console; the
monitor has not yet launched. Before actual data was available,
the logical hash finisher compiled in
an explicitly non-deployable syntax-control mode. Its subsequent actual-data
build and console whole-logical hash pass completed; synthetic identities and
hashes were never eligible for console execution.

The larger slot count uses more of the existing cache budget: unrounded payload
banks total 1,333,248,000 bytes versus the mixed model's 1,162,137,600. Native
case 8780 realized all 867 slots. Its CPU heap peak was 402,718,720 bytes and
tracked device-ledger peak was 1,749,024,768 bytes; the latter is a scoped
allocator ledger, not aggregate console physical memory.
The bank cap and total budget remain unchanged. Twelve exact resource/identity/
completion checks and the actual selected cache/provider link map passed.

For capacity, 253 historical executable copies have complete native/host SHA256
matches and retained host backups, totaling 13,115,588,608 allocated console
bytes. After the owner's explicit deletion approval, the frozen cleanup ran
once and removed all 253 copies. Before and after deletion it verified the
whole native hashes of 11 protected files (six programs and five production
settings) and 996 retained model inode references. The native available-capacity
measurement immediately after cleanup was 18,387,435,520 bytes;
the Direct window retired positively. All BF16/Q4/mixed model files and current
and rollback programs remain intact. Final read-only audit 8790 additionally
verified the separate original MOSS rollback: seven programs and five settings
passed whole native SHA256, identity and EOF checks. Exact mixed production is
installed, with native title, gateway and model inactive. No reboot, CI or
persistent cache was used. The all-Q2 data remains isolated pending normal-app
validation and verified production placement.

| Candidate | Headless decode tok/s | Fixed quality | Final disposition |
| --- | --- | --- | --- |
| Gate/Up Q2_K, Down Q4_0 | 0.913361 | 9/9 pass | Selected; normal API 0.912591 tok/s |
| Gate/Up Q2_K, Down Q2_0 MSE | 1.031136 | 6/9 strict; 9/9 answer contents correct | Expected loss accepted; normal-app validation pending |

## Component results

| Format | Original matrices sampled | Weight NRMSE range | Native GPU cases / graphs | Maximum GPU vs own-format F64 error |
| --- | --- | --- | --- | --- |
| Q2_0 | 27 | 0.717013–0.735435 | 27 / 324 | 1.766e-9 |
| Q2_K | 27 | 0.296395–0.311307 | 18 / 216 | 3.580e-9 |

Both formats passed independent decoded-value references, canaries, repeated
Expert IDs and indexed widths 1/2/4, with positive backend retirement and zero
live device ledger bytes. Q2_K native encoding also reproduced all 27 host
reference SHA256 values. These finite matrix cases do not measure language
quality. Q2_K has 2.625 effective bits including block metadata; Q2_0 has 2.25.
Original Gate/Up rows divide Q2_K's 256-value block. Original Down rows of 640
values do not, so the first candidate keeps Down at Q4_0.

## Storage and source integration

The complete mixed model has 98 Q2_K Gate/Up tensors and 49 Q4_0 Down tensors.
The Expert triplet shrinks from 2,764,800 to 1,996,800 bytes, or 27.78%, before
alignment and cache effects. This is a byte ratio, not a promised speedup.
The original cache budget admits 581 active slots plus one staging plane under
the unchanged 512 MiB individual-bank cap.

The new physical files contain only Q2_K Gate/Up data and complete GGUF headers
and alignment padding. Composite logical ranges reuse exact sealed Q4 Down and
non-Expert payloads. Original BF16 is the quantization source; Q4 is never
requantized. Complete logical GGUF tensor coverage and offsets are retained.
Every new physical byte is densely written and fully read back in 512 MiB parts.
The retained payload SHA256, original whole-file hashes and native identities
remain independently bound by the source admission metadata.

The first packed producer ended explicitly after 59 completed files when a
write returned `-1`; a subsequent FTP publication returned `ENOSPC`. Its CPU
Direct window retired positively and no GPU was started. The original write
errno was not recorded, so the FTP error and successful continuation after
capacity recovery support storage pressure as the cause. New writes record
errno and retain a two-GiB disk margin. This is a disk policy, not a change to
kernel-memory or GPU admission.

Capacity recovery removed one archived closed trial copy and a batch of 130
explicitly listed files, including trial/layout copies and the backed-up
incomplete output.
Every retained current/older rollback was verified with whole native SHA256
before and after the batch; each removed batch file passed whole native
SHA256 and stable identity checks against its complete host copy. Original
BF16 and Q4 model source files were untouched. Measured available space
recovered to 9,128,837,120 bytes. The 59 completed files / 79 physical parts
were retained by exact native identities, and only the remaining 15 logical
files were submitted to a fresh CPU continuation. That continuation completed:
all 74 replacement logical files and all 75,264 Expert matrices are accounted
for, and both producers positively retired their CPU workers and Direct owners.
Both producer journals are preserved separately; combined receipt rows are
explicitly marked as derived. The completed model receipt covers 76 logical
files, 1,256 tensors and all 147 Expert tensors. Actual completed metadata passed
the source parser with 74 composite plans and 405 physical source references.

A sparse prototype was rejected before GPU work when readback exposed five
16 KiB zero-tail blocks within partly written 64 KiB filesystem allocation
units. Independently regenerated quantized weight bytes matched. The selected
packed representation avoids sparse holes entirely. No production data was
deleted or changed to make room for the candidate.

The isolated source derivative retains the qualified resident reader. Ordinary
single-range paired I/O stays on its existing path. Cross-range pairs use a
bounded Direct gather that handles different logical and physical alignment
residues, preserves already assembled bytes and retains completion ownership.
Host cases cover single reads, paired reads, upload callbacks, part/alias/EOF
boundaries, alignment and positive retirement. Eight malformed range plans and
nine malformed complete-source metadata plans were rejected.

Two preliminary title launches terminated before GPU initialization during
backing-metadata admission. The diagnostic launch read the full metadata with
the expected SHA256 and stable descriptor identity; its final `lstat` returned
`-1`. Native-title `lstat` had already returned `EPERM` in historical case 3474.
The corrected metadata reader uses the same independently reopened
`O_NOFOLLOW` descriptor plus `fstat` method as the qualified launch-integrity
reader. It retains all ten identity fields, the explicit 1 MiB CPU Direct
window, whole SHA256, EOF and positive close/unmap/release checks. Source-plan
admission and GPU math are unchanged. Both CPU-failed launches ended by normal
OS close and exact Q4/settings restoration; neither is model-quality evidence.

The next CPU-only return exposed an ordinary-source assumption in Direct GGUF
metadata registration: a shorter physical first part had to be exactly 512 MiB.
Packed composite file 2 has 275,252,832 physical bytes and a 1,632-byte header;
file 75 contains only its 832-byte header. Their complete logical tensor spans
are backed by the already validated composite ranges. The isolated metadata
extension therefore admits the exact complete first header prefix, independently
checks its first physical identity, retains the full logical tensor size for
GGUF span validation and bounds actual reads by physical bytes. It never pads
missing bytes, removes tensors or changes ordinary-source registration.
Focused host tests cover 832-byte and multiple-window prefixes, exact content,
aligned reads, malformed bounds, short-read quarantine and ordinary behavior.

## Implementation references

- [Q2_K encoder](../tools/expert_q2k_quantize.c): pinned `nearest_int`,
  `make_qkx2_quants`, `quantize_row_q2_K_ref` and original-BF16 wrapper.
- [Native CPU conversion](../native/qwen_flash_next/expert_q2_local_convert.cpp):
  `Source`, `Writer`, four-worker encoding, full source hashes and physical readback.
- [Composite source admission](../native/app/expert_q2_composite_source.h):
  `expert_q2_composite_source_integrity` validates complete logical regions
  against the retained Q4 receipt, proof, layout and exact payload hashes.
- [Reader derivative](../tools/expert_q2_sparse_reader.py): `reader_header` and
  `reader_source` derive isolated views; the original reader is unchanged.
- [Composite metadata window](../native/app/expert_q2_metadata_window.h) and
  [its isolated derivative](../tools/expert_q2_metadata_reader.py): separate
  physically readable header bounds from the complete logical tensor span.
- [Native relink](../tools/build_expert_q2_composite.py): replaces the comparison
  entry and qualified resident source-owner object, preserving GPU providers.
- [Model comparison](../tools/expert_q2_model_source.py): `entry_source` and
  `cache_source` preserve original guards and F32 inputs, select the compressed
  cache, and distinguish quality failure from GPU completion uncertainty.
- [Metadata sealing](../native/qwen_flash_next/expert_q2_seal.cpp): full Direct
  metadata hashes, identities, EOF, own-file permissions and positive release.
  Three new metadata files are staged outside the title, verified, and renamed
  into their owned destination without overwriting existing paths or changing
  production-directory permissions.
- [Upstream license](../third_party/notices/ggml-quantization/NOTICE.md).
- [All-Q2 source schedule preflight](../tools/expert_all_q2_preflight.py):
  `reader_header` selects a sufficiently large sealed payload while preserving
  offsets, exact hashes and parallel/coalesced read checks.
- [Owner relink](../tools/relink_expert_all_q2_preflight.py) and
  [focused preflight controls](../tests/expert_all_q2_preflight.cpp): retain
  exact cache/provider linkage and refuse malformed or duplicate admissions.

Upstream llama.cpp is pinned to
[`0a1ef309cdbb9f2024f58a38fb4c42352c5db569`](https://github.com/ggml-org/llama.cpp/tree/0a1ef309cdbb9f2024f58a38fb4c42352c5db569).
The driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, with persistent caches disabled. No CI or reboot was used.

The [fixed quality cohort builder](../tools/build_expert_quality_cohort.py)
uses three predeclared prompts, three independent requests per prompt, complete
same-format output rows/routes, and separate answer-quality predicates.

## Acceptance

Follow [the finite staged plan](expert-q2-plan-20261029.md). A completed mixed
counting regression is a tested quality failure and stops the conditional
all-2-bit stage. If counting passes, compare a fixed Japanese instruction,
arithmetic and extraction/JSON cohort against Q4, requiring retention of every
Q4-correct answer. Measure decode separately from prefill on the same console.
That mixed-stage condition was met. For the subsequent all-Q2 adoption, apply
the owner's later acceptance of expected quality loss, retain the original
strict results, and require passing source, arithmetic, completion, normal-app
and measured-speed checks. The exact mixed, Q4 and BF16 controls are retained.

## Measured cache policy and selected all-Q2 production

Actual all-Q2 case 8900 compares aged-LFU/probation/probation/aged-LFU in one model lifetime at 867 slots and 1,333,739,520 cache bytes. Decode improves 1.029182 to 1.127026 tok/s (+9.507%). Complete F32 rows have zero difference and ordered routes match. All native owners retire; ordinary close and exact control restoration pass.

Final normal passive/API case 8940 measures 1.126481 and 1.125980 tok/s, pooled **1.126230**. Both actual native frames were viewed with correct precision, UTC clock, CPU/GPU and 1.13 tokens/s information. Placement 8950 verifies the complete canonical app, every retained mixed/Q4/BF16/older rollback and all five settings, with fresh idle. Selected SELF is `06e096630ce08b1a4b865798f7070295f74c9b5bb33fa7d0c32a5ad2bf729590`. Expected Q2 loss remains disclosed: strict format 6/9, answer contents 9/9, no output normalization.

CPU-only actual-weight case 8914 reduces three same-byte reads to one: read-wall throughput improves 44.298% (time decreases 30.699%). This component result is not whole-model acceleration; bundle model integration and the other six optimization gates remain open in the maintained plan. No CI, reboot or persistent cache was used.
