# Reviewed continuation after a Windows uploader interruption

The uploader ended with Windows status `0xc000013a`, without a Python exception
or positive file completion for split 35. The actor that caused the interruption
was not established. The parent retained the failure and the full-plan waiter
stopped before case creation, title launch or GPU execution.

The first 34 files have positive source-stream SHA, FTP completion, published
size and readable regular-file records, totaling 216,633,567,072 bytes. A bounded
read-only review found the exact expected model directory and an unchanged
3,341,876,428-byte partial for the 3,355,443,456-byte split 35. Its source identity
was unchanged; its final destination was positively absent. No successful file
was resent and no uncertain prefix was appended.

The incomplete partial was preserved outside the active model directory.
Publication returned `226 Path renamed`; FTP SIZE and independent bounded parent
directory metadata confirmed the retained size, root ownership and readable
regular-file mode. Both the old partial path and final model path were positively
absent. The directory listing contained 4,584 entries within its explicit bounds.
The successful rename was not repeated. This preservation verifies metadata,
not the incomplete file's content hash.

The first preservation destination was refused with FTP 550. The subsequent
destination used the existing CPU-helper staging area. Its successful move was
followed by a protocol-check failure because this server's LIST command accepts
directories rather than individual files. Independent directory metadata then
resolved publication without another mutation. The retained file's actual mode
was `0777`, which satisfies the existing regular/readable-file contract; an
initial diagnostic's exact `0644` assumption was rejected. Every prior intent,
failure and positive response remains preserved.

Detached Windows parents remain bounded. Long-running children now explicitly
use `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`. A local qualification in the
same detached-parent context observed a zero console window and child exit zero.
Adding a child breakaway flag was refused before any console request; that
failure is retained. Five simulated preservation checks covered success,
unchanged-size admission, existing destinations, negative replies and refusal
to repeat an existing attempt. Those checks made no console requests.

Data continuation 011 reuses all 34 positive file records and the completed
preservation proof. Split 35 has one explicitly reviewed new upload attempt;
automatic retries remain disabled. The original whole-batch identity, clock and
deadline are unchanged. The incomplete old bytes remain retained separately.
Full-plan continuation 029 waits for positive data completion and process exit
before the unchanged, unused physical case 019. The sealed application and
driver were not rebuilt for this continuation.

Independent native SHA of the complete active model, physical memory/load and
generation, two API/display measurements, ordinary shutdown and every original
restoration/readmission gate remain pending. Transfer or preservation success
does not complete that plan. Execution, deployment, release and CI defaults
remain disabled.
