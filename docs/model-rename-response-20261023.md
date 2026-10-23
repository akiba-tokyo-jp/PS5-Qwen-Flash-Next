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
