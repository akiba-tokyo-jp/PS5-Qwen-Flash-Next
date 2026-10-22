# Original-model CPU preflight before Vulkan

`model-validation` is an implementation stage for the complete transferred
original model. It requires the complete v2 conversion receipt, the exact pinned
model/format audit and the original 1,256-tensor footprint. A private policy must
bind the preceding successful combined SELF and fresh idle/original-restoration
evidence. Native display, learned model loading and Vulkan initialization are
rejected in this stage. Committed execution and deployment flags remain disabled.

The application streams SHA256 for every file before backend initialization.
One 30-minute deadline covers the entire verification sequence, rather than
restarting the allowance for every split. Checks occur between completed reads;
64 MiB progress boundaries persist phase observations. GGUF metadata, exact
precision, PLE constants, dimensions, counts and the full footprint are checked
before any address-space admission.

The native mapper opens regular files read-only without following symlinks,
checks actual sizes, and maps each using non-fixed `PROT_READ | MAP_SHARED`.
It requests no prefetch and never reads through the mapped pointers. It checks
native page size, rounded extents, address arithmetic and pairwise disjointness.
The 256-file/512 GiB limits bound metadata and virtual file size; they are not
physical RAM or device-memory claims. Mapping calls have a separate 60-second
deadline checked at completed observation boundaries.

After all files map, each completed mapping is unmapped once in reverse order.
Failure or an unknown result stops further cleanup and retains remaining
process-owned backing for ordinary OS title close. No automatic retry, fixed
mapping, protection mutation, driver reset or GPU request occurs. A successful
report states `completed_waiting_for_ordinary_close`, with mapped/unmapped counts,
total bytes, no model load and zero GPU compute calls. The title then stays in
explicit idle ownership; it does not return through the CRT's fault hook.

Host API-stub checks cover exact byte accounting, rounded ranges, size changes,
partial mapping failure, descriptor-close uncertainty, overlapping/unaligned
addresses, observation failure and partial unmap failure. The actual syscall
provider compiles for the PS5 ABI. These checks do not admit actual PS5 model
mapping or resident inference memory. Physical execution requires complete model
preparation and verified transfer first, followed by the existing preservation,
ordinary-close and exact original-restoration protocol.
