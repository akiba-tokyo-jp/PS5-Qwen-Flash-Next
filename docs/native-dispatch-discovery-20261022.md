# Static Vulkan dispatch omission found on the physical PS5

The distinct native-frontend SELF
`0e527b0a8bfe975ba7421b7aa3b405f7f6549b2926b89f544203361743cd34ee`
passed host link/import/SELF/shader checks and was launched once through the
ordinary OS path. Its CPU prerequisites, sole AGC8 initialization, empty owner
admission and Vulkan instance initialization completed. The application then
exited before device enumeration returned. No completed BF16 graph or model
inference was observed. The original SELF was restored and fully read back;
fresh original numerical admission is recorded separately.

The existing kernel message-buffer log identified a user instruction-fetch
page fault at address zero. Offline symbolization used the immutable packaged
PIE and the native loader's observed code base. The call chain reaches
`radv_init_wsi` through physical-device enumeration. WSI calls the physical
device's `GetPhysicalDeviceProperties2` trampoline during initialization.
The exact failed ELF lacks `vk_common_GetPhysicalDeviceProperties2`; its real
common physical-device entrypoint-table field is zero. The other five checked
callbacks are present. A non-null exported trampoline therefore did not establish
a non-null implementation behind it.

Mesa's generated entrypoint tables use weak references. The application's
ordinary static archive scan omitted the otherwise unreferenced common
implementation. The successfully admitted original application's link retains
the native Vulkan archive with `--whole-archive`; Qwen's link now follows that
same policy, retaining `--gc-sections` and the exact selected archive bytes.
No driver arithmetic, feature advertisement, cache policy or numerical threshold
is changed by this application link correction.

`tools/native_dispatch.py` compiles the actual native table-field offsets using
the pinned Mesa compile recipe. It reads the linked ELF and its relocations,
then checks the six required implementation symbols and exact nonzero table
targets. The immutable failed SELF's source PIE fails this audit specifically at
`GetPhysicalDeviceProperties2`, reproducing the omission without console code
execution. A successful audit is now required by the native builder and packager.
At this discovery checkpoint the correction still required host linking,
real-module imports, SELF/shader checks and a distinct physical-console admission.
The subsequent artifact passed those checks and the BF16 fixture with 16 exact
outputs; see [the later result](native-bf16-success-20261022.md). The failed
candidate's outcome remains unchanged.

The failed candidate, phase records, kernel-log capture, symbolization and
owner-private journals are preserved outside Git. Its completed CPU log-copy
permission refusal is also retained; a distinct bounded copier used the reviewed
temporary-read/FD-restoration pattern and confirmed the original file metadata
after capture. No application relaunch or GPU reset was used to obtain the logs.
