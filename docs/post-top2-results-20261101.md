# Post-Top2 execution evidence

Work in progress. Production30300 remains unchanged. Acceptance below means
selection for the final composition; it is not a claim of completed deployment
or completion of all17 candidates.

| Candidate | Native evidence | Observation | Disposition |
| --- | --- | --- | --- |
| R1 Top2 Gate/Up |30700,180 graphs | Full F64 outputs, duplicate IDs, canaries and fallback pass; maximum absolute error5.100e-12. Backend time is37.8–44.0% shorter for one token and31.9–32.6% shorter for two. | Whole-model verification required.31700 stopped during loading.33300 completed14 requests but recorded zero candidate dispatches; its timing is coverage-invalid and is not a fused-kernel speed result. |
| N1 CPU selection slice |31500,14 requests | Full F32, routes and tokens match. Retained decode−0.717%; whole time+0.431%. | Tested negative. Compact GPU selection and deferred evidence remain separate work. |
| R2 cap6/8 |31600,14 requests | Cap8 makes7 attempts, accepting6 and rejecting1 on timed inputs; cap6 accepts6/6. Decode+0.415%, whole time+0.149%. | No adoption. Cap12 does not bind on the recorded timed proposal sequence; its separate disposition must not be called a measured speed result. |
| N2 cost capture |32400,3 requests and normal API/display | Full numerical evidence, resource retirement, ordinary close and exact restore pass. Retained output-projection intervals total86.687ms; the other category totals1342.640ms. | Diagnostic only. Divisor40/10 comparison32800 is built; native comparison pending. |
| N4 static Top4 prefill |32500,14 requests | Cold TTFT−24.322%, cold total source bytes−30.659%. Cold output is prematurely `1,2`; retained decode−9.361%, whole time+29.478%. Three of four semantic tasks pass. | Tested negative for deployment. Shorter incomplete answers are not equivalent completed work. Adaptive prefill remains separate work. |
| N5 observed startup |32600,3 requests, both API streams and2 frames | Settle5.006610326→0.100198499s. All three token/byte outputs match30200, including the existing prefix-answer error. All owners retire; ordinary close and exact restore pass. | Accepted for final composition. No decode-speed gain claimed. |

N5 first recorded stage to context-ready is26.949297476s, compared with
34.967627542s in30200. Only the4.906411827s settle-component reduction is directly
attributed to the changed wait. Other startup variation is not attributed to it.

## Measurement and interruption boundaries

- Timestamp intervals include barriers and possible queue/submission gaps. They
  are not isolated shader-instruction times, and the diagnostic changes
  scheduling. Do not subtract them from ordinary request time and call the
  remainder pure CPU time.
-31700 completed935 fenced upload copies,2857697440 bytes, then reached the
  application loading predicate: free1135 pages versus minimum898 plus256
  padding pages. This is not proof of physical allocation failure. The case was
  normally closed and the exact production/settings restored.
- The application `statfs` addition in31100 resolved to an unqualified direct
  syscall396 in title code. The owner exited before model load. The exact kernel
  exit mechanism is unproven; the call was removed from every later candidate.
- The109-tensor output-Q4 preparation reuses108 complete qualified payloads and
  converts only the original BF16 output head. Independent whole-payload and
  header checks pass. This saves317849600 resident bytes; it is not a speed result.
-32350 returned FTP ENOSPC after14202880 bytes although `statfs` reported about
  1.75GB available. Both paths have the same filesystem ID. Treat that reading as
  reported availability, not a guaranteed writable lower bound. The exact failed
  prefix was archived, compared with its source and retired; the CPU publisher
  and GPU never ran.
- Obsolete source directory509cf was the unadopted Expert-Q2_0 experiment. It is
  absent from the protected current/rollback roots. Full archival was stopped
  before any deletion because of transfer cost. Original BF16 files76/76,
  generation/publication recipes, metadata and all partial/completed archives
  remain.32370 retires170 generated files,22673162481 logical bytes, with all12
  current/rollback files verified before and after. Full archival of the old
  generated weights is explicitly not claimed.

Driver872cc126/cumulative-idle, disabled persistent caches, no reboot, no CI and
no learned host inference remain unchanged. Live source ancestors and both
qualified program/settings sets remain protected.

Native33900 qualifies the256-thread finite-argmax variant on110 synthetic graphs, including all vocabulary values, first-index ties, invalid values and canaries. Single-row readback/selection is547.255 to375.007 microseconds; two rows1027.496 to376.781 microseconds. These are not whole-model results.

Native33800 executes216 two-token GDN selections per timed candidate request. Whole time is0.262% shorter, within variation; the quality counting answer repeats7. No adoption. Native34000 cap12 completes14 requests; whole time is0.451% slower, with all four quality tasks passing. No adoption.

The first output-Q4 model case33600 returns before GPU because its old isolated output-Q8 two-part source has no Expert composite plan. The34120 adapter preserves both complete old parts and their trailing bytes, with16 malformed-geometry refusal controls;34200 is a fresh native test.

Native35100 resolves the runtime policy: the entry environment forces one node per submit, despite the provider default100. The explicitly scoped1-to4-node comparison preserves original kernels, flop cap and completion fences. All14 requests retain exact F32/routes/tokens and four semantic tasks pass. Retained throughput improves11.916%,whole time9.439%; submissions35856 to21541. Accepted for final composition, pending larger-group comparison and normal qualification/placement. Driver defaults are restored after each graph; original physical guards are unchanged.


### Further native results (cases34700–37500)

- Node16, then node256: the direct16→256 comparison37300 completed14 requests with every F32 value, route and token exact, four semantic tasks passed, positive retirement, ordinary close and exact restoration. Decode gained2.4115% and whole time fell1.1073% relative to node16. The actual maximum candidate batch was163 nodes and no node-cap event occurred;256 is nonbinding on this workload. This is separate from the earlier1→16 result; do not add percentages.
- OutputQ4 format34700 versus bracketing unchanged cap6 Q8 controls31600/35400: all four Q4 retained replays were faster than every Q8 control. Mean whole time fell0.46125%, decode rose0.45111%, with exact routes, emitted work, source bytes/calls and controller attempts. Resident output storage falls317,849,600 bytes. Four semantic checks passed; broad quality equivalence and cross-format full-vocabulary KL are not established. Same-format internal replay variation is not called format gain.
- Ring36300 completed14 requests and four semantic tasks but only+0.3228% decode/−0.1872% whole-time change, within A/A variation. Not selected. The explicit loading206 trial retained OS minimum898 and reservation206; actual minimum1165 never exercised the lower206-versus256 interval. This is not a measured lower-limit proof. Fifth-slot counters are added for the separate C3 combination.
- Gate/Up37500 captured actual model metadata and still executed zero fused kernels. Its result is coverage-invalid, not a negative fused-kernel speed result. The original graph optimizer protects GDN/QSA spans but has no protection for the new Gate/Up span; the captured post-optimizer nodes are two compatible MM_ID operations followed by unrelated nodes. A new integration protects all three nodes in both pulling passes, retains external-input lifetimes, preserves patterns while control graphs are cached, and requires positive candidate dispatch.
- CPU-only37000 stopped during whole-SELF inspection after two returned reads: free1261→754 versus unchanged919 floor. No GPU initialization occurred; ordinary close/restoration completed. Previous completed scopes recovered free pages during inspection. Candidate37500 includes a bounded same-floor wait and completed14 requests, but never needed that wait; its recovery branch is not claimed as tested by this run.
- R4's unconstrained fixed-size refit regressed all four held-out traces. The revised phase-specific selection reuses the existing sealed1024-triplet file, preserves all348 prior keys and activates398 decode keys. Supplemental covered misses change236/10/237/148/183/230→254/42/257/148/185/233 for training cold/retained and four held-out tasks, with no regression. Native verification remains pending.

Production30300 is still unchanged. Node256, outputQ4 and condition-based settling are candidates for final normal/API/display composition; no deployment is claimed yet.


## Further completed comparisons

R1 finally executes816 candidate dispatches per timed request in39300. It is0.0527% slower in whole time and is not selected. Prior zero-dispatch trials are coverage failures, not fusion-speed results.

R4 phase-refit39700 completes all14 requests and four semantic checks, but whole time is0.4072% longer. C3 combination39900 is8.72095% longer with2of4 semantic checks passing. Neither is selected. C2 combination40300 executes both kernels (768 Gate/Up and252 GDN2 dispatches per timed row); initial whole time is0.65047% shorter, with3of4 semantic checks passing. Fresh replication41100 is prepared before adoption.

The40700 heap diagnostic records mapped503,382,016 bytes, historical peak671,219,712 bytes, cap536,870,912 bytes and zero libc fallbacks. No actual GPU argmax ran. The mapped value is below the app quota; the historical peak is above it. This does not establish physical exhaustion. The synchronized obsolete-scheduler/replacement overlap is being removed without raising the quota or cutting Expert-cache slots.

D3 first-layer/rank slice41300 completes180 graphs over five shapes, every representation-specific F64 output and input/output canaries, positive retirement and ordinary close/restoration. The rank32 Q8 basis plus TQ1 residual reduces Expert-triplet bytes22.1667%, but Gate/Up slice time grows56.70% (one token),67.48% (two tokens),105.30% (30-token prefill). Relative squared weight error is approximately0.66; it is not an answer-quality measurement. Full-model speed and answer quality are not measured or claimed. This representation is not advanced to full conversion after the unfavorable first-stage cost/approximation screen. The40500 source-open failure is retained;41300 changes only the title-visible app0 binding before the successful slice.


C2 replication41100 completes14 requests with actual dual-kernel coverage and the same3of4 semantic result. Average whole-time reductions are0.6505% and0.4727%, but paired reductions are[46.4664,−5.4199]ms and[−5.0413,34.7800]ms; control A/A spreads are29.1758ms and26.3689ms. Each cohort contains a slower candidate pairing. The decoder-only eligibility flag in the generic analyzer is insufficient for the plan's repeatable whole-time criterion. C2 is therefore not selected; no quality regression is adopted for this inconsistent result.

The final node256 divisor40/10 case38300 completes14 exact requests and four semantic checks. Divisor10 gives−0.5232% decode and0.1889% shorter whole time, within variation. Node256/divisor40 remains selected.

The41500 changed lifetime scope gets past the earlier explicit heap refusal, then returns a decode failure. It is ordinarily closed/restored; no GPU-selection speed claim is made. The next changed scope preserves complete F32 evidence by sharing unchanged greedy raw/sampled output views, avoiding the stale separate raw plane that the framework does not download when every sequence is backend sampled.


N1/C1 full-model42900 completes14 requests with22 actual GPU argmax dispatches per timed candidate row; full F32/routes/tokens are exact and all four semantic tasks pass. Whole time is4.62039% longer and decode3.03014% slower, so GPU selection is not selected. This is the first qualified full-model result; preceding returned allocation/configuration failures are not speed measurements.

C4 is numerically qualified by42900: scheduler replacement now releases167,837,696 bytes before allocating the new owner (486,604,800→318,767,104 bytes). Whole-process tracked CPU peak falls671,219,712→503,382,016 bytes, below the unchanged536,870,912-byte quota, without cutting3712 Expert slots. The physical raw/sampled F32 greedy views share one unchanged plane; every full row and row order remains checked. Standalone throughput improvement is not claimed for this memory-lifetime correction.

MTP42500 durably identifies the41900 lost terminal as a library assertion: llama-batch.cpp:718 n_ubatch>n_keep_tail. The precise cause is the hybrid recurrent rollback splitter, not PLE: n_rs_seq1 requests a two-token trailing rollback window. A stateless one-token auxiliary needs no rollback; the public API defines n_rs_seq0 as disabled. The target keepsn_rs_seq1 and complete verification. The temporarybatch16 implementation is retained as an unlaunched control; the corrected candidate uses auxiliarybatch1/n_rs_seq0 and the actual-head graph budget.
