# Five software optimization experiments

The owner authorized implementation, physical PS5 comparisons and adoption of
measured improvements on 2026-10-31. The control is the installed c2eafe1a SELF,
Expert Q2, resident Q8, 3072 active slots, 768 placement keys and native recurrent
rollback. CI and learned host inference remain disabled. No reboot is available.

## Finite experiment queue

1. Extend current cache-aware routing with lower and adaptive Expert counts.
   Compare Top-6 with Top-4, Top-2 and a score/cost-aware choice on the actual
   graph. Preserve original mixture probabilities and report quality separately
   from speed; approximate outputs are not rejected for F32 inequality alone.
2. Extend causal speculation beyond the six-attempt budget. Evaluate complete
   request time, accepted tokens per verification, rejected work and Expert bytes
   per committed token. Screen wider verification against the actual hybrid
   memory rollback implementation before attempting it on the console.
3. Reallocate memory and alter cache policy together. Reuse the completed negative
   3424-slot experiment; do not rerun an unchanged larger-cache configuration.
   Price bank geometry, actual live allocations and layer-wise retention.
4. Compare lower precision resident/state storage with the memory it makes
   available for Expert retention. Reuse the negative 108-matrix Q4 result and
   build only a materially changed combined candidate. Inspect Attention KV and
   recurrent-state storage independently; tiny PLE convolution remains BF16.
5. Improve the source/GPU handoff on its measured critical path. Screen queue
   refill, consume ordering and independent-operation batching. Any concurrency
   change must own all read buffers until returned reads and completed GPU use.

## Measurement and completion

Use one shared native comparison harness where independent runtime arms permit
it, with warm-up and interleaved controls. Separate cold, weights-retained and
prefix reuse. Record decode, TTFT, whole request, actual bytes/calls, cache events,
speculative decisions and complete finite output. Reuse existing trace evidence
for screening and preserve all negative/failed attempts. An execution refusal is
not a speed result or a physical impossibility claim.

Software capacities may be changed with explicit allocation accounting. Preserve
source identity, valid shapes, unique resource ownership, positive completion and
ordinary close. Do not remove required synchronization or reuse a consumed case.
Select faster candidates against measured control variation, then qualify their
combined normal/API/display behavior and production placement. Report every
candidate as measured/adopted, measured/no gain, or concretely execution unavailable.
