# Q2 I/O reduction: native comparisons and production adoption

All four requested proposals have a final measured disposition. The combined
winner was exercised in the normal application on the physical PS5 in case
9400 and installed in case 9410. First independent API decode improves from
**1.143314 to 1.293876 tok/s (+13.16896%)**. The previous exact application
remains a verified rollback. There are no pending comparisons in this four-item
scope. See the [sanitized evidence](expert-q2-io-reduction-results-20261030.json)
and [current installation](../config/production-installation.json).

## Candidate decisions

| Proposal | Native comparison | Result | Decision |
| --- | --- | --- | --- |
| Merge adjacent Expert bundles | Prior ABBA 9340: 1.144370 -> 1.149977 tok/s | +0.48996%; 184 fewer decode calls over 21 transitions at equal bytes | Adopted; actual normal-app execution verified in 9400 |
| Add 84 Gate/Up/Down bundles to the original 336 | ABBA 9380: 1.147220 -> 1.168182 tok/s | +1.82721%; both candidates faster than both controls | Adopted |
| Protect recent two-touch Experts for 144 layer-access observations | ABBA 9380: 1.148488 -> 1.147274 tok/s | -0.10565%; both candidates slower than both controls | Tested and closed; production retains original probation, window 0 |
| Read four eligible demands concurrently | ABBA 9380: 1.147096 -> 1.292355 tok/s | +12.66318%; both candidates faster than both controls, actual peak four | Adopted |

These percentages come from separate comparisons and must not be added.
Adjacency is enabled in all 9380 arms; its isolated effect is already established
in [9340](expert-q2-io-distribution-20261030.md). The new normal test measures the
actual combination separately, retaining the original prefix and final-consumer
causal verification behavior.

## Conditions and attribution

The complete Qwen3.8-Flash-Next model uses Gate/Up Q2_K and fitted-scale Down
Q2_0 MSE. Other weights remain original BF16/F32, inputs and KV remain F32,
and all layers, Experts and top-10 routing remain. The cache remains 867 active
slots, 868 physical planes and 1,333,739,520 bytes.

Case 9380 runs one warmup and three independent ABBAs in one native launch:
`0,0,1,1,0,0,2,2,0,0,3,3,0`. Modes are adjacent control, extra placement,
temporal protection and four-demand reads. Each request starts with an empty
Expert cache and uses the same 30-token prompt, 22 generated tokens and 21
accepted decode transitions. No prefix reuse, speculation, HTTP or display
confounds these headless comparisons. All complete F32 rows, ordered routes
and emitted token IDs match exactly. All source/device owners retire positively;
ordinary close and exact previous-program/settings restoration pass.

The following are decode-only measurements; prefill and final EOS are excluded.
GB denotes decimal GB. Each row compares against its own adjacent-enabled control.

| Candidate | Read calls/token, control -> candidate | GB/token, control -> candidate | Producer source wait ms/token, control -> candidate |
| --- | --- | --- | --- |
| Extra 84 bundles | 722.429 -> 687.571 | 0.430369 -> 0.429643 | 668.16 -> 654.12 |
| Temporal 144 | 722.429 -> 725.571 | 0.430369 -> 0.429175 | 667.16 -> 668.39 |
| Four demands | 722.429 -> 725.524 | 0.430369 -> 0.430420 | 668.24 -> 577.36 |

Source wait is the producer's blocking interval, not the sum of overlapping
individual `pread` times. The four-demand candidate reduces producer waiting
despite slightly more calls: effective bytes per producer-wait second increase
from 0.644038 to 0.745493 GB/s. Mean individual call duration increases from
1.460892 to 1.678654 ms. This demonstrates useful overlap, without establishing
SSD hardware queue depth or maximum hardware bandwidth.

Temporal protection reduces whole-request misses from 12,717 to 12,701, but
whole-request calls increase from 35,026 to 35,101 and decode slows. Fewer misses
alone do not establish a useful cache policy. The finite result closes this
tested variant; no untested or pending label is retained.

The extra pack contains 84 static Expert keys selected from existing traces.
Its 129,368,064 bytes were built and hash-verified on the PS5 in case 9362,
including exact source and pack readback, read-only publication and positive
CPU retirement. The original model and 336-Expert pack remain intact. This is
partial placement of 420 Experts, not replacement or pruning of the model.

## Bounded concurrency implementation

The separate CPU component test 9367 uses 46 actual same-layer four-demand
groups, equal calls/bytes and native SHA checks. After warmup, the timed order
is `1,2,4,4,2,1`. Mean elapsed times for depths 1/2/4 are
945.164/654.620/528.229 ms. Four versus two improves component throughput
23.9274%; this number is not a model token rate. Actual depth four and positive
thread/buffer retirement pass.

The model integrates the same bounded pool with the existing 8 MiB scratch
partitioned into four disjoint 2 MiB leases. Three persistent workers plus the
producer execute at most four reads. The old pair worker remains owned and idle
during a four-demand batch. All original source-scheduling predicates remain:
eligible whole ranges, 16 KiB alignment, 1 GiB source regions, 4 MiB inset and
pairwise admission. Crossing, coalescible and unsupported ranges fall back to
the qualified pair/original reader. GPU uploads remain on the producer after
exact read completion and stable source identities. Workers perform no GPU calls.

Adjacent groups merge at most five physically contiguous bundles, bounded by
7,700,480 bytes in the original scratch. Extra placement has separate immutable
descriptor/hash admission. No source-cache capacity or memory floor is raised.

| Source | Relevant function or generated operation |
| --- | --- |
| [Bounded pool](../native/app/bounded_read_pool.h) | `BoundedReadPool::start/read/require_completed/stop_completed`; disjoint leases and positive retirement |
| [Reader/owner derivation](../tools/expert_q2_io_reduction.py) | `header_source` inserts `upload_Q2_four`; `owner_source` inserts `read_four` and separate extra-pack admission |
| [Cache derivation](../tools/expert_q2_io_reduction.py) | `cache_source` orders fills by physical bundle position and dispatches eligible four-demand groups |
| [Normal build](../tools/build_expert_q2_io_monitor.py) | `monitor_scope`, `normal_owner`, `main`; frozen selection 5, temporal window 0, actual per-request path counters |
| [Observer](../tools/observe_expert_q2_io_monitor.py) | Retains original stream, frame, owner and completion checks; requires all selected paths actually execute |
| [Model analysis](../tools/analyze_expert_q2_io_reduction.py) | `main`; complete closed ABBAs and every-candidate-versus-every-control selection |
| [Tested temporal policy](../native/app/expert_temporal_probation.h) | `TemporalProbationPolicy::observe`; 144 tested, 0 selected |
| [CPU component](../native/qwen_flash_next/expert_q2_read_depth.cpp) | Native equal-byte depth comparison and positive Direct-buffer retirement |

The generated four-demand reader passed host tests for both Q2 role sizes,
unaligned logical ranges, crossing/invalid fallback and disjoint completion at
depths 1/2/4. The exact tested reader SHA appears in the relink provenance.
Twelve existing resource/ownership/completion audit families pass unchanged.
Six current/previous optimized-control tests and eight original/historical
control tests pass manually, including missing-proof and wrong-owner rejection.
The historical mixed fixture is pinned to its original committed report rather
than the later report root replaced by successive production adoptions.

## Normal application and placement

Normal case 9400 has one warmup and two API requests, with one VideoOut owner.
Both actual 1920x1080 frames were viewed: token rate, current UTC time, CPU/GPU
information and Q2/BF16/F32 labels are legible, there are no chat controls, and
unavailable utilization counters remain `--`.

| Matched normal condition | Previous 9290 | Candidate 9400 |
| --- | --- | --- |
| First independent API decode | 1.143314 tok/s | **1.293876 tok/s** |
| First API TTFT | 17,548.174 ms | 13,921.305 ms |
| Exact-repeat decode | 1.106472 tok/s | 1.264045 tok/s |
| Exact-repeat TTFT | 63.117 ms | 62.080 ms |
| Two-request throughput including prefill, capture and restore | 0.773582 generated tok/s | 0.906237 generated tok/s (+17.1481%) |

Independent and retained-cache conditions are kept separate. The normal
comparison spans successive finite runs, whereas the three candidate ABBAs
are interleaved in one launch; no broad confidence interval is claimed.

Actual path counters for warmup/first API/final API are respectively:
adjacent calls saved 382/382/305, extra bundled Experts 466/466/418, and quad
batches 5,081/5,081/1,797, with a lifetime maximum of four reads in every row.
These counters include prefill/EOS and are not decode-only rates.

Ordinary same-width F32 error is zero. The final retained-prefix request
preserves the earlier unlike-width maximum difference 0.971474 with complete
finite-vocabulary/top1 and identical emitted-token checks; it is not claimed
bit-exact across widths. Earlier same-width and forced rejection case 9160
remains the qualification for that original causal path. The exact final-prefix
engine source is reused. The original Expert-Q2 quality result remains strict
format 6/9 and answer contents 9/9, with owner-accepted loss and no normalization.

Normal CPU heap peak is 486,604,800 bytes and device-ledger peak is 1,870,659,584,
unchanged from the previous normal app and within 512/1,792 MiB caps. Final
device live bytes are zero. All source/model/GPU owners retire, ordinary close
and exact previous-program/settings restoration pass before adoption.

Placement 9410 then installs SELF
`db542fa213d399ec6935dbcb60e156b152afcb33340618d6bc998a7cee5c4a5c`
(17,495,415 bytes). All **10 canonical/rollback programs and five settings**
pass native whole SHA256, stable identity and EOF checks. Previous SELF
`bb61e2af568ac5fba907fea8c14704413f5ea17452772d865aa097834170de00`,
probation-only, mixed, Q4, BF16 and original MOSS programs remain preserved.
Fresh idle is confirmed; the native title, gateway and model are inactive.
Placement launches no model. This finite binding is consumed; sustained service
is not qualified. No reboot, CI or automatic retry was used.

## Provenance and scope limits

Implementation commits are
`53f15ba` and `d156568a5bbf3b07c4abf641a883878864b873d5`. Actual native
build 9394 and SELF package 9396 retain exact entry/owner/reader/cache/engine
hashes in the JSON report. The qualified existing driver is reused unchanged:
PS5-Vulkan-Inference `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, linked archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled.

Headless 9380 retains an old descriptive `maximum_parallel_source_reads=2`
field; its own sealed experiment scope declares four and both candidate rows
actually execute 5,465 quad batches with observed peak four. Normal 9400 fixes
the descriptive field. Two-lane occupancy events are disabled in quad arms;
the earlier two-lane occupancy percentage is not reused for the new pool.

An earlier CPU component attempt 9365 returned a known ShellCore-lock admission
refusal, retired its CPU owners and made no GPU calls. The later CPU-only
9367 predicate admits that exact unchanged ShellCore SLOCK, matching an existing
qualified CPU test; GPU/memory/identity guards remain. Superseded host-only
builds were never launched. No consumed native case was replayed.

The older eight-family plan retains its historical tested losers and actual
output-Q8 ENOSPC outcome. This report closes the new four-item scope and does
not relabel that unavailable historical experiment as successful.
