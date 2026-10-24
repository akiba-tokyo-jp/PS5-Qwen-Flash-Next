# Fresh-boot original-model validation

The recovery-first memory prerequisites are complete: native telemetry, 16 KiB
reservation/protection/release, direct I/O through 8 MiB with four prefix hashes,
normal close after every phase, and exact original restoration/readmission/close
with final CPU and full SELF readback. See
[native memory qualification](native-memory-qualification-20261024.md).

The distinct full-model case uses the scoped-admission SELF
`e51cb5646355f37f9010143585216c4d1877a8480c49ff4c0947318895e337b7`.
Fresh complete CPU, current-boot service/owner and clock admission passed before
the one ordinary title launch. The exact original and preceding configuration
were preserved and fully verified. The app's actual native pre-integrity gate
passed with 16 MiB CPU heap mapped, zero libc fallbacks, 404,750,336 Flexible bytes,
and 2,556 kernel free pages at 16,384 bytes per page. The kernel minimum/target/
reserved counters were 898/2,974/206. Inactive pages were not counted.

The PS5 completed SHA256 verification of all 76 original-precision files,
359,246,956,672 bytes, in 5,408,068 ms. Every digest matched the complete
converted receipt. This is a new-boot native result; the previous boot's proof
was not reused. Model conversion and transfer were not repeated.

The subsequent tiny 16 KiB reservation/protection/release passed. Three source
ranges of 3,508,781,056, 3,512,991,744 and 3,436,396,544 bytes were reserved and
their zero protection verified. The fourth reservation, 102,400,507,904 bytes
for the large PLE file, returned `-2147352564`. All five reserve calls,
including the tiny probe, returned. The app saved its exception and entered the
bootstrap's `native_main_returned` terminal hold. File-backed mmap, backend
initialization, GPU work, model loading and external generation were not reached.
This returned reservation rejection is separate from the earlier unreturned
file-backed mmap and owner-confirmed freeze.

Immediately before virtual-source admission the native CPU heap was 32 MiB
with zero libc fallbacks, Flexible availability remained 404,750,336 bytes, and
kernel free pages were 1,926. The scoped pool/kernel predicate passed. These
measurements do not establish the largest available virtual address interval or
the title's process virtual-memory limit; those require separate observation.

The exact failed owner was then normally closed once. Fresh complete CPU guards
passed before and after restoring the original SELF with full raw readback.
The original subsequently passed its existing numerical gates, ordinary shutdown,
final complete CPU guards and a second full SELF readback. No native owner
remained. No uncertain close was retried and no resource was manually released.

A new read-only sealed-identity snapshot checked all 77 model/receipt entries
twice, their unchanged directory, sealing evidence and this boot's complete
native integrity report. Every timestamp and identity gate passed between fresh
CPU guards, without model payload reads, mappings or permission changes. This
preserves the expensive current-boot SHA proof for a later case; it does not
reuse old-boot owner/session state or qualify a different reservation method.

The finite controller retained one source/artifact binding and stopped at the
returned rejection. After corrected native virtual-source admission, remaining requirements are
original-precision model loading and generation, two external requests, saved
native frame review, positive resource retirement, ordinary close, exact original
restoration, numerical readmission, ordinary shutdown and final CPU/full SELF
readback. Unknown or failed operations are retained for review without retry,
force-kill, GPU reset or speculative cleanup. The failed case and subsequent
guarded restoration remain separate records.

No full-model tokens/s, answer quality, resident-memory qualification or overall
completion is claimed by this checkpoint. The private repository, disabled
Actions, pinned `872cc1264ad8ba5d6b888b092968fa5858a38c58` / `cumulative-idle`
driver, disabled persistent caches and disabled committed deployment/release
controls are unchanged.
