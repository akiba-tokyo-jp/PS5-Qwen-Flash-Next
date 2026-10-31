# Weight follow-up: measured results

The selected normal application combines a3072-slot Expert cache, validated
weight retention across requests and parallel delivery of small PLE/embedding
rows. It keeps every production weight byte unchanged: Gate/Up Q2_K, Down
Q2_0 MSE, resident matrices Q8_0, the original81920-byte BF16 PLE convolution,
and F32 activation/KV state. Native normal/API/display case12220 qualifies the
combined application. Production placement12260 is complete. Both the selected executable and its
immediate bd390 control, plus both five-setting sets, pass native whole
SHA256/identity/EOF verification. Runtime ownership is restored and a fresh CPU
observation confirms no native title, gateway or model running. The previous
control remains available. Placement starts no title or GPU inference. The
finite normal run binding is consumed; another run requires a fresh case.

| Priority | Candidate | Native result | Decision |
| --- | --- | --- | --- |
| 1 | 1381 ->3072 cache slots and retain verified Expert weights | Case11660 completes12 requests. Four-task total29.594s against38.410s mean of controls before/after:22.952% less time. Controls drift4.709%; candidate JSON uses24 rather than18 tokens. All task contents correct. | Selected |
| 2 | Up to8 small rows on4 existing read workers | Cases11760 and12120 reverse execution order at the same3072-slot capacity. Pooled scalar73.786s ->batch70.218s:4.836% less time. Full F32 rows, ordered routes, tokens and bytes are exact. | Selected |
| 3 | Gate/Up Q2_K ->Q2_0, Down unchanged | CPU conversion12004 completes all96 tensors; Expert payload falls3,774,873,600 bytes, triplet1,536,000 ->1,382,400 bytes. Case12040 generates the correct22-token counting answer, but its legacy byte-accounting guard rejects the cohort. Corrected12060 and compact-metadata12080 both stop during model loading on kernel-memory policy. | Not adopted; complete comparison cannot execute under the current measured memory condition |
| 4 | 108 large resident Q8 matrices ->Q4 | Case11880 completes8 requests, all task contents correct, same-profile full F32 difference0. Four warm task totals39.021s against historical37.218s:+4.844%. Saves1,038,090,240 resident payload bytes. | Tested, slower; rejected |
| 5 | 48 F32 routers ->Q8 | Case11940 completes8 requests, all task contents correct, same-profile full F32 difference0. Four warm task totals37.100s against historical37.218s:-0.316%. Counting decode3.920 versus3.932 tok/s. Saves184,811,520 bytes. | Tested, no demonstrated material gain; rejected |

The two precision comparisons use sequential historical control11520 rather
than a new matched ABBA. Their times include different possible output lengths;
they measure actual task completion, not identical generated work. The router's
0.316% difference is insufficient to attribute a useful speed improvement.
Same-profile F32 identity does not establish equality across quantization formats.

## Normal application

| Request condition, case12220 | Decode tok/s | TTFT | Total | Generated tokens |
| --- | ---: | ---: | ---: | ---: |
| Cold Expert cache, first generation | 4.377562 | 6.454s | 11.453s | 22 |
| Empty request/KV state, Expert weights retained | 4.177872 | 2.235s | 7.486s | 22 |
| Exact prefix reuse plus the existing causal controller | 6.300317 | 61.873ms | 3.872s | 22 |

The second request retains weights, not a conversation's KV state. The third
request has a different reuse condition; these rates must not be pooled into
one general performance claim. First-generation compilation/setup can bias
cold timing. The measured candidate gains above must not be added together.
The normal historical control11480 uses different cache occupancy; no matched
normal ABBA or sustained-service speed claim is made.

Both actual native frames were viewed, showing4.18/6.30 tok/s,22 tokens,
clock, CPU/GPU identity, memory and precision. Unsupported utilization counters
remain `--`. Three API POSTs, all counting token IDs/bytes, full-vocabulary
finite values, complete actual routes, prefix handoff and positive source/model/
GPU retirement pass. The final device ledger is0. CPU heap peaks at503,382,016
bytes under536,870,912; transient device ledger5,068,816,384 under5,086,097,408;
actual workspace8MiB under48MiB. The ledger is not total physical RAM usage.

Cache-aware ranking can choose different Experts when cache occupancy changes.
The normal maximum F32 differences3.459213/3.509688 are disclosed rather than
treated as an exact arithmetic comparison. Exact cold same-cache controls for
row batching independently pass with maximum0. Four fixed short tasks and a
counting display do not qualify broad reasoning or long-running service.

## Failed Q2_0 comparison and execution constraint

This candidate requantizes the current Q2_K through F32; it is not a direct
original-BF16 quantization. The unused original-BF16 host conversion was canceled
and its identity-verified host process closed. The native codec independently
matches the pinned reference on1,048,576 decoded values and294,912 encoded bytes.

Case12040's partial counting observation is2.5916 decode tok/s, with first-run
setup bias; it cannot establish a complete or matched performance result.
Its positive intermediate GPU fences and reset are preserved. The accounting
constant is corrected to the actual1,382,400-byte triplet in the maintained
builder. Selected-tensor metadata is then compacted without changing source
integrity or shape/type/byte checks, and all1256 tensor descriptors and negative
fixtures pass on the host.

Case12060 observes1145 free kernel pages; compact case12080 observes1122.
Both require1360:898 ordinary minimum +206 reserved +256 margin,16KiB/page.
Neither completes model loading or the eight-request comparison. This is an
application policy refusal under the observed condition, not proof of a
physical PS5 impossibility. There is no supported speed or quality admission
for this format. Its disposition is execution unavailable under this condition,
not untested or a silently pending benchmark.

The failure terminals retain `unknown_completion=true` for resource retirement
before ordinary close. Both titles subsequently close through the ordinary OS
path, exactly restore the control and confirm fresh idle. Do not erase that
failure evidence or replay these consumed cases. A future separately scoped
variant must reduce measured startup kernel consumption, finish all eight
requests with the original reserves, then improve total request time before
adoption. Reboot, relaxed reserves and repeated identical launches were not used.

## Implementation and provenance

`build_resident_cache3072.py` prices expanded banks from verified resident
payload savings. `resident_weight_retention.h` checks both directions of all
live slot maps; the original request/KV reset and completed-GPU requirements
remain. `build_weight_followup_normal.py` enables the measured retention and
small-row defaults in the normal composition.

`resident_small_rows.inc` maps and sorts immutable physical row spans, merges
eligible duplicates/overlaps and dispatches through the four existing workers
and8MiB scratch. It checks identity, EOF, original reserves and completion
before consuming rows on the original thread. Real counting822 logical rows
still require822 physical reads; the Japanese554 rows require553. The observed
gain primarily comes from concurrent reads and amortized boundary handling,
not a large syscall-count reduction. No extra GPU or scratch allocation is added.

The normal executable is SELF
`3066dfe45c32d0586e3bdddb9e9ab31b200b3185a20aa0206e2418f326b2002f`,
20,081,383 bytes. Its native build is `Weight-followup-normal-12200`, package
`Weight-followup-normal-SELF-12202`; receipt digests and the exact application
source revision are recorded in the adoption JSON. Driver source remains
`akiba-tokyo-jp/PS5-Vulkan-Inference` revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. No driver relink change,
CI, agents, forced PS5 signals, GPU reset or reboot was used.

CPU-only cleanup11787 retires26,066,742,624 logical bytes of obsolete Q4 parts
with all559 current/immediate-control source identities protected. Cleanup12172
retires the rejected dense candidate's1,179,356,480 bytes, preserving its complete
host payloads and729 protected source identities. Native full SHA256/EOF checks
precede truncation; filenames remain to preserve directory identity. The latter
operation changes free kernel pages5517 ->5516: file retirement did not recover
kernel memory. No exclusive OS VM attribution is established.

See `weight-followup-adoption-20261031.json`,
`weight-followup-retention-results-20261031.json` and
`weight-followup-small-rows-results-20261031.json` for machine-readable results.

Manual validation includes the native cases above, exact small-row/scratch/EOF
and retained-map ownership fixtures, all1256 overlay descriptor checks and
negative controls, actual source-planner/scope checks, Python syntax checks and
production admission refusal tests. The final installed record also passes the
ordinary `qualified_control` dispatcher. No CI was run. Unused interrupted host
conversion outputs11800/11801 are removed (2,799,688,352 and10,048,788,512 bytes);
original BF16 sources and all selected model sources remain.
