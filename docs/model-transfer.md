# Original-model transfer preparation

The complete original checkpoint must finish SHA verification, bounded BF16
conversion, independent full-payload auditing and every final GGUF hash before
`tools/plan_model_transfer.py` can produce an offline plan. It compiles and uses
the actual native `model_receipt.h` gate, checks the frozen six preparation
sources and complete copy-adapter provenance, and pins local file identities.
The plan uses one upload connection and includes a separate 32 GiB storage
reserve. Planning performs no console access, model evaluation or GPU work.

`tools/storage_capacity.py` parses only the unique expected `/data` filesystem
row from a bounded, completed CPU capture. Human-readable quantities use decimal
units with one displayed quantum subtracted, conservatively allowing for unit
choice and rounding. The original payload, receipt and 32 GiB reserve must fit
that lower bound. The parser does not prove command completion or freshness;
the coordinator must bind both separately. A preserved historical capture
parsed successfully, but is not fresh admission for a later bulk transfer.

`tools/model_transport.py` provides the per-file transport operation. The
coordinator must first admit a fresh unchanged idle session, the shared console
reservation, current capacity and an owned destination directory. It must hold
one OS writer lease for the entire batch and set bounded FTP socket timeouts.
The module alone is not a console execution command or a complete batch uploader.

`tools/model_transfer_batch.py` sequences the complete batch with one OS writer
lease. It checks fresh completed capacity before each new file, records bounded
progress, and publishes the original receipt only after every file has positive
transfer records. An explicit resume reuses only positively recorded files with
matching remote sizes. Any uncertain file/publication attempt is refused before
another write; immutable failures and partials remain available for review.
The original whole-batch deadline and host clock continuity survive resume.

`tools/transfer_model.py` supplies the outer private admission. It rechecks the
actual compiled native receipt gate, frozen conversion provenance, completed
original restoration, shared reservation, fresh unchanged CPU evidence and a
separately prepared owned model directory. Default invocation validates locally
without opening a connection; `--execute` additionally requires every private
admission. The directory-preparation proof and full original model are not yet
available, so no bulk model transfer has been admitted or started.

Each new file receives an immutable attempt record before its first write and
uploads to a nonce-specific partial path. Sequential reads use at most 1 MiB;
their complete SHA256 must match the original receipt. Stable file identity,
positive FTP 226, exact remote size and native-readable file mode precede one
rename. Positive FTP 250 and final size precede the local transfer record.
Failure retains remote data and durable failure evidence. An existing attempt
cannot be repeated automatically, including an ambiguous transfer or rename.
No remote deletion or existing-file overwrite is implemented.
The console FTP service supports directory listings, so permission checks use
one bounded parent-directory listing and select the exact partial basename.
Unrelated entries cannot satisfy the file check; a file-directed `LIST` is not
used. This preserves the regular-file/world-readability requirements.

`tools/ps5_model_connection.py` confines metadata reads to the owned model
directory, checks management service identities and absence of native owners,
and performs only the advertised read-only `df` plus a fresh echo marker for
capacity. Capture size, connect/prompt/command waits and socket waits are bounded.
The exact prompt-prefixed echo output is accepted; an echoed command cannot
prove completion. A distinct read-only physical probe passed service/capacity
checks after the first strict parser refused that output format. The refused
capture remains preserved. Neither probe uploaded a model or launched a title.

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
Batch sequencing tests explicitly stub the full-model gate to inject failures
using tiny synthetic files. They do not manufacture a real successful model
receipt. The actual gate separately rejects marked fixtures before any batch
or connection can start.
