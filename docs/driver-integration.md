# Latest shared-driver integration

The owner authorized acquisition and application integration of the updated
driver on 2026-10-22. Remote `main` was fetched and matched local source at
`872cc1264ad8ba5d6b888b092968fa5858a38c58`. The selected profile is explicitly
`cumulative-idle`; persistent shader/pipeline caches remain disabled before
backend initialization. Existing bounded driver/MOSS results do not qualify
this Qwen model, its BF16 numerical behavior or memory footprint.

## Exact inputs and completed host work

The profile was rebuilt with the selected repository's `driver/mesa/build_profile.py`,
using Mesa `1ba9874f478657ccf6da72ce55f0260164cc0bd0` and pristine base archive
`149ad31788c0c8bc78de971f0f95b931832f3db94eafda38b28bdf2aff1218fa`.
ISA capture is disabled for this client build. Only `radv_shader.c.o` and
`winsys_ps5_radv_ps5_winsys.c.o` changed; all 702 other member identities were
preserved. The driver source checkout was not edited.

The new archive SHA256 is
`67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9`.
Its exact manifest, source files, patch digests and profile are pinned in
`native/qwen_flash_next/dependencies.lock.json`. The old diagnostic archive is
a historical artifact, not the selected application dependency.

`tools/driver_inputs.py` rejects a stale or dirty tracked driver checkout,
changed source/manifest/archive, wrong profile/member provenance or incompatible
cache policy before engine build or native link writes. `tools/build.py` rebuilds
the pinned engine with the actual Strata/Maya policy and loader patches.

`tools/build_native.py` compiles the real session, model adapter, HTTP service,
native entry point and pinned native CRT, then links them with the engine and
selected driver. The initial intermediate native PIE was 136,255,816 bytes.
Its required engine/driver symbols and 16 initializer slots are present; all
recorded link inputs retain their digests. Six native runtime providers are
recorded, including `libkernel.sprx`. Source, compiler, linker, object/archive,
runtime-import and layout identities are retained in the private build receipt.
The public-safe [integration record](driver-integration-20261022.json) identifies
the exact initial artifact; binaries and raw build records stay on the data disk.
The subsequent native monitor/guarded SELF is recorded separately in
[native-monitor-20261022.json](native-monitor-20261022.json), preserving the
earlier milestone. It retains 16 initializers and seven runtime providers.
Its 344 imports resolve through actual module stubs, excluding weak convenience
stubs as runtime evidence. SELF integrity and all six reconstructed segments pass.

## Native adapters and layout

`vulkan_bridge.cpp` forwards static Vulkan entry points to RADV/Mesa without
altering feature advertisement or arithmetic. Client blocking waits have a
finite ceiling, and failed submit/wait operations halt before unwinding or
resource reuse. The native entry point selects serialized one-node submissions
with asynchronous transfers disabled. See [native validation](native-validation.md).
`native_socket.cpp` implements the SDK's missing `accept4` using `accept` and
checked descriptor flags. This app never forks or execs; the fallback is not a
general atomic close-on-exec replacement for a process that does. Flag failures
close the newly accepted socket and preserve the original error.

The public SDK's actual `ps5_open_memstream` is bound with both required
flush/close wrappers. Native bridges remain internal through a symbol visibility
map. The pinned driver's CRT and PIE layout preserve IEEE startup, static
initializers and unwind boundaries at the source/link level. Their actual
execution, imports, TLS/unwind and loader behavior still need console admission.

The CRT/layout and adapted glyph/tile primitives originate in BlackBearReloaded's native boilerplate, inherited
through Mihawk-99's PS5_Vulkan and the selected derivative. The public SDK's
platform runtime carries Mihawk's GPL-3.0-or-later notices. These external
CRT/runtime sources are referenced in place and hashed. Adapted raster/tile code
retains its original GPL notices and a bundled license/attribution notice.
Their license obligations apply to any future bundled artifact;
no runtime or native binary is distributed here.

## Manual reproduction

The selected fresh profile output is
`C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference/.local/qwen-cumulative-872cc126-001`.
The driver builder requires a fresh directory and preserves the pristine base.
A new profile output must be reviewed and pinned; do not overwrite this artifact
or assume a different output has the same archive digest.

```powershell
python tools/build.py --workspace C:/Users/User/ps5-ai --driver-root C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference --driver-manifest C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference/.local/qwen-cumulative-872cc126-001/manifest.private.json --cache D:/PS5-AI/qwen-flash-next --jobs 4
python tools/build_native.py --workspace C:/Users/User/ps5-ai --driver-root C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference --driver-manifest C:/Users/User/ps5-ai/driver-work/PS5-Vulkan-Inference/.local/qwen-cumulative-872cc126-001/manifest.private.json --cache D:/PS5-AI/qwen-flash-next --runtime-imports D:/PS5-AI/public/PS5-AI-WAI/.local/dependencies --jobs 4
python tools/check_native_adapters.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
python -m unittest discover -s tests -v
```

The runtime-import argument identifies local SceAgc import stubs, never a model
or a host inference engine. No build command accesses the PS5. Fifteen Python
tests pass, including source/profile/artifact integrity and the console guard.
Host API-stub checks pass for the real Vulkan bridge and socket adapter, including
argument forwarding, flags, failure cleanup and error preservation.

## Remaining gates

Host SELF conversion/packaging now passes. Native startup, model-independent GPU admission,
the read-only display's native presentation, original checkpoint acquisition,
lossless conversion, large mappings, PLE, sustained shared-memory residency,
full-model output quality and measured tokens/s remain separate work.
These remaining gates are separate from those host results. The first console
mode is limited to CPU display validation with no model/Vulkan initialization.
Full inference modes remain rejected by policy. Release and CI remain disabled.
