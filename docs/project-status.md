# Project status

Status date: **2026-11-05**. This is a source/evidence baseline, not a live
console-health report.

## Established results

Full text-model inference has executed on one physical PS5 with SSD-backed
expert delivery. The host prepares data, builds and observes; learned inference
runs on the console. Required text-model components, including PLE, remain present.

The completed eight-candidate campaign selected R1 completed-stage synchronization
reuse and P1 cold-prefill output selection. G1, Q1, Q2, Q3, I1 and S1 were not
selected after distinct comparisons/refinements. See [performance](performance.md).

| Area | Selected configuration |
| --- | --- |
| Routed weights | Gate/Up Q2_K; Down Q2_0 MSE |
| Resident weights | Quantized deployment; BF16 data retained as reference |
| Activations and KV/recurrent state | Floating point; original F32 input policy |
| Routing | Six decode experts, cache-aware ranking in the latest observed requests |
| Active expert-cache slots | 3,712 |
| Demanded source scratch | Existing bounded 8 MiB, four source lanes |
| Engine | Pinned llama.cpp `0a1ef309…` with application patches |
| Driver | `872cc126…`, selected `cumulative-idle` |
| Persistent shader/pipeline caches | Disabled |

Historical Top2, smaller-cache and original-BF16 profiles are research controls.
Their settings must not replace actual latest request observations. The lock
file describes source pins and original preparation; deployment receipts describe
later optimized profiles.

## Latest console session is unresolved

Both Strata cache-wait refinements match all 69 full-vocabulary F32 hashes,
ordered routes, tokens and output bytes against the selected P1 reference.
Their numerical cases normally closed and restored the selected files. The
first timing control also normally closed and restored.

The next timed candidate completed three requests and positively retired model,
source and device resources with zero live device bytes. Communication was then
lost while collecting an already submitted ordinary close. The OS close result
and original-file restoration are **unconfirmed**.

The last authenticated installed console image was a timing candidate; the host
still selects R1+P1. Do not claim matching deployments, an idle console or a
running service. No reboot, initializer replay, model replay or second close was
submitted. Cause and power state are unknown. No console work is part of this
documentation/publication cleanup.

## Remaining work

| Item | Status |
| --- | --- |
| ST1: existing Q8_1 input-image sharing | Ineligible under the selected floating-activation policy |
| ST2: SwiGLU plus existing Q8_1 conversion | Ineligible in selected decode/prefill paths |
| ST3: two cache-local wait refinements | Numerical checks pass; speed comparison incomplete; no adoption |
| Existing ordinary-close result and restoration | Unconfirmed; resolve before another model operation |
| Readback-refinement timing and final control | Pending; completed cases must be reused |
| Broader prompts, long contexts and sustained service | Not qualified by the short reported cohorts |
| Portable reproduction of the selected executable | Not supplied by a clean checkout alone |

An unavailable or incomplete comparison is not a measured slowdown. A rejection
applies to its tested configuration, not every future refinement. See
[the Strata record](strata-validation-20261105.md).

## Repository defaults

Committed execution/deployment flags remain disabled in
[development.json](../config/development.json). Historical and experimental
providers coexist with selected mechanisms. A source merge, host check or
component GPU result does not qualify a whole model or authorize console use.

This is a research source release, not a packaged consumer application. Private
captures and retained native inputs remain outside Git. Public preparation
does not change device state or establish a completed binary release.
