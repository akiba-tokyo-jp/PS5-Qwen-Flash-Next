# Cold and different-input request validation

All five finite decisions and selected normal/different-input/timestamp
qualification are now complete. See [measured results](cold-request-results-20261030.md)
and [full counters](cold-request-results-20261030.json). The progress entries
below are historical; placement has its own exact adoption receipt.

The selected control is placement10820: shared/output Q8, routed Expert Q2,
1381 active cache slots, 64 MiB workspace and the unchanged 872cc126
`cumulative-idle` driver. Persistent caches and CI stay disabled. No reboot is
available. This is a new campaign; the completed memory/delivery/graph campaign
and its failed variants remain closed.

| Candidate | First decision | Native comparison |
| --- | --- | --- |
| Prefill32 | Price the complete 192-demand CPU bookkeeping and existing workspace; screen chunk reuse | Compare first response and total request time against prefill16 |
| Layer cache allocation | Reproduce native1381 misses, then screen causal layer quotas on fixed routes | Run only a useful policy; disclose cache-aware routing/quality changes |
| Indexed replacement | Match every control victim and miss on retained native traces | Compare unchanged routing/cache decisions with less CPU management |
| Continuous four-lane demand reads | Measure actual barrier-induced idle intervals | Test only a structurally different immediate-refill path; do not rerun unchanged completion-delivery losers |
| Deadline-aware forecast | Join current route forecasts with miss/residency and demand deadlines | Test only useful timely predictions within the existing total cache budget |

Measure queue delay, syscall-inclusive read latency, policy/source CPU work and
GPU intervals separately. Read wall time includes filesystem/kernel/device
work; do not claim raw SSD service time without kernel/device evidence. Do not
add overlapping intervals. Extend existing bounded diagnostics rather than
introducing per-read file logs or hot-path allocation. Preserve source identity,
memory reserves, destination ownership and positive GPU/read completion.

Reuse closed traces and checks. A frozen-route result is a screen, not a speed
or quality result. Native candidates preserve the immediate installed control
and settings, use a new finite binding, and normally close and restore. Compare
different inputs with complete-prefix reuse disabled; distinguish application
cache-empty from hardware/OS-cache cold. Use a small reversed-order screen
before expanding a winning comparison. Primary endpoints are request time and
TTFT; disclose decode regressions, added bytes and memory. Keep all failed
results. No candidate is adopted from a read-count improvement alone.

## Initial closed-trace screens

Current1381 case10760 reproduces5439 hits/4878 misses for its independent
request and5921 hits/461 misses for its retained request. Past-only repeat
weighted layer floors increase misses to5304/499 (linear weights) and5146/508
(square-root weights). Both specific quota variants are closed without native
execution; this does not establish that every nonuniform allocation is worse.

The indexed window0 probation prototype reproduces every chosen slot and miss
on actual997 and1381 traces, followed by synthetic retained cycles crossing the
4096-observation aging boundary. Host mean replay time over the six-request1381
sequence is298.953 ms for the control and28.802 ms for indexed replacement.
This measures CPU bookkeeping on the host, not native generation throughput.
Native build10860 fails before console use because an early include loads two
different base policy headers. Corrected build10862 places the indexed header
after the selected native base; the failed build remains preserved.

## Native progress

Control diagnostic10850 and indexed10870 each complete all three requests,
positive owner retirement, ordinary close and exact installed-control/settings
restoration. The independent plan cost falls65.192 ->10.294 ms. Request time
falls15075.218 ->15004.991 ms and retained time5362.076 ->5306.533 ms. Source
bytes, calls, ordered routes and output tokens remain identical. These are
sequential cohorts; adoption and a combined comparison are still pending.

At10850, source-call P50 is in1.408--1.536 ms, P95 in2.048--2.176 ms and P99 in
2.432--2.560 ms. Histograms have128 us resolution. Four-job tail-idle capacity
is5.327% of the existing quad batches, not5.327% of whole request time. Only7440
of13895 reads use those fixed four-job batches. Cross-projection known-demand
streaming therefore targets lane coverage as well as barrier refill. The new
pool/source fixtures verify exact mixed-size payloads,1--4 Experts, producer
callbacks,8 MiB canaries, bounded concurrency, failed callbacks/reads and EOF
refusal before I/O. No additional scratch or GPU buffers are used.

Prefill32 case10890 completes warmup but refuses the next checkpoint: the
software device ledger needs8986624 additional bytes. The original failure's
conservative GPU uncertainty is retained until successful ordinary OS close;
the exact fastest/settings restoration completes. Changed case10930 tightens
workspace reservation and capacity enforcement64 ->48 MiB with every total,
physical, kernel and CPU limit unchanged. It completes all three requests,
positive owner retirement and ordinary close/restoration. Measured workspace
capacity remains8388608 bytes. Independent request time is13695.504 ms, TTFT
6499.168 ms and decode3.054111 tok/s; retained decode4.804408 tok/s. Initial
source traffic falls7.705364 ->6.829934 GB and reads13895 ->12196. Same-policy
F32 error is0; final unlike-cache/width maximum3.935983 is disclosed with exact
counting tokens. Different-input quality and combined adoption are pending.
