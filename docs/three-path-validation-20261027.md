# Three-path validation

The owner selected OS I/O paths, predictive caching, and expert-aware speculative
verification for a new bounded validation. This reopens these specific scopes;
it does not replay the consumed cache-128 cohort or turn the earlier closing
ledger into a claim that these new comparisons have already completed.

Use original BF16/F32, F32 KV, one PS5, the qualified driver/profile, no reboot
dependency, no CI, exact identity and positive retirement. Keep production
unchanged until a complete model comparison establishes a winner.

1. **OS I/O:** reuse completed per-thread syscall/wait controls. Audit actual
   strong module exports and a pinned PS5 AIO declaration. First qualify a
   read-only, bounded AIO lifecycle independently of GPU/model startup. Compare
   the actual paired reader and AIO with the same original bytes, Direct
   destinations, descriptor identities, hashes, priority and durable completion.
   No raw block-device, mount, firmware, kernel ownership or unknown release
   modification is part of this test. A failed prerequisite closes that scope.
2. **Predictive cache:** replay SHA-bound completed original routes at 53 slots.
   Compare current LFU4096 with causal reuse-deadline eviction and bounded
   cross-layer transition predictions, reserving at most two existing slots.
   Count every speculative load, eviction and subsequent reload. Protect actual
   selections and the preceding layer's pinned set. Predictions are scored before
   observing the target route; train only after it is observed. Fixed parameters
   are not selected from the reported evaluation result.
3. **Expert-aware verification:** use only committed token history for drafts and
   past token-route associations for cost estimates. Compare ordinary decoding,
   fixed width two and a metadata-only width-one/two/four cost selector. Score
   future greedy tokens only after selection. Report accepted-path expert unions
   separately from unknown rejected-branch routes, checkpoint cost and actual
   multi-token arithmetic. A route replay is not a speculative speed benchmark.

The online speculative design is independently written. SpecFit's public README
explicitly says its reported experiment uses separately collected reference
routes and excludes route acquisition time. Neither those routes nor the current
trace's future rows may be inputs to our selector. Any traffic opportunity must
survive native route acquisition, state capture/restore, verification and full
request timing before adoption. The new checks stop after these three finite
decisions; no general literature refresh or identical startup poll is scheduled.

Implementation and results are appended after the tests. Missing native/model
evidence remains explicit. Exact source revisions, receipts, code paths and
reopening conditions accompany each outcome.

## Results: cases 3190-3196

The three bounded scope decisions are complete. Full-model speed comparisons of
all three mechanisms are not complete: their current native stage is explicitly
execution unavailable. The installed fastest application was neither replaced
nor launched. One new CPU-only ELF ran, without model initialization or GPU calls.

| Mechanism | Completed validation | Decision |
| --- | --- | --- |
| OS AIO API path | Actual PS5 strong imports, invalid-descriptor lifecycle, eight reverse-controlled original-byte pairs, exact hashes/identities and retirement | Source fixture loser; do not integrate this implementation |
| Predictive cache | Exact native LFU baseline replay and five causal alternatives; every speculative load and eviction-induced reload counted at the same 53 slots | No logical-traffic winner; retain LFU. Native latency hiding and actual backing remain unqualified |
| Expert-aware verification | Past-only draft/cost selector controls, native SDK metadata compile, and complete conditional width-two trace regrouping | Conditional traffic opportunity; actual two-token arithmetic, rollback and speed remain execution unavailable |

### Physical OS I/O result

CPU ELF `8c61e7d54c451014c961e1a99a4f6b00adc97f67be7d007149535588ec843691`
(479,528 bytes) linked 66 actual strong imports, including the five AIO functions.
The source is `native/qwen_flash_next/aio_source_probe.c`; lifecycle ownership is
in `aio_read_lifecycle.h`, and the control uses the application's actual
`PairedSourceIO` through `source_contention_probe_cpp.cpp::probe_cpp_read`.
The independent result review is `tools/aio_source_result.py::validate`.

The invalid descriptor returned SCE EBADF (-2147352567) with terminal state 3;
the single ID was positively retired exactly once. This is why an error value
must be checked independently of the terminal state. All 16 original matrix
deliveries (52,690,944 physical bytes) then passed complete original/envelope
SHA256 and stable descriptor identity. Four controls averaged **7.352782 ms**;
four AIO batches averaged **10.799674 ms**, a **46.88% elapsed-time regression**.
All four reverse ratios were below one (0.87249, 0.61122, 0.66635, 0.58039).
The control spread was 38.05%; the warm/cold variation is retained, not hidden.
No full-model tokens/s result is inferred.

Both arms used the same two original 3,293,184-byte envelopes and disjoint Direct
destinations. Timed AIO includes submission, bounded wait and completed single-ID
retirement. Default process AIO initialization, allocation and SHA checks are
outside both source intervals. Application-level requests are capped at two;
kernel-internal splitting and worker counts were not profiled. This comparison
does not identify the internal reason AIO loses. No further identical AIO run or
model integration follows. Source workers joined, every AIO ID retired, Direct
memory unmapped/released, and all three exact boot/service boundaries passed.

The broader filesystem-lock/raw-NVMe proposal remains execution unavailable
through the established PS5 interfaces. Export availability supplies neither
matching proprietary filesystem source nor a qualified ownership/bypass path.
No block-device takeover, raw kernel patch, mount or firmware change was made.
This AIO result does not rule out a future genuinely different OS path.

### Causal predictive-cache result

`tools/validate_predictive_paths.py::PredictiveCache` implements reuse-gap EWMA
deadline eviction; `CrossLayerForecast` implements a bounded two-anchor
cross-layer transition table. These are new trace-screen implementations, not
the full neural SeqMoE predictor or an actual hidden-state tap. All decisions use
past observations. The 53-slot LFU control independently reproduces the completed
native hit/miss/unique counters. Both external requests use the original saved
counting workload; the second retains its cache. This is limited workload evidence.

| Policy | External logical Expert bytes | Increase over LFU control |
| --- | ---: | ---: |
| LFU control | 381,232,742,400 | 0% |
| Reuse-deadline eviction | 383,188,992,000 | 0.5131% |
| LFU + one forecast slot | 381,547,315,200 | 0.0825% |
| LFU + two forecast slots | 381,970,022,400 | 0.1934% |
| Deadline + one forecast slot | 383,857,459,200 | 0.6885% |
| Deadline + two forecast slots | 384,437,452,800 | 0.8406% |

For LFU plus one forecast slot, 218/243 prefetches were used at the next layer,
but foreground demand fell by only 211 deliveries. Including 243 prefetches
therefore increased total delivery by 32 Experts (314,572,800 bytes). Correct
prediction does not automatically compensate for cache pollution. These are
logical Expert payloads, not physical SSD bytes or measured latency. A predictor
could still hide some waiting despite a small traffic increase; actual lead
time, foreground delay, source queue occupancy and genuine physical backing
leases are unqualified. Do not promote this trace screen as a speed result.

### Expert-sharing verification result

The past-only consistent-history drafter found five correct proposals among 21
eligible positions in each external request. Five successes are not a calibrated
acceptance probability or broad workload result. Local accepted-pair union counts
showed reuse, but local overlapping windows are not summed as a request speedup.

The separate full trace regrouping applies the fixed width-two choice causally,
preserves request cache reset/retention and simulates the entire 53-slot cache
lifetime. Conditional on unchanged per-token routes when batched, external
logical Expert delivery falls from **381,232,742,400 to 368,934,912,000 bytes**,
or **3.2258%**. Selection never sees future target routes. Saved greedy tokens
and ordinary routes are used afterward for counterfactual scoring. If any draft
is wrong, the calculation stops with unknown rejected-branch routes instead of
pretending that the ordinary greedy route describes the wrong draft.

This is a conditional traffic estimate. Original BF16/F32 batch arithmetic,
actual router equality, capture/restore, discarded work and request speed have
not passed a new native test. In particular, no 3.2258% tokens/s gain is claimed.
The metadata-only cost selector in
`native/app/expert_verification_cost.h::choose_expert_verification_width` prefers
accepted tokens per total estimated time and retains smaller widths on ties.
Its fixed screening assumptions (0.5 acceptance per draft, zero checkpoint time,
0.18 s compute per target and historical effective source 1.939 GB/s) are not
native measurements or calibrated online costs. Under them every selected width
was one. The function passed host refusals and actual PS5 SDK object compilation;
it is not connected to production model execution.

### Native availability and final state

After the positively retired new AIO lifetime, one read-only screen observed
**5799 -> 5799 kernel pages**, below staged full-model CPU entry **8159**. The
earlier initial full-title decline was 6749 pages, before the retained operational
floor. No model title, new GPU work, automatic retry or reboot followed. The
prediction/verification full-model stages are **execution unavailable in this
environment**, not failed speed benchmarks or permanent hardware impossibility.
Reopen only after a supported measured startup reduction or materially changed
available headroom, then qualify backing/width-two exactness and perform a fresh
matched model comparison including every route-acquisition/checkpoint cost.

Production remains original BF16/F32 and F32 KV, exact fastest SELF
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
Driver revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925` and
disabled persistent caches are unchanged. No new model-speed winner was adopted.
All new native source owners returned; no application was changed and no unknown
completion remains. No CI ran.

Manual checks: eight causal/cache/cost test groups, three independent AIO result
groups, sixteen actual AIO lifecycle fault controls, sixteen native-cost input
refusals, actual native cost SDK compilation, CPU AIO link/import audit and the
physical comparison. Preparation failures are preserved privately. The first
screen's exact implementation was preserved before adding full conditional
regrouping; the final screen binds the current source SHA256.

### Primary references and evidence

- [SharpProspero `KernelAio.cs` at 5dfdb4b0](https://github.com/SvenGDK/SharpProspero/blob/5dfdb4b0b166e83dc9ae275001afb695f12c7174/src/SharpProspero/Interop/Kernel/KernelAio.cs): 16-byte result, 40-byte request and 60-byte three-priority parameter ABI; bounded wait and single completed-ID retirement. Interface facts were independently declared; third-party implementation code was not imported.
- [SpecFit README at 4973b3cd](https://github.com/Chlience/SpecFit/blob/4973b3cdc48e5c016bc6c5ed18639d3163e8b2f5/README.md): reported route acquisition excluded from timing and separately collected routes; no online predictor result inferred here.
- [SpecMD, Apple Research](https://machinelearning.apple.com/research/specmd-expert-prefetching) and [SeqMoE v1](https://arxiv.org/abs/2609.12978v1): motivation for future-use-aware cache management. Their model/hardware results are not Flash-Next PS5 estimates; our fixed bounded heuristics do not reproduce those systems.

The [allowlisted JSON](three-path-validation-20261027.json) records aggregate
results, exact artifact identity, assumptions, status and private evidence
SHA256 values. Raw logs, source bindings, endpoints, SDKs and binaries remain
outside Git.
