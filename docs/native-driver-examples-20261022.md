# Native Vulkan implementation references

The owner requested implementation based on actual Vulkan-driver examples.
The sources below were inspected on 2026-10-22. Their measurements do not qualify
this Qwen application. No PS5 access is part of the following host work.

| Actual source | Relevant behavior | Application change |
| --- | --- | --- |
| [PS5LM native entry](https://github.com/cobanov/PS5LM/blob/c4595784ce75c1d58777b11ef812d3e087e74296/ps5/app/main.cpp#L68) | Static RADV ICD entry points feed GGML; direct commands use Mesa common dispatch | Retain this existing static route, with native device registration and submitted-work accounting |
| [PS5LM driver lifetime patch](https://github.com/cobanov/PS5LM/blob/c4595784ce75c1d58777b11ef812d3e087e74296/patches/mesa/0007-radv-ps5-a-destroyed-buffer-s-memory-waits-for-the-G.patch) | Records a console hang when destroyed memory remained referenced by submitted work; delays release until completion | Use the preserved native per-BO retirement implementation and an explicit completed frontend boundary |
| [Pinned PS5 Mesa platform](https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/amd/vulkan/winsys/ps5/radv_ps5_platform.c) | RADV owns `sceAgcInit` through `call_once`; ordinary BO placement uses Direct memory and GPU-visible mapping | Keep RADV as the sole explicit Init8 caller, wrap its result, then prepare exact native owner metadata before physical-device discovery |
| [Selected driver contract](https://github.com/akiba-tokyo-jp/PS5-Vulkan-Inference/blob/872cc1264ad8ba5d6b888b092968fa5858a38c58/docs/driver_integration_contract.md) | Preserve client-native allocator/address members while applying the compiler/winsys profile; disable persistent caches | Keep the exact `cumulative-idle` pair and all native compatibility members |
| Preserved MOSS native implementation and its immutable original build receipt | Own log before explicit AGC, single-producer ownership, positive quiet plus matching completion epoch before per-BO retirement | Adapt the MIT native implementation into `native/driver`; source hashes are retained in its provenance record |

PS5LM's published model examples use quantized checkpoints. Only its Vulkan
integration and lifetime behavior inform this work; Qwen retains original BF16,
every expert and required PLE. No PS5LM/HAR patch code was copied here. The
adapted per-BO implementation is the separately licensed MIT native source.

The PS5LM deferred record copies a BO's memory descriptor. The preserved native
owner also validates its original descriptor address, so stacking that patch on
top would break the owner contract. Qwen instead uses the native callback's
existing metadata retirement and its existing `retire_quiet` function. Optional
submit-thread and spin/sleep tuning from the PS5LM example is not enabled.

## Implemented frontend boundary

`DriverLifecycle` requires an exclusive application journal, exactly one explicit
successful AGC version8 call, native metadata preparation and an empty owner
before Vulkan discovery. It records stages on both sides of explicit AGC. It
does not establish a hard timeout for the AGC kernel call.

One frontend producer holds the lifecycle lease throughout initialization or
an adapter operation. Registered device creation and both Vulkan submission APIs
are connected to this owner. A nonblocking host mutex excludes concurrent queue
submission and device-idle calls; overlap is rejected before another GPU call.

After GGML synchronization, the frontend requires successful device idle,
an idle native completion worker, equal positive requested/completed epochs and
healthy exact ownership before calling the existing deferred retirement path.
It then saves a durable journal checkpoint. Failed waits, owner mismatch or
incomplete retirement permanently retain the graph and reject another producer.
The adapter checkpoints after every completed `llama_synchronize`, including
each prefill token, while retaining its producer lease for the next token.
Initial model loading also checkpoints before observing remaining context/cache
headroom. Retired transient BOs therefore do not wait for the entire prompt or
the next request before reaching a completed frontend retirement boundary.
Initialization with no submitted GPU work does not invent a completion epoch or
release retired allocations without one.

These conditions follow the [Vulkan device-idle contract](https://docs.vulkan.org/refpages/latest/refpages/source/vkDeviceWaitIdle.html)
and [memory-release requirements](https://docs.vulkan.org/refpages/latest/refpages/source/vkFreeMemory.html).
The logical device's queues require external host synchronization; work that
uses a memory object must have finished before its memory is released.

The Qwen driver journal is opened exclusively below this application's own
sandbox. It has a 64 MiB cap with reserved failure space and never falls back
to another application's log or removes earlier evidence. Unowned CPU heap/file
pointer imports are refused. The pinned GGML failed-import path can use its
existing completed staging transfers; no precision or arithmetic changes follow.

The preserved native compatibility objects also query the optional import-only
pool's 72-byte statistics ABI. Source inspection confirms that zero owned pool
bytes skips only that extra heap and leaves the original Direct heaps intact.
`native_import_pool.cpp` therefore reports exact zero ownership and rejects
imports. It never reserves or advertises the other application's 10 GiB pool.

## Host verification and current restriction

The adapted native platform compiles using the pinned Mesa recipe and its actual
header graph. Its archive SHA256 is
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Only the native platform member differs from the prior composed native archive;
all other 703 member occurrences remain byte-identical. The selected shared
compiler/winsys donor remains
`67fe76cc3362a191ba6e3e1cfad4436624ec1f928b419a867e88c6a9ef30f4e9`.

The actual per-BO implementation passes 35 deterministic host ownership cases.
Frontend API stubs cover log/Init8/prepare failures, duplicate initialization,
producer overlap, concurrent queue calls, failed device idle, incomplete epochs,
busy/faulted workers and failed retirement. Adapter and Vulkan bridge stubs check
their actual hook placement and error paths.

The final native frontend link, real-module import audit, local SELF integrity
and six reconstructed segments pass. The exact artifacts and the 28 passing
Python tests are recorded in [the host result](native-frontend-host-20261022.json).
Engine, native link and native platform receipts are copied immutably into the
local package. No resulting binary is committed, installed or executed.

Actual journal implementation stubs also check partial and interrupted writes,
capacity refusal, sync failure and single terminal diagnostics. A sticky failure
never resumes or keeps appending emergency messages. The original-source owner
test also checks Qwen's real path-prefix and once-only journal guard.

All console operations and validation deployment remain disabled, and native
GPU modes still reject execution independently of configuration. The previous
shell-state and original-restoration requirements remain unresolved. Host
implementation and cross-linking do not establish console compatibility,
original-BF16 output quality, large-model memory fit or measured tokens/s.
