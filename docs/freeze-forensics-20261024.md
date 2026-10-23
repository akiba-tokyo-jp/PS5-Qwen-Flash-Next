# File-mapping freeze: evidence, limits and recovery

The owner confirmed that the console had frozen and restored it by disconnecting
power and restarting it. Case 023 did not complete inference or ordinary close.
An HTTP management response was insufficient evidence of console interactivity.
The failed candidate was not executed again during this investigation.

## Findings supported by the saved run

| Observation | Interpretation and limit |
| --- | --- |
| All 76 sealed identities passed in 346 ms using the prior complete native SHA result | This was metadata reuse in the preceding boot, not a new full payload hash |
| Last durable stage: `model_mapping_before_public_mmap`, zero completed mappings, model and GPU initialization not started | The failure boundary is before backend/model execution |
| First file: 3,508,767,456 bytes, about 3.27 GiB | The first native regular-file mapping attempted a large range without a preceding tiny native file-mapping qualification |
| Frozen native owner and the additional loader candidate each had one thread with wait description `pfault` | Both were waiting in the VM fault path; the additional process's exact executed helper is not proved |
| No `.failure`, `.fatal`, mapping-completion or backend-start record | No application-handled exception, backend abort or completed mapping was established |
| One ordinary-close transport timed out before HTTP response headers | Helper entry, OS close invocation and acceptance remain unknown; no retry was sent |
| Postboot stage file is byte-identical to the pre-power-cycle capture | No later durable application stage was found |

The preserved candidate SELF is SHA256
`d30e49933c358cd11f46a2aa499c3b517577b8c10b528b3455eb6a0203ae7733`.
Its wrapper was disassembled from the matching preserved link image. The call
uses a 64-bit length, `PROT_READ`, `MAP_SHARED`, the file descriptor and offset
zero. ELF relocations identify imported `mmap` and then `__error`. The static
provider audit identifies `libkernel.sprx`; the old SDK static `mman.o` definition
is absent. No length truncation or argument-register mismatch was found.
This checks static linkage and the call site, not a captured runtime instruction
pointer or the firmware's internal implementation.

The wrapper reads `errno` after `mmap`. The outer policy then checks its deadline
before writing the return stage. Consequently, the missing return stage cannot
prove that the CPU was still inside the syscall: the import call, error access,
deadline handling and subsequent journal path are not separated by the saved
trace. There is no frozen instruction pointer, fault address or kernel stack.

## Leading mechanism and demonstrated design defects

VM free-page allocation starvation near the first regular-file mapping is the
leading hypothesis. In the corresponding
[FreeBSD implementation](https://github.com/freebsd/freebsd-src/blob/releng/11.0/sys/vm/vm_page.c#L2624),
`vm_waitpfault` sleeps on the free-page counter with wait description `pfault`.
This explains the saved wait descriptions and is consistent with a second
process failing to finish startup. The PS5 kernel is modified; that reference
does not independently prove its exact implementation or the exhausted pool.

Source order and bounded postboot counter reads establish three concrete
admission defects:

1. The first file-backed mapping was approximately 3.27 GiB. No tiny, completed
   native file-mapping prerequisite had established its commitment/quota behavior.
   Disabling prefetch did not prove that this native mapping was harmless.
2. The complete model/OS memory admission was after mapping. The source and
   expert-cache limits therefore did not protect this earlier platform operation.
3. The OS reserve query uses `vm.stats.vm.v_free_count` and
   `vm.stats.vm.v_page_size`. Both returned unavailable on the actual firmware.
   The PS5-specific `vm.stats.vm0.v_free_count`,
   `vm.stats.vm0.v_inactive_count` and `hw.pagesize` were readable. These are
   domain counters, not a proven replacement for process-available RAM. The old
   unsupported query would have rejected admission if reached; it was not a
   false positive memory reading and is not independently the cause of the
   earlier freeze.

The application now invokes its existing strict CPU/OS budget gate before the
first virtual-source probe or range admission. Missing counters therefore reject
the run before that OS operation. No reserve threshold or memory interpretation
is relaxed. This safeguard does not make the unsupported telemetry usable:
correct native-context memory accounting remains a prerequisite to enabling
inference. The earlier host-qualified reserved-source SELF predates this added
gate and remains withheld from physical use.

The guarded replacement compiled and linked against the unchanged seven source
overlays and pinned driver. Its 58,628,631-byte SELF has SHA256
`82b73be97f0e7123b59e44e01ce6e79d04a59e15d92e88e720c34ffed2d8fada`.
All six segments roundtrip and the static public-module import audit resolves
291 imports with none missing. Both committed-policy checks pass. This is a
host build only: it has not been deployed, and the unsupported memory telemetry
still prevents native source admission. No model or GPU test was repeated.

The 60-second deadline was checked around the call, not enforced inside it. It
could reject an eventual late return but could not interrupt a blocked kernel
operation. Likewise, a management GET did not prove that the foreground UI or a
new close helper could run. These limitations were material to this failure.

Whether pages were exhausted by the mapping itself, by the native flexible-memory
quota, an earlier allocation or a kernel reclaim problem remains unproved.
No frozen-boot free/active/inactive/wired counters, commitment measurement or
kernel stack were captured. GPU compute, expert eviction and numerical model
execution had not been reached and are not supported as the immediate cause.

## Additional log inspection

The postboot kernel ring contained 131,072 bytes from the current boot. It cannot
replace the lost frozen-boot ring or prove that the preceding boot had no fault.
The inspected persistent error history ended before case 023's native start;
its four latest entries concerned a different system title and `CE-105773-3`.
Those entries were not attributed to this freeze. The app-log directory was
empty and the checked crash-report path was absent.

Raw logs, process identities, addresses and system error records remain private
outside Git. The offline correlation receipt freezes their hashes together with
the candidate, disassembly, source order and restoration evidence.

## Recovery and execution status

Fresh CPU discovery verified a different boot and no native owner. The optional
native compatibility runtime was not loaded. A distinct recovery-only CPU guard
checked firmware, boot identity, seven exact management/system process identities
and no native/foreground title twice. Its 14 imports resolved in the existing
public module audit. It performs no title launch/close, GPU work, runtime load,
model payload read or file mapping. This limited recovery scope does not relax
the complete runtime/model admission or authorize inference.

The failed SELF was retained under a distinct name. The exact original
107,911,351-byte SELF was restored from its preserved backup; complete raw
readbacks before and after restoration matched SHA256
`2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d`.
The failed candidate's complete readback also matched. A new recovery CPU guard
then passed in the same new boot, with no native owner. No original numerical
readmission has run in this boot. The old close remains unknown rather than
being reclassified as accepted because of the power cycle.

File-backed model mmap remains prohibited. The replacement reserved-source SELF
has not been deployed or run. Its new virtual-memory APIs still require an
isolated, tiny, model-independent native qualification, with memory observations
before the call and explicit entry/return/completed-release evidence. A deadline
observer must never be described as cancellation of an opaque kernel operation.
Previous same-boot SHA-reuse bindings and service/owner/session admissions are
invalid for the new boot. Rebinding their outer session is insufficient to
revalidate the old integrity evidence. Conversion and transfer need not be
repeated merely for this forensic investigation.

The driver pin, `cumulative-idle` profile, disabled persistent caches, original
precision and all experts/PLE requirements remain unchanged. Native inference,
two external requests, frame review, numerical admission and final ordinary
shutdown/restoration remain outstanding. The full plan is not complete.
