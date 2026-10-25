# BF16 system candidate validation

> Historical partial checkpoint. Its later one-worker demand and GPU delivery comparisons subsequently completed and were rejected. The [finite memory-plan completion](memory-plan-completion-20261026.md) supersedes the pending/refused status below; the [plan index](plan-index.md) separates broader unimplemented research.

Historical checkpoint: the [2026-10-26 follow-up](kernel-memory-cause-20261026.md)
records measured readback consumption, recovered CPU-fixture admission, the
completed one-worker comparison and subsequent prelaunch refusals. GPU palette
delivery and a new full-model comparison remain unqualified.

Status: **partial validation, blocked by measured kernel headroom**. The complete
requested candidate validation and production adoption are not finished.
No new full-model generation speed or production optimization is claimed.
The [allowlisted evidence](bf16-system-validation-20261025.json) distinguishes
an implemented prototype, a completed native comparison, a positive refusal,
and a pending test. The preceding [research report](bf16-system-optimization-research-20261025.md)
records the design and pinned external sources.

## Implemented and measured

The experimental exact palette format stores original sign/mantissa bits,
seven common exponents, three code bitmaps per 64 values, indexed uncommon
exponents, and explicit bounds. There is no quantization or target-router
change. `native/app/bf16_palette.h` implements encoding, complete prevalidation
and CPU reconstruction. `native/qwen_flash_next/bf16_palette_decode.comp`
implements a separate Vulkan integer reconstruction kernel.

The host controls cover all 65,536 BF16 patterns, maximum-sized matrices,
output canaries, malformed headers/prefixes, truncated input and alias refusal:
249 checks passed. All 27 retained original matrices also encoded and restored
with exact original SHA256. Their actual unaligned encoded sizes are
73.142–73.547% of original; aligned read envelopes are larger.

The shader passed GLSL compilation and Vulkan 1.2 SPIR-V validation. Its actual
pure integer functions were mechanically extracted and compiled for the host;
their reconstructed bits matched all BF16 patterns, small tile/dispatch-tail
sizes, and all 27 complete original matrices. This checks shader arithmetic,
not PS5 execution, memory visibility, fences or native GPU speed.

The new CPU path completed one PS5 cohort: nine original matrices, two modes,
six rotated rounds, **108 complete exact matrix deliveries**. Every read
returned; complete sample-pack integrity/EOF and every original SHA256 passed.
The 8 MiB Direct window was positively unmapped/released. Fresh CPU state,
the held reservation and the canonical production SELF were verified.

| PS5 case 2280 | Original raw | Palette + CPU reconstruction |
| --- | ---: | ---: |
| Median read | 4.478 ms | 3.448 ms |
| Median reconstruction | 0 | 5.493 ms |
| Median complete delivery | 4.478 ms | 8.995 ms |
| Median paired-round throughput ratio | 1.000x | **0.488x** |

The CPU implementation is rejected. Read savings do not repay restoration.
Medians need not add to the median total; paired ratios use complete round
totals. These are matrix-delivery measurements, not new tokens/s.

## One-worker demand scheduling

`native/app/demand_source_batch.h` adds one persistent I/O worker plus the
caller, matching production thread count. Both take the next actual request
without a pair barrier. It owns a bounded copy of at most 40 requests, rejects
overlapping destinations, permits at most two active reads and retains backing
after uncertain completion. Fifty-one host controls passed, including refill
while another read is pending, full-bound batches and joining after a known
short read.

Separate CPU fixtures compare pair waves and continuous known-demand lanes
using identical original matrices and padded destination strides. They do not
launch a title or GPU. The first 20 MiB comparison, case 2285, and a distinct
10 MiB comparison, case 2288, both returned before allocation:

| Case | Destination allocation requested | Observed kernel free pages | Required before allocation | Work started |
| --- | ---: | ---: | ---: | --- |
| 2285 | 20 MiB | 2,008 / 2,008 | 2,434 | None |
| 2288 | 10 MiB | 1,761 / 1,761 | 1,794 | None |

Required pages equal the original minimum plus `max(reserved, 256)` plus the
proposed allocation pages. Neither floor nor concurrency was relaxed. Both
records contain a positive failed terminal, zero allocation/payload-read/worker
start, released backing, and no retry. They are preserved consumed cases;
neither is unknown completion or a speed result. The success parser correctly
refused to admit them as benchmarks. A separate strict refusal parser records
their completed zero-work disposition. Five focused evidence tests passed.

The prior two-worker fixture's approximately 4% signal remains an earlier
observation; the new production-thread-count queue has no native speed result.

## Actual blocker and remaining candidates

An allocation-free, same-owner kernel metadata observation after both refusals
reported 1,767 free pages of 16 KiB: **27.609 MiB**. The actual native startup
target is 2,974 pages, **46.469 MiB**. The qualified full prelaunch gate requires
10,142 pages, **158.469 MiB**, including its unchanged extra allowance.
Flexible availability was 8,554,283,008 bytes. That separate value is not usable
as kernel-page headroom. This is not an SSD-space finding.

The observation preceded the final canonical SELF readback. It is a point
observation, not admission for a future launch, and does not establish why
available kernel pages changed between cases. No claim about a leak, a specific
cache, or GPU failure follows from these values. No title or GPU was launched.

| Candidate | Implemented / checked | Remaining qualification |
| --- | --- | --- |
| Continuous demand refill | Bounded one-worker queue, host ownership tests, compiled native fixtures | An admitted native comparison, actual owned GPU-bank integration and same-model generation comparison |
| GPU lossless reconstruction | Exact codec, shader, host bit checks, SPIR-V, native CPU control | PS5 GPU readback/completion, complete read+reconstruct delivery win, storage/layout integration and full-model comparison |
| Ready-expert compute | Design and source/ownership review | New graph/slot ownership implementation and numerical/GPU timing checks; no speed evidence |
| Two-slot router forecast | Capacity and original F32 router review | Bounded actual hidden-state observation, accuracy/useful lead time, wasted-byte and foreground-latency measurement; no predictor or speculative reads enabled |
| Exact speculative verification | Accepted-path route-union analysis | Complete KV/recurrent/PLE checkpoint and commit/rollback implementation, memory admission, acceptance and full-model speed measurement |

For speculative verification, the existing host checkpoint variant needs at
least 118,038,528 recurrent/PLE bytes before KV/logits, exceeding the measured
83,820,544-byte CPU-budget slack. This rejects that host variant only. A device
checkpoint is separate, unimplemented work; the post-load device ledger's
numeric budget alone is not proof of physical UMA/kernel admission.

Further native work requires a distinct case with fresh unchanged kernel,
startup, Flexible, source, owner and completion admission. Do not reuse a
consumed binding, lower a floor, deliberately pressure/reclaim memory, reset
services/GPU, or start a full model merely to obtain a timing sample. Host
success does not lift this physical admission failure.

## Production and reproducibility

The canonical fastest SELF remains
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`,
28,017,271 bytes, verified by a complete final readback. Its preserved rollback
was not substituted. Native owners, gateway and loaded models remain absent;
no uncertain completion exists in these cases.

These codec, queue and fixture sources are **experimental and not linked into
the qualified production application**. Original BF16/F32, F32 KV, every
expert/PLE, 512 MiB parts, 53 slots, 8 MiB production scratch, the pinned
`872cc1264ad8ba5d6b888b092968fa5858a38c58` cumulative-idle driver and disabled
persistent caches remain in place. There was no application relink, driver
rebuild, whole-model conversion/transfer or CI run. Native CPU fixture builds are
recorded separately from application builds and GPU qualification.

Manual host entry points are `tools/check_bf16_palette.py`,
`tools/check_demand_source_batch.py` and
`python -m unittest discover -s tests -p test_completion_delivery_result.py`.
The first two require `--workspace` and a fresh `--out` on the private data disk.
Native fixture contexts, source packs, SDK inputs, compiler/import receipts,
raw console evidence and executables remain private. There is no general
console-launch command in the repository. Preserve native source bytes using
the matching `.gitattributes` rules.
