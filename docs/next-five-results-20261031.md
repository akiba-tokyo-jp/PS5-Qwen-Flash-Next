# Five software optimization results

All five families were exercised. This is an approximate faster configuration: decode uses two active Experts and 108 large resident matrices use Q4_0. It does not preserve the original Top6/Q8 mathematical model. Expert Gate/Up remains Q2_K; Down remains Q2_0 MSE. Other resident matrices remain Q8_0, tiny PLE convolution remains BF16, and Attention KV/recurrent S remain F32.

## Native candidate evidence

| Family / candidate | Physical result | Decision |
| --- | --- | --- |
| 1. Top4 | Retained decode +7.76%, request time -9.48% | Superseded by faster Top2 |
| 1. Top2 | +25.83%, request time -24.01% | Select |
| 1. Adaptive2/4/6 | +13.24%, request time -8.97% | Superseded by fixed Top2 |
| 2. Up to32 speculation attempts | +0.39%; timed workload used only5 attempts under either cap | No demonstrated gain; keep6 |
| 2. Width4 / three recurrent slots | Backend aborted during context initialization; no completed requests | Current prototype execution unavailable; not a physical impossibility claim |
| 3. Relax layer cache floors | Exact replay of seven native traces increased misses | Negative host screen; no native speed claim |
| 3/4. Q4 plus3712 slots | Decode -1.51%, request time -13.03% within common Q4 | Select only its faster Top2 combination |
| 3/4. Q4 /3712 /Top2 | Top6 to Top2 within common Q4: +34.09%, request time -31.25%; sequential versus Q8/3072/Top2: +4.98%, request time -20.72% | Select |
| 4. Attention KV F16 |14 completed requests,8MiB saved; separate-run rate5.30–5.34 versus nearby F32 about5.42–5.46 | No demonstrated gain; keep F32 |
| 4. Recurrent S F16 | Fixed unsupported F16 SCALE zeroing; second physical initialization still aborted | Current prototype execution unavailable; keep F32 |
| 5. Early I/O refill with owned copy | Decode -0.26%, request time +0.14%; exact F32/routes/tokens | Do not select |
| 5.1444-key placement, all phases | Requests4440 to3007, time -1.98%, decode -0.91%; all F32 rows/routes/tokens exact | Refine scope; do not select all-phase mode |
| 5.1444 keys only during prefill, Q4/Top2 | Cold TTFT5207.735 to5062.331ms; cold time -2.16%; cold requests8467 to7364. Retained bytes/calls unchanged and rate -0.40% | Select only initial prefill; use original768-key placement for all decode and later requests |

Each complete native cohort contains14 requests: two warmups, interleaved cold/retained controls and candidates, and four fixed semantic tasks. All four tasks pass in every complete candidate cohort. This finite suite does not establish unchanged general reasoning quality or arbitrary-prompt speed. Cold/retained/prefix timings are never pooled. Sequential precision comparisons are explicitly different from matched ABBA routing comparisons.

Q4 saves1,038,090,240 bytes;640 additional Expert slots consume983,040,000 bytes. Active/physical planes become3712/3713, with5,703,659,520 bytes of Expert cache. The application ledger cap is6,199,160,832 bytes and single allocation cap2,147,483,648 bytes. CPU512MiB and workspace48MiB caps, physical reserves and OS watermarks remain unchanged.

## Source and memory corrections

The expanded pack is1,577,058,304 bytes and1024 triplets, sealed on the PS5 with whole-file SHA256 `98a25de242a9862ba5ae6572d1c2f1d2bff170def03685eb6a71b526399944e8`. Both single/group source guards now admit exactly this additional declared size while preserving identity, extent and reserve checks. Supplemental group offsets subtract their actual namespace origin rather than modulo512. Case27600 exercises3199 upper-half index hits; case28800 exercises1931 and zero during decode. All vocabulary F32 rows and routes remain exact in these placement comparisons.

Pending uploaded SELF file cache was a measured cause of low VM free pages. Retiring only the owned unpublished closed file cache recovered1206 pages (2934 to4140, about19.8MB) with identical file identity and positive descriptor/mapping retirement. Fresh uploads now perform this step before mandatory native whole-file integrity. It uses no GPU, OS-counter writes or reboot. The same operation on the model pack recovered zero pages; no general cache-recovery claim is made. Known obsolete closed files were removed only while protecting current and immediate rollback programs/settings and every referenced source.

The driver remains revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, cumulative-idle; effective archive SHA256 `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`. The qualified original GPU object `17cb982ec26903fcee469639592d5acd761acd6f883bc35135b9d665fc4b6ad2` is preserved. Persistent shader/pipeline caches remain disabled. No CI, learned host inference, reboot or forced reset was used.

## Implementation map

- `native/app/next_five_policy.h`, `native/app/next_five_routing.inc`, `native/app/next_five_causal.h`: finite routing/speculation policy interfaces and complete decisions.
- `tools/build_next_five_comparison.py`, `build_next_five_Q4_routing.py`, `build_next_five_Q4_cache.py`: actual linked routing, Q4 formats and memory geometry.
- `tools/build_next_five_placement_model.py`, `build_next_five_normal.py`: exact large-file bounds/offsets, prefill-only source selection and initial-request-only normal composition.
- `tools/self_upload_cache.py`, `build_closed_pack_cache_reclaim.py`: positive file-specific upload-cache retirement.
- `tools/prepare_next_five_normal.py`, `finalize_next_five.py`, `next_five_production.py`, `prepare_first_case.py`: exact fresh model/API/frame/close evidence and future selected-production admission.

The complete immutable attempt dispositions are in `next-five-worklog-20261031.json`; final selection, native normal timings and exact placement are in `next-five-adoption-20261031.json` and `config/production-installation.json`.

## Quality and completion behavior

The approximate Top2/Q4 model must retain its actual answers. In the first fully returned normal cohort29600, cold and retained counting passed, while exact-prefix repetition produced repeated7 and failed the counting task. The completed native computation is not a GPU error: all three requests return, both API streams match their own native token IDs/bytes, both real frames present, and all GPU/model/source resources positively retire to zero live ledger bytes. The final selected cohort below reports the same checks independently; it must not be described as unchanged quality.

The historical normal observer required a positive adjacent-merge counter even when the larger cache eliminated that demand. Cohort29600 reported zero adjacent merges,4 supplemental Expert hits in the retained request, and maximum4 concurrent reads. Its remaining, never-issued finish POST was sent once from a journaled continuation using the existing returned streams/frames; no inference was replayed. Future next-five observers preserve bounds and actual zero counters without forcing feature exercise in every short request.

The actual native screen was inspected and its old resident-Q8/Top6 footer corrected to mixed resident-Q4/Q8 and Top2 for the final selected SELF. Unknown CPU/GPU utilization remains marked unknown, with the real reported device identities, calibrated UTC time, token rate, TTFT and generated token count.

## Final selected normal cohort30200

| Condition | Previous19000 decode tok/s | Selected30200 decode tok/s | Selected total ms | Selected TTFT ms | Counting correct |
| --- | ---: | ---: | ---: | ---: | --- |
| cold_start | 4.377344 | 5.537146 | 10228.984 | 6282.451 | true |
| request_reset_weights_retained | 5.012038 | 6.538603 | 3945.386 | 563.971 | true |
| exact_prefix_repeat | 7.036085 | 7.872825 | 2937.320 | 61.090 | false |

These are sequential native cohorts, not a matched ABBA comparison. The same counting prompt uses30 prompt tokens and22 output tokens in each condition; the selected prefix-repeat answer is incorrect and is not correct-answer throughput. The independently measured candidate comparisons above provide separate evidence for routing, cache geometry and placement. General answer quality is not preserved.

Selected SELF SHA256 `5b829d396dbbf4f7b6d07b139917ee5d3740c44bbb245cf4542f24371d1e36cd`, source revision `76870d256094c93d083aa72a45b626e1b8b04975`, sealed model-receipt SHA256 `5f991ad0e335993fd2c0d2e97d1d8925e8e95adda013f2549ea923cefd679ec9`. Both actual final native frames show mixed resident Q4/Q8 and Top2. Native upper-half pack index hits are392, with zero during decode. Application device peak is6,167,724,032 bytes, below6,199,160,832. All device ledger bytes return to zero; model/source owners retire, ordinary OS close and exact prior-control restoration pass.

Production installation is pending the separately journaled30300 placement. It preserves the immediate c2e control and its five settings, verifies both complete programs and both setting sets with native SHA256/identity/EOF, and launches no additional GPU work.
