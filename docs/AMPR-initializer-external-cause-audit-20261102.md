# Initializer failure: cross-case source audit

**Final disposition: failed and closed by the owner on2026-11-02.**
No continuation is queued. Trial artifacts and old rollback copies are retired.
The [current closure and cleanup record](current-validation-closure-20261102.md)
supersedes pending-work and retention statements below. Earlier observations
remain historical partial results.

Scope: investigate PS5 abnormal termination using reports, fixes and source
across the PS5 ecosystem. The owner explicitly prohibited filtering information
collection by firmware. Search by symptoms, failure stage, implementation and
fix history. Record the conditions of a report when assessing a fix; do not
exclude a report because its firmware differs.

## Findings on the current boot

Read-only observations62420 and62470 completed with positive END, equal boot
and protected-service snapshots, ordinary helper return and helper retirement.
The two helper artifacts were removed after62470. No initializer, title,
APR command, PFS mutation or GPU work was submitted in either observation.

- Runtime compatibility is absent. No native application owner was present.
- All six expected physical production files passed complete digest checks.
- All four inherited bootstrap descriptors passed F_GETFD.
- The self dynlib pointer chain used by the existing initializer resolves to
  kernel pointers. Its range is not already unbounded.
- No sharing of that dynlib/object/segment chain with the seven protected
  services was observed. This is not a retrospective observation of62300.
- The exact frozen ShellCore import resolver obtained all seven required GOT
  locations from the current process's dynamic tables, without modifying them.
- Mount enumeration was stable at1095 entries, with zero PFS-named mounts.
  The existing title directory resolves to the underlying system_ex filesystem;
  the volatile title nullfs alias is not mounted.

These results remove several missing-prerequisite explanations on the current
boot. They do not execute or validate the initializer's internal kernel path,
qualify direct PFS, or establish that the earlier failed process had the same
descriptor and object state. Registered-title metadata and mounted aliases have
not been requalified for a new native launch.

## External cases and source fixes

| Mechanism | Primary evidence | Relevance and disposition |
| --- | --- | --- |
| Invalid kernel write gadget | [Issue79](https://github.com/EchoStretch/kstuff-lite/issues/79), [fix fe7fef6](https://github.com/EchoStretch/kstuff-lite/commit/fe7fef639aafbbdacc73cf9f4f49a45f6798106d), merged PR82 | Startup black-screen/power-off reports have a concrete offset-typo fix in prosper0gdb/offsets/12_70.h. This establishes an initialization failure mechanism. Inspect the selected write path and executable provenance; copying a numeric address is not a general fix. |
| Stale payload-manager asset | [Maintainer's resolution](https://github.com/EchoStretch/kstuff-lite/issues/79#issuecomment-5860252326), [v1.11 release](https://github.com/EchoStretch/kstuff-lite/releases/tag/v1.11) | The maintainer identified an outdated manager payload. Our archived official ELF exactly matches the current release asset digest, so that specific stale-asset condition is not observed. A version label alone is insufficient provenance. |
| Entry-app transition overlaps payload initialization | [Autoloader changelog](https://github.com/kam821/ps5-y2jb-autoloader/blob/af99f18a604716f3ba23778a6e66801156a476fb/CHANGELOG.md), [unified main.c](https://github.com/itsPLK/ps5-unified-autoloader/blob/8e9684689f1d379a4bb7a785189f2c3da9274973/src/main.c), [app_killer.c](https://github.com/itsPLK/ps5-unified-autoloader/blob/8e9684689f1d379a4bb7a785189f2c3da9274973/src/app_killer.c) | The implementation closes entry applications before subsequent payloads and delays transitions. This supports lifecycle/order investigation. Our preflight observed no native app, but that does not prove all system transitions were finished. Do not transplant the external forced-kill sequence. |
| Corrupted return/trap state | [CR0 fallback fix2156fd1](https://github.com/EchoStretch/kstuff-lite/commit/2156fd18caa7715a430ef133d623f85eea24fba1), ps5-kstuff/uelf/utils.c: write_cr0_preserving_trap_frame_checked | A synchronous fallback could replace the completed outer trap frame. The fix preserves/restores it. This commit is an ancestor of the pinned85fb source (57 commits behind); its code is present in the local source. It is not a newly discovered missing source patch. Source-to-release reproducible equivalence remains unproven. |
| PPR key and mount lifetime | [Cleanup35472f7](https://github.com/EchoStretch/kstuff-lite/commit/35472f79ff4d159107caec8926c06d2484505b47), [lifecycle533cb86](https://github.com/EchoStretch/kstuff-lite/commit/533cb862d89dd4870d2d9ffa72bc1e63c5cff785), [ShellCore scope41b6692](https://github.com/EchoStretch/kstuff-lite/commit/41b66927adc550d30107f97369553e2274225626) | Resource release and interception scope are relevant to the first post-PFS stop. Classic savedata PFS and plaintext PPR are different paths; these fixes do not establish which ran at the first stop. The lifetime mechanisms belong in the audit, not an assumed causal explanation. |
| Launch-context mismatch | [Issue98](https://github.com/EchoStretch/kstuff-lite/issues/98), [fix4c53baf](https://github.com/EchoStretch/kstuff-lite/commit/4c53baf274b149f1814531731bcb6db59cd5ee8e) | A supplied title ID was overridden and a PS4 process crashed. A live patch prevented the reproduced startup failure during a60-second observation. It is an application-launch case, not proof about a kernel initializer that never returned. |
| Closing an app triggers a system panic | [Issue80](https://github.com/EchoStretch/kstuff-lite/issues/80) | Reporter observed failure with1.11 and successful closure with1.12-fpkg-dr-test9. This is a useful lifecycle regression comparison, without a proven single causal commit. Do not present the alternative build as qualified on this console. |
| Multiple independently reported hard failures | [Issue101](https://github.com/EchoStretch/kstuff-lite/issues/101), [Issue95](https://github.com/EchoStretch/kstuff-lite/issues/95), [Issue102](https://github.com/EchoStretch/kstuff-lite/issues/102) | Reports cover initialization and application startup, including loss of klog output. Symptoms alone cannot assign a common cause. ShellUI trophy-worker errors in95 are not evidence that our omitted worker ran. |

The official v1.11 asset was replaced on2026-09-23 after its original release
publication. Its current1737080-byte SHA256 is
ab9a6cb4d3b1daf139d4d646e402b1cf569071acd64599c936d7a3a6164dc779,
matching our archived ELF. Keep the distinction between release asset bytes,
the85fb source reference, and a reproducible build. The embedded public PLD is
intentionally not a standard ELF-magic file (lib/frankenelf.py); a generic
readelf rejection is not corruption evidence.

The complete upstream85fb..aaf921e diff contains three changed files:
prosper0gdb/offsets/12_70.h, ps5-kstuff/main.c and
ps5-kstuff/shellcore_patches/13_60.h. The common main.c change enables package
hooks on development/test kits. No general retail initializer recovery fix was
found in that diff. This conclusion follows from branch conditions and source
differences, rather than excluding reports by firmware.

Following Issue80 to the author's fork, the current drakmor1.12 branch is
[e3cca8d](https://github.com/drakmor/kstuff-lite/commit/e3cca8de402f28c19e1976f0a03064e1f4ac71cd).
Git blob identities are equal to85fb for the entry/bootstrap headers, r0gdb.c,
uelf/utils.c, uelf/fpkg.c, uelf/syscall_fixes.c, loader main.c and the import
resolver. The kernel main.c differences concern kit hook eligibility and the
welcome string. Thus the version name alone does not identify a new common
kernel-entry repair. The historical test9 binary from the report is not
qualified here; the current fork source comparison is not a binary equivalence
claim for that historical build.

## New persistent logs

Capture62500 acquired the latest bounded platform log and two newly listed
system-title error records. One records0x80020008, matching the earlier OS
launch rejection; the other records0x80ba0013. Neither provides a kernel stack
or demonstrates a faulting initializer instruction. The platform log adds
startup, an orderly reboot entry, then another startup after the reported
abnormal event. Do not generalize the earlier boot's lack of an orderly
shutdown entry to this latest complete capture.

## Cause status and implementation consequences

The second failure is bounded by BEFORE upstream_kernel_entry and the missing
RETURN/ready END. The first failure followed native return, ordinary view
unmount and restoring renames, during complete file readback. A common cause
has not been established. Current prerequisite success does not change that.

1. Retain separate investigations for kernel-entry progress and filesystem
   lifetime. Audit low-level write/return state as well as competing consumers.
2. Preserve the actual source/binary/SDK and entry-context identities. Do not
   substitute a similarly named version, guessed address or emulator stub.
3. Before another initialization, require a documented implementation correction
   or source-backed prerequisite change. A fresh boot or an external report
   alone does not explain the failure. Original upstream initialization before
   database/UI/mount monitoring supports testing order as a hypothesis; the
   alias-order difference is not a proven cause or guaranteed repair.
4. If kernel-entry execution is reopened, persist individual progress boundaries
   for bootstrap setup, allocation, per-core handler installation and ShellCore
   integration, including actual return/error status. Establish that logging
   itself is valid at each low-level stage before deploying instrumentation.
5. Keep draft PR85 outside production. Its runtime-ready guard addresses the
   confirmed unnecessary launch attempt; its direct-PFS lifetime protocol remains
   host-built and unqualified on hardware.

No new initialization request, driver change, deployment or CI run occurred in
this audit. No acceleration was adopted. CPU entropy Kraken remains measured
ineffective; hardware Kraken, direct PFS execution and AMPR read/batch timing
remain unperformed. This report does not mark the full hardware campaign done.

Private evidence: post-initializer-readonly-62420,
initializer-readonly-62470, post-initializer-platform-62500. Raw logs, endpoints,
process addresses, proprietary modules and detailed execution receipts remain
private. The driver remains872cc126/cumulative-idle with persistent caches off.
