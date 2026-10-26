# PLE phase pricing, backing ownership and postboot observation

This is intermediate evidence for the [remaining plan](remaining-validation-plan-20261026.md).
The four-graph physical PLE result remains qualified in its recorded scope;
the 208-graph comparison and original-model adoption are incomplete. Source
integration does not change the installed production artifact.

## Reproducible phase pricing

`tools/price_ple_admission.py` reads the completed CPU calibration 2738 and
physical GPU smoke 2741, including ten preceding observations, exact owner,
policy, completion and restoration. It refuses mixed executable identities,
missing phases, changed floors/pools, untracked heap fallbacks or unknown
completion. It uses the upper prelaunch observation bound when pricing a
decline, retaining 256 separate variation pages. Six manual test groups passed.

| Quantity | 16 KiB pages | Scope |
| --- | ---: | --- |
| Largest observed CPU-phase requirement | 7701 | Observed decline plus operational floor 1154 and variation 256 |
| Largest observed pre-GPU requirement | 8190 | Observed decline plus unchanged startup target 2974 and variation 256 |
| Proposed next same-SELF prelaunch requirement | 8190 | Maximum of phase requirements, not their sum |
| Regular full-model prelaunch requirement | 10142 | Unchanged |

The GPU smoke's post-source decline was 4960 pages, above the earlier CPU-only
4878-page estimate. The earlier consumed 8108-page gates and refusals are
preserved unchanged. The 8190 value prices a future case of that exact executable;
it is not a hardware minimum, current admission or a transferable allowance for
a changed binary. Native startup, operational and Direct/Flexible checks remain
independent. No console operation is performed by the pricing tool.

## Actual allocation identity for the ready-expert prototype

`split_bank_bridge.h` and `owned_mapped_backend.cpp::ggml_app_vk_probe_owned_split_bank`
add a separate experimental byte-root borrower. The current three-dimensional
production-bank predicate is unchanged. The borrower validates the original
27-plane extent, BF16 type, actual Vulkan context, device-local/host-visible/
coherent flags, mapped extent, read alignment and descriptor alignment. It
keeps the actual shared Vulkan buffer alive across a synchronous callback and
reports its **VkDeviceMemory identity**, rather than inventing an identity per
logical slot or view. A changed owner or invalid callback result refuses.

The existing ready-wave owner can conservatively reject overlapping groups
that name the same allocation. Distinct roots do not prove distinct backing.
The caller must already hold its CPU role and retain every tensor and matching
GPU epoch; a callback must not export a pointer or leave an operation pending.
This API does not grant overlap or enable it in production.

Manual host check 2763 exercised the extracted actual borrower against API
mocks: 19 root/lease refusals, changed-owner refusal and shared-allocation
overlap refusal passed. The complete implementation also compiled with the
actual PS5 SDK/backend ABI. Upstream header-local unused helpers are treated
as system headers; application warnings remain errors. The initial host test's
unavailable `aligned_alloc`, and the separate upstream-header warning failure,
are retained. Actual independent BOs, source/GPU overlap and numerical/model
performance remain unqualified.

## New boot: recovery is measured, not assumed

The owner completed a normal restart. Read-only discovery 2764 proved a new
boot, two matching process snapshots, exact firmware and zero native owners.
The existing compatibility runtime was not loaded. Its proposed restoration
has **not executed**: automated approval rejected the temporary kernel/ShellCore
modification pending explicit owner authorization. No alternative kernel entry
or indirect workaround was used. CPU-only observations continued.

| Global kernel VM snapshot | Free | Active | Inactive | Wired |
| --- | ---: | ---: | ---: | ---: |
| Prior boot, restored/idle 2759 | 7877 | 25518 | 72442 | 32902 |
| New boot, CPU census 2767 | 3499 | 63960 | 41985 | 29295 |

The new boot did not immediately increase free memory. These are sequential,
different-boot observations, not a matched causal subtraction or the Direct
memory pool. The new census completed two inventories of 88 processes, without
native owners, stopped processes or zombies. SceShellUI reported 50966 resident
pages (796.34375 MiB), versus 35599 in earlier census 2672; AgcCompositor reported
19152 versus 18478. RSS includes shared pages and must not be summed into free
physical capacity or assigned as the sole cause of the VM difference. No system
process was killed, no cache pressure was applied and no pool was resized.

The earlier closed GPU journal reported 19075 bytes through native metadata
(2758). FTP SIZE had returned an invalid unsigned sentinel, which was excluded
from capacity evidence. Its residency probe returned a known refusal before
mapping/content reads, with zero live/pending mappings. No identity guard was
relaxed or failed execution replayed. Its payload size alone cannot explain
hundreds of missing pages; its broader filesystem overhead is not attributed.

## Current-boot shader proof preparation

The isolated title now has an independent strict CPU-bootstrap policy. It
verifies all original shader assets on the current boot, instead of reusing an
older boot's report, then completes the existing source-owner CPU prerequisite
and stops for ordinary closure. Its fresh shader report uses the exact original
plan/run-ID format. Prior proof is forbidden in this scope. Both the full native
entry and the GPU-fixture entry explicitly reject the CPU-bootstrap scope before
any GPU initialization.

Host check 2768 passed 104 scope/identity refusals and three actual SDK units,
including the guards before GPU entry. This implements a preparation path;
it does not claim current-boot shader execution, GPU comparison or adoption.
Native build 2769 passed actual strong-module imports and driver dispatch.
Package 2770 passed all six SELF segment roundtrips at 23104522 bytes,
`690003b7167ee14e47558775e47648636e3b0bf4432feec04df3f8f1b5f8405b`.
The driver/engine/shader donors are unchanged; the executable has no model/chat
entry points. It has not been transferred or run on the PS5. The preceding
8190-page estimate belongs to the earlier SELF; this new binary still needs
independent admission and phase observations.
The latest completed production speed measurements remain 0.391093 / 0.398430
tok/s. The driver pin, original precision, persistent-cache policy and disabled
CI remain unchanged.

## Subsequent authorized restoration and low-memory refusal

The [2026-10-27 continuation](postboot-runtime-memory-20261027.md) supersedes
the authorization-pending state above. The same existing runtime completed one
entry after the owner's instruction. New-boot discovery and full CPU admission
passed. Inventory then refused before any query at 1060 free pages; an existing-
shell, boot-bound screen observed 1017 -> 1012, below floor 1154. No title/GPU,
current-boot shader bootstrap, performance adoption or production change occurred.
The implementation/validation request remains incomplete for measured resource
and remaining package prerequisites, with no unknown operation or automatic retry.
