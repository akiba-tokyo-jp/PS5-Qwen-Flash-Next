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
