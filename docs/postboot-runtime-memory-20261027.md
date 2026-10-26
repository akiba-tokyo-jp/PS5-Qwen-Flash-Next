# Runtime restoration and refusal before staging

This continues the [remaining validation plan](remaining-validation-plan-20261026.md).
**The overall implementation and validation request remains incomplete.**
The current obstacle is measured kernel VM headroom, not missing authorization.
No new inference-speed result or performance adoption follows from this work.

## Completed current-boot actions

After disclosure of the temporary kernel/ShellCore operation, the owner
explicitly instructed continuation without another permission request. Case
2765 then executed the same verified existing runtime exactly once through the
approved path. The earlier automatic-review refusal remains historical; it
was not bypassed or treated as an execution.

The 554264-byte runtime was reused after whole local/remote SHA256 verification:
`29760209bda40396f3453e5358674e9a15b4348c914abf40a4176206fe268120`.
The previous journal was archived intact. The new terminal journal positively
reported returned upstream entry, result zero, loaded compatibility query and
resident loader. Firmware, boot and services matched, with one matching runtime
process and no native title. There was one kernel entry, no automatic retry and
no production SELF/settings change. These volatile changes remain until reboot.

Read-only discovery 2771 verified the same new boot, loaded runtime, two equal
process snapshots and zero native owners. Full CPU observer 2772 positively
completed with unchanged source rebound to eight actual management/system/runtime
identities. It replaced the old-boot session in the reservation. Payload-context
Direct reporting is not native-title quota and does not admit a title or GPU.

## Physical memory outcome

Process-memory case 2773 returned a known refusal before its two inventory
queries. Its existing check observed 1060 free pages, below operational floor
1154 plus 35 pages of fixed inventory allowance. The terminal journal reported
`success=0`, zero inventory queries/returns, zero explicit allocations, zero
payload reads and zero title/GPU launches. It was not replayed. No operation has
unknown completion.

Scalar diagnosis 2774 used the already running shell, with no new ELF. The fixed
filesystem buffer/vnode counters were unavailable; they are not treated as zero
or evidence of a small filesystem allocation. Readable VM counters confirmed low
free memory. Cumulative paging counters are not resident-byte attribution.

| Sequential global VM observation | Free | Active | Inactive | Wired |
| --- | ---: | ---: | ---: | ---: |
| Earlier new-boot census 2767, before restoration | 3499 | 63960 | 41985 | 29295 |
| Refused inventory 2773, after runtime/full CPU admission | 1060 | 18509 | 89169 | 30001 |
| Boot-bound passive screen 2776, final free sample | 1012 | 18523 | 89192 | 30011 |

Pages are 16 KiB; the last free value is **15.8125 MiB**. The VM domain contains
138739 pages, not the console's entire RAM or the Direct/Flexible pools. These
sequential observations span a substantial interval. Active-to-inactive
redistribution is visible, but does not identify a reclaimable owner, prove a
runtime leak or make inactive pages available. No new process RSS inventory
ran, so earlier ShellUI RSS must not be presented as current.

Even the unchanged operational floor `898 + max(206, 256) = 1154` was unmet.
Startup target 2974 and regular full-model prelaunch 10142 remain unchanged.
The old PLE phase price 8190 belongs to the earlier SELF and cannot qualify the
new bootstrap SELF. No allocation/title/GPU work was attempted to force progress.
There was no system-process kill, reset, cache pressure/advice or pool resize.
Exact global VM attribution and a supported correction remain unresolved.

## Avoid repeated preparation under insufficient headroom

`tools/kernel_vm_preflight.py` screens before new case transfer/publication. It
uses one existing-shell connection, 13 fixed read-only queries, 45 seconds and a
65536-byte response cap. Boot time is checked before/after against a complete
CPU session. Missing/error/malformed counters fail closed; both free samples
must meet the declared phase requirement. Inactive is never added to free.

Before connecting, it authenticates the input session's terminal native journal,
manifest, observer artifact and eight compiled process identities. Passing never
replaces fresh native owner, source integrity, consecutive memory or pool checks.
The new bootstrap keeps the conservative regular requirement while its own
phase cost is unmeasured; the old SELF's allowance is not transferred.

Physical screen 2776 matched both boot observations and free 1017 -> 1012. It
completed as `refused_before_staging`, with zero new ELF requests, title launches,
GPU calls, kernel entries and sysctl writes. The installed fastest executable
was not read back again under low memory; no executable/settings mutation was
made in this continuation.
The input authenticator was subsequently strengthened and checked offline
against the actual completed 2772 evidence. The physical screen was not replayed;
its original receipt and source revision remain distinct from that host check.

`tools/rebind_cpu_context.py` generates observer/context-guard headers from that
complete evidence plus a positive same-boot runtime receipt. It binds actual
PID, parent, UID and start time for eight owners. It has no execution path and
grants no mutation/admission. This replaces ad hoc old-boot constant substitution
for future cases; historical consumed manifests/helpers stay unchanged.

Eight focused host test groups passed, covering malformed/duplicate dumps,
missing counters, stale boot, low memory, floor reduction, changed native
evidence/artifact and changed/missing/duplicate owner identities. Both generated
headers compiled against two unchanged actual native units (2775). Actual 2772
evidence passed the strengthened authentication. A duplicate-dump parser gap
and a host temporary-directory refusal were fixed before completion; neither
host failure ran on PS5.

## Remaining prerequisites

Do not loop on refused cases or stage a title under this measured condition.
A supported identified correction or an observed external-state change must
precede a useful new screen. Then require fresh native admission, all 1527
current-boot shader checks, own-SELF pricing, PLE timing and any surviving
original-model qualification/placement. The other remaining packages retain
their incomplete dispositions. No automatic recovery or scheduled retry exists.

Original BF16/F32, F32 KV, every expert/PLE, driver `872cc126` / `cumulative-idle`,
disabled persistent caches, production limits and disabled CI remain unchanged.
The latest production measurements remain historical 0.391093 / 0.398430 tok/s.
