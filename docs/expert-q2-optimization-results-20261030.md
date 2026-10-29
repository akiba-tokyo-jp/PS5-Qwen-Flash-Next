# Expert Q2 optimization comparisons

All eight proposed families have a terminal comparison or an observed execution
constraint. The qualified winners are installed in case 9310 after normal-app
case 9290. A component win is reported separately from production speed.

The control uses all routed Experts, Gate/Up Q2_K, fitted-scale Down Q2_0 MSE,
unchanged non-Expert BF16/F32, F32 inputs/KV, 867 active slots and
1,333,739,520 cache bytes. The original strict quality result remains 6/9 format
and 9/9 answer contents; the owner accepted expected Q2 loss. No normalization
was introduced. Driver revision is
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, linked
native archive SHA256
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches, CI and reboot remain disabled.

| Family | Actual comparison | Disposition |
| --- | --- | --- |
| Expert replacement | Case 8900: aged LFU 1.029182 to two-touch probation 1.127026 decode tok/s, +9.507%; exact full F32 and routes. Normal 8940 pooled 1.126230. | Already adopted, placement 8950. |
| Gate/Up/Down bundled reads | Case 9180 ABBA: 1.127256 to 1.143810 tok/s, +1.469%; exact F32/routes and miss count. Whole-request calls 38,532 to 35,339. | Adopted after normal composition 9290 and placement 9310. |
| Serialization / genuine overlap | Case 9040 composite parallelism: -0.0609%. Case 9250 actual-weight overlap: 36.388 ms unsplit, 59.367 ms split serial, 57.442 ms split overlap. | Tested losers for these implementations; retain unsplit scheduling. |
| Expert-sharing causal speculation | Case 9160 ABBA: 1.128018 to 1.143629 tok/s, +1.384%, one actual causal attempt accepted per candidate request. Forced rejection restores the ordinary continuation. | Adopted for the final exact-prefix consumer in 9290/9310. |
| Resident non-Expert compression | Original BF16 output to Q8 saves 595,968,000 payload bytes. Host format/reference checks pass; FTP and native file writes both return ENOSPC before the new asset completes. | Execution unavailable under the current filesystem allocation. No Q8 GPU, model quality or speed result; not adopted. |
| Intermediate copies | Case 9080 exercises streaming copies at compressed sizes: 1.127649 to 1.121675 tok/s, -0.530%; same F32/routes/bytes. | Tested loser; original copy path retained. |
| Exact prefix/full-state reuse | Case 9100: repeat TTFT 17,612.906 to 60.607 ms. Capture-charged two-request group throughput 0.583314 to 0.761875 tok/s, +30.611%. | Adopted for exact repeated prompts in 9290/9310. |
| CPU metadata | Case 9040 independent ABBA: atomic immutable-range hint 1.127225 to 1.129072 tok/s, +0.164%; both candidates exceed both controls, same data and routes. | Adopted in the normally qualified combination 9290/9310. |

## Measurement boundaries

Decode rates exclude prefill and final EOS. Do not add the independent percentage
gains. Case 9100 uses a warm retained cache within each two-request group; its
second-request decode rate is not directly comparable with an independently
emptied-cache production request. Prefix benefit is primarily TTFT and complete
group time, including capture cost.

The bundle pack contains 336 complete Expert triplets, seven per trunk layer,
using 517,472,256 extra bytes. Original source files remain fallback for every
other demand. The counting-only selection covers 12.684% of counting misses
and 4.596% of held-out quality misses; it does not prune Experts or use future
routes. All 49 stored layers, including the retained MTP layer, remain present.

Copy case 8990 had zero actual streaming copies because an old default-off
selector remained disabled. It was a setup result, superseded by the operative
9080 comparison. The latter is the terminal copy result. The unchanged
unstarted diagnostic 8880 is superseded by the original-policy arms of 8900.

## Genuine overlap result

Case 9250 reuses the sealed existing pack, ten actual quantized Expert triplets
from a fixed mixed-layer asset cohort. This is a scheduling component, not a
real routed token or a whole-model benchmark. Each timed arm reads the same
15,400,960 bytes in two requests and computes all ten contributions plus the
original left-fold reduction. Three warmups precede the symmetric six timed
arms: unsplit, split serial, split overlap, split overlap, split serial, unsplit.

Two independent 8 MiB CPU windows keep the I/O worker away from GPU banks. The
sole producer uploads a completed window and submits GPU work; source and
device owners stay live until positive completion. The two overlap arms show
5.789 and 6.042 ms of intersection between read and GPU-producer intervals.
These are CPU observations, without hardware timestamp queries. Every one of
28,160 F32 contribution/output values matches the serial control exactly;
canaries, all 21 graphs, source retirement and zero live device ledger pass.

Overlap improves throughput 3.352% relative to the already split control, but
loses 36.652% relative to the original unsplit control. Extra submissions and
split-graph overhead exceed the saved source wait. A full-model port of this
losing implementation is unnecessary. This does not establish that every
possible asynchronous streaming design must lose.

## Resident compression execution constraint

The isolated Q8 output GGUF needs 675,430,560 bytes plus its 777,928-byte
metadata. The original BF16 file remains intact. Full readback of the first
512 MiB upload passes, but the tail upload returns ENOSPC. A native CPU helper
then converts the required original BF16 tail locally, independently of FTP;
its normal `pwrite` also returns errno 28. Both CPU attempts positively retire
their Direct memory and never launch a title or GPU work.

A separate native `statfs` observation reports about 2.686 GB available. Thus
logical free-space reporting alone does not explain or prevent this allocation
failure. It is a current filesystem execution constraint, not proof of a GPU
memory limit, a physical hardware impossibility, or a negative Q8 speed result.
The host encoder matches all bytes of 6,144 original BF16 blocks to the pinned
reference, including the part seam.

The first CPU attempt refused a transient exact ShellCore `SLOCK` observation.
Its normally closed partial was wholly verified against the pinned Q8 prefix
before continuation. The changed CPU-only scope admits that lock-wait state
only for the exact ShellCore identity; all UID/start-time/tracer/memory checks
remain. The continuation establishes the actual ENOSPC failure. No GPU launch
guard was changed. Do not replay either consumed attempt.

The failed native partial was copied to host and wholly checked. Only the two
new unadopted Q8 staging files were retired, reclaiming 617,054,208 logical
bytes; absence was independently verified. Every original model, rollback and
the qualified Expert bundle remain. Q8 source publication and model execution
were never completed. Reconsider this candidate only after additional actual
allocation capacity is available for the complete asset and required transfers.

## Implementation locations

- `tools/expert_q2_reader_candidates.py::candidate_header` implements the
  atomic range hint and the separately rejected composite-pair alternative.
- `tools/expert_q2_bundle_reader.py::{reader_header,owner_source,cache_source}`
  adds the immutable one-read/three-consumer source. Native pack creation is
  `native/qwen_flash_next/expert_q2_bundle_pack.cpp`.
- `native/app/expert_q2_speculative.h::ExpertQ2SpeculativeEngine` uses only
  committed past tokens and completed Expert-route observations. The forced
  rejection diagnostic never supplies a causal speed-arm proposal.
- `tools/build_expert_q2_prefix_comparison.py::entry_source` qualifies complete
  F32 KV, recurrent state, positions, logits and application state.
- `native/app/expert_q2_ready_graph.h` and
  `native/app/expert_q2_overlap_fixture.cpp` isolate the tested Q2 split graph
  from the unchanged original BF16 ready-graph guard.
- `tools/build_expert_q2_copy_comparison.py` explicitly enables the tested
  copy candidate while preserving mapping visibility, ownership and `sfence`.
- `tools/prepare_resident_output_q8.py`, `resident_output_q8_quantize.c` and
  `build_resident_output_q8_tail.py` retain the isolated, unadopted Q8 work.
  The original receipt/source/budget classes remain unchanged.
- `tools/build_expert_q2_optimized_monitor.py` composes the measured winners.
  `FinalPrefixHandoff` permits snapshot replacement only after the final exact
  prefix restore, with the same rounded capacity and actual allocator caps.
  The normal app must qualify and be verified in production before adoption
  can be claimed.

Ordinary same-width full F32 and route checks remain exact. The final composed
width-two request has an explicit separate full-vocabulary finite/top1 and
same-token requirement; unlike-width bit equality is not a valid prerequisite.
Same-width speculative equality and forced rejection were qualified in 9160.
All console cases above use ordinary close and exact control restoration;
none leaves an unknown GPU completion or running title.


## Normal qualification and verified production placement

Case 9290 completes one warmup and both actual passive/API requests. The first
independently emptied-cache request measures **1.143314 decode tok/s**, 1.494%
above the faster old normal-control request (1.126481). Its complete F32 rows
and ordered routes match exactly. Prefix capture is included in its 36.861 s
complete request time.

The exact repeated prompt measures **1.106472 decode tok/s**, **63.117 ms TTFT**
and 20.017 s complete time. Its cache is retained, so it is not pooled with the
independent-cache rate. Both 22-token requests together give 0.773582 generated
tokens/s including prefill, capture, restore and verification: 32.618% above the
matched ordinary two-request control from 9100. Independent percentage wins
were not added. Relative to the earlier prefix-only repeated-cache cohort,
the final decode rate is higher; the original prefix-only TTFT was about 61 ms.

The final causal attempt is accepted once and supplies one bonus. Every emitted
token/byte and all full-vocabulary top1 decisions match the ordinary reference.
The maximum unlike-width F32 logit difference is 0.971474; it is disclosed,
not relabeled as bit equality. Native same-width equality and forced rejection
remain qualified in 9160. Actual bundle and atomic-hint counters are positive
in all three requests. CPU heap peaks at 486,604,800 bytes and the device ledger
at 1,870,659,584, below unchanged 512 MiB / 1792 MiB caps.

Both actual native frames were viewed: 1.14 and 1.11 tokens/s, correct Q2/BF16/F32
labels, synchronized UTC date/time, CPU/GPU information and no chat controls.
Unavailable utilization counters remain dashes. Full model/source/device
retirement, ordinary close and exact old-control restoration pass.

Placement 9310 installs SELF
`bb61e2af568ac5fba907fea8c14704413f5ea17452772d865aa097834170de00`.
All 9 canonical/rollback programs and 5 settings pass native whole SHA256,
identity and EOF verification. A fresh idle observation confirms no native
title, gateway or model remains active. Original MOSS, BF16, Q4, mixed and
probation-only rollbacks are preserved. The finite run binding is consumed;
sustained service and unattended relaunch are not qualified by this test.

Implementation commit: `af15450f61cbcc77d60f00a5295209dd06f07e5f`.
Exact native ELF, entry, source-owner, engine, reader and cache digests are in
the adjacent JSON report. All eight current proposals have a final disposition;
Q8 model execution is classified unavailable, rather than falsely reported as
tested or left as an unimplemented speed claim.
