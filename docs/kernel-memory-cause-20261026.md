# Kernel memory consumption and BF16 candidate qualification

Subsequent evidence is recorded in the
[memory attribution and GPU follow-up](memory-palette-followup-20261026.md).
It completes the standalone GPU screen with a negative result; the fused candidate
remains unmeasured after a zero-launch memory refusal. The historical cases and
point observations below are preserved unchanged.

The requested plan is **not complete**. A same-process control identifies large
HTTP readbacks as one reproducible source of free-page consumption, and the
revised integrity order recovers pages without reducing any guard. The one-worker
demand comparison completed and failed its adoption gate. The exact GPU palette
prototype compiled, but its physical GPU measurement remains unqualified because
the latest unchanged prelaunch admission refused. No new production optimization
or full-model tokens/s is claimed. See the [sanitized evidence](kernel-memory-cause-20261026.json).

## What the memory measurements establish

All page counts below use 16 KiB pages. They describe the measured kernel VM
domain, not all PS5 memory or the available Flexible/Direct quotas. Its operational
floor remains `minimum + max(reserved, 256)` = 1,154 pages. Native startup still
requires 2,974 pages; the full prelaunch gate requires 10,142 pages, including its
unchanged additional allowance. Inactive pages never grant admission. Counter
queries are sequential, rather than one atomic snapshot.

Case 2311 ran matched idle, one complete HTTP readback of the 28,017,271-byte
production SELF, full Direct SHA256/identity/EOF verification, and final idle in
the same CPU process with unchanged boot/services. The predeclared HTTP ceiling
was six seconds within an eight-second observation window; the readback took
4.031 seconds. All 28 native reads returned, and the file closed positively.

| Interval | Free-page change | Inactive-page change | Wired-page change |
| --- | ---: | ---: | ---: |
| Idle before | 0 | 0 | 0 |
| Complete HTTP readback | -1,712 | +1,702 | +10 |
| Complete Direct integrity | +1,712 | -804 | -908 |
| Idle after | -1 | 0 | 0 |

The 1,712-page change is 26.75 MiB, approximately the executable size. Separate
Direct controls recovered 1,712 pages for this SELF and 6,592 pages (103 MiB) for
the 107,911,351-byte preserved rollback. These observations support changing
verification order. They do not identify the proprietary cache mechanism, prove
a leak, establish that the HTTP server allocates one whole-file buffer, or show
that every inactive/wired page is reclaimable. The older case 2304 positively
completed its native work but exceeded its original host timing gate; it remains
rejected as a formal matched comparison.

The implemented operational reductions are:

1. Reuse a sealed source pack instead of uploading and HTTP-reading identical
   data again. Current native whole-pack SHA256/identity/EOF is still required.
2. Finish all required large transport readbacks, including the published
   candidate readback, before final Direct integrity and fresh memory admission.
3. Include required preserved executables in that bounded final integrity pass.
   Preserve forensic files and verify their exact original bytes; do not purge a
   cache, create memory pressure, change a reserve or repeat consumed helpers.

Earlier recovered headroom admitted the previously refused 20 MiB demand fixture.
It did not guarantee later title admission. Case 2354 verified six complete
published/preserved sources after the last large HTTP readback. The published
candidate and retained case-2344 executable each returned another 1,716 free
pages. The final observation was **9,751 pages (152.359 MiB)**, still below 10,142
pages (158.469 MiB). Its separate prelaunch gate positively refused with zero
title launches/GPU calls. The gate's failed threshold precedes its `MEMORY` log,
so it supplies no exact failing counter; 9,751 is the preceding integrity
observation, not a fabricated gate sample. It is not permission to retry or
lower the requirement.

After exact production/configuration restoration and its mandatory raw readbacks,
the allocation-free case 2363 observed 6,351–6,352 free pages (99.234–99.250 MiB),
71,915–71,923 inactive pages, 32,623–32,631 wired pages, and 27,841–27,842 active
pages. These are later observations; the earlier 9,751 point is not current
admission. Remaining consumption is not attributed to individual processes/files.
No safe global reclaimability or kernel-pool resizing mechanism is established.

## Candidate outcomes

| Candidate | Physical result | Decision |
| --- | --- | --- |
| One-worker continuous known-demand refill | 60 batches / 360 exact original matrix deliveries; paired median 1.040344x; 9/10 rounds faster, one 0.992239x | Reject the tested variant: original gate requires median >1.05x and every round >1.0x |
| Exact palette reconstruction on CPU | Previous complete delivery ratio 0.488x | Keep rejected; read savings do not repay CPU reconstruction |
| Exact palette reconstruction on GPU | Native link/import/SELF and host API/SPIR-V checks passed; actual GPU dispatches zero | Pending physical delivery/numerical/completion qualification; no speed claim |

The demand comparison kept the production thread count: one worker plus caller,
at most two outstanding reads, exact original SHA256, and positive joins/Direct
release. Pair-wave and refill median batches were 30.270478 and 29.082210 ms.
The improvement is a fixture delivery result, not a full-model decode gain.
Neither the installed engine schedule nor production SELF was replaced by it.

## GPU implementation and consumed attempts

`native/app/palette_gpu_dispatch.cpp` creates one registered Vulkan device,
two owned coherent 4 MiB buffers, integer-copy/palette pipelines, explicit
host/compute visibility barriers, and a finite two-second fence for every
submission. Unknown/failed completion retains backing and forbids reuse.
The 16 MiB policy ceiling covers explicit buffer allocations; it does not include
driver, pipeline, command, journal or other application overhead. Resources remain
owned until positive frontend completion followed by ordinary OS close.

`palette_gpu_admission.cpp` verifies complete source/shader hashes before GPU
initialization, checks every BF16 bit pattern, and defines 108 matrix deliveries
over nine original samples and six rotated rounds. Baseline delivery is **raw
Direct read only**: the raw GPU copy checks correctness outside baseline timing.
Palette delivery includes read, complete CPU format validation, dispatch and
fence. `tools/palette_gpu_result.py` rejects incomplete ownership/completion,
changed physical envelopes, missing pairs and unfair timing scopes. Even a
passing delivery screen cannot authorize production adoption without integration
and the complete same-model comparison.

No attempt reached GPU initialization:

| Case | Positive terminal / failure | Disposition |
| --- | --- | --- |
| 2320 | External `/data/ai` sample path unavailable before driver setup | Ordinary exact-owner close and exact fastest/config restoration passed; native access scope remains unidentified |
| 2334 | Unused monitor clock calibration expired before source/GPU work | Ordinary exact-owner close and exact restoration passed |
| 2344 | Prelaunch metadata gate refused | Zero launch; exact restoration passed |
| 2354 | Final six-source Direct proof passed; subsequent prelaunch gate refused | Zero launch; exact restoration passed |

The title-visible pack now uses fixed `/app0/qwen-runtime/palette-samples.pack`.
Headless palette mode omits UTC monitor initialization and uses admitted
monotonic timing; other modes retain their UTC guard. The corrected source and
SELF passed actual native linking, runtime-import audit and six-segment SELF
roundtrip before cases 2344/2354. Their refusal leaves the corrected source-open
path and GPU execution unqualified. The earlier host observer's failure to stop
on a `.failure` record was corrected; it does not turn a known pre-GPU refusal
into an unknown GPU operation.

## Maintained checks and provenance

The scalar trace is in `native/app/kernel_memory_trace.h`; the bounded CPU probes
are `native/qwen_flash_next/kernel_memory_trace_probe.c` and
`kernel_memory_category_probe.c`. `tools/kernel_memory_trace_result.py` validates
same-owner/boot completion, fixed phases, every returned read/EOF, unchanged
floors, and the matched network window. Run focused manual checks with:

```text
python tools/check_kernel_memory_trace.py --workspace WORKSPACE --out NEW_OUTPUT
python tools/check_palette_gpu_probe.py --workspace WORKSPACE --cache DATA_CACHE --out NEW_OUTPUT
python tools/check_validation_policy.py --workspace WORKSPACE --cache DATA_CACHE --out NEW_OUTPUT
```

Host controls cover counter boundaries, malformed traces/network phases,
incomplete/failed fences and submissions, coherent-buffer bounds, strict policies,
and complete delivery-result accounting. The unchanged validation-policy suite
passed 316 rejection cases. These checks do not execute a GPU. Actual native
build receipts, consumed intents, source-at-execution copies, console identities,
private SDK inputs, binaries and raw logs remain outside Git.

The experimental SELF was built from main base
`3b2b00564318b9aeb5f6a3ff9a4ae5ed5ef86bab` plus the recorded source overlay;
the JSON records repository-relative source hashes. No driver/engine archive
was rebuilt. Application relinking retained driver revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, native
archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled.

## Current state and remaining work

The exact fastest production SELF
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`
and its prior settings are restored and fully read back. The original MOSS
rollback remains preserved. Fresh idle CPU/boot/service guards passed; no native
owner, gateway, model or unknown completion remains. No fresh numerical generation
was repeated during restoration. Existing production rates 0.391093/0.398430 tok/s
remain the previous short-request qualification, not measurements from this task.

The six-stage plan stands at: consumption mechanism partly isolated; avoidable
readback pressure reduced; earlier CPU admission regained; demand screen complete;
GPU delivery and same-model integration/comparison still pending; no new candidate
adopted. Further GPU execution requires a distinct fresh case passing every
unchanged memory/lifecycle guard. Repeated publication/readback cycles under the
same insufficient conditions add work without qualifying the candidate. Diagnose
the remaining consumption before another publication; preserve all consumed cases.
Private-repository status and disabled Actions were checked. CI runs remain zero.
