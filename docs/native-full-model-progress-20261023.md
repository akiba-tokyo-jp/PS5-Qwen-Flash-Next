# Native full-model verification checkpoint

All 76 original-precision GGUF containers, totaling 359,246,956,672 bytes, and the
complete v2 receipt have positive transfer completion. The source-stream hashes
matched the completed conversion receipt. This is separate from independent
native destination integrity, model loading and generation.

Case 019 retained its local pre-publication failures. The first failure was an
exclusive writer incorrectly used for mutable local state; a distinct private
controller preserves each transition and atomically updates that state. A
subsequent guard compared FTP metadata with raw SELF sizes. A fresh CPU diagnostic
read only 64 bytes from each existing executable and confirmed raw descriptor
sizes and seek endpoints of 107,911,351 and 58,586,023 bytes. FTP metadata instead
reported 108,537,048 and 59,114,504. Full raw readbacks matched both expected
SHA256 values. Only the host metadata check changed; the native candidate was
reused. No failed or uncertain SELF rename was repeated.

The first native attempt then failed its pre-backend file-permission admission.
Its ordinary close and the subsequent successful plan-bound permission completion
are recorded in [the file-sealing report](model-file-sealing-20261023.md). That
failed attempt does not establish generation or model residency.

Case 020 uses a fresh run identity with the same sealed candidate:
`b380e755daf7ecfa3b10a46ed3aefc867bca80d5917d831d1815262f18f4bfc0`.
It reuses the already preserved original SELF backup, with fresh complete raw
readbacks of the candidate and original backup. A new unchanged CPU session and
clock calibration preceded the new launch. No model transfer, application build
or successful SELF publication was repeated.

At 14:55:40 UTC on 2026-10-23, native integrity progress reported file 4 of 76,
21,665,327,424 of 359,246,956,672 bytes processed, and 323,992 ms elapsed. The
whole-model verification deadline remains 7,200 seconds. This is partial progress,
not a claim that every destination hash passed; backend initialization and model
loading had not begun at this checkpoint.

The native stage journal has an existing 8 MiB capacity. Its approximately 5,400
whole-model progress records can exceed the old observer's 1 MiB GET bound.
The stage reader now uses the same 8 MiB bound; other report and frame limits
remain separate. Before any external generation or finish POST, the old host
GET-only observer was positively ended and its immutable records preserved.
The same native owner and integrity work continued. The new observer retains
the original observation start conservatively, without resetting either deadline.

Full-plan continuation 047 freezes 177 source/proof records and will continue
through actual load/memory admission, the arithmetic request, two fixed external
requests, passive display capture, positive retirement, ordinary close, exact
original restoration, numerical readmission and final idle/readback checks.
Final display legibility still requires visual review. No full-model tokens/s,
answer-quality result, final restoration or full-plan completion is claimed here.
