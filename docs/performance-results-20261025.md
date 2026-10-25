# Bounded performance implementation and physical results

All eight proposals were screened. Bounded prefill and compact completed-route
observation were implemented and physically qualified. The representative
512 MiB file comparison and subsequent complete-layout native qualification
also completed. The remaining variants did not pass
their current storage, delivery-cost or state-restoration prerequisites; they
are not represented as implemented. See the
[complete allowlisted measurements](performance-results-20261025.json).

The screen follows the current
[Strata design notes at 7dd5cf18](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/docs/DETAILS.md),
the existing [Maya application policy](expert-policy.md), and original-precision
offload/batching research. Each mechanism is checked against the actual PS5
storage, UMA, state and completion contracts; upstream benchmark rates are not
used as native BF16 performance evidence.

| Proposal | Disposition and measured evidence |
| --- | --- |
| Bounded prefill | Widths 2 and 4 implemented and independently qualified. Width 4 reduced mean external TTFT 35.30%; decode changed +2.17%, with significance unqualified. Width 8 requires 80 active slots and fails the unchanged 53-slot capacity. |
| Physical splitting | All 76 originals replaced in place by 711 parts, with every logical/physical SHA256 verified and host originals retained. Full native inference/frames/retirement/original numerical restoration passed. Mean decode improved 1.50%; TTFT fell 0.35% versus the compact-observer control. No complete second console copy. See the [complete layout result](native-split512-success-20261025.md). |
| Expert-centric packing | One expert is 9.375 MiB versus 8 MiB scratch. At least two reads plus an indexed gather/reorder path are needed. A complete second text-expert pack alone is 241.6 GB before reserve and cannot fit. Not implemented. |
| Cache admission/profile | Actual complete demand captured; exact linked C++ replay and an independent Python implementation agree. None of 11 compared settings saves expert payload versus current Maya LFU4096. LRU/SLRU add 3.32%; retain the current policy. |
| Shared prefix | A host checkpoint needs at least 118,038,528 recurrent/PLE bytes before attention/logits, versus 100,597,760 CPU bytes left at the baseline peak. Reject that host variant. A device checkpoint remains separate unimplemented copy/restore/lifetime work. |
| Route-ahead | Previous-route candidates miss the next target 57.01% / 68.91% of nonresident predictions at limits 1 / 10. Existing known-miss overlap remains; no new predictive reads. The two current aligned windows leave less than one matrix of scratch. |
| Lossless transport | Nine original BF16 matrices restore exactly. Plain/byte-plane zlib achieves about 1.25x / 1.39x, but host restoration takes 28.9 / 19.3 ms, missing the initial delivery-cost screen. This codec is not selected; native/other codec speeds are unqualified. |
| Model-free drafts | Prompt batching is qualified, while generated tokens remain single-token. The one-sequence context reserves zero recurrent rollback snapshots. Full attention/recurrent/PLE restore and target verification remain prerequisites; drafts are not implemented. |

## Actual route comparison

The native observer adds no GPU download. All 384 / 1,440 / 1,440 layer records
agree with the actual completed cache transfers. Cold and retained external
requests have 500 / 787 hits and 19,529 / 19,242 misses. Each expert payload is
9,830,400 bytes. These upload counters are not physical SSD traffic or bandwidth.

The current 4096-route decay and 3072/8192 alternatives tie on this short trace;
shorter tested intervals increase transfers. Even a future-informed optimistic
53-slot replay saves only **2.39%**
of external expert payload here. It is an upper bound, not an implementable policy.
The portable `tools/replay_expert_routes.py` requires all three admitted route/
result pairs and exact owner/run arguments, rejects counter mismatches, and
executes integer metadata processing only. Its CLI passed on the actual evidence.

## Compact observer and complete native lifecycle

The corrected candidate holds **267,648 bytes** of completed raw rows for the
fixed 8/30/30-call sequence. JSON is created and written only after positive
model/GPU/source-worker retirement. Existing token, performance and monitoring
records keep their timing. Actual GGML checks cover 21 cases, including three
retained batches, and actual PS5 compilation/link/import/SELF gates passed.
See the [observer contract](completed-expert-routes.md) and
[preserved refusal](completed-route-refusal-20261025.md).

Both native external outputs/token IDs and arithmetic match the one-token
control exactly. Observer-candidate TTFT is **57.759 / 56.781 s**;
decode is **0.339691 / 0.345981 tokens/s**.
This is a separate observation case, not an isolated additional speedup claim.
Its CPU heap peak remains **436,273,152 bytes** and post-load device peak remains
**945,815,552 bytes**. Memory pressure events and passive wait time are both zero.
All original reserves, budgets, stronger startup gates and 20s/60s bounds remain.

Both actual 1920x1080 passive frames were viewed. All three requests, source/GPU/
model retirement, ordinary candidate close, exact original restoration, fresh
original numerical admission, ordinary original shutdown and final idle CPU/
complete original executable readback passed. The finite parent ended with all
**439 inputs unchanged**. No native app, gateway or loaded model remains.

The selected driver remains `872cc1264ad8ba5d6b888b092968fa5858a38c58`, explicit
`cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
The compact candidate SELF is `363d8156845ed7930944aeecab6024537fdba80fb7ca1bce5fd56a3ebf335243`.
Original BF16/F32, all selected experts and required PLE are retained. Persistent
shader/pipeline caches, CI and general release/execution flags remain disabled.
These fixed thinking-disabled answers establish neither broad reasoning quality
nor sustained service or significance of the small decode change.
