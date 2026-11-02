# PS5 Qwen Flash Next

Experimental **Qwen3.8-Flash-Next on one PlayStation 5**, streaming the complete
text model from SSD into bounded shared memory. The original baseline is BF16;
the owner subsequently authorized routed-Expert/resident quantization and lower
active decode Expert counts. Every Expert and
required model component is retained. Learned PC/cloud inference is not used.

## Current status

The new hardware-bound performance campaign is active. The owner-authorized
successful startup route now positively completes current-model inference on
this boot, with ordinary closure and exact selected-file restoration. Read the
[latest native comparisons](docs/native-performance-comparisons-20261102.md).
R1 is adopted after complete-request ABBA gains and exact whole-vocabulary F32
comparison. P1's measured profile is not adopted. G1's observational
state qualification passes; GPU numerics/speed and other candidates remain.
The single runtime initialization is consumed and must not be repeated.

The owner closed every current AMPR/APR/PFS, Kraken, compatibility-initializer
and runtime-entry investigation as failed on2026-11-02. No candidate from that
campaign is adopted and no remaining validation is queued. See the
[closure and current-only cleanup record](docs/current-validation-closure-20261102.md).

The selected current application is the scheduler-owned-map program:
SELF `a786b8adfe2fe0bbfb196fe696f644024bb3d090734f97a5533a6d6845ee415e`,
application source overlay `9601f9048dc943cf28705f3e8ec784d8d91ca54a` over
the retained base `2b683814c9b6ed18c13352963c0a989f9e4d0b15`.
The PC package is `D:/PS5-AI/qwen-flash-next/current`; PS5 retains this same
program, five settings and required model/startup assets. Historical trial
files and older deployed programs are retired. Driver872cc126/cumulative-idle
and disabled persistent caches remain. Current-boot inference succeeds with
the explicitly repaired dependency identities. The original56c deployment
is replaced by the qualified R1 application on both PC and PS5. Completed token
ledgers synchronize before the request result; an interrupted request can lose
its unsynced ledger tail. Retained/prefix complete spans improve1.22%/1.64% in
the matched fixed workload, including final sync and close; no cold gain is claimed.

### Historical throughput control

The throughput campaign is complete: normal56100 and verified placement56200.
Selected SELF9824030372e2eed7204275209a9bb6a6700a385ced8f9ca6e40d22fae258c135,
sourcec60c1ab891dbbcf250db2bf919fa323f0ebc8727. Use `tools/throughput_production.py`,
`docs/throughput-results-20261101.md` and `docs/throughput-adoption-20261101.json`.
All four candidates have actual dispositions: selectT1/T3 (throughput mode5);
T2 GDN join andT4 WAR synchronization are completed negatives and excluded.
Six complete native cohorts total84 requests, plus60 synthetic synchronization
graphs and3 actual normal/API generations. Current-core55900 retained decode
11.291957 ->12.234850tok/s (+8.350123%); final normal cold9.759321,
retained11.574572 and prefix12.801323tok/s. All3 normal counting tasks pass.
Two actual native frames, all3 ledgers, positive ownership retirement, ordinary
close, exact1a76 restoration,12-file native placement and42 refusal controls pass.
Expert triplets cover22968/24576 Experts in66 immutable SSD parts;1608 retain
original reads. Cache3712/3713, precisions, driver872cc126/cumulative-idle,
persistent caches disabled and original memory/OS/worker/completion/durability
controls remain. No GPU/CPU/usage values are fabricated. Native/gateway/model
are inactive. Preserve exact1a76 immediate rollback and historical4f5d controls.
Normal build/package are `D:/PS5-AI/qwen-flash-next/build/Throughput-normal-56080`
and `D:/PS5-AI/qwen-flash-next/build/Throughput-normal-SELF-56088`.
All finite cases are consumed; never replay them or depend on reboot.

### Historical frontier control

The four ordered owner/HC/command categories are verified in five complete
native comparison cohorts (70 requests), followed by normal53100 (three
generations). Winners1/2/3 are installed through verified placement53200.
See [results](docs/frontier-results-20261101.md),
[adoption](docs/frontier-adoption-20261101.json),
[all dispositions](docs/frontier-worklog-20261101.json) and
[installation](config/production-installation.json). The preceding
[service/kernel](docs/service-kernel-results-20261101.md),
[load analysis](docs/load-followup-results-20261101.md) and
[post-Top2](docs/post-top2-results-20261101.md) records remain historical controls.

Selected frontier mode7 adds duplicate durable owner-checkpoint reuse, checked
adjacent Q8 HC Down/Inject weight aliases with one shared-input projection, and
shape-limited HC split-K4. Existing service mode69 retains per-token fsync,
positive same-generation GPU completion, all fresh owner/retirement checks,
node256/divisor40 and the qualified tail policy. HC prefill/TTFT improves;
recorded secondary-command reuse is measured negative and excluded. Split-K8
has no stable whole-time gain and fails one fixed task; split-K4 passes all four.

Actual normal decode: cold8.278168, retained weights/empty request10.825984,
exact-prefix/causal12.099275tok/s,22 generated tokens each. Retained TTFT is
0.397102s and whole request2.438066s. All three current counting answers pass.
Normal50100 and53100 are sequential configurations, not ABBA. Prefix output
changed from the previous incorrect25-token answer, so its rate is not a
same-output speed comparison. Kernel reduction order changes full F32 values
(max9.860172510 in the split-K4 comparison); independent candidate F32/routes
repeat exactly. Finite task passes are not unchanged general model quality.

Expert Gate/UpQ2_K and DownQ2_0 MSE,109 resident Q4 matrices including output,
remaining Q8/original F32/tiny BF16 PLE, F32 KV/recurrent state,3712 active
slots/3713 planes,5703659520 cache bytes and all allocation caps remain.
Initial-prefill placement1444, later/decode768, Top2 decode and six-Expert
prefill remain. Driver872cc126/cumulative-idle and disabled persistent caches
remain. No CI, host inference, restart or reset is used.

SELF1a76c37007962b9da767b0e70667d140bfaeb2138a4d29925245958afd84047e
is natively verified with the exact immediate4f5d control and five settings
each (twelve files). Thirty rejection controls and current admission pass.
All source/model/GPU owners positively retire; ordinary close and exact
restoration precede verified placement. Native/gateway/models are inactive.
Finite launch bindings are consumed; never replay them or depend on reboot.

## Historical cold and different-input campaign

**Cold and different-input improvements are qualified and installed.** See the
[results](docs/cold-request-results-20261030.md),
[complete adoption evidence](docs/cold-request-adoption-20261030.json) and
[installation record](config/production-installation.json).

| Normal application metric | Previous10760 | Selected10970 |
| --- | ---: | ---: |
| Independent decode |2.892716 tok/s |**3.717603 tok/s (+28.516%)** |
| Exact-repeat decode |4.534210 tok/s |**5.261777 tok/s (+16.046%)** |
| Independent TTFT |7.460586 s |**5.719974 s (-23.331%)** |
| Independent whole request |15.038473 s |**11.635879 s (-22.626%)** |
| Capture-charged pair throughput |2.159641 tok/s |**2.708417 tok/s (+25.411%)** |

The selection combines prefill32, exact indexed probation and continuous
four-lane demanded Gate/Up/Down reads using the original8 MiB scratch. Cache
stays1381 slots; ExpertQ2, output/shared144Q8 and F32 activation/KV are unchanged.
Workspace reservation/cap tightens64 ->48 MiB around measured8 MiB capacity;
original CPU/physical Direct512 MiB and total device limits remain.

All four different-input pairs improve with empty application caches and
prefix/speculation disabled: total49.022730 ->40.137210 s. Complete F32 logits,
ordered routes, output bytes and tokens match across delivery modes. Contents
pass8/8; raw format6/8 because both JSON outputs retain Markdown fences. Normal
independent F32 repeat error is0; final unlike-cache/width maximum3.935983 is
finite with identical counting tokens. These are finite short tasks and
sequential normal cohorts, not ABBA, broad reasoning or sustained service.

Two causal layer-quota variants increase misses. The actual early-router
observer shows no whole-request gain and few useful miss predictions; physical
predictive I/O is screened out. Independent source wait falls9.986 ->6.750 s,
but P99 read latency increases to[3.072,3.200) ms. Syscall/producer intervals do
not isolate raw SSD service time; diagnostic GPU sums are not ordinary wall
percentages. See the report for counter semantics and retained failures.

Placement11050 installs SELF57043cbe with exact immediate5c5 control and both
sets of five settings verified by native whole SHA256/identity/EOF. Ownership
and fresh idle are confirmed; the native app/gateway/models are inactive.
Driver872cc126 cumulative-idle and disabled persistent caches remain. No CI,
reboot, forced signal or reset is used. Optional55-old-settings deletion is a
separate unresolved permission item, not an inference prerequisite.

## Previous shared-Q8/cache1381 control

The prior memory/delivery/graph campaign remains complete in its
[results](docs/memory-delivery-graph-results-20261030.md) and
[adoption evidence](docs/memory-delivery-graph-adoption-20261030.json).
Placement10820/SELF5c5 is now the immediate control. Its source/configuration
and the earlier measured candidates remain preserved as historical evidence.

## Previous output-Q8/997 production control

**The six-candidate composition is implemented, qualified on the PS5, and
was installed before the current memory composition.** See the [results](docs/six-candidate-results-20261030.md),
[sanitized evidence](docs/six-candidate-adoption-20261030.json) and
[installation record](config/production-installation.json).

| Normal application metric | Previous 9720 | Selected 10140 |
| --- | ---: | ---: |
| Independent TTFT | 11.634333 s | **7.800974 s (-32.949%)** |
| Independent whole request | 20.179917 s | **15.986655 s (-20.779%)** |
| Independent decode | 2.567815 tok/s | **2.681407 tok/s (+4.424%)** |
| Exact repeated-prompt decode | 3.448557 tok/s | **3.676969 tok/s (+6.623%)** |
| Capture-charged pair throughput | 1.621072 tok/s | **1.949547 tok/s (+20.263%)** |

The selected composition adds resident output Q8,997 active Expert slots,
prefill Top6, guarded graph reuse and28 supplemental triplets (448 total).
Other non-Expert weights remain original BF16/F32; inputs and KV remain F32.
Shared16-prefix reuse is implemented and physically qualified for different
suffixes; the identical-prompt normal default retains complete-prefix reuse.
Late output cropping is tested without a qualified gain. All six finite scopes
are closed. Gains are measured in the combination, not added across candidates.

The normal control is historical9720, not a fresh normal ABBA. Independent
same-policy F32 error is0; final approximate cross-cache/width error6.634334 is
disclosed with finite full vocabulary and identical counting tokens. Both actual
information-only native frames were viewed. Placement10160 verified13 programs
and five settings. Subsequent [owner-authorized cleanup10200](docs/obsolete-version-cleanup-20261030.md)
removes108 obsolete executables and1,346 setting backups. SELF `5487e687...`
and the five current settings remain exact;12 qualified past programs retain
host archives. That historical cleanup retained only the then-selected application.
Native/gateway/models are inactive after verification. Sustained service and
broad reasoning remain outside this finite qualification. Driver872cc126,
disabled persistent caches, physical reserves and no-CI policy remain.

## Previous width16/all production control

**Width16/all prefill is implemented, qualified in the normal PS5 app, and
was installed before the current composition.** See the
[historical adoption evidence](docs/prefill16-adoption-20261030.json) and
[preserved installation](config/production-installation-prefill16-20261030.json).

| Normal application metric | Previous 9550 | Selected 9720 |
| --- | ---: | ---: |
| Independent time to first token | 14.014686 s | **11.634333 s (-16.985%)** |
| Independent whole request | 22.571456 s | **20.179917 s (-10.595%)** |
| Independent decode | 2.565459 tok/s | **2.567815 tok/s** |
| Exact repeated-prompt decode | 3.522102 tok/s | **3.448557 tok/s (-2.088%)** |
| Repeated-prompt first token | 62.492 ms | **63.143 ms** |
| Capture-charged two-request throughput | 1.497207 tok/s | **1.621072 tok/s (+8.273%)** |

This normal integration uses the historical 9550 protocol as control, not a new
normal ABBA. It retains every prior routing/I/O winner and complete-prefix reuse.
Seven final causal attempts reconcile as six accepts and one rejection, with
seven captures and one complete restore. Independent same-policy F32 rows and
tokens are exact; the final approximate cross-cache/width difference is 7.322802,
with finite full vocabulary and identical counting tokens. Both actual passive
frames were viewed. Three normal requests, positive resource retirement,
ordinary close and exact control restoration pass before placement.

The internal workspace capacity and fixed ledger reservation are tightened from
256 to 248 MiB. Each actual four-buffer capacity sum still has to fit that tighter
bound; total post-load device 1792 MiB, single buffer 512 MiB, CPU 512 MiB and all
physical Direct/Flexible/kernel reserves remain. This reduces conservative ledger
reservation, not measured physical allocations. GPU math and the pinned driver
are unchanged. Initial returned failures 9660/9690 and their ordinary restoration
are retained in the evidence; neither was replayed.

At historical placement9730, **12 programs and five settings** passed two bounded
native hash/identity/EOF batches. SELF `f49ba8ef...` was installed with exact
`55a8e4c4...` and older rollbacks retained before cleanup10200. Native/gateway/models are inactive
after verification; the finite binding is consumed and sustained service remains
outside qualification. No CI, reboot, forced Unix signal or ambiguous GPU retry.

## Earlier finite prefill comparison

The first [lean-qwenflash prefill comparison](docs/lean-prefill-results-20261030.json)
is complete on the PS5: 31 requests, one model load, six compositions, positive
resource retirement, ordinary close and exact production/settings restoration.
These were isolated experimental implementations; normal production adoption is
qualified separately above. The 30-token counting prompt has two timed repetitions
per mode, following one width-four warmup.

| Prefill width | Output rows per chunk | Mean prefill seconds | Mean whole request seconds | Decode tok/s |
| --- | --- | ---: | ---: | ---: |
| 4 | All | 13.909 | 22.539 | 2.552567 |
| 4 | Tail only | 13.723 | 22.259 | 2.582485 |
| 8 | All | 13.076 | 21.736 | 2.541953 |
| 8 | Tail only | 12.410 | 21.216 | 2.505059 |
| 16 | All | 11.648 | 20.232 | 2.564703 |
| 16 | Tail only | 11.412 | 20.232 | 2.500912 |

Width16 reduces prefill by 16.25% with all outputs and 17.95% with one tail
output per chunk. Both improve whole-request throughput by about 11.40% against
width4/all. Tail-only adds no whole-request gain over width16/all: its shorter
prefill is offset by slower decode. The predeclared prefill-first rule selects
mode5 for normal confirmation; mode4 remains an important comparison. Do not
claim a decode improvement or multiply these gains by earlier routing gains.

All counting tokens match; all 18 fixed content and strict-format checks pass.
Same-policy control F32 repeats are exact. Cross-mode full-vocabulary maximum
logit difference reaches 6.403900 and is explicitly not bit equality or broad
reasoning qualification. Zero-output batches are avoided because the current
backend's final-layer crop bypasses its Expert-cache path. Common context
capacity16, 160-entry CPU bookkeeping and complete route/output counters are
qualified; GPU math, four-read delivery, cache budget and original guards remain.
Normal prefix/speculation integration is now completed above. Memory-phase reuse,
complete packing and other lean-qwenflash ideas are not tested by this comparison.

The owner's [storage cleanup](docs/closed-trial-cleanup-20261030.json) removes
54 obsolete closed test programs and one unpublished transfer fragment,
916,829,098 logical bytes (874.356 MiB). Each removed file matches its complete
host preservation copy. Production, all 11 qualified programs, five settings
and all model data remain; 16 unclassified historical copies are retained.

## Retained routing baseline

The successful routing settings remain **implemented in production**.
See the [adoption report](docs/routing-winners-adoption-20261030.md),
[sanitized evidence](docs/routing-winners-adoption-20261030.json) and
[installation record](config/production-installation.json).

Normal PS5 case 9550 measures **2.565459 independent decode tok/s** versus
1.293876 (+98.277%). Exact prompt reuse gives **3.522102 decode tok/s** and
62.492 ms to the first token. Capture-charged two-request throughput is
**1.497207 generated tok/s**, +65.212%. These cache conditions remain separate;
initial independent first-token time stays about 14 seconds.

Production selects decode Top-6, cached ranking x1.5 and up to eight causal
pair verifications on the final positively restored-prefix consumer. The actual
normal consumer completes seven attempts, six accepts and one rejection with
complete rollback. Preference snapshots stay fixed during each target event;
both decode widths use Top-6. Prefill keeps Top-10 and exact prefix reuse remains.
The first independent repeat is F32-exact; final approximate cache/width logits
have maximum difference 3.666849, finite full vocabulary and identical emitted
counting tokens. Three fixed quality tasks pass for each of the three compositions;
broad reasoning accuracy is outside these finite checks.

Expert weights stay Gate/Up Q2_K and Down Q2_0 MSE; other BF16/F32 weights,
F32 inputs/KV, every stored Expert, 867 cache slots, original probation,
420 bundles, adjacency and four-demand reads remain. Graph reuse is disabled
for the variable policy. Persistent shader/pipeline caches stay disabled.

Historical placement 9560 verifies SELF `55a8e4c4...`, all **11 programs and five settings**
with native complete hashes/identity/EOF, and fresh idle. Both actual frames
were viewed with CPU/GPU information, synchronized time, 2.57/3.52 tok/s and
no chat controls. Unknown utilization remains `--`. The exact prior db542fa2,
older Q2/Q4/BF16 and MOSS applications remain rollbacks. Native title, gateway
and models are inactive; the inherited finite binding is consumed and sustained
service is not qualified. No CI, reboot, forced Unix signal or GPU retry ran.

The [composition comparison](docs/routing-winners-adoption-20261030.md#direct-composition-comparison)
discloses the post-exploratory generation-speed selection refinement: repeated
verification adds a reproducible decode gain, while its additional whole-request
gain is small and uncertain. Independent percentages are not added.
The [first-stage report](docs/expert-routing-sharing-results-20261030.md),
[earlier I/O winners](docs/expert-q2-io-reduction-results-20261030.md),
[eight-family dispositions](docs/expert-q2-optimization-results-20261030.md) and
[plan index](docs/plan-index.md) retain the measured historical controls.

## Native driver integration

The owner authorized integration of the updated driver on 2026-10-22. The source
is PS5-Vulkan-Inference at `872cc1264ad8ba5d6b888b092968fa5858a38c58`, explicitly
selecting `cumulative-idle`. Persistent shader/pipeline caches remain disabled.
The new profile is rebuilt from this source; older artifacts remain historical
controls. See [driver-integration.md](docs/driver-integration.md) for provenance,
manual build commands and the remaining native runtime/model gates.

The corrected application [passed the BF16 Vulkan fixture on the physical PS5](docs/native-bf16-success-20261022.md):
one 32x16 graph, 16 finite outputs, maximum absolute error 0. The passive monitor
also returned two HTTP 200 responses. The exact original SELF was restored,
numerically readmitted, normally closed and fully read back again. Fresh CPU
metadata confirmed no native owner. The task retains the console reservation.
The subsequent [combined admission](docs/native-combined-success-20261022.md)
also passed: completed BF16 computation and retirement, the first native TV
monitor frame, two passive HTTP responses and app-local UTC calibration.
The original app was again restored, numerically readmitted and normally closed.
The later [original-weight operation admission](docs/native-original-operations-20261022.md)
passed a 2560x16 BF16 matvec plus F32 RMS/SiLU: all 5,136 outputs met the fixed
numeric limits, followed by positive completion/retirement and complete original
restoration/readmission. These were component admissions; the later complete
model result and measured tokens/s are recorded above.
Committed console/deployment flags remain disabled in
[development.json](config/development.json). A private frozen fixture policy
and guarded ordinary launch are required. General `inference` mode remains
rejected; the completed session used a separate, frozen validation policy.
The native allocator/lifecycle integration is implemented and host-verified. See
[native-validation.md](docs/native-validation.md) for the staged gates and exact
preservation/restoration requirements. Driver tests do not establish Qwen quality
or memory admission. The [required-operation inventory](docs/qwen-operation-coverage.md)
keeps specialized Qwen graph paths separate from completed small-fixture coverage.

## Application development

The application includes session control, a Qwen/llama.cpp adapter, a read-only
inference monitor and a streaming HTTP API for external requests. The monitor
shows CPU/GPU information, date/time, generation tokens/s, TTFT and expert-cache
counters. It contains no chat input or operation controls. The host preview uses
an explicit demo backend; unknown hardware counters remain unavailable.
The real model adapter has API-stub tests and PS5 object compilation.
A guarded native entry point and BF16 conversion tool are implemented. The
native integration build and full-model qualification are recorded separately.
The native TV monitor uses two fixed VideoOut buffers and updates independently
of browser polling. Its display-only validation mode never initializes Vulkan.
See [application.md](docs/application.md) for exact check coverage and remaining
work. The demo is not evidence of Qwen inference or console performance.

## Earlier implementation checkpoints

At these earlier checkpoints, full-model PS5 inference had not been achieved.
The completed physical result above supersedes that historical status.
The pinned original checkpoint has 131 shards and 1,658 tensors. Every shard
header was inspected through bounded HTTP ranges: 359,999,962,848 bytes of BF16
weights and 280 bytes of exact I64 constants. All 131 original files have now
also passed their complete SHA256 checks. Conversion, independent output auditing,
all 76 final hashes, transfer and native model hashing subsequently completed;
the dated records below preserve earlier intermediate results.

The engine was rebuilt with the latest selected driver source on 2026-10-22.
The real application, original-BF16 adapter, HTTP service, Strata/Maya cache
patches and selected RADV archive now link into one intermediate native PIE.
The earlier host link is retained in [the integration record](docs/driver-integration-20261022.json).
Historical host builds and the first failed startup are preserved in
[the monitor host record](docs/native-monitor-20261022.json),
[the initial startup record](docs/native-startup-20261022.json) and
[the corrected host record](docs/native-monitor-corrected-20261022.json).
The subsequent [display/status admission](docs/native-display-20261022.json)
completed all 16 initializers, the first native frame and two HTTP 200 status
responses from the same verified owner. It initialized no model or Vulkan.
This artifact has six runtime providers, 289 verified actual-module imports and
six verified reconstructed SELF segments. At that display-only checkpoint,
native CPU percentage and wall-clock calibration were unqualified; tokens/s
stays unavailable without inference.
The exact original executable was restored, numerically admitted and normally
closed. Fresh observations confirmed no native owner and an unchanged boot.
At that display-only checkpoint, original acquisition and full checksumming
were incomplete. These display results are separate from the later successful
no-display BF16 fixture and the subsequent host model-preparation progress.

The separate no-display [BF16 fixture attempt](docs/native-bf16-20261022.json)
persisted its headroom and clock checks, then exited before owner admission or a
completed GPU readback. Its cause is unresolved. It was not retried; the exact
original SELF was restored. This is a failed admission, not a compute result.

The later [corrected initialization attempt](docs/native-bf16-fixed-20261022.json)
completed instance creation and checked instance dispatch, then exited before
physical-device enumeration returned. No BF16 compute or completed readback was
observed. The shell-state check then failed. The later
[reassessment and restoration](docs/console-reassessment-20261022.json) completed
on the physical PS5 without changing that failed result. The original bytes
and failed evidence remain preserved.

Host implementation now adds streaming model SHA256 checks before loading,
original-dimension/PLE verification, checked memory budgets, 64 MiB completed
transfer chunks, loader progress and separate inference phase records.
[Runtime implementation](docs/runtime-initialization-20261022.md) records their
scope. A host-only driver composition tool preserves the native allocator and
three native compatibility objects while applying the exact two selected
shared-driver members. The frontend now implements own-log initialization,
sole AGC8 ownership and retirement after device idle plus matching completion
epochs. [The source review](docs/native-driver-examples-20261022.md) records the
actual PS5LM/RADV and native MOSS examples and the implementation decisions.
Host integration does not establish Qwen console compatibility or numerical quality.

The distinct native-frontend trial subsequently passed explicit AGC8 and owner
initialization but exited during enumeration. The
[physical-console discovery record](docs/native-dispatch-discovery-20261022.md)
identifies a missing weakly referenced static Vulkan callback. Native linking
now retains the selected driver archive as the admitted original does, and
packaging requires an audit of the actual callback-table targets. The distinct
[corrected artifact](docs/native-bf16-success-20261022.json) subsequently passed
the physical BF16 fixture and positive completion/retirement checks. Its
117.013471 ms fixture interval is not model throughput. Native BF16 arithmetic
units were not advertised; the shader widens original BF16 storage to F32.
The later combined artifact passed native first-frame presentation and bounded
app-local UTC calibration. Long-term clock drift, original-model mapping/residency,
full-model quality and tokens/s remain unqualified.
The next [CPU model preflight](docs/model-preflight.md) independently verifies
complete model hashes/metadata and read-only virtual mappings before Vulkan.
The [physical CPU hash probe](docs/native-cpu-hash-20261022.md) measured 512 MiB
at 167.49 MiB/s with the production SHA object. Its compute-only projection led
to a fixed two-hour verification budget and structured progress; full-file disk
performance and integrity remain separate admissions.
The [resident buffer admission](docs/model-buffer-admission.md) now distinguishes
the upstream batching target from hard limits and checks aligned tensor sizes.
Host conversion now [bounds original BF16 copies](docs/bounded-conversion-20261022.md)
while retaining the pinned dense transformations and complete output audit.

The upstream llama.cpp model implementation is `qwen4exp`. Its PLE lookup,
hybrid attention, hyper-connections, expert-cache and scheduler paths are the
starting point. Strata/Maya principles are now wired into the actual engine cache:
UMA budget admission, aged-frequency eviction with recency ties, feasible layer
floors, active-expert protection and bounded miss read-ahead advice. See
[expert-policy.md](docs/expert-policy.md) for pinned sources, adaptations and
manual checks. Host fixtures preserve BF16 bits; they do not predict console speed.

## Dependencies

- [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next),
  pinned in [dependencies.lock.json](native/qwen_flash_next/dependencies.lock.json).
  Its Qwen Community License applies to the model, separately from this code.
- [llama.cpp / GGML](https://github.com/ggml-org/llama.cpp), MIT.
- The owner's private [PS5-Vulkan-Inference](https://github.com/akiba-tokyo-jp/PS5-Vulkan-Inference),
  an unofficial derivative of [PS5_Vulkan](https://github.com/mihawk-99/PS5_Vulkan)
  and [PS5_Mesa](https://github.com/mihawk-99/PS5_Mesa). Imported notices apply.
- Design references: [Strata](https://github.com/Niko1221/Strata) and
  [Project Maya](https://github.com/mw00/project-maya).

No models, native binaries, proprietary SDK material or private device captures
are distributed in this repository. GitHub Actions and other CI are disabled.

## Inspect and acquire the original checkpoint

Python 3.11+ is sufficient for metadata and acquisition. Point `--cache` at a
data disk with room for the original model and subsequent lossless GGUF output.

```powershell
python tools/qwen_flash_next.py prepare --cache D:/PS5-AI/qwen-flash-next --jobs 6
python tools/qwen_flash_next.py download --cache D:/PS5-AI/qwen-flash-next --jobs 4
```

`prepare` fetches metadata, tokenizer and shard headers. `download` explicitly
fetches all original shards, resumes partial files, verifies their original
SHA256 digests and publishes each shard only after verification. It performs
no inference or console operations.

`tools/prepare_model.py --acquire` runs resumable acquisition and bounded BF16
conversion as one host batch with OS writer leases and durable phase records.
The [complete conversion audit](docs/model-preparation-20261022.md) derives all
1,256 expected tensors from the pinned converter, checks split metadata and exact
precision, compares all original PLE/expert/embedding copies and replays every
dense weight-format transform, then publishes final
file digests. The derived memory footprint also matches the native admission
policy. All 131 original files have now been acquired and independently SHA256
verified. Conversion, output auditing, final hashes, transfer and physical PS5
memory admission subsequently completed before the generation result above.
The native client requires the complete v2 conversion audit and exact original
footprint before backend initialization; legacy receipts are rejected.
[The native contract build](docs/native-model-contract-host-20261022.json)
passes 289 actual-module imports, SELF integrity and six segment roundtrips.
That artifact has not been installed on the console.

[Offline transfer planning and per-file transport](docs/model-transfer.md) now
require the complete original receipt and preserve ambiguous transfer outcomes
without retry or deletion. Full-model console transfer subsequently completed;
the successful session reused its sealed files and same-boot native integrity.

## Manual PS5 build

The build uses the owner's local PS5 SDK, compiler, Vulkan headers and selected
driver archive. These dependencies are not redistributed. Keep the model cache
and build directory on the data disk.

```powershell
python tools/fetch_engine.py --cache D:/PS5-AI/qwen-flash-next
python tools/build.py --workspace C:/Users/User/ps5-ai --driver-root C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference --driver-manifest C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference/.local/qwen-cumulative-872cc126-001/manifest.private.json --cache D:/PS5-AI/qwen-flash-next --jobs 4
python -m unittest discover -s tests -v
```

This cross-builds static engine libraries and records local archive digests.
It does not install or launch an application. Console execution and numerical
acceptance remain separate milestones in [architecture.md](docs/architecture.md).
The tracked source patch links the required SPIRV-Headers include dependency;
the build receipt records its digest separately from the pinned upstream source.

`tools/console.py` inspects a native application before an explicitly requested
ordinary OS close. It records the PID, process start time, application ID and
title identity locally. It never sends force-kill signals or resets the GPU.
