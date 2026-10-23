# Native integrity completion and public mapping linkage

The physical case 020 completed SHA256 verification of all 76 original model
containers, 359,246,956,672 bytes, in 5,370,082 ms. All hashes matched. It then
recorded `model_mapping_before_open`, without a completed mapping admission.
The native process was subsequently absent. No Vulkan/backend initialization
or model load was reached. The exact terminating call and signal are unknown.
A fresh CPU observation passed with the same boot/services and no native owner.
No ordinary-close request was sent after that already-completed process exit.

The failed title defined `mmap` from the SDK's static `mman.o`, which directly
executes a payload-context syscall. The corrected application removes exactly
that member from a separate SDK archive copy, preserving every other member
occurrence. The original SDK is unchanged. The native `mmap` symbol must now
resolve to the real public `libkernel.sprx` provider. This fixes a concrete
linkage defect; it does not establish the previous process's exact failure cause
or prove that full-file mapping is supported by the native title.

The new 58,605,367-byte SELF has SHA256
`7b83ea8945851e826eaa66a070db72e652154b2def11adda446b6ec2338571cd`.
Its six segments roundtrip correctly, all 290 actual module imports resolve,
and `mmap` resolves to `libkernel.sprx`. The driver remains revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, native
archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. The relink/package receipts
retain the source, filtered SDK archive and actual provider provenance.

To avoid repeating the 89.50-minute native payload hash pass, a read-only CPU
controller verified the original sealing log and native integrity report,
then captured the identities of all 77 root-owned mode-0644 model/receipt files
and their directory. Their identity/timestamp evidence remains unchanged since
sealing, before the complete native hash pass. The next native candidate accepts
the exact prior report only with its bound raw SHA, matching receipt/start record,
and fresh full file/directory identity checks. This assumes the task's controlled
writers and protected files; metadata does not defend against a malicious root
actor forging timestamps. The model writer lease remains held during execution.

The native evidence validator passed 14 host checks, including digest, ownership,
size, namespace, inode uniqueness, timestamps and deadlines. The mapping policy
passed its completed-cleanup and no-retry failure-retention checks. Seven focused
result-reconstruction tests passed, including explicit reused-integrity metadata
and deadline failures. A reused report clearly identifies the prior payload hash
duration and the current metadata-only validation duration.

Case 021 is a distinct attempt with the corrected SELF and a fresh run identity.
It still requires successful mapping, source I/O, measured memory admission,
full original-precision load, arithmetic smoke, two fixed external requests,
passive display/clock evidence, positive GPU completion/retirement, ordinary
close, exact original restoration, numerical readmission, another ordinary close,
fresh final CPU guards and full original SELF readback. The two actual saved TV
frames must be viewed before the overall plan is declared complete. The original
SELF remains preserved in its original backup until those restoration steps.
Host checks do not establish successful full-model inference or a token rate.
