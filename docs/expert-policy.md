# Strata and Maya application integration

This application code is connected to the pinned engine's real expert-cache
planner and copy callback. Full-model PS5 execution remains unverified. The
selected shared-driver source is updated for native integration; console work
remains disabled.

## Pinned sources and adaptations

| Source | Principle used here | Application adaptation |
| --- | --- | --- |
| [Strata UMA cache](https://github.com/Niko1221/Strata/blob/011c9e600a93bbc9fd451c563501b5831c32bbca/include/strata/core/uma_cache.hpp) | A GPU cache on UMA consumes system RAM; size against both driver and OS observations after a reserve. | `uma_cache_budget` clamps even an explicit budget. Unknown observations reject admission. |
| [Strata expert cache](https://github.com/Niko1221/Strata/blob/011c9e600a93bbc9fd451c563501b5831c32bbca/src/core/expert_cache.cpp) | Bound residency and distribute cache capacity across layers. | A soft layer floor applies only after reserving room for the complete active set. |
| [Maya fast path](https://github.com/mw00/project-maya/blob/451f9cb6a21ea65673bdde2e57b4a670ae2b8859/src/core/glm_fast_path.cu) and [route replay](https://github.com/mw00/project-maya/blob/451f9cb6a21ea65673bdde2e57b4a670ae2b8859/tools/glm_tier_replay.py) | Aged usage frequency with recency breaking eviction ties; halve counts every 4096 routes. | Learn from actual unique selected IDs in each cache callback, without a saved usage profile or speculative route. |

Maya also has a recency policy, including a single-conversation default at this
revision. This application explicitly selects its aged-frequency alternative.
The route count is per cache group here. No CUDA code, quantized formats, CPU
lane, multi-GPU ownership, drafting or speculative expert pruning is imported.
The portable implementation and PS5 adaptations are application code. Original
source licenses are preserved under `third_party/notices`; pinned revisions and
file digests are in `native/qwen_flash_next/expert-policy-sources.json`.

## Runtime path

1. `native_main.cpp` requires patched engine symbols and selects
   `LLAMA_APP_EXPERT_POLICY=maya-aged-lfu` before backend initialization. A separate
   loader patch disables eager model mmap prefetch.
2. After model admission, it observes driver free memory and OS free page
   counters. Expert-cache size is `min(512 MiB, driver_free, os_free - 256 MiB
   reserve)`, saturating subtraction at zero. Missing counters or less than
   128 MiB reject context admission. These initial limits await qualification;
   other context allocations, mapped pages and PLE are not bounded by this formula.
3. The existing `llama-moe-cache.cpp` callback synchronizes before reading actual
   selected IDs. The policy observes unique IDs, ages frequency counts and evicts
   the coldest eligible resident, with oldest access breaking ties. All currently
   selected experts remain pinned through fills, including newly admitted ones.
4. Empty slots are used first. When feasible, other layers keep at least
   `floor((slots - active_unique_experts) / cached_layers)` residents. The current
   layer may replace its unselected residents. Small caches may have a zero floor;
   the policy never sacrifices a selected expert to promise a layer quota.
5. A PS5-specific adaptation issues page-aligned `MADV_WILLNEED` hints before
   uploading actual misses, with a 64 MiB rounded budget per callback. Unsupported
   or rejected advice leaves exact on-demand reads intact. These are hints for
   known misses, not predictions of a future layer.
6. The upstream callback uploads original tensor bytes to existing device banks,
   preserving copy ordering and slot-map synchronization. Tensor types, top-k
   choices, routing weights and required PLE remain unchanged. The app uses
   one-token microbatches.

The storage path is SSD-backed mapped weights, the OS page cache and bounded
device expert banks. CPU/GPU share physical RAM. OS caching is not a separately
bounded application RAM tier. This does not prove a sustained RSS limit or
efficient read/compute overlap.

## Counters and monitor

The patched callback counts unique expert hits, fills, uploaded expert bytes and
OS-accepted page-advice bytes. The model adapter reads these atomic process totals
on the engine owner after completed operations. HTTP threads read a copied
snapshot. Advice may include repeated hints and page rounding. Uploads count
expert data submitted to backend copies, excluding slot maps; they do not measure
SSD traffic, GPU throughput or saved time. Demos report no real cache counters.

The read-only monitor shows these counters alongside CPU/GPU identity, current
date/time, TTFT and generation tokens/s. Use measured cold/warm console runs
after application runtime admission to assess benefit.

## Manual evidence

```powershell
python tools/check_expert_policy.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
```

This verifies the upstream archive and applies the actual loader/cache patches
to an isolated source copy with the tracked policy header. It extracts that
patched engine's slot planner for host replay: 8,200 routes with the new policy
and 8,200 with baseline SLRU. Checks cover all selected slots, eviction-map
consistency, duplicate IDs, bit-exact BF16 fixture copies, frequency aging,
recency ties, hot-expert retention, layer floors, oversized active sets, UMA
arithmetic and advice bounds. Both patched engine sources compile to PS5 objects.

These checks do not execute GGML kernels, actual SSD reads, model inference or a
PS5. App API-stub and HTTP checks separately cover telemetry forwarding and the
read-only monitor. `tools/build.py` installs the same header overlay and records
its digest for a future static engine build. The selected driver pin and native build are recorded in [driver-integration.md](driver-integration.md).
