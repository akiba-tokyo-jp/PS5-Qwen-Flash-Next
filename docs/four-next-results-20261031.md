# Four optimization comparisons

All four requested candidates have actual native dispositions. Adopt the
768-key placement and complete speculative capture elision with native
one-token recurrent rollback. Do not select the tested two-token convolution
fusion or Q2 Gate/Up fusion prototype. The model, Expert Q2/resident Q8/BF16 PLE
precision,3072/3073 cache geometry and original single-token GPU object remain.
The [adoption record](four-next-adoption-20261031.json) binds final qualification
and placement separately from the matched candidate measurements.

| Candidate | Actual comparison | Disposition |
| --- | --- | --- |
| Placement676 ->768 keys; supplemental256 ->348 | Native17300,14 requests. Retained decode4.981678 ->5.050946 tok/s,+1.390%. Both temporal directions improve beyond the measured control spread. | Adopt |
| Two-token convolution/SiLU/QK RMS-scale fusion | Native17400 checks216 full-state F64 graphs, then17700 completes14 model requests. Retained5.280618 ->5.317423 tok/s,+0.697%, below A/A spread and not faster in both temporal directions. | Tested, not selected |
| Native recurrent rollback instead of pre-verification complete captures | Native17600,14 requests. Retained5.245591 ->5.416584 tok/s,+3.260%;35 captures elided and15 actual forced rejection rollbacks. | Adopt |
| Q2 Gate/Up matmul+SwiGLU prototype | Native17800,108 graphs. One-token backend+sync124.127 ->157.389 us; two-token149.320 ->297.062 us. All F64 outputs/canaries pass. | Tested, not selected:26.80%/98.94% longer |

## Placement and I/O scope

`tools/screen_four_next_placement.py` replays the actual installed planner,
reproduces native hits/misses exactly and checks held-out semantic traces.
`tools/build_four_next_placement_model.py` compares original256 versus348
active supplemental entries in the same immutable348-triplet file. The common
physical file reorders existing entries; this is not an unchanged-old-file
comparison. The complete535953408-byte file fits512MiB and passed native
whole SHA256, identity, EOF and positive source retirement.

Retained physical reads fall4684 ->4388,296 fewer calls per complete
30-input/22-output request. Bytes fall2968256768 ->2962276608, about6MB,
so the main result is fewer requests, not a large reduction in useful payload.
These totals are not decode GB/token. Cold whole-request differences have
opposite temporal signs; the adoption evidence is the reproducible retained
decode and whole-time improvement. Cache capacity remains3072 slots; the
additional placement coverage consumes no new Expert cache slots.

## Recurrent rollback and memory

`tools/build_four_next_rollback.py` selects `n_rs_seq=1` in
`streaming_context_params`. The candidate path in `next_with_one_draft`
elides complete pre-verification capture and uses the pinned
`llama_memory_seq_rm(memory,0,position+1,-1)` on rejection. This rewinds the
attention, convolution, PLE and GDN modules to the committed pending token;
the already computed complete first F32 logit row supplies the continuation.
Normal selects it with `qwen_app_compact_rollback_select(true)`.

Both matched comparison arms price an additional124MiB application GPU-ledger
allowance for the extra recurrent state. The postload cap is5216120832 bytes;
the measured comparison peak is5186256896. This is not total console memory
and does not reduce physical Direct/Flexible reserves or the OS minimum.
Eliding explicit snapshots does not eliminate recurrent state storage.
All compared counting F32 bytes/routes/tokens remain exact and four fixed
semantic tasks pass, including later continuations after15 forced rejects.

## Nonselected GPU prototypes

`native/app/gdn_conv_norm_two.comp` and `tools/build_four_next_two_model.py`
exercise both one/two-token paths and preserve unsupported three-token fallback,
pre-allocation dependencies and full external-input ranges. Native17700 has
actual candidate selections, finite full-vocabulary rows, equal counting
tokens and four passing tasks; maximum compared logit error is0.0073594451.
Its small throughput estimate is within measured control variation. This is
a completed negative adoption decision, not an untested item.

`native/app/expert_gate_up_q2.comp`, `expert_gate_up_backend.inc` and
`expert_gate_up_fixture.h` use actual encoded Q2 weights and F32 accumulation.
The fixture uses three physical Expert samples, repeated across six selected
IDs, with boundary planes and canaries. The maximum F64 error is approximately
5.10e-12. The immutable additional-shader registry remains capacity1: the
isolated fixture admits only Gate/Up and suppresses the unused GDN registration.
No registry expansion enters normal. Timings include backend dispatch and
synchronization; no whole-model gain is claimed and the slower prototype does
not justify another full-model run.

## Final consumer and preserved evidence

`tools/build_four_next_normal.py` composes the winners. Its native consumer
requires zero explicit speculative captures/restores and reconciles elided
attempts and all-memory rewinds with the actual controller. It retains the
original final-prefix certificate, complete routes, finite vocabulary,
counting tokens/bytes, physical bounds and positive completion. The final
`tools/refresh_four_next_normal.py` rebuilds only this entry provider; the
GPU/cache/owner/engine and budget providers remain byte-identical.

Host preparation18000 did not launch. Normal18200 stopped at a completed load
boundary with1146 free kernel pages versus its1154-page predicate and was
ordinarily closed/restored. Ancillary18600 tested206-page application loading
padding while preserving898-page OS minimum and206-page OS reservation. Its
minimum during loading was2110, so it did not establish admission below the old
boundary. It generated all three22-token outputs, then stopped on the obsolete
native capture-count predicate; resources were retained until ordinary close.
The final normal restores original256-page loading padding and corrects the
consumer predicate, with no operation retry, reboot, forced reset or CI.

All immutable failed/native/host evidence is retained. Individual matched
percentages are not added to predict joint normal speed. Three identical
normal prompts and four fixed semantic tasks do not establish arbitrary-prompt
quality, indefinite availability or sustained reboot-free service.
