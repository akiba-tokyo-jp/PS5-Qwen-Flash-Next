# Measured GPU initialization and remaining model comparisons

Native case **3593** completed one empty Vulkan backend lifetime. Its maximum
sampled global free-page decline was **8 pages (128 KiB)**, from 2,778 to 2,770,
across 90,490,531 ns. The backend synchronized and retired; the global device
remained owned until normal exact-owner OS close. Exact fastest and all five
settings were restored with native whole SHA256, stable identity, EOF and a
fresh idle observation. There is no unknown completion. See the
[machine-readable evidence](gpu-phase-calibration-20261028.json).

This completes the empty-backend measurement. It does **not** complete C2/C3,
establish an 8-page full-model budget, qualify a speedup or adopt a production
executable. The prior 1,958-page global GPU/load interval also contained final
CPU setup, weight allocation/loading, context creation and OS variation. That
whole interval is not exclusive initialization cost or a physical minimum.

## Completed and preserved cases

| Case | Scope and terminal result | GPU backend lifetimes | Normal close and exact restoration |
| --- | --- | ---: | --- |
| 3555 | Complete CPU preflight, then selected 2,178-page initializer entry refused at about 1,961 pages | 0 | Passed |
| 3567 | Complete CPU preflight, then selected 1,666-page initializer entry refused at 1,658 pages | 0 | Passed |
| 3580 | Prepared but abandoned before application publication or launch; reservation returned | 0 | No application mutation |
| 3593 | Static SELF/shader/table resources qualified, then one empty backend synchronized and retired | 1 | Passed |

The final scope performs no unrelated 76-container preflight, source worker,
model load, tensor allocation, graph or inference. Completed source/worker/
geometry proofs are reused. The first application sample was 2,795 pages;
prelaunch observations were 7,309–7,310. These are global samples, not exclusive
ownership measurements or a guarantee about a future title's headroom.

## Admission components and phase observations

The ordinary formula remains kernel minimum 898 plus max(reserved 206, selected
ordinary extra 256), or **1,154 pages**. The selected initializer entry is
**1,410 pages**, or minimum 898 plus a total allowance of 512. This total
already includes the ordinary extra; it is not charged twice.

The component estimate uses complete prior 128-slot fixture 2840: positive
sampled active/wired movements 226 pages, plus Direct metadata 17 and idle 2,
giving 245. Ordinary extra 256 plus 245 fits inside the selected 512. This is a
sampled population proxy, not an attributed instantaneous maximum. The exact
prior report SHA256 is
`d596ba7c1c149b9b8819f095826063bf972f6ef2f612cad2a019641b05861411`.
Native full integrity and the independent 360-graph validator both preceded
the new initializer. Entry prepays its total allowance once. Later completed
boundaries retain the ordinary floor. Production admission defaults remain.

| Completed phase | Global free pages | CPU Direct heap bytes |
| --- | ---: | ---: |
| Before frontend | 2,778 | 16,777,216 |
| Frontend returned | 2,774 | 16,777,216 |
| Registry returned | 2,770 | 16,777,216 |
| Device query returned | 2,770 | 16,777,216 |
| Backend returned | 2,770 | 16,777,216 |
| Empty queue synchronized | 2,770 | 16,777,216 |
| Backend retired | 2,770 | 16,777,216 |

Flexible availability remained 437,256,192 bytes at these samples. No model
SourceReader existed. The production post-load ledger requires a completed
source window, so this source-free fixture does not enable or query that
model-only ledger. Frozen backend initialization creates fences/command pools
without entering tensor-buffer allocation or graph preallocation. No fake
source completion or production guard exception is used.

## Concrete source and verification

- `native/app/resident_gpu_calibration_policy.h`: exact typed v3 scope and
  prior-fixture components; 68 altered/missing controls rejected.
- `native/app/resident_gpu_calibration.inc`: early model-free entry, seven
  completed samples, positive synchronization and backend retirement.
- `tools/build_resident_comparison.py --GPU-initializer-calibration`: branch
  after verified static GPU resources. The ordinary model path stays intact.
  Chained factory reuse validates actual originally compiled source, recipe
  and object rather than recompiling unchanged code.
- `tools/staged_self_upload.py`: complete FTP transfer, then mandatory fresh
  native SHA256/identity/EOF while original SELF stays canonical. Removes a
  redundant raw HTTP SELF readback. Physically passed 3567/3593; no exclusive
  VM saving is established.
- `tools/resident_gpu_calibration_result.py`: exact owner, ordered completed
  boundaries, policy components, no model/source work, positive retirement,
  ordinary floor. It grants no model admission or speed qualification. Host
  controls reject incomplete, reordered, wrong-owner and below-floor reports.

Native build 3603 / package 3604 passed manual link/import audits, all 673
tables and 677 converted pointers, and all six SELF segment roundtrips.
Executed SELF:
`8c7bae2386007b8267328dcfebd34b42a16f9ea0cb762cd924736925ffb96815`.
Original BF16/F32 weights, F32 KV and required components remain intact.
There were no CI runs.

Driver: `akiba-tokyo-jp/PS5-Vulkan-Inference`, source
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
Selected compiler archive:
`67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9`.
Application-linked native allocator/platform archive:
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader and pipeline caches remain disabled.

## Remaining execution constraint

The next proposed capacity measurement would allocate up to five raw GPU
buffers totaling the original 8,755,105,280-byte resident weight payload,
without model data or graphs. Automatic approval review rejected the patch:
general validation authorization did not clearly approve this materially
greater memory-pressure/PS5-hang risk. The patch was **not applied** and no
such allocation was attempted. An explicit risk decision was requested; this
experiment remains pending that decision. This is an approval constraint,
not an observed physical allocation failure.

C2 matched predictive/speculative comparisons and forced rejection/full-F32
restore, and C3 cache53/128 plus prefix comparisons, remain unexecuted. Their
shared resident allocation/load/context budget is not established by an empty
initializer. Preserve the [16-family/22-item ledger](vm-revalidation-results-20261028.json),
completed numerical/regression evidence, consumed cases and exact production
restoration. No unchanged refused launch is replayed.
