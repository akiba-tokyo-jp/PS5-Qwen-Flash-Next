# Expert-only Q4 actual-model comparison

This records the completed isolated model screen. Subsequent normal-application
qualification and verified production adoption are in
[the final report](expert-q4-adoption-20261029.md).

The completed PS5 run uses all Experts, Q4_0 Expert weights, unchanged non-Expert
BF16/F32 tensors, F32 activation inputs and F32 KV. The original BF16 application
and five settings were restored after positive resource retirement and ordinary
OS close. This report does not declare normal-application production adoption.

| Request (0 is warmup) | Decode tok/s | TTFT seconds | Whole-request physical GB | Counting passed |
| --- | --- | --- | --- | --- |
| 0 | 0.864200 | 23.174 | 44.920 | True |
| 1 | 0.871094 | 21.191 | 44.920 | True |
| 2 | 0.871914 | 21.204 | 44.920 | True |

Pooled timed decode: Q4 **0.871504 tok/s**, original BF16 **0.419813 tok/s**,
ratio **2.0759x**. Each rate counts accepted decode transitions and excludes
prefill. I/O counters include the entire request and must not be labeled decode-only.
All counting answers passed: **True**. Full same-Q4 F32/route comparisons and
positive retirement passed. This is a finite counting result, not broad reasoning
qualification or BF16/Q4 logit equivalence.

The cache budget remains 1,333,739,520 bytes: 134 BF16 slots versus 481 Q4 slots.
The BF16 controls use six-demand padded delivery; Q4 uses contiguous compressed
delivery. These are serial runs of the same original model with different Expert
precision and cache representations. A finite candidate gain/quality screen passed:
**True**. Normal passive monitor/API qualification remains separate.
