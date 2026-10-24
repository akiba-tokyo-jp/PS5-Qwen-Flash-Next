# Complete original-precision generation on one PS5

The implementation and physical validation plan completed on 2026-10-24. One
physical PS5 ran the complete pinned Qwen3.8-Flash-Next text model with original
BF16/F32 tensors, all experts and required PLE. Host work prepared and built the
application; model inference ran on the console. No quantization, expert pruning
or substitute PC/cloud inference was used.

## Measured requests

| Request | Output | Prompt / generated tokens | TTFT | Decode tokens/s | Total |
| --- | --- | ---: | ---: | ---: | ---: |
| Arithmetic smoke | `4` | 26 / 1 | 90.915 s | Unavailable: one token | 94.476 s |
| External API 1 | `1, 2, 3, 4, 5, 6, 7, 8` | 30 / 22 | 104.619 s | 0.284548 | 181.884 s |
| External API 2 | `1, 2, 3, 4, 5, 6, 7, 8` | 30 / 22 | 102.145 s | 0.288819 | 178.296 s |

Each request used one-token prompt microbatches and thinking disabled. Decode
rate uses the interval after the first output token; it excludes prompt prefill
and first-token latency. The independent observer matched every external token
event to its durable native record and reconstructed the UTF-8 answers. Exactly
two generation POSTs and one finish acknowledgement were sent, with no retries.
The model remained loaded across all three requests. The completed arithmetic
context was recreated for an empty expert cache before API request 1; API request
2 reused that cache. File pages and pipelines were not claimed cold.

## Actual runtime and monitor

The application uses Strata-style UMA capacity admission and Maya aged-frequency
expert eviction with recency ties, active-expert protection and feasible layer
floors in the real engine callback. Its 48-layer cache has 53 BF16 expert slots
(506.25 MiB). Cumulative counters after API 1 were 1,091 hits / 36,349 misses and
357,325,209,600 uploaded expert bytes. After API 2 they were 2,261 / 60,139 and
591,190,425,600 bytes. These are backend upload counters, not SSD bandwidth or
proof of a comparative policy speedup. Accepted page-advice bytes remained zero.

The model's 76 containers total 359,246,956,672 bytes. Its complete native hash
proof was reused only through the matching same-boot sealed-identity admission.
No conversion, transfer or whole-model hash scan was repeated for this session.
Protected source keys add zero resident file pages; an owned 8 MiB Direct heap
window performs bounded reads. The session reported 604,409,906,688 source-read
bytes over 185,553 chunks. CPU matrix fallback and protected-pointer dereferences
remained disabled. CPU heap peak was 436,273,152 bytes (416.0625 MiB), inside the
unchanged 512 MiB total CPU budget, with zero untracked libc fallbacks.
Post-load device buffers peaked at 945,815,552 bytes and returned to zero.

Both actual 1920x1080 native scanout-source frames were saved after matching
positive VideoOut flips and visually inspected. Their passive layout showed
CPU/GPU identity, synchronized UTC, completed state, generated-token count,
TTFT, elapsed time and approximately 0.28 / 0.29 tokens/s. CPU/GPU utilization
was unavailable and correctly shown as `--`. Displayed GPU memory usage/budget
are raw driver estimates; the pinned driver duplicates usage into counters that
are summed on this APU. They are diagnostic and must not be interpreted as
physical available memory. Allocation admission used the separately qualified
native Direct allocator and unchanged CPU/Flexible/kernel/platform margins.
Frames are private device evidence and are not committed.

## Completion and restoration

All required gates passed, in this order:

1. Frozen source/package/session admission, one ordinary candidate launch,
   complete model load and arithmetic answer.
2. Two completed external requests with measured token streams, passive assets,
   advancing clock and actual native frames.
3. Positive finish acknowledgement, stopped API listener, completed source I/O,
   positive GPU completion/retirement and model-resource release.
4. Ordinary candidate close and exact original SELF restoration.
5. Independent original numerical readmission, ordinary original shutdown,
   fresh idle CPU guards and complete original SELF readback.
6. Saved actual-frame review, final same-boot/service guards and another full
   original SELF readback. Both case and parent recorded full-plan completion;
   the exact parent process ended and its stderr was empty.

No native owner, gateway or loaded model remains. No force-kill, GPU reset or
reboot was used in this successful session. The earlier freeze and refusals
remain preserved as separate historical results. The task retains its console
reservation. Committed execution/release controls and GitHub Actions remain off.

## Reproducible provenance and limits

| Component | Exact identity |
| --- | --- |
| Tested application source | `701f474cb8ca94dae5c854f080f3ec972d0d0c26` |
| Tested SELF SHA256 | `cb775555fd7423738cc6ef53efa760362c8b1c384ef2574b5b5797295bccbb3b` |
| Driver source revision | `872cc1264ad8ba5d6b888b092968fa5858a38c58` |
| Driver profile | `cumulative-idle` |
| Relinked native archive SHA256 | `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925` |
| Persistent shader/pipeline caches | Disabled |
| Original model revision | `de4b8e4d43b917e7706784d8bb445c9af86a3540` |
| Pinned llama.cpp revision | `0a1ef309cdbb9f2024f58a38fb4c42352c5db569` |
| Complete model receipt SHA256 | `d2a0705e0e8d8d5999cf2e6bd9519ccb0654837abcf1ab47d0295030a8bb5495` |
| Scheduler scratch / metadata bound | 167,772,160 / 158,936,784 bytes |
| Restored original SELF SHA256 | `2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d` |

The native link, actual runtime-module imports, six SELF segment roundtrips and
focused accounting/API failure controls passed before this candidate launch.
The seven engine overlays and selected driver archive were unchanged by the
final application accounting/API fix. The subsequent documentation commit does
not change the tested executable. See the accompanying sanitized JSON for
unrounded measurements.

This completes the accepted finite implementation/validation plan. It qualifies
three short original-precision requests and their lifecycle. Broad answer
quality, thinking-mode performance, long context, sustained service, utilization
telemetry and a Strata/Maya comparative speedup remain unqualified. The measured
0.28–0.29 tokens/s and roughly 102–105-second external TTFT are the practical
performance of this session.
