# Bounded Direct input for launch integrity

The full native candidate still refused before model metadata and Vulkan at
2,338 free kernel pages against its unchanged 2,974-page target. Its prelaunch
observation was 7,400 pages. Ordinary OS close, exact original restoration/full
raw readback, fresh idle CPU and all 412 frozen inputs passed. This is not an
inference or throughput result.

The ordinary launch controller still used buffered reads for full SHA256 checks
of the executable, libraries, mounted copies and metadata. Original preservation
also reread the 107,911,351-byte original executable through the management file
server immediately before rename. These inputs deserve separate measurement;
a process VM map alone does not establish their cache residency.

`native/qwen_flash_next/launch_integrity.h` implements a serial aligned input
stream with one 1 MiB window, 16 KiB alignment, bounded file length/deadline,
exact returned bytes and an explicit final block for EOF. Every read has durable
before/returned markers. Short, oversized, failed, late or invalid results
quarantine the stream without retry. The native adapter verifies `O_DIRECT` via
`F_GETFL`, retains the current whole SHA256 and stable descriptor/path identity,
and checks the unchanged kernel minimum plus reserve before every new read.
It does not request cache reclamation or change any mapping.

`tools/build_launch_integrity.py` replaces only the original controller's digest
input function. Its boot, service, registration, title, mounted-inode, owner,
claim and done-marker code remains textually unchanged. Build receipts bind the
original controller, actual headers, compiler, retained CRT, generated source
and real import providers. A separate CPU-only qualification main has no title
launch/close, GPU, target-memory or mapping imports. Preparation snapshots remain
immutable when the enclosing publication plan later advances.

Host controls cover aligned and unaligned lengths, exact EOF, refusal before a
read, failed markers, negative/oversized/short results, timeout, failed consumers
and replay rejection. PS5 compilation and actual module import audits passed.
The physical CPU qualification verified the complete original executable SHA256
in 1,040,491,313 ns, with the Direct flag set and all 108 reads returned, including
fresh-session validation. Fresh idle guards before and after passed with the
same boot/services and the original executable unchanged. No title or GPU ran.

Its immediate free-page observations were 7,151 before and 13,738 after the
original-file read. This is one measured interval, not proof of a particular
kernel cache implementation, stable available capacity or inference speed.

A distinct complete sequence may use this same qualified input implementation
for current original preservation before rename and for launch integrity. Stage
the exact fresh session once, retain its full native SHA256 guards thereafter,
and keep distinct log journals without changing claim/done ownership. Require
positive helper completion and every read return before publication continues.
Unknown completion retains files and prevents launch. Candidate full raw
readback, both native 2,974-page gates, current 76-file reservations, original
BF16/F32 weights, all experts/PLE, driver/cache policy, all requests and native
frames, GPU retirement and full original restoration/readmission remain required.
