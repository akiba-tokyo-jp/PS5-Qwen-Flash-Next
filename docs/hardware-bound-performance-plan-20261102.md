# Hardware-bound performance implementation and verification

The owner authorized implementation, verification and adoption of beneficial
performance changes on 2026-11-02, explicitly including non-quantization work.
This is a new application campaign. Closed APR/PFS/Kraken and compatibility
initialization attempts are not reopened or replayed. Restart is unavailable.
The initial campaign baseline was SELF56c29e9c..., source2b683814.... The
[current measured deployment](native-performance-comparisons-20261102.md) is
P1 over completed-stage R1 SELFc5afc565..., installed on PC and PS5 through
publication65256. Driver872cc126/cumulative-idle and disabled persistent caches
remain. The later Q3 component65259 unexpectedly exits without a completion
certificate; P1 files are positively restored, while further native GPU scopes
remain pending positive completion classification. Host work continues.

## Independently controlled candidates

| ID | Candidate | Required observation before adoption |
| --- | --- | --- |
| Q1 | Shared Expert Q8_0 to Q4_0, encoded from original BF16 | Exact selected 144 tensors, reference encoder equality, actual PS5 whole-request/latency/quality comparison |
| Q2 | Routed Gate/Up Q2_K to IQ2_XXS | Actual indexed PS5 shader support, independent numerical fixtures, complete model quality and matched native timing |
| Q3 | Routed Down Q2_0 MSE to IQ2_XXS | Same as Q2, independently controlled; do not silently reuse mixed-format bundles |
| R1 | Production execution/diagnostic policy | Separate telemetry and persistence costs from compute; preserve resource completion; measure changed durability explicitly |
| G1 | GPU residency ranking and all-hit continuation | Actual linked RADV indirect behavior, stable maps/addresses, exact hit/miss/resume routes and complete state |
| P1 | Final-output-only prefill after correcting crop/cache interaction | Boundary lengths and complete continuing state, prefix/speculation behavior, TTFT and whole request |
| I1 | Q2 staging prefetch and ready-work/read overlap | Actual demand-blocked wait, useful/wasted bytes, slot leases, no prediction-induced routing changes |
| S1 | Persistent/prewarmed stateful MTP verification | Include auxiliary setup, draft, acceptance, rollback and target verification in whole time; no unverified output |

CPU heap, device ledger, per-buffer geometry, cache slots, I/O depth, context,
request/output bounds and telemetry frequency are implementation choices.
Replace them only with explicit measured accounting or a supported implementation;
do not represent a historical guard refusal as a physical hardware limit.

Compare empty Expert cache, retained weights and exact-prefix reuse separately.
Report TTFT, complete request time, accepted decode throughput, p95 token latency,
memory ownership and quality. Same-computation variants record full F32/routes/
tokens; approximations disclose their differences. Use repeated matched orders
and measured control variation rather than a fixed two-percent cutoff.
Host checks and source/object evidence do not qualify PS5 speed or adoption.
Keep production intact until native comparison and ordinary closure succeed.
Retire rejected generated artifacts after their owners have ended; retain only
the current production package and sanitized reproducible source/results.
