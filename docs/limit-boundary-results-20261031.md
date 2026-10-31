# Application limits, operating boundaries and affected decisions

The owner-requested audit classifies21 limit families, indexes174 saved model-result cases and executes two new native scopes. Case12840 completes one model load and all10 counting requests while permitting application kernel padding to decrease. Case12900 completes288 numerically checked GPU graphs with split timing. Both ordinarily close, exactly restore production SELF5564792a and its settings, and return a fresh inactive native/gateway/model session. No production default is adopted by this investigation.

The central finding is that the application contains **policy thresholds, accounting reservations and measurement cutoffs that are not hardware limits**. The successful new scopes establish finite operating points; they do not manufacture a universal physical exhaustion point. The [numeric report](limit-boundary-results-20261031.json) preserves values, case IDs, evidence sizes/hashes and the explicit remaining qualification boundaries.

## What the new kernel experiment establishes

The actual selected admission provider has three modes: CPU metadata preparation adds21 pages to the observed minimum; model loading adds `max(reserved,256)`; the later context/inference mode adds64. With observed minimum898 and reserved206, the latter two predicates are1154 and962 pages. These are application policies.

The experimental provider changes only the application padding at positively completed boundaries. It can lower256 -> observed reserved ->128 ->64 ->0 pages, preserving the observed OS minimum, physical Direct/Flexible/CPU/ledger checks, source identity, positive GPU completion and ordinary shutdown. It does not write OS counters or replay an I/O/GPU operation. A below-floor observation still enters the existing bounded wait/refusal path.

| Phase in12840 | Admission evaluations | Minimum observed free pages | Minimum selected application padding | Legacy predicate failures |
| --- | ---: | ---: | ---: | ---: |
| Model loading |6791 |2312 |256 |0 |
| Context preparation |9 |2267 |64 |0 |
| Inference |241616 |873 |0 |43 |

All10 requests complete with exact full-vocabulary F32 rows (maximum0), ordered routes, tokens and bytes for the byte-placement controls. Model/source/GPU owners retire positively and the device ledger is0 before normal close.

Inherited `kernel_extra_margin_bytes` fields describe the legacy provider's report labels. In this explicit experiment, the scoped `limit_margin_probe` counters and selected header determine the effective predicate. Likewise, the old terminal's64MiB workspace label does not override the actually compiled48MiB reservation. Neither stale label is treated as a physical measurement.

**873 is an observed global free-page count, not an admitted execution threshold.** It is below the observed898-page watermark and therefore belongs to the wait/refusal path. Successful completion shows that the process subsequently proceeds through admitted observations. The43 evaluations are failed instantaneous legacy predicates, not43 separate canceled requests or proof that the old20-second wait would necessarily time out. Padding reaches0 during inference; it was not0 for the entire ten-request run.

The experiment demonstrates completion after dropping the former post-load64-page cushion. It does **not** reproduce the old load failures below1154: loading in this run remains above2312. The old load cases remain evidence of an application threshold, but their hypothetical remaining execution cannot be inferred from this run. No claim that1154,962 or898 is a physical kernel exhaustion point follows.

Upstream [FreeBSD page-allocation code](https://raw.githubusercontent.com/freebsd/freebsd-src/releng/9.0/sys/vm/vm_page.c) uses distinct allocation-class/reserved watermarks; their sum is not a universal hardware-capacity formula. This explains why adding observed counters needs justification. Exact equivalence to the proprietary PS5 allocator is not established. The probe preserves the larger observed minimum and does not assume inactive/cache pages are immediately allocatable.

## Inventory and established boundaries

Values refer to the actually linked generated providers, not only repository header defaults.

| Limit family | Current value | Evidence and boundary finding | Classification |
| --- | --- | --- | --- |
| Loading kernel predicate | Minimum +max(reserved,256) =1154 pages | Fixed4MiB padding has no minimum-necessity qualification; old returns1148/1137 fall6/17 pages short | Application padding |
| Post-load kernel predicate | Minimum +64 =962 pages |12840 reaches0 extra and completes; below-minimum observations still wait | Application padding with measured component ancestry |
| Context entry |1005 =898+64+43 | Prior observed context decline41 plus2 padding; new scope prices41 but does not reach a low context-entry point | Finite component observation, not universal minimum |
| GPU/CPU initial entry |1185 /1410 pages | GPU components include8 observed initializer pages,2 initializer padding,2 worker pages and19 source allowance; startup costs are checked by phase | Component estimates and padding |
| Source Direct metadata |19 extra pages for a new allocation;0 for an already owned window |17 observed metadata pages plus2 padding; reuse must not charge the allocation again | Measured components plus padding |
| Initial CPU metadata |21 pages over minimum | Sampled Direct metadata17, idle2 and selected2; no tight minimum established | Measured components plus padding |
| Old startup estimates |10142/8159 pages; historical100MiB interpretation | Whole global intervals were not an exclusive per-operation cost; later phase-local lifetimes supersede these admission estimates | Retired estimates |
| Physical Direct reserve |512MiB | No minimum-reserve sweep establishes512; it is separate from kernel pages | Unmeasured physical-pool cushion |
| Additional Direct platform margin |256MiB | Added separately from CPU/staging; minimum marginal necessity not established | Unmeasured physical-pool cushion |
| Flexible reserve/read allowance |256MiB +8MiB | Native preflight reports423MiB available; source read window is already Direct-backed. The8MiB Flexible metadata price is not a measured minimum | Separate quota cushions |
| CPU mapped-heap cap |512MiB | Successful normal peak480.0625MiB; new headless peak432.0625MiB. These are mapped allocator peaks, not intrinsic live model memory | Software cap; finite observed lower requirement |
| CPU growth pricing | Full512MiB cap before load | The Direct-free query already excludes owned CPU extents. Unlike the older after-load pricing helper, before-load pricing does not subtract already-mapped CPU; a simultaneous heap sample is needed to quantify the extra price | Conservative growth accounting |
| Workspace reservation |48MiB | Rounded capacity peak8MiB for the tested context;40MiB accounting difference. Raw terminal's64MiB label is stale | Fixed accounting reservation |
| Post-load single buffer |1600MiB | Selected backend reports2GiB; four2GiB allocations previously returned successfully.1600MiB is not the demonstrated allocation ceiling | Software cap |
| Post-load live byte quota |5086097408 bytes | Normal peak5068816384; quota headroom17281024 bytes. Older checkpoint refusal needs only8986624 bytes beyond its older quota despite ample Direct/Flexible values | Software quota |
| Expert cache profile |3072 slots | Typed profile, byte quota and1600MiB bank cap constrain growth; capacity pricing and exact planner replay are below | Selected configuration, not maximum physical capacity |
| Entry/evidence capacities |8192 ledger entries; bounded VM/route arrays |12360 exhausts a diagnostic observation vector after19 requests; later corrected cohort completes | Software evidence bounds |
| I/O lanes/window/group |4 lanes,2MiB scratch/lane,8MiB total,12 known reads/group |2/3/4-lane evidence exists; higher concurrency/larger-window optimum is not established. Current values are not SSD hardware limits | Finite performance tuning range |
| Other tuned finite choices |Prefill32,1536 protected keys,6 causal attempts | Alternatives were measured; neither optimality over all workloads nor a hardware limit is claimed | Workload-specific selections |
| Wait/time horizons |20s boundary/60s process,100ms polling,20min load | These bound an experiment; expiration is not evidence of memory exhaustion | Chosen recovery/time bounds |
| Performance/stopwatch rules |At least2% in both orders; isolated timer included whole completion checkpoint |2% is a chosen adoption screen, not hardware- or variance-derived. Checkpoint interval is99.082% of the new isolated measured total | Decision/measurement constraints |

Alignment, overflow/shape/source identity, complete numerical output, unique resource ownership, positive GPU completion and ordinary close are correctness requirements. They are not treated as expendable padding by this audit.

## Cache capacity: explicit software and resource envelopes

The closed native preflight records a12280922112-byte Direct pool (11.4375GiB),12201230336 available bytes before loading, and11289882112 planned bytes including the existing reserves. This leaves911348224 bytes in that snapshot. The selected reported buffer batch limit is2147483648 bytes. These are runtime observations/client limits, not a guarantee of future identical availability.

With the current537600-byte largest-role stride,1600MiB permits at most3119 active slots plus one physical plane; the2GiB reported batch limit permits3993. The current byte quota independently has only about16.48MiB over the successful normal peak. Increasing cache size therefore requires regenerating its typed geometry **and** byte quota, not editing one count.

Keeping the existing512MiB Direct reserve,256MiB platform margin and the builder's separate24MiB weight-saving/alignment allowance yields a **3424-slot planning point** within the independently verified resident-Q8 saving. The captured preflight alone prices3665 slots; the per-bank batch geometry prices3993. These constraints must be intersected. The larger values are not native allocation or inference qualifications, and the old2GiB allocation fixture did not execute indexed model-bank arithmetic.

The exact current planner and accepted-history semantics complete host replay at all six sizes, validating ownership maps. These are summed misses over the two captured installed-prompt requests:

| Slots | Fixed1536 history misses | Reduction from3072 |
| ---: | ---: | ---: |
|3072 |5732 |0 |
|3328 |5466 |4.64% |
|3424 |5383 |6.09% |
|3584 |5251 |8.39% |
|3665 |5183 |9.58% |
|3993 |4468 |22.05% |

The larger replay does not establish native tok/s or qualify larger buffers. It identifies a concrete software ceiling and a useful first candidate3424 while retaining the existing physical reserves. No additional allocation-to-failure experiment was needed to distinguish1600MiB from the already demonstrated2GiB allocation point.

## Earlier I/O refusal and the2% adoption cutoff

Current-miss676-key placement completes the previously unavailable full comparison in12840. Retained requests reduce physical calls5281 ->4694, saving587 (11.12%); physical bytes fall9371648 (about0.31%). Whole-request reductions are **1.5186% forward and1.9317% reverse**. Cold reductions are1.7418% /1.1676%. All full-row/route/token/byte controls remain exact.

This is positive observed timing, not "no effect". The former fixed2% cutoff would reject it. The cutoff is a chosen screen, not a measured speed limit. There are only two candidate retained requests, and adaptive margin state/OS pressure changes during this diagnostic cohort; a separate stable-policy paired variance assessment and normal/API/display qualification are still needed for adoption. No result is promoted solely by lowering a threshold.

## Earlier GPU rejection and checkpoint timing

Case12900 preserves all original checks, shapes, shader bytes and288 graphs. It separately measures graph computation plus GGML backend synchronization, then the original frontend completion checkpoint. The latter includes `DeviceWaitIdle`, queue/worker/epoch/owner checks and a durable journal checkpoint (`native/app/driver_lifecycle.cpp::finish_boundary`). It accounts for **99.082%** of summed measured isolated wall time. Both components remain executed before any resource retirement.

Scalar GDN128 backend/synchronize results, with positive percentages indicating reduced time:

| Tokens | Snapshots | Forward | Reverse | Interpretation |
| ---: | ---: | ---: | ---: | --- |
|1 |1 |+6.745% |+4.771% |Decode-shaped backend improvement |
|1 |2 |+2.324% |+7.257% |Decode-shaped backend improvement |
|32 |1 |-2.522% |-3.351% |Prefill-shaped regression |
|32 |2 |-2.003% |-1.104% |Prefill-shaped regression |

F64 maximum error remains1.71012346298e-8; complete snapshots and canaries pass. The unconditional four-column variant remains unsuitable because prefill regresses, but the earlier blanket GPU "no qualifying benefit" statement cannot exclude a decode-only specialization. These are CPU wall components including backend synchronization, **not pure GPU timestamps or model-speed gains**. The concrete reopening point is `ggml_vk_op_get_pipeline` for `S_v128`, scalar gate and `src2->ne[2]==1`; retain original prefill selection. It requires a new complete model comparison before adoption. Do not remove candidate-required barriers or positive completion to improve a stopwatch.

Older ready/PLE/fused screens should only be reconsidered where the same common non-target checkpoint dominated their isolated timer. Additional synchronization intrinsically required by a candidate remains part of its real cost. Fully measured whole-model regressions, output failures and source-integrity errors are not invalidated by this timing audit.

## Which historical decisions are affected

The174-case scan identifies **22 kernel-policy interruption records** and **five checkpoint-byte-quota records**. These are record counts, not22 or27 unresolved techniques. Many early cache/context/prefix mechanisms were subsequently qualified and adopted.

| Family/cases | What actually prevented qualification | Current treatment |
| --- | --- | --- |
| Current-miss placement12640/12680 | Loading predicate at1148/1137 versus1154 | Fresh12840 completes; exact controls and positive sub2% timing observed |
| Gate/Up Q2_0 format12060/12080 | Same1154 predicate at1145/1122 | Reopen a new format-specific measured-margin comparison; no old speed/quality approval inferred |
| Early startup/load/context3700/3870/3910/3960/4110/4260/4340/4440/4460/4600/4860/4940/5100/5120/5300/5400/6480/8460 | Application phase predicates | Preserve original cases; reconcile later successful implementations before scheduling another test |
| Old full-title estimate3174 |6583 observed versus8159 estimated from a global interval | Superseded by phase-local startup and later qualified capacities; no obsolete BF1653/128 replay |
| Checkpoint5520/9460/9690/10660/10890 | Software byte quota/retained accounting |10890 has2489319424 requested live bytes versus2480332800 cap, although Direct1.432GB and Flexible423MiB pass their listed reserves. Later prefix/checkpoint adoption supersedes these failures |
| VM evidence12360 |Bounded context-observation storage after19 completed requests | Corrected12420 already completes; not a physical memory failure |
| GDN12720 |Guard-inclusive stopwatch and whole-shape requirement | Split-timing12900 exposes decode/prefill differences; unconditional variant remains unadopted |
| Fully executed losing or quality-failing11420/11720/11880 and host-negative policies |Actual output/performance results | Retain their distinct negative outcomes; memory-padding changes do not overturn them |

The source-preprocessed1154 predicate also corrects the older authored **1360** explanation for12060/12080: the206-page reserved value and256-page application value were alternatives selected by `max`, not additive. Actual deficits were144KiB /512KiB. Authored prose/JSON are corrected with an explicit note; original native records, hashes and published Git history remain intact.

## Concrete source and verification

- `native/app/limit_margin_probe.h::required` implements monotone application-padding selection, observed-minimum retention and per-phase counters. `tools/check_limit_margin_probe.cpp` directly checks unchanged inactive behavior, thresholds, transient price, phase order and statistics.
- `tools/build_limit_margin_probe.py` coherently recompiles16 actual application providers, preserving the exact installed Vulkan object `d49976ac...efe6fe`, driver archives and model encodings. Actual preprocessing of entry, source owner and system-memory provider confirms the same scoped predicate in all three. A separate typed policy authorizes this experiment; historical "unchanged margins" wording is not used to block the owner's new request.
- `tools/audit_limit_evidence.py` indexes existing case evidence and reconciles its saved index without repeating native operations. `tools/analyze_limit_audit.py` checks both new native terminals, numerical/ownership evidence and exact restoration before writing the sanitized numeric report.
- `tools/build_gdn_columns_fixture.py --split-timing` adds timing components to the isolated experimental fixture while retaining all checks. `tools/screen_cache_limit.py` prices the captured preflight and replays the frozen actual planner; it makes no native throughput claim.
- Important follow-up source sites are generated `system_memory.h::qualified_system_headroom`, `resident_phase_vm.h`, `model_cpu_budget.h`, `mapped_source.h`, `device_buffer_budget.h`, `tools/build_resident_cache3072.py` and `native/app/driver_lifecycle.cpp`. Repository defaults may differ from the selected generated source view; use bound compile/link receipts.

Driver source/profile remains PS5-Vulkan-Inference872cc126/cumulative-idle, native archiveb57fe26e, persistent caches disabled. Expert Q2, resident Q8, BF16 PLE convolution, F32 activation/KV and physical reserves remain unchanged. No OS counter write, reboot, forced signal, CI or agent was used. The experiment is completed and restored; zero-padding production admission, larger native caches and conditional GDN model speed are not claimed by this audit.
