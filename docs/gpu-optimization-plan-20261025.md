# Original-precision GPU optimization qualification

The owner authorized sequential implementation, physical validation and adoption
of beneficial candidates after the PS5LM source investigation. The completed
512 MiB result remains the control: BF16 weights, F32 KV, 53 expert slots,
prefill four, 256-token context and the existing finite output bound.

Keep driver revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile
`cumulative-idle`, the native archive and disabled persistent caches unchanged.
Do not run CI, rewrite model data, increase budgets or weaken completion guards.

| Order | Candidate | Qualification and adoption condition |
| --- | --- | --- |
| 0 | Completed decode/source/upload counters | Separate prefill and decode; establish the actual mapped/staging copy branch. |
| 1 | Existing BF16 indexed-vector shader | Narrow decode-only shape/layout predicate; original-shape numerical fixture before full model; completed matched throughput comparison. |
| 2 | Source window scheduling | Exact-byte CPU trace replay of 2 x 4 MiB versus 4 x 2 MiB within the existing 8 MiB; use only qualified file-region pairs. |
| 3 | Known-miss overlap / owned mapped-bank writes | First establish the copy mode; retain slot/descriptor leases, padding bounds and positive GPU retirement. |
| 4 | Indexed-vector kernel tuning | Only if the admitted path is useful; real 2560 x 640 / 640 x 2560 shapes, top ten, wave32 and unchanged precision. |
| 5 | Attention / complete prefix state | Assess against actual context and memory fit. Warm-prefill gains are separate from decode. |

Use fresh one-attempt cases and preserved control artifacts. A kernel improvement
does not qualify whole-model speed. A candidate must complete numerical output,
source/GPU retirement, normal close, exact original restoration, fresh original
numerical admission, ordinary shutdown and final idle/full-readback checks.
Unknown completion retains backing and is never retried automatically.

Promote only after a completed comparison supports an improvement without a
material regression or reduced numerical safety. Small gains require repeated
completed samples. Keep an unproven or slower candidate disabled and document
its measured disposition. Production adoption requires its own exact artifact,
configuration and ordinary lifecycle; temporary qualification is not deployment.

Quantization and reduced KV precision remain outside this original-precision
implementation sequence. A second console or a PS5LM Flash-Next installation
is unnecessary: future A/B comparisons use this console sequentially.

The owner subsequently explicitly authorized code changes, manual builds, PS5
validation and adoption. CI remains disabled. Before another GPU comparison,
qualify a byte-identical Direct frame writer: the first vector case completed
one external answer but its second request refused the unchanged kernel-page
reserve. This intermediate result does not qualify the vector path for adoption.

The isolated CPU AB/BA comparison completed four new 8,294,454-byte BMP files.
Every full SHA256 matched, all native operations returned, the Direct allocation
was positively released, and fresh idle CPU/session guards passed. Ordinary
writes reduced kernel free pages by 508 in both samples; Direct writes reduced
them by four in both samples. A subsequent independent Direct hash restored the
starting count in each case. This supports avoiding buffered frame evidence;
it does not establish the sole cause of the loaded-model refusal or a decode
speedup. Keep monitoring, raster bytes, deadlines and all reserves unchanged.

The actual completed vector decode interval contained 21 processes and 3,024
BF16 indexed-vector calls. Source wait accounted for 84.12% of process time;
all 94.54 GB of recorded uploads used the mapped-coherent branch, with zero
staging bytes. These are accumulated logical transfers over 21 decode steps,
not resident GPU memory. The first answer's 0.34861 tokens/s alone is insufficient
for adoption because the complete case failed its second request.

The separate CPU trace replay of two 4 MiB reads versus four 2 MiB reads used
the same 8 MiB window and exact selected expert bytes. Six rotated rounds gave
median throughput 0.9593 versus 0.9691 GB/s. The approximately 1.03% difference
is inconclusive: the paired mean time-saving interval includes zero. Do not
integrate four-read production scheduling or claim whole-model speedup from it.

## Candidate dispositions after sequential qualification

* P0: completed source/consumer/upload-route measurements. Current uploads use
  coherent mappings; there is no staging-copy workload to eliminate.
* P1: repeated full-model comparisons support the narrow indexed-vector route.
  The final same-SELF matched pair gained 1.36188% in mean decode. It is now
  selected in the final artifact/profile after the complete ordinary lifecycle.
* P2: the two-versus-four-read CPU screen is inconclusive. Do not widen
  concurrency or replace the qualified selected file/range schedule.
* P3, non-temporal copy: completed same-SELF full comparison was 3.55552%
  slower, with exact routing and source bytes. Reject and keep disabled.
* P3, owned direct-bank I/O: mapping/Direct read and all 360 padded-layout GPU
  references passed with complete restoration. The actual cache/source path is
  implemented behind an exact private policy. Both full same-SELF arms passed:
  mean +12.1829%, cold +12.1447%, warm +12.2204%, identical outputs/token IDs,
  routes and physical bytes. It is selected in the qualified profile.
* P4: specialization is conditional on an identified kernel bottleneck.
  The present fixture wall times include queue/checkpoint overhead and do not
  measure individual node GPU costs inside the model graph. Source wait remains
  dominant. Keep the already-measured vector dispatch, and defer additional
  workgroup/shader specialization until a completed post-streaming profile
  demonstrates a material kernel target. This is a documented applicability
  decision, not an implemented or measured shader speedup.
* P5: Flash Attention is already enabled; a complete recurrent prefix checkpoint
  does not fit the admitted spare memory. Neither is a new decode optimization
  within these unchanged precision/context/budget limits.

Final acceptance covers both native frames, full inference and resource
retirement, ordinary close/restoration/fresh original numerical readmission,
final idle/full executable readback, explicit selection of beneficial routes,
and private GitHub source preservation/merge. A completed fixture alone never
completes this plan. General unattended service and broader-context/quality
qualification remain distinct from this finite optimization task.

All applicable implementation and physical qualification stages above passed.
Rejected/inapplicable candidates retain their explicit measured dispositions.
The final qualified profile, sanitized results and private source merge complete
the owner's adoption sequence; they do not automatically start another case.
