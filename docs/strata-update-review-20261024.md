# Strata update review for PS5 performance

The owner requested applicable improvements from current Strata. Source inspected
on 2026-10-24: [main at 7ddc17a38fe7f31637e895ecfba58c2cd43d65ec](https://github.com/Niko1221/Strata/tree/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec),
whose README identifies engine 0.1.48. The
[comparison with our previous reference](https://github.com/Niko1221/Strata/compare/011c9e600a93bbc9fd451c563501b5831c32bbca...7ddc17a38fe7f31637e895ecfba58c2cd43d65ec)
contains 131 commits. This is source inspection, not a PS5 speed measurement.

## Applicable mechanisms

The current [expert source](https://github.com/Niko1221/Strata/blob/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec/src/core/expert_source.cpp)
groups known source windows, sorts them by file/offset and merges touching
windows. Its Linux direct reader queues a batch before waiting; staged buffers
have explicit publication and consumer ordering. These principles can inform a
PS5 implementation with a fixed total scratch budget, exact original bytes,
bounded outstanding requests and positive I/O completion before reuse. Linux AIO
and Windows overlapped APIs are not PS5 APIs. Existing PS5 no-access source keys
and zero file-backed model mmap must remain intact.

The [batched DMA helper](https://github.com/Niko1221/Strata/blob/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec/include/strata/core/dma_batch.hpp)
requires immutable sources and disjoint destinations. Its
[measurement report](https://github.com/Niko1221/Strata/blob/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec/docs/BATCHED_DMA.md)
distinguishes lower submission cost from whole-model tokens/s. The CUDA calls
cannot be transplanted into Vulkan. The helper's fallback after a failed batch
also does not meet this application's no-retry rule for uncertain operations;
any adaptation must quarantine and retain unknown work.

The [near-tail prompt checkpoint](https://github.com/Niko1221/Strata/blob/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec/docs/PROMPT_CACHE_TAIL.md)
retains existing chunk geometry and bounds its extra checkpoint. Prompt-state
reuse could lower later TTFT, but needs exact token-prefix/state validation and
bounded hybrid-attention/recurrent-state ownership. It is not a decode-speed
claim or a reason to alter the cold expert-cache control benchmark.

## Exclusions and priorities

The 131-commit delta does not modify the referenced `uma_cache.hpp`,
`expert_cache.cpp` or `expert_cache.hpp`. Our existing UMA admission therefore
does not become faster just by changing its reference revision. Preserve the
stronger PS5 physical allocator and whole-runtime guards.

Current [native dense defaults](https://github.com/Niko1221/Strata/blob/7ddc17a38fe7f31637e895ecfba58c2cd43d65ec/src/core/native_dense.cpp)
can create Q8 hyper-connection copies even from a BF16 pack on selected AMD
devices. That path violates the owner's no-quantization requirement. CUDA/HIP
architecture-specific kernels, multi-GPU disjoint caches and long-context KV
prefetch are not direct fits for this single PS5's short-context Vulkan control.
Recent DFlash2 work adds a drafter and verifier paths; it requires a separate
memory/operation/acceptance assessment rather than enabling an environment flag.

The profile-only candidate completed and measured approximately 87.5% of decode
wall time in serial direct reads. The application now implements bounded paired
known-miss reads within the unchanged 8 MiB window, with exact completion and
retention controls. Host concurrency, byte-parity, failure and actual patched
cache-loop checks passed. Its physical two-read candidate was slower and failed
the kernel headroom predicate; exact original restoration completed. Preserve
[the rejected result](source-concurrency-refusal-20261024.md). The next candidate
adapts staged consumption with only one outstanding read. Its completed physical
comparison measured 0.285184 / 0.289577 tokens/s, an observed mean 0.82% above
the matching profile control. All three requests, actual native frames, positive
retirement and exact original restoration/readmission/shutdown/final checks
passed. See [the measured result](performance-20261024.md). The small two-request
sample does not establish a general speedup. No public Strata timing
is a forecast for PS5, and no inspected mechanism is recorded as integrated
before its implementation and physical comparison complete. Upstream MIT notices
and precise source pins must accompany any adopted code or algorithm.
