# Native integration of the selected predictive paths

This continues the owner's three-path validation request. The previous trace
screens did not implement the two model integrations. The native source now
contains a default-off predictive read path and a default-off expert-aware
width-one/two controller. Host checks and a PS5-target application build are
separate from native execution, arithmetic qualification and speed adoption.

The complete instruction to validate all three paths has **not** been completed.
No new PS5 inference or model-speed result is reported here. The AIO implementation
already physically lost and is not repeated or connected to the model.

| Selected path | Implementation and completed checks | Native acceptance |
| --- | --- | --- |
| OS I/O | Earlier physical AIO comparison lost by 46.88%; retain paired pread | Proprietary filesystem/raw-NVMe changes remain unavailable through the established interfaces |
| Predictive caching | Connected predictor, actual allocation leases, existing slots, one persistent read worker, completion coordination and result accounting | New worker/GPU overlap, whole-model numerical equality and matched speed are unqualified |
| Expert-sharing verification | Connected causal history proposals to measured route/timing observations and the native width-two checkpoint/restore implementation | Controlled native acceptance/rejection, continuation equality and matched speed are unqualified |

## Predictive cache source path

`patches/native-model-io/0002-llama-moe-cache.patch` now connects
`llama_moe_cache::impl::copy` to `predict_next_expert`. It drains the preceding
prediction before a new cache plan, observes only synchronized actual IDs and
loads at most one nonresident Expert for the next layer. The existing LFU policy
protects every Expert selected by the current route. Forecasts never increment
the demand-frequency counts. Declined eligibility leaves slot maps unchanged.

`native/app/cross_layer_forecast.h::CrossLayerForecast` stores at most 512
two-anchor contexts and 16 targets per context. Two prior observations and 3/4
frequency are required. Training follows observation; future routes are not
inputs. Batched prefill does not train the single-token predictor. This remains
the bounded statistical heuristic screened earlier, rather than a neural router.

`native/app/owned_mapped_backend.cpp::qwen_app_begin_predictive_expert` obtains
three actual shared Vulkan allocation leases through the existing bank-layout
validator. Each alias retains the real buffer, not an imported CPU pointer.
`MappedSourceReader::begin_expert_prefetch` resolves all three original roles,
checks complete source identities, aligned envelopes, disjoint destinations and
the original 53-slot geometry before any job starts. Cross-part/EOF-ineligible
envelopes decline prediction; ordinary demand retains its existing path.

`native/app/expert_prefetch_io.h::ExpertPrefetchIO` owns one persistent worker.
It performs the three role reads sequentially, retaining their actual leases.
The existing paired reader remains idle during this job. The producer joins
before another source operation, descriptor mutation or subsequent cache plan.
The original per-read kernel/Flexible predicate is checked through a read-only
worker observation, without modifying the producer's admission controller.
An unknown 10-second completion retains the job, worker and allocations; there
is no cancellation, fallback, automatic retry or uncertain resource retirement.

The source reader charges all predictive logical bytes, aligned physical bytes,
read counts, worker time and foreground join time. Join time also enters the
ordinary producer-wait aggregate. No new weight cache is allocated: placement
uses the existing 53 slots. One additional CPU worker and bounded metadata do
consume resources and still require actual native admission and measurement.

`native/app/predictive_cache_policy.h` and `native_main.cpp` expose the independent
private `native_predictive_cache` scope. It cannot be combined with expanded
cache, checkpoint, prefix or speculative experiments. It is absent from the
production profile. A final explicit join precedes model retirement.

## Expert-aware width-one/two source path

`LlamaEngine::enable_expert_aware_speculation` connects complete measurement hooks
to `OnlineExpertVerification`. Ordinary completed processes supply actual
48-layer routes through `last_completed_single_token_routes`, elapsed time and
source critical-path time. Only 32 past token-route associations are retained.
The existing model-free drafter uses two consistent past matches.

`OnlineExpertVerification::choose` estimates a pair's per-layer union from those
past observations. It charges both target computations, predicted source work,
capture time and expected rejected work including ordinary reprocessing. The
first causally eligible pair is a labeled calibration attempt. Subsequent
acceptance estimates use a Beta(1,1) prior updated by observed outcomes. Before
a rejection supplies actual restore timing, measured capture time is used as a
provisional restore estimate; it is **not** an established physical bound.
Context-dependent routes, linear union/source cost and doubled compute cost
remain modeling assumptions. They cannot establish a speedup.

The controller actually calls `choose_expert_verification_width`; width four is
unavailable in this native scope. Width one keeps ordinary execution. Width two
uses the existing `next_with_one_draft`: full original target logits, greedy
verification, complete-state rollback on rejection and one queued bonus after
acceptance. Capture and restore costs include the real checkpoint operations.
No additional learned model, quantization or future-route oracle is introduced.

The independent private `native_model_free_speculation.verification_policy`
value `expert-union-online-v1` enables this integration and requires the completed
route observer. Omitting it retains the older fixed-width prototype. Actual
choices, attempts, acceptance, rejection and bonus samples are reported separately.

## Validation and traffic accounting

- `check_native_predictive_integration.py` executes extracted **actual** cache
  planner/prediction functions. The positive control submitted 94 predictions,
  retained every pinned current Expert and counted every delivery. The declined
  control submitted no delivery and preserved placement. These are synthetic
  metadata/API controls, not model or GPU results.
- The actual source coordinator passed original-envelope pattern checks,
  producer/worker completion, a returned-short-read refusal, and timeout retention
  of a real allocation lease. The worker timeout is not tested on the console.
- The actual Llama adapter and upstream greedy sampler passed 32 API/state cases,
  including ordinary and width-two outcomes through the new cost hooks.
- Scope checks passed 23 predictive and 44 speculative/prerequisite refusals.
- The actual completed-route observer and real GGML CPU provider passed 29
  cases, including complete single-token extraction and refusal of incomplete
  or batched observations. Its actual PS5 object also compiled.
- Eleven Python result-review groups cover complete original routes, speculative
  work, predictive transfer totals, owner identity, retirement and zero-attempt
  reports. Zero attempts do not qualify an optimization.
- Seven isolated native model-I/O objects compiled with the actual PS5 SDK.
  The final native application linked, actual-module imports passed, and the
  28,419,239-byte SELF passed integrity and all six segment roundtrips. Its
  SHA256 is `fb5687036fc72bb419b4395b8e0f7e76d3e8c1b65f5dfea224efb814e4a4c56b`.
  This artifact was not installed or launched. Earlier build iterations remain
  preserved; the final receipt binds the corrected source and accounting.

Predictive route sidecars use schema v2: original routing is retained, cache
behavior is explicitly changed, and demand/predictive bytes are separate while
`uploaded_bytes` includes both. The independent route reviewer requires explicit
`predictive_cache=True`. Speculative route review counts actual width-two groups,
including discarded rejected branches, rather than substituting ordinary routes.
The result reviewers do not promote any result as a speed qualification.

## Remaining native work and environment

The last completed admission observation is case 3194: 5799 free pages versus
the existing staged full-model CPU reference of 8159. That reference used an
observed 6749-page initial CPU decline, the 1154-page operational floor and a
256-page variation allowance. These are application policies/measurements, not
hardware minima or permanent impossibility. The new worker's actual native cost
is not established. This implementation supplies no measured startup reduction.
No unchanged refused model scope, new ELF, title or GPU work was repeated.

Native execution remains unavailable under the established current conditions.
Reopen after a supported measured startup reduction or materially changed actual
headroom, price the new scope and retain its ownership/numerical/completion gates.
Then validate each feature independently: controlled acceptance and rejection,
original F32 continuation logits and per-token routes, exact original bytes and
bank lifetime, followed by fresh matched A/B and B/A requests. Include every
prediction, checkpoint, discarded batch and reload in total time and traffic.
Report prefill, TTFT, decode tok/s, kernel/Direct/heap peaks and positive retirement.
The trace's conditional 3.2258% traffic opportunity is not a speed prediction.

The exact fastest installed SELF remains
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
Original BF16/F32, F32 KV, 512 MiB parts, 53 slots and all settings remain selected.
Driver revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`,
archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`
and disabled persistent caches remain unchanged. All 1527 original shaders and
the exact existing encoded resource pool are retained. No CI or console operation
is part of this integration round. No new production speed winner is claimed.

The [allowlisted result JSON](native-predictive-integration-20261027.json) records
artifact identity and evidence digests. Raw logs, private runtime bindings,
endpoints, SDK content and binaries remain outside Git.
