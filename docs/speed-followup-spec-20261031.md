# Speed follow-up specification

## Baseline and decision rules

The reference is installed SELF `3066dfe45c32d0586e3bdddb9e9ab31b200b3185a20aa0206e2418f326b2002f`, normal case12220, resident-Q8 receipt `8b67b85e6cb2f3fd910e900b0299c3325d8717814f0ffab9ef505cab1dfc686b`. Expert precision remains Q2_K Gate/Up and Q2_0 Down; PLE convolution remains BF16. Keep3072 active slots,3073 physical planes, all original memory reserves, four read workers, ownership and positive GPU completion. Use driver872cc126/cumulative-idle/archiveb57fe26e; persistent caches stay disabled. No CI, reboot, forced termination or repeated consumed launch.

The ordinary weights-retained request measures4.177872 decode tok/s,2.234619s TTFT and7.486257s whole request. Exact-prefix/causal reuse measures6.300317 tok/s and3.871905s whole request. Compare like reuse conditions. Accepted decode comprises21 transitions; physical request totals also contain prefill and EOS. Never treat summed overlapping pread wall as elapsed SSD wait or the process residual as pure GPU time.

Each candidate ends as **adopted**, **tested without sufficient benefit**, **host-rejected before native execution**, or **execution unavailable under the measured current policy**. The last state is not physical impossibility. A fixed-trace replay is a selection screen, not native speed or quality evidence. Do not leave failed candidates labelled untested. Native adoption needs complete ownership/retirement, correct finite outputs, unchanged reserves, a successful normal/API/display qualification, exact restoration and verified production placement. Pure byte-cache changes require exact full-vocabulary F32 and ordered routes; cache-policy changes require finite full-vocabulary output and task-content validation because cache-aware routing can change. Require at least2% lower whole-request time in both comparison orders, or a consistently improved targeted tail without material ordinary-request regression; disclose finite sample scope. No adoption from decode alone when prefill regresses.

## S1: bounded protection of previous decode Experts

Target `IndexedProbationPolicy::victim/observe` in `native/app/indexed_probation_policy.h` and the actual native cache provider frozen by12200. Retain a bounded most-recent set of keys used in the previous accepted decode. During the next prefill prefer eligible victims outside that set. Never protect future trace keys, the current selected set remains ineligible, and original per-layer floors remain. Fall back to the original eligible victim when all eligible keys are protected. No additional weight bank or allocation limit increase.

Screen protection caps0/512/1024/1536 using the frozen planner and captured ordered demands. Attribute misses to prefill, accepted decode and EOS; compare their sum. Reconcile cap0 exactly with native counters and validate bidirectional ownership after every request. Exercise the4096-observation aging boundary. Only a net-positive screen proceeds to an independently measured native policy comparison. A screen loss closes this candidate without a redundant native run.

## S2: identity-bound owned BF16 row cache

Targets `ResidentMappedSourceReader::upload_small_rows` in `native/app/resident_small_rows.inc`, its actual `resident-mapped-source.private.h` provider, and the CPU BF16 get-rows bridge from `tools/build_resident_small_rows.py`. Store exact completed row bytes in owned bounded storage; never retain scratch pointers. Key by source generation/identity, file, offset and byte length, including PLE n-gram-derived offsets. Keep320-byte PLE rows separate from5120-byte embedding rows. Do not quantize PLE convolution or preload the102.4GB mapped table.

Reserve and account for storage explicitly; initial design512KiB payload, no enlarged512MiB libc heap or physical/device limits. Retained cache lifetime ends before source/model release. Preserve source identity and headroom checks on hits, original scratch lease completion on misses, logical row accounting and CPU BF16 conversion. Consume hits before an insertion can replace their storage. Track hits/misses, physical calls/bytes and storage high water. Host verification covers byte exactness, source/key isolation, eviction, duplicate rows, reset and stale pointer independence. Native comparison uses four different fixed inputs in A/B/B/A order with fixed phase-start cache state, full F32/route/output checks and separate cold/retained timings. A consistently slower or non-material result is rejected rather than enabled.

## S3: avoid an unproductive final speculative attempt

Targets `native/app/causal_expert_sharing.h::next` and the actual normal entry's bounded causal policy. Compare attempt caps8 and6 on the same22-output-token request and reuse conditions. The existing width2 reject/restore/ordinary fallback remains mandatory; never infer ordinary EOS from a rejected speculative row. No changed sampling, token limit or EOS semantics. Bound scope to the existing finite demonstration until additional input coverage exists. Compare final-token-to-finish tail, whole request, accepted decode, attempted/accepted/rejected proposals, F32 finiteness and final output. Use fresh case identifiers. Restore the exact selected SELF after each run. If the target attempt is not reached or the total gain is insignificant, close without adoption.

## S4: measure the selected delivery path

Target `native/app/streaming_read_pool.h::worker/run`, not the legacy two-lane occupancy class or quad-only wrapper. Add bounded cumulative queue-to-start, syscall, ready-to-consumer and consumer durations, and elapsed occupancy at0..4 active reads. Use token-boundary snapshots for prefill/accepted decode/EOS physical calls/bytes. Keep error draining, positive completion and10s deadlines. Timers and aggregates must not write files from read workers. Verify short-read/exception handling and exact request accounting on the host. Separate read-call wall from wall-clock intervals and CPU producer/consumer time.

Use the existing optional Vulkan timestamp diagnostic only if a remaining GPU question requires it; its extra scheduling fences cannot be compared as ordinary inference speed. Keep monitoring and durability checks. Correct stale867-slot/reset labels in newly generated experimental records from actual selected settings, preserving all original raw evidence.

## Execution order

1. Freeze source/SELF/model/driver identities; confirm the current title is inactive.
2. Implement and run S1 replay and S2/S4 focused CPU checks. Reject negative screens immediately.
3. Build only the surviving composed native row-cache/telemetry comparison with exact actual source overrides. Run one bounded native comparison if admitted by unchanged current memory policy. Do not retry an identical refused profile; record measured available/required pages and normally close/restore.
4. Run S3's minimal normal comparison if the unchanged current profile is admitted. Qualify the composed winner through normal/API/display before production placement.
5. Record every disposition and actual evidence, verify selected production/rollback identities and idle state, commit the specification, implementation and results. Do not publish private console data or build/model artifacts.

## Finite evidence capacity and confirmation amendment

Initial case12360 completed19 requests, then returned `Bounded context reuse observations exhausted`: its inherited96-entry VM observation array did not cover24 requests. This is a harness-capacity defect, not a memory-floor refusal or a console hang. Ordinary OS close and exact3066 restoration completed; pre-close whole-owner retirement remains conservatively unknown. Preserve that failed terminal and every completed request separately; do not replay the case or label the entire cohort complete.

Bind VM evidence capacity to `5 * maximum_requests + 8`, in addition to bounded route arrays and checked accesses. A16-request sequence needs at most81 observed samples and reserves88 entries. Qualify alignment of owned BF16 row payloads explicitly; the confirmation uses16-byte-aligned storage,525344 total bytes and491520 payload bytes. Unsupported row sizes retain the original uncached path.

The preserved first A/B/C/C sections avoid repeating that work. Complete the missing comparisons using B/C/B/A over four tasks,16 requests, with all original physical/kernel/heap limits. This establishes a reverse row-cache comparison and both-order protection comparisons. Treat the first model execution's pipeline warming as a timing limitation. The four-input fixed-route screen predicts a small protection loss, whereas actual cache-aware inference changes demands and shows a preliminary gain; native full-row/route/output checks decide adoption. The native evidence must override neither the screen's assumptions nor the unchanged safety policy.

Completed12420 shows that the protection aggregate also changes JSON output from24 to18 tokens. Do not qualify equal-work throughput from that aggregate. Evaluate equal-output tasks separately and the existing fixed identical-prompt normal application directly. The normal program accepts only its compiled bounded demonstration prompt; a benefit there does not enable protection for arbitrary future prompts. Row-cache standalone reverse gain is1.495%, below the initial2% standalone target, with exact full-row SHA256/routes/tokens/bytes and684 fewer physical calls. It remains a component of a composed normal candidate; claim a composed gain only after normal qualification, without inventing an independent2% row-cache result.
