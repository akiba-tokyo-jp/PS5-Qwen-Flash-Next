# Native allocator admission after complete model load

The complete original model subsequently loaded on the PS5. Native device idle
and the matching driver completion checkpoint passed. The next context/cache
headroom predicate returned a refusal before generation. The old artifact did
not persist the exact post-load Vulkan free value; it established only that it
was below the unchanged 1,920 MiB remaining requirement. All resources were
retained until the exact owner normally closed. Original restoration, numerical
readmission, normal shutdown, final CPU and full SELF readback passed again.

The pinned Mesa PS5 `radv_query_heap_info` assigns the same winsys driver-byte
count to both `allocated_vram` and `allocated_vram_vis`. The integrated-GPU budget
code subsequently adds them. This source defect can underreport free memory
once the model owns more than half the physical pool. The precise old post-load
numeric sample is not available. Vulkan's memory budget is an allocation guideline
and usage estimate; see the [Khronos definition](https://docs.vulkan.org/refpages/latest/refpages/source/VkPhysicalDeviceMemoryBudgetPropertiesEXT.html).

The application now uses the native allocator's existing canary-validated largest
available Direct extent for its allocation admission. This is the allocator that
backs every native Vulkan BO. Its observed pool must equal the Vulkan device's
reported total. Both pool/free observations and owner snapshots must be valid
and stable, the journal and exact owner healthy, every physical/mapping extent
known, and each free sample no greater than pool minus owned storage. Admission
uses the lower free sample. It never invents availability from nominal capacity,
sums inactive pages, or subtracts already-excluded owned bytes again.

Raw Vulkan estimates remain diagnostic. The application saves separate native
pool/free/owned values and the unchanged context/workspace/staging/reserve/cache
requirements in `.memory.after-load`. Its initial memory report explicitly names
the native allocation source; hardware information uses that same actual pool.
The Direct requirement, CPU limit, Flexible reserve and every other safety margin
remain unchanged. The shared driver source/archive, selected compiler profile,
GPU kernels and all seven model-I/O overlays are unchanged.

The actual observation function passed 29 host cases covering model-sized
ownership, lower-sample selection, fragmentation/external use, pool mismatch,
zero/unknown results, concurrent owner changes, invalid mappings and retained
faults. Its numeric journal records stay within 1,024 bytes. Native link, actual
runtime imports and six SELF segments passed. A new frozen physical case must
still qualify context/cache admission, real generation and every final
restoration/readmission gate; no model tokens/s result is claimed here.
