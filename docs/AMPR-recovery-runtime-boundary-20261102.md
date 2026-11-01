# Recovery and the separate runtime initialization failure

The owner confirmed an abnormal console termination and powered it on again.
The interrupted compatibility initializer's journal was recovered afterward.
It stops at `BEFORE upstream_kernel_entry`; there is no matching RETURN or
ready END. The failure window includes the kernel-initialization call and the
interval before the next journal record. No exact failing instruction or
internal kernel cause has been established. Do not automatically replay the
same initialization conditions. Reopening it requires a documented corrected
implementation or source-backed prerequisite change; a new boot alone is not
such evidence.

## Two distinct abnormal-stop boundaries

| Scope | Immediately preceding OS operations | Last positive evidence | Interruption boundary |
| --- | --- | --- | --- |
| Previous PFS experiment | Owned PFS, readonly nullfs view, temporary own-process auth change; after native exit, ordinary view unmount and credential/parent restoration | Native 16 KiB read exact, APR ENOTTY, native END/ordinary return; unmount returned zero; auth and parent restoration positive; restoring SELF renames acknowledged | Host whole-file readback loop after the original program had been renamed back; actual kernel crash point unknown |
| Current compatibility restoration | Original title alias restored, attempted native launch rejected by OS, original program restored; exact existing initializer requested once, including its own dynlib-range update and global kernel/ShellCore entry | Fresh idle/current-boot preflight and original initializer identity checks; recovered journal reaches BEFORE upstream_kernel_entry | No kernel-entry return/ready END, then lost management/FTP; owner confirms abnormal termination |

Both scopes include OS/kernel operations. Neither executed application GPU
inference, hardware Kraken decompression or an APR read command. The CPU
entropy comparator had completed separately and is not an immediate crash
boundary. These facts do not establish a common cause for the two stops.

Historical successful setup restored compatibility first (58010), then the
existing title alias (58202). This attempt restored the alias first (62152),
encountered an OS launch rejection (62280), then requested compatibility
initialization (62300). The initializer bytes were identical; the surrounding
sequence was not. This ordering difference is an untested condition, not a
proven cause. Reusing a binary does not establish equivalence of kernel state.

## Completed recovery before the second abnormal stop

- Reconnected to the owner-confirmed endpoint; no address is published here.
- Two read-only CPU snapshots established the changed boot and zero native
  owners. Physical program and five settings passed whole-file SHA/EOF checks.
- A complete stable 1095-entry filesystem inventory had zero actual PFS mounts.
  The old fixture path used its ordinary parent filesystem. Its exact 64 MiB
  image/inode and empty directory were verified before removal.
- Five old trial files were identity-checked and removed; the image/directory
  and recovery helpers were retired. Parent ownership was restored.
- Only the missing existing title nullfs alias was restored. Its registered
  metadata, source files and all six mounted aliases were verified. No system
  remount, registration change, model inference or driver relink occurred.
- Read-only credential observations found no sharing with the parent or seven
  protected services, before/after loading the original filesystem module.
  No credential write was made by that observer. This observation does not
  retrospectively authenticate an old process's credential lifetime.

One cleanup monitor used a mismatched log path. Its actual positive END and
helper absence were recovered without resubmitting cleanup; all helper artifacts
were removed. The executed builder was archived before correcting substitution
order and adding a declared/compiled path assertion.

## Native rejection and initialization request

Direct-PFS candidate 62280 returned OS error `0x80020008` before native entry.
The direct supervisor did not run. The original SELF, five settings and alias
were restored and checked. The earlier read-only runtime query had reported
compatibility absent. The launcher had not checked that prerequisite before
calling LaunchApp; a correction remains on the unqualified prototype branch.

The exact existing runtime was requested once, using the previously qualified
554264-byte deployment binary, SHA256
`29760209bda40396f3453e5358674e9a15b4348c914abf40a4176206fe268120`.
Its frozen local provenance/input checks and complete remote identity passed.
The underlying public kernel blob is the unchanged kstuff-lite v1.11 release
from source reference `85fb88a526e58e357d6f1e626ce05af4acdb8b5d`.
This was a global compatibility initialization request, not a Vulkan archive
switch or an application GPU submission. The HTTP dispatch returned an empty
response; that does not prove a successful kernel entry or ready return.

The recovered journal records an absent-runtime check, loader mapping, the
self dynlib-range update marker, and then BEFORE upstream_kernel_entry.
Initialization progress beyond that marker is unconfirmed. The subsequent
owner restart restored read-only access for journal recovery; the latest boot,
runtime state and title alias have not yet been readmitted. No reentry was made.

## Platform logs and limits

The prior boot's platform log contains no intervening orderly Shutdown entry.
Two captured error-history entries report CE-108262-9 for system titles, not
PPSA99190, around startup. The official description concerns reading system
software/application data; it does not identify our failing kernel path.
See [PlayStation's CE-108262-9 description](https://www.playstation.com/ja-jp/support/error-codes/ps5/ce-108262-9/).
No linked kernel stack/panic trace was obtained. Firmware updates, database
rebuilds and system resets are outside this investigation.

## Disposition

Current status is investigation after the owner-confirmed abnormal termination,
not completed hardware validation. Original program placement was last fully
verified before the compatibility request. Fresh boot/readmission is required
before further execution; do not infer that an old alias survived startup.
First inspect the recovered initialization boundary and document a corrected
implementation or source-backed prerequisite change before another attempt.

[Draft prototype PR85](https://github.com/akiba-tokyo-jp/PS5-Qwen-Flash-Next/pull/85)
contains direct-PFS lifetime control and a runtime readiness guard. Its native
SELF and supervisor/launcher cross-builds pass, but the direct filesystem path
has not executed on PS5. It is outside main and production. No acceleration
candidate was adopted; AMPR batching, hardware Kraken and matched model timing
remain unperformed. CI remains disabled.

Evidence cases: owner-boot-observer-62090, owner-recovery-inventory-62110,
owner-recovery-cleanup-62130, owner-alias-restore-62152, owner-recovery-62160,
credential-observer-62190, shutdown-evidence-62210/62220,
APR-direct-classic-62280, known-runtime-restore-62300,
runtime-boundary-62310, runtime-power-state-62350,
after-abnormal-exit-62370. Raw system logs, bytes, endpoints and proprietary
module data remain private. Driver 872cc126/cumulative-idle and persistent-cache
policy are unchanged.
