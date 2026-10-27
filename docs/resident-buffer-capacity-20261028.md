# Direct capacity and model startup measurements

The console reported **12,245,254,144 available Direct bytes (11.404 GiB)** in
case 3643. The selected raw-buffer experiment requested **8,755,105,280 bytes
(8.154 GiB)** because that is the original model's resident-weight payload,
not because 8.75 GB is a hardware limit. The streamed experts and other original
components remain required and are not included in that resident-weight total.

Five buffers (four 2 GiB buffers and one 165,170,688-byte buffer) were allocated
successfully. Driver-owned bytes reached 8,771,911,680, including 16,793,600
already owned before the experiment. Sampled kernel free pages remained 2,500
before and after every allocation. Backend initialization declined by eight
16 KiB pages. These are finite global samples, not a universal zero-cost bound.

This fixture performed no payload first touch, model-tensor layout, upload,
graph or queue submission. All five buffer callbacks returned; physical backing
remained owned until ordinary OS application teardown because no submitted
epoch existed. No fake completion epoch or manual GPU release was used. Normal
close, native whole-file integrity, exact fastest executable and five settings
restoration, and a fresh idle observation passed.

## Actual original-model follow-up

Case 3678 loaded the original BF16/F32 model, created its F32 context and
completed one exact 22-token warmup at **0.3905692470 decode tokens/s**. This
is a control observation, not a matched speedup. Global kernel free pages were
1,880 after startup settling, 1,957 after model loading and 1,917 after context
creation. The separate kernel VM domain did not require the old whole-interval
1,958-page prepayment. Source windows retained their operational floor and
19-page additional allowance, and original Direct/Flexible/heap/device guards
remained in force. These observations do not establish a universal lower bound.

The comparison then stopped at a test assertion: the test incorrectly expected
process-global expert counters to become zero when recreating a context. The
actual cache slot maps and policy reset per context; the counters are static
atomics and deliberately remain cumulative. No memory-pressure event occurred
in the completed warmup. The returned error retained resources, and one exact
owner ordinary close and exact fastest/settings restoration passed. The
pre-close unknown-resource flag is preserved in the original evidence; it is
not a successful complete cohort or a hanging inference.

`native/app/resident_counter_baseline.h` now checks that context recreation
does not add or reset any cumulative counter. Each request continues to measure
its actual counter differences. Host controls accept a nonzero cumulative
baseline and reject all eight single-field changes and a substituted zero
baseline.

The corrected case 3700 returned before GPU/model work at **1,109 free kernel
pages versus the original 1,154-page operational floor**, after the existing
bounded passive wait. Its first application sample was 1,318 pages, compared
with 3,371 in case 3678. Direct resident capacity is therefore distinct from
this current kernel-VM refusal. One ordinary close, exact fastest/settings
restoration and a fresh idle observation passed, with no unknown completion.
The failure does not prove physical impossibility. C2 is incomplete, and C3
native comparisons share this unmet startup prerequisite. Replaying the same
startup for every cache arm would not answer a new question.

## Independent cache and prefix comparison integration

`native/app/resident_additional_policy.h` and
`native/app/resident_additional_tail.inc` implement the remaining C3 cohorts:
one warmup plus two fresh-context cache requests, or one warmup plus four
ordinary/prefix/prefix/ordinary pairs. Prefix pairs retain the same engine for
their second request; each new group starts with a new context. The original
128-slot geometry proof, Direct/Flexible/heap/ledger limits and actual model
loading remain mandatory. Complete F32 continuation rows, emitted tokens/bytes,
all expert selections and actual source/cache accounting precede acceptance.
Capture and restore costs remain inside the measured request. A prefix prefill
gain cannot be represented as a decode speed gain.

`tools/resident_additional_comparisons.py` provides the dedicated builder paths.
All 120 altered policy controls, nine cumulative-baseline controls, five Python
result/source tests and manual native link/import/table/ELF/SELF roundtrip
audits passed. Cache SELF SHA256:
`b5ea3ae126cc23580c32ebded2a19af84fdf108f87fa9b08ae88f8ddcbad6336`;
prefix SELF SHA256:
`a6f55eef83d60c4129b1d294ee33d2568028403e353d7dcec1f0b034863257e1`.
Neither package was deployed or launched. These are host-qualified integrations,
not native numerical or speed qualification. The shared failed startup is not
repeated for each arm. Ordinary production and admission defaults stay intact.

## Startup journal collision

Case 3627 reached no new application marker. A later read-only native stat
proved its PID-only exclusive startup journal predated both the current boot
and launch. The original `O_EXCL` bootstrap had stopped before main and GPU
initialization. Ordinary close and restoration passed; no second launch was
issued. The opt-in comparison bootstrap now includes native boot seconds,
microseconds and PID in its bounded journal path. Old logs are preserved. This
addresses the demonstrated cross-boot collision, without claiming protection
against arbitrary same-boot PID wraparound.

## Provenance and scope

| Case | Executed SELF SHA256 | Result |
| --- | --- | --- |
| 3611 | `3dbee63e62d5ba2a1134950ab28820a6f308fab071181089e865958d4437bac9` | CPU floor refusal before GPU; normal close/restoration |
| 3627 | `31153a6770f50686324754d93816a03f962f58707e04f26994f2603ece8df2be` | Pre-main exclusive-journal collision, reconciled by native stat |
| 3643 | `30ff7cd4f9058cb05f34813ae98b11c0e1dc0fe76a7c6993b648aedbd6b75b2c` | All five original-size raw buffers allocated; normal close/restoration |
| 3678 | `3046522542097a0423d77f508a72fe18a857fc2c8a2b2f4872cc8aa883a51b5e` | One original-model warmup, then returned cumulative-counter assertion |
| 3700 | `e139a66a2d8d392f12553fbb8d7962252b2ea23afd4c9e93dd147947407c0045` | Corrected comparison, CPU operational-floor refusal before GPU/model work |

The owner explicitly accepted the disclosed freeze risk before case 3643.
Raw capacity report: 3,178 bytes, SHA256
`66ad9bbcb2e4fa45ecffee0e4f29a9367d934049759932970f49d85bcc30c94d`.
Unlaunched cases 3665 and host failures 3608, 3675 and 3691 are preserved;
none is counted as a console execution or numerical/performance result.

Driver source remains `akiba-tokyo-jp/PS5-Vulkan-Inference`, revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, linked
native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches and CI remain disabled. The exact restored
production SELF is
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
No speed adoption or completion of C2/C3 follows from these partial results.
