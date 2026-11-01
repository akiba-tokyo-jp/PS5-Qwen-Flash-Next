# Ordered owner, HC and command-reuse validation

All four requested categories were verified in order:1/2, then3, then4.
Five complete fourteen-request native cohorts cover the categories and split-K
choices. An initial HC contiguity assertion was corrected in a changed scope;
its exact program/settings restoration is preserved separately. No unchanged
failed launch was repeated. CI, agents, learned host inference, restart, forced
reset and persistent shader/pipeline caches were not used.

| Category | Native case | Retained decode change | Whole-request time reduction | Result |
| --- | --- | ---: | ---: | --- |
| 1: Owner/journal-generation certificate | 51100 | +2.392034% | +2.099551% | Selected |
| 2: HC Down/Inject projection alias | 51500 | +0.010170% | +3.277885% | Selected |
| 3: Shape-limited HC split-K4 | 51700 | +0.259558% | +0.593444% | Selected |
| 4: Resident secondary-command cache | 52100 | -0.028376% | -0.429743% | Tested negative; excluded |

These are separate matched comparisons, not additive gains. All four scoped
categories passed four fixed semantic tasks. Split-K8 case51900 completed its
protocol but failed one task and did not show a repeated whole-time gain beyond
A/A spread; it is a completed negative result. Split-K4 independently repeats
all candidate full F32 rows and routes exactly; its cross-control maximum F32
difference9.860172510 is disclosed rather than used as an arbitrary cutoff.
The owner, HC-join and command-cache comparisons preserve cross-control full
F32 bytes and ordered routes exactly. Finite task passes are not general model
quality equivalence.

## Concrete implementation and measured scope

- `tools/build_frontier_owner.py::transform` changes
  `DriverLifecycle::finish_boundary` using
  `native/app/owner_checkpoint_certificate.h`. The queue lock, fresh worker
  health/epoch, retirement and complete owner checks still run. A duplicate
  durable checkpoint is reused only when device, submission, worker,
  allocation-attempt, owner-signature and arena-journal generations match.
 132 timed reuses save53.820/50.864ms, beyond3.281ms A/A spread. Focused
  API-stub checks cover allocation ABA, new submission, journal/owner changes,
  unhealthy logs and original refusal/retention paths.
- `tools/build_frontier_HC.py::transform` changes
  `llama_model_qwen4exp::load_tensors` and `graph::build_hc_mix`. Original Q8
  Down/Inject tensors become adjacent. A metadata-only combined root alias is
  allowed only after actual same-buffer, contiguity, type, range and no-adapter
  checks. One projection reads their common normalized input; output slices are
  explicitly contiguous. No weight is duplicated, changed or requantized.
  The initial51300 CPU scale contiguity assertion retained backing until
  ordinary OS close; corrected51500 completed all fourteen requests. Timed
  candidates execute5376 joined projections. Whole time falls3.277885%; the
  established benefit is prefill/TTFT (80.586/72.647ms versus1.992ms A/A),
  not decode throughput (+0.010170% mean with opposite-signed pair changes).
- `tools/build_frontier_split.py` changes `ggml_vk_mul_mat_q_f16` within the
  qualified Q8 HC guard: K>=2048, M<=512, N16-32, original split1. Selected
  split-K4 uses existing shaders and original allocation limits. Actual GPU
  selection counts and split sums prove the changed path executed388 times in
  the timed candidate requests. Savings12.628/15.495ms exceed6.243ms A/A.
- `native/app/frontier_command_cache.inc::qwen_frontier_dispatch_pipeline`
  verifies actual resident decode projection replay with immutable owned
  descriptors. The full binding/push/pipeline/layout/shape/context/family and
  buffer-destruction generation key passes40 host invalidation checks. All
  original barriers and fence waits remain; stale command pools retire only
  after positive synchronization. The scoped256-entry variant executes9984
  timed cache hits with256 recordings and17320 capacity fallbacks. Whole time
  worsens0.429743%; extended retirement eventually returns positively. This
  implementation is excluded from the normal binary. The slice does not prove
  that every possible larger primary-segment design is impossible.

## Qualified normal application

Native53100 includes one local cold self-test, two actual generation API streams,
a finish POST, two viewed native frames, three exact token-ledger readbacks,
positive source/model/device retirement, zero live device bytes, ordinary close
and exact prior SELF/settings restoration. All three controlled counting answers
pass without output rewriting. Rates include generated reasoning/answer tokens.

| Condition | Decode | TTFT | Whole request | Generated tokens | Counting task |
| --- | ---: | ---: | ---: | ---: | --- |
| Cold weights | 8.278168 tok/s | 5.822022s | 8.460676s | 22 | Pass |
| Retained weights, empty request/KV | 10.825984 tok/s | 0.397102s | 2.438066s | 22 | Pass |
| Exact-prefix reuse plus causal path | 12.099275 tok/s | 0.056919s | 1.896591s | 22 | Pass |

Normal50100 and53100 are sequential product configurations, not matched ABBA.
Retained decode changes from10.555503 to10.825984tok/s
(+2.562458%); whole time falls
5.875720%. Prefix output differs from the previous25-token
incorrect output, so its rate is not a same-output speed comparison.

Normal mode7 actually executes86 duplicate checkpoint
reuses and2400 joined projections. GPU split sums independently
prove factor4. CPU peak503382016B and device-ledger peak
6167724032B remain within unchanged budgets.

Expert Gate/UpQ2_K, DownQ2_0 MSE,109 resident Q4 matrices including output,
remaining Q8/original F32 and tiny BF16 PLE, F32 activations/KV/recurrent state,
3712 active slots/3713 planes, Top2 decode/six-Expert prefill, node256/divisor40
and the existing tail policy remain. Driver source stays
872cc1264ad8ba5d6b888b092968fa5858a38c58/cumulative-idle, profile archive
67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9 and
native composed archive b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925.

The exact clean application relink revision and fingerprints are in
[the adoption record](frontier-adoption-20261101.json); normal source revision
is a24f6da7a09859432cb9c994f221bf727441c9b5. Verified production placement53200
is complete. Thirty current-config rejection controls and future-case admission
pass; all twelve current/control native files have full SHA256/identity/EOF proof. The immediate4f5d control and all
five settings are preserved. Qualification is this finite scope, not arbitrary
prompt, context or sustained-service qualification.
