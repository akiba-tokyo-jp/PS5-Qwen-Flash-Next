# Original-model transfer preparation

The complete original checkpoint must finish SHA verification, bounded BF16
conversion, independent full-payload auditing and every final GGUF hash before
`tools/plan_model_transfer.py` can produce an offline plan. It compiles and uses
the actual native `model_receipt.h` gate, checks the frozen six preparation
sources and complete copy-adapter provenance, and pins local file identities.
The plan uses one upload connection and includes a separate 32 GiB storage
reserve. Planning performs no console access, model evaluation or GPU work.

`tools/model_transport.py` provides the per-file transport operation. The
coordinator must first admit a fresh unchanged idle session, the shared console
reservation, current capacity and an owned destination directory. It must hold
one OS writer lease for the entire batch and set bounded FTP socket timeouts.
The module alone is not a console execution command or a complete batch uploader.

Each new file receives an immutable attempt record before its first write and
uploads to a nonce-specific partial path. Sequential reads use at most 1 MiB;
their complete SHA256 must match the original receipt. Stable file identity,
positive FTP 226, exact remote size and native-readable file mode precede one
rename. Positive FTP 250 and final size precede the local transfer record.
Failure retains remote data and durable failure evidence. An existing attempt
cannot be repeated automatically, including an ambiguous transfer or rename.
No remote deletion or existing-file overwrite is implemented.

A successful transfer record explicitly says `native_SHA_verified=false` and
`awaiting_native_SHA_admission`. Source-stream SHA plus remote size does not
prove remote payload integrity. The later bounded native CPU model preflight
must independently hash every console file before mapping or GPU/model load.
There is no full-model transfer, mapping or inference result yet.

Focused host fault injection covers success, concurrent writers, invalid names,
existing files, changed source bytes, unreadable output, deadlines, missing
completion responses and ambiguous transfer/rename outcomes. Preparation tests
reject incomplete phases, metadata fixtures, incomplete hashes, altered frozen
sources and incomplete adapter provenance. These tests use synthetic bytes and
metadata only; their results do not establish console transfer performance.
