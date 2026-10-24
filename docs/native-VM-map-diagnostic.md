# Bounded native application VM map diagnostic

The current application can verify immutable original shaders and complete its
CPU reservation rehearsal, but its separate full startup still refuses the
stronger kernel-page target before model metadata. VM placement metadata helps
identify which application regions merit further investigation. Virtual extent,
reported resident pages and system-wide free pages are separate measurements.
Shared mappings may also refer to the same physical pages; do not sum these
records into available capacity or use them to lower an admission predicate.

The primary [retail PS5 example by psxdev](https://gist.github.com/psxdev/f7a935d82bea88db75d6430d757f5099)
uses `sysctl` with `CTL_KERN, KERN_PROC, KERN_PROC_VMMAP, pid` and reports packed
144-byte records. The SDK defines the fixed 136-byte `kinfo_vmentry` prefix followed
by a variable path. The parser accepts bounded packed records, including empty
paths, and verifies record length, total input, ordering and complete path bounds.
It does not dereference target addresses or read process memory contents.

`tools/build_vmmap_probe.py` builds the standalone helper from the already
qualified credential-preserving CRT and manual controller recipe. It checks the
actual parser/query paths, compiles against the SDK layout and audits actual
strong module providers. The build requires the qualified `sys/priority.h`
overlay and asserts the measured 1,096-byte process ABI; the unmodified SDK
alone produces 1,088 bytes and must be refused. Its receipt binds the compiler,
CRT objects, actual include graph, module providers and generated context.
The helper has no title launch/close, GPU, `mmap`,
`mprotect` or `ptrace` imports. Generated boot/nonce headers, binaries and raw
evidence remain outside commits.

The finite CPU controller first proves that every native source call returned
and that the title reached a CPU-only terminal state. The helper binds its exact
PID, start time, application identity, title and boot before and after the query.
It issues at most one size query and one data query, with a 1 MiB cap, 4,096-record
limit and 64-byte canaries. Unsupported queries or layouts are recorded without
retry or interpretation. No mapping, cache, source or memory-admission state is
changed by this diagnostic.

Ordinary close requires positive helper completion, matching durable call
markers and the unchanged owner. An uncertain query keeps the title and backing
retained. The controller subsequently verifies exact original restoration and
fresh idle CPU. Host parser/query fault controls and native import checks have
passed. The physical diagnostic subsequently completed both metadata calls,
parsed 188 records from 27,072 bytes, and confirmed the exact owner again. Ordinary
OS close, exact original SELF restoration with full raw readback, and fresh final
idle CPU guards passed. The same-boot original numerical evidence was preserved;
this CPU-only diagnostic did not perform a new original GPU admission.

The largest reported region was 17,146,314,752 bytes with protection 0 and raw
resident 0. It is a virtual reservation, not evidence of resident capacity or
permission to release it. All addresses, identities and raw records remain private.

The retained title also completed all 76 current source reservations/releases.
Its diagnostic free-page samples were 3,170 before, 3,159 after and 3,155 after a
matched two-second idle. These are observations, not a replacement for either
mandatory 2,974-page full-startup gate. Current external resource SHA256 and 382
lookups passed, with current 0/prior 1,527 shader-byte evidence; each used module
still requires its current full original SHA256. Full inference and improved
tokens/s remain unqualified.

The initial fresh helper attempts refused their own process-size check because
the permission-controller build recipe omitted the qualified ABI overlay. They
returned without a VM query. A later, size-correct helper returned before its
first VM query; its original log did not identify the failed prerequisite. The
instrumented successor logged credentials, boot, headroom and owner results,
then completed the two queries. No failed or unknown operation was replayed.
The original service guard was preserved when a fresh owner observation followed
the refused immediate post-launch observation. The historical failed service
field remains unidentified; the later exact fields matched the baseline.

Neither host checks nor VM map size alone qualifies full-model memory or
inference throughput.
