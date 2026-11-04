# Strata and Maya application integration

**Scope:** the original cache-policy integration below preserves the arithmetic
of that original profile. Later selected profiles quantize weights and change
routing; they are not described by its unchanged-precision claim. See
[current architecture](architecture.md) and [selected status](project-status.md).
The dated source-reader observations remain historical evidence.

Current source-path status: the [complete physical session](native-full-generation-success-20261024.md)
passed arithmetic generation, two external counting requests and every final
restoration gate. The [replacement source reader](reserved-source-20261024.md)
uses inaccessible virtual keys and an 8 MiB bounded direct-read window; model
page-advice hints are disabled on that path. The original file-backed model mmap
attempt froze the console before this cache executed.
See [the investigation](freeze-forensics-20261024.md). The historical mapped-file
mechanism below is not a qualified native memory tier.

This application code is connected to the pinned engine's real expert-cache
planner and copy callback. The selected shared-driver source and real native
cache executed in the completed full-model session. General inference remains
rejected by committed policy outside the finite validation scope.

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
2. The qualified native path observes the canary-validated Direct allocator and
   separate CPU/Flexible/kernel scopes. Raw Vulkan estimates remain diagnostic.
   The original generic UMA clamp remains an additional cache limit; it cannot
   replace the native whole-model and post-load allocation guards. The actual
   48-layer cache has 53 BF16 expert slots (506.25 MiB), inside its 512 MiB cap.
3. The existing `llama-moe-cache.cpp` callback synchronizes before reading actual
   selected IDs. The policy observes unique IDs, ages frequency counts and evicts
   the coldest eligible resident, with oldest access breaking ties. All currently
   selected experts remain pinned through fills, including newly admitted ones.
4. Empty slots are used first. When feasible, other layers keep at least
   `floor((slots - active_unique_experts) / cached_layers)` residents. The current
   layer may replace its unselected residents. Small caches may have a zero floor;
   the policy never sacrifices a selected expert to promise a layer quota.
5. The historical file-mapped adaptation issued page-aligned `MADV_WILLNEED` hints before
   uploading actual misses, with a 64 MiB rounded budget per callback. Unsupported
   or rejected advice leaves exact on-demand reads intact. These are hints for
   known misses, not predictions of a future layer. The qualified protected-key
   reader disables these hints and reads misses through its bounded window.
6. The upstream callback uploads original tensor bytes to existing device banks,
   preserving copy ordering and slot-map synchronization. Tensor types, top-k
   choices, routing weights and required PLE remain unchanged. The app uses
   single-token generation. Prompt batches default to one token; explicitly
   admitted bounded profiles now support two or four tokens. See the
   [physical prefill comparisons](native-bounded-prefill-20261025.md).

The qualified storage path is original SSD bytes, protected no-access source
keys, bounded direct reads and device expert banks. CPU/GPU share physical RAM.
Source keys add zero resident file pages. The completed session proves this
finite path; it does not establish efficient read/compute overlap or a speedup
over another eviction policy.

The [subsequent completed-demand replay](performance-results-20261025.md)
matched all three real native hit/miss/upload totals. Eleven C++ settings and
ten independently implemented Python settings found no reduction versus the
current aged-LFU policy on those fixed requests. LRU/SLRU increased expert
payload by 3.32%; the selected 4096-route policy remains. This short trace does
not qualify a policy for general workloads.

## Counters and monitor

The patched callback counts unique expert hits, fills, uploaded expert bytes and
OS-accepted page-advice bytes. The model adapter reads these atomic process totals
on the engine owner after completed operations. HTTP threads read a copied
snapshot. Advice may include repeated hints and page rounding. Uploads count
expert data submitted to backend copies, excluding slot maps; they do not measure
SSD traffic, GPU throughput or saved time. Demos report no real cache counters.

The read-only monitor shows these counters alongside CPU/GPU identity, current
date/time, TTFT and generation tokens/s. Use measured cold/warm console runs
after application runtime admission to assess benefit. The completed requests
measured 0.28455 / 0.28882 tokens/s. Request 1 began with an empty expert cache
after a completed context recreation; request 2 reused it. Neither represents
cold storage or cold pipelines, and no comparative policy speedup was measured.

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
