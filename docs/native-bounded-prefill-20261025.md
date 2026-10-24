# Bounded two-token prefill on the physical PS5

The two-token candidate completed arithmetic `4` and both fixed external answers,
including exact baseline token IDs and output bytes. All actual frames,
positive retirement, ordinary close, exact original restoration, fresh original
numerical readmission, ordinary original shutdown and final idle CPU/full raw
readback passed. The finite continuation positively ended. This completes this
candidate; the [eight-proposal performance plan](performance-plan-20261025.md)
remains in progress.

| Metric | Previous one-token control | Two-token candidate |
| --- | --- | --- |
| External TTFT | 89.441 / 87.378 s | 70.901 / 69.452 s |
| Decode rate | 0.332877 / 0.337782 tokens/s | 0.336222 / 0.342238 tokens/s |
| CPU heap peak | 436,273,152 bytes | 436,273,152 bytes |

Mean TTFT fell **20.62%**. Mean decode changed **+1.16%**; two short requests do
not establish significance or sustained throughput improvement. Prompt batching
primarily improves input latency. See [allowlisted counters](native-bounded-prefill-20261025.json).

The explicit private profile accepts widths 1, 2 or 4; only width 2 has completed
physical qualification here. Generation stays single-token and greedy. Every
prompt output is requested to keep the final-layer expert cache eligible, with
unchanged causal positions. The actual cache method admits at most five tokens
at 53 slots/top-10; eight needs 80 slots and is rejected. No width is silently
substituted after failure. The actual complete graph must still fit the unchanged
160 MiB scheduler arena and all native allocation/retirement limits.

Original BF16/F32, all experts/PLE, 8 MiB scratch, eight descriptors, 512 MiB CPU
heap, actual 76-file rehearsal, both startup targets, all reserves/passive wait
bounds and pinned cumulative-idle driver remain unchanged. Persistent caches,
CI and general release/execution flags remain off. The SELF is
`ab5200d8db3fe120051b6832201f5e51ac4778c36b78eba6ad68038db7a4ca23`.

The collector initially supplied the lifecycle aggregate to the first performance
validator. Only the first terminal record owns `prefill_batch_tokens`. All native
requests and resource retirement had already completed. The failure was retained;
the ended parent and 425 unchanged frozen inputs were confirmed, then every
original validator was applied to the correct saved record before normal close.
No inference, finish POST or native launch was repeated. The permanent collector
repair also checks exact first-terminal/aggregate result agreement.

Focused checks cover actual cache eligibility, batch setup/causal positions,
partial final batches, generated-token isolation, invalid widths/budgets,
quarantine on setup/decode failures, actual PS5 ABI compilation, real imports,
SELF roundtrip and the actual lifecycle's ownership/cleanup exception paths.
The monitor and every validation guard stay enabled.
