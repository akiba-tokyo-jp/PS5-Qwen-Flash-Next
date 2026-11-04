# Strata candidate validation, 2026-11-05

This follows the three conditional candidates in
[the pinned source review](strata-candidate-review-20261105.md). Production is
R1+P1, SELF `c5afc565fdbb4adcf830eae645a32589825331dfa7783a1b9ae2985e7fb5c2ed`.
The selected driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, with persistent caches disabled. No initializer is replayed;
no restart or recovery is used.

## ST1 and ST2: executed-path eligibility

The actual selected entry sets `GGML_VK_DISABLE_INTEGER_DOT_PRODUCT=1`,
`GGML_VK_DISABLE_COOPMAT=1` and `GGML_VK_DISABLE_COOPMAT2=1` before backend
initialization. It has no `unsetenv` call. The error guard explains why:
`Output Q8 requires original floating activation inputs`.

The selected Vulkan lineage gates single-token matrix/vector activation
quantization on `device->integer_dot_product`. Indexed multi-token matrix
quantization has the same prerequisite. The ordinary shared matrix path also
allows cooperative integer matrices, which the selected entry disables.
These are distinct checks of decode and prefill, and routed and shared
consumers. Both an existing-image reuse and a producer-written-image refinement
have no original Q8_1 image/consumer to optimize under this policy. The GLU/down
boundary likewise lacks the Q8_1 conversion that ST2 would fuse in either phase.

Applicability observation65602 positively executes the original cold,
retained and exact-prefix sequence in one model load. All three runtime rows
confirm the integer-dot disable flag. All 7,259 source windows complete;
source/device owners retire, the device ledger reaches zero and ordinary close
restores all seven selected files. The observation changes bounded CPU counters
only; GPU instructions, shaders, original source IO and completion stay intact.
Its rates are not performance evidence.

ST1/ST2 are ineligible in the selected arithmetic configuration; they are not
measured regressions. Enabling a new F32-to-Q8_1 activation conversion would be
a separate numerical experiment, outside the two precision-preserving
adaptations reviewed here. No activation or weight precision is changed.

## ST3: two distinct cache-local refinements

The PS5 reader has four CPU workers, four owned 2 MiB leases and potentially
out-of-order read completion. Its positive producer callback completes before
a lease can be reused. It has no CUDA-style per-copy GPU event ring to sparsify.
The upstream event-rule test already passed and is not replayed.

A narrower executed PS5 target does exist: the current cache synchronizes the
backend before every group of independent streamed experts. The selected-ID
readback has already synchronized that backend. Between that boundary and the
stream loop, planning is CPU work and each bundle upload is synchronous.
Within the stream loop, every `ggml_backend_tensor_set` callback returns after
the original upload visibility/fence/cleanup sequence. No compute or asynchronous
slot-map publication intervenes. The original readback fence, source callback
completion, fallback upload paths and final publication remain unchanged.

| Condition | Stream scopes | Attempted groups / waits | Completed groups | Positive upload callbacks | Waits beyond the first group |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cold | 1,104 | 46 | 43 | 462 | 36 |
| Retained | 1,104 | 4 | 4 | 12 | 0 |
| Exact-prefix | 768 | 5 | 4 | 12 | 0 |

Attempted groups include stream-route ineligibility/fallback; they must not
be mislabeled as completed transfers. The observation reports both separately.

* `group` retains the first pre-stream wait in each nonempty scope and skips
  later group waits. The observed opportunity is 36 cold calls and zero later
  calls.
* `readback` reuses the already completed selected-ID boundary for the entire
  stream loop. Its opportunity is all 46/4/5 attempted-group waits. It does not
  remove a real source or GPU-copy completion.

Each change affects one wait expression in the exact reconstructed selected
cache source. Undoing that expression reproduces the original source exactly.
The selected GPU, owner, engine, graph and shader objects are retained. There
are no extra GPU buffers, CPU workers or source leases.

Build65604 produces two qualification packages and three observer-free timing
packages, including the original-cache control. The qualification-only full
vocabulary observer reconstructs byte identically to its previously tested
provider; its unchanged host tests are reused. Native qualification compares
all 69 ordered 248,320-column F32 hashes, actual route records, tokens and output
bytes against the completed selected P1 eight-row reference65016.

The primary endpoint remains `(generated_tokens-1)*1000/decode_ms`, separately
cold/retained/exact-prefix. Prefill, TTFT and whole-request time are secondary
and are reported independently. Timing excludes the whole-vocabulary SHA
observer. Both refinements share controls; only a promising screen advances to
a second candidate and final control for an ABBA comparison. No performance
adoption is established by the eligibility count or by a qualification run.

## Host preparation and ownership

The previous cleanup removed historical trial object paths while retaining the
canonical byte-identical identity object. The new receipt changes only that
artifact path, authenticates the original immutable receipt and preserves all
three linked identity definitions. Two positive and nine rejection controls
cover receipt retention; the original 69-file/138-observation native proof
remains required. This does not regenerate an identity from host assumptions.

Early host preparation failures are retained: duplicate include-overlay roots,
deleted historical identity-object paths, wrong proof filenames and strict
receipt-path equality. Completed compilations, links, readiness and clock
observations were reused after those host corrections. They caused no model
launch. The actual applicability launch is submitted once and positively
retired.

Capacity preparation uses only the latest actually completed model's source
read ownership. New original-model Strata scopes require the unchanged recipe,
all original overrides, actual completed source windows, ordinary exit and exact
current restoration. One actual positive owner and eight altered-owner controls
pass. Old consumed cohorts and cursors remain unchanged. The original finite
readonly cache API, 1,154-page floor and 7,374-page model screen remain unchanged.
No FTP or deployment transport change is claimed as inference acceleration.

Detailed private receipts are under
`D:/PS5-AI/qwen-flash-next/strata-validation-20261105`.

## Interruption65611: no adoption and no restoration claim

Both ST3 refinements pass actual native qualification: all 69 ordered
full-vocabulary F32 hashes, all actual route records, tokens and output bytes
match reference65016. Both qualification cases normally close and restore.
The first observer-free control also normally closes and restores.

| Condition | Control, first timed run | Group refinement, first timed run |
| --- | ---: | ---: |
| Cold | 10.401232 tok/s | 10.446024 tok/s |
| Retained | 12.199695 tok/s | 12.258107 tok/s |
| Exact-prefix | 13.349245 tok/s | 13.373284 tok/s |

**This is an incomplete pair, not a measured adoption benefit.** The group
refinement finishes all three requests, all source windows and positive
source/device retirement with zero live device bytes. However, the host times
out while collecting the ordinary-close helper. Its once-only submission
receipt exists, but no native close journal/result has been collected. Its
start, OS close call, exit and completion cannot be inferred from submission.
Original restoration has not started. A collection-only attempt for that
same helper also times out connecting; no second close is sent.

One subsequent reachability observation finds all three known services
(8080/8084/2121) timing out. ICMP returns `Destination host unreachable` from
the PC; the ping utility's zero exit code does not establish a console reply.
The cause, console power state and ordinary-close outcome are unknown. This
does not prove a kernel failure or an inference failure. No initializer,
restart, recovery request, repeated model or second close is submitted.

Host `current` still selects R1+P1/c5afc565. The console's last authenticated
installed image is the group timing candidate
`66ee5fdaaa9d50faecce07d5f7f1fbf71c49f6b49d7b05ff79c67dcbcd39827d`.
It is incorrect to claim that the console has been restored to c5afc565.
The durable state explicitly retains unknown completion and the pending owner;
`native_running=true` there is a reservation marker, not a fresh process
observation. The first close plan, once-only receipt, original restore binary,
all candidate binaries and all evidence remain preserved.

ST1/ST2 eligibility is resolved; both ST3 numerical refinements are resolved.
Readback timing, the final control and any justified extension remain
**pending because console access is unavailable**. No candidate is rejected as
slower on this incomplete evidence, and none is adopted. Production inference
source is unchanged. The previous R1+P1 measurements are not combined with this
cohort or replaced by the incomplete pair.

The owner was asked only about a power/LAN availability change. No restart is
requested. After an actual external availability change, the prepared
`--collect-close` path first collects the exact existing helper and restores
the selected files. It preserves the original close admission, reports,
identity checks, positive helper retirement and ordinary exit inventory.
`record_closed_strata_case.py` then records the already executed case without
another model run. `--completed-prefix-from` continues only the unexecuted
suffix, reusing both numerical qualifications and both first timing cases.
These continuation paths are prepared; restoration and the remaining native
validation have not been established. All original source-window cursors are
preserved. Trial-binary cleanup is deferred while the pending owner and restore
inputs are unresolved.
