# Critical review of execution efficiency

## Assessment

The original plan did not minimize elapsed time to a correct physical PS5 result.
It serialized a preventable full source read, left the dominant transfer duration
weakly characterized, and allowed status/continuation plumbing to cause additional
interventions. Its forward status also became stale. Those are planning and
execution defects; the number of completed host checks does not offset them.

The immediate proposal to replace the data path also needed review: removing work
does not improve the remaining schedule if migration and validation take longer
than the work removed. Do not equate fewer reads with a proven earlier finish.

## Evidence at this review

The exact audit, data-waiter and full-plan process identities were freshly verified
alive from the host process view. There were no physical execution intents, data
batch or first-generation case. The complete content audit has passed, while the
final model receipt and physical full-model inference remain pending.

| Evidence | Observation | Scheduling meaning |
| --- | --- | --- |
| Converted containers | 76 files, 359,246,956,672 bytes | The remaining workload is substantial data movement. |
| Positive final hashes | 17 files, 157,875,714,144 bytes | 43.95% of bytes, rather than 22.37% suggested by file count. |
| Remaining hash bytes | 201,371,242,528 | No conversion or content replay is needed for these files. |
| Recent hash throughput | 38.43 MiB/s across eight completed files | About 83 minutes remain if sustained. |
| Previous transfer sample | 16 MiB at about 11.50 MiB/s | About 8.3 hours for all containers if sustained; full-model transfer speed is unmeasured. |
| Native SHA timing | Synthetic CPU-only timing | The approximately 34-minute compute projection excludes actual filesystem I/O. |
| Native candidate | Link, real imports, SELF roundtrip and linked shaders passed | Rebuilding the unchanged candidate does not shorten data readiness. |
| Full model on PS5 | Not yet loaded or generated | Memory admission, whole-graph operation and usable token rate are still unknown. |

The hash estimate uses completed-file durations in the existing progress log,
not cumulative process read counters that also include the earlier content audit.
These estimates must not be added into a promised completion time: actual transfer,
native storage reads, model load and generation have different uncertainty.

## Findings and decisions

| Priority | Inefficiency or gap | Decision for the current run |
| --- | --- | --- |
| High | Pre-transfer SHA and transfer-stream SHA reread the same source bytes. | Record the design defect, but finish the active pass. A streaming-first replacement is not yet implemented, validated or shown to beat its roughly 83-minute remaining window. |
| High | Bulk transfer is likely longer than the remaining host work, yet the estimate rests on a small sample. | Use the existing transfer's byte/time progress to measure sustained throughput. Do not add a separate probe or parallel writers. |
| High | A status-file sharing failure previously ended waiting controllers before physical work. | Reuse the bounded local read/publication fix already tested. Keep worker identity, observation availability and physical completion separate. |
| High | The active document still described completed conversion and content auditing as future work and named superseded waiters. | Update the single forward queue to current phases and identities. Keep old results as evidence, outside the work queue. |
| Medium | Repeated broad builds, component trials or restoration cycles could consume time without resolving an active blocker. | Reuse the sealed candidate and qualified component results; perform one ordered model/demo session and its required final restoration. Add a targeted diagnostic only for a concrete failure. |
| High | Full-model feasibility and throughput remain unmeasured despite extensive host progress. | Make the first correct physical smoke result the next runtime milestone, ahead of display/performance evaluation. Never describe host success as model readiness or usable speed. |
| Medium | Progress emphasized counts and activity rather than the critical path. | Report the active phase, positive bytes, elapsed/rate evidence, blocking dependency and next physical action. Use byte-weighted progress for unequal splits. |

Independent native destination hashing, fresh memory/ownership/session checks,
positive GPU completion and exact original restoration serve distinct purposes.
Removing them would change correctness or physical safety. Fresh CPU guards and
small metadata checks are not the observed multi-hour bottleneck.

## Why the immediate streaming switch is not selected

The current transfer plan requires the final receipt digest. The directory owner
marker binds that receipt; the directory controller builder, admission helpers,
transfer validator and physical-case preparer require the same completed chain.
An unknown-digest streaming path therefore needs an explicit new admission and
provenance design across these components. Placeholder hashes, weaker existing
schemas or bypassed native receipt gates are not valid shortcuts.

The potential saving now is only the remaining hash duration. This review has no
evidence that implementing and checking that change would take less time. Keep
the running jobs and their source bindings unchanged. A streaming-first design
belongs before a future preparation starts, unless a later concrete failure
requires rebuilding this path anyway. It is not an extra current deliverable.

## Feasibility limits that the schedule must expose

The 359 GB file set is not resident PS5 memory. The runtime plans about 8.76 GB of
resident weights plus bounded expert, context, workspace and other allowances,
with a total budget of 12,110,548,480 bytes. This has not passed fresh physical
full-model admission. The 512 MiB expert cache cannot make all original expert
weights resident; storage reads and cache misses may dominate generation.

Strata-style admission and Maya-style caching are implemented mechanisms, not
evidence that this model will fit or produce an impressive tokens/s result. The
existing physical session must record actual source I/O, cache behavior, memory,
TTFT and decode rate. Do not start an optimization campaign before that result.
The three short fixed requests establish bounded functionality, not general
model quality or unrestricted production use.

## Changes made by this review

The active execution plan now records completed work, the remaining critical path,
reuse requirements and the decision against a mid-run transport redesign. No
worker was stopped or restarted; no frozen implementation was changed; no PS5
request was made for this review. All physical completion requirements remain
unfinished and remain part of the overall objective.
