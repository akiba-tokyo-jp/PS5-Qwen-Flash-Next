# FTP publication response and reviewed first-file continuation

The first original GGUF split transferred 3,508,767,456 bytes. Before publication,
the uploader passed positive FTP 226, complete source-stream SHA256, unchanged
source identity, remote partial size and regular/readable metadata checks.
`FTP.rename` then returned normally, but the application required literal 250.
The Python client's normal return already requires a 2xx completion. The old
application did not persist the exact reply before rejecting it.

A bounded read-only review found the exact published filename, expected size and
readable regular-file mode, with positive HTTP 404 for the old partial path.
The original failure, traceback, intent and byte-identical old uploader source
remain preserved. No file data or rename command was repeated. This review does
not claim that the unrecorded reply was 250 or that native SHA has already passed.

Future file and receipt publication accepts a bounded positive FTP completion
class, then independently checks the published size/full receipt readback and
positive partial-path absence. File upload checks remain unchanged. Completed
upload facts and the raw rename reply are now persisted before later checks.
Nonpositive, ambiguous or inconsistent outcomes still stop without retries.

The reviewed first-file record explicitly reports `FTP_250=false`, an unknown
exact reply, and the bound independent review. Resume admission verifies the
review's original file/destination/facts and digest, then rechecks actual remote
size and readability before skipping that file. It never treats an uncertain
intent alone as completion. The original whole-batch clock and deadline are
preserved when continuing the remaining 75 files.

Twenty-nine file/batch protocol and failure-injection tests passed, including
positive 200 replies for payload and receipt publication, retained partials,
negative or ambiguous rename, altered reviewed proofs and no uncertain resend.
These are protocol checks, not physical full-model quality or throughput results.

Data continuation 007 can reuse the original plan, positive directory proof and
reviewed first file. The finite full-plan continuation waits for its positive
completion and exit before preparing the unchanged physical case 019. Independent
native destination SHA, memory/load/generation, passive display and every exact
original restoration/readmission result remain pending.

The next physical file completed with the recorded reply `226 Path renamed`.
Its complete source SHA, published size and positive partial absence passed the
corrected checks; the first file was not resent. The data and full-plan processes
were both observed active. See `model-transfer-checkpoint-20261023.json` for this
sanitized checkpoint. The first file's exact old reply remains unknown.

The fourth file, the 102,400,491,712-byte PLE container, subsequently completed
with the same recorded positive 226 rename reply, complete source-stream SHA,
unchanged source identity, exact published size and positive partial absence.
The first four files account for 112,858,638,848 positively completed transfer
bytes. Transfer continued with file five. Independent native destination SHA,
model load, inference and original-title restoration remain pending; these
transfer results do not establish those later outcomes.
