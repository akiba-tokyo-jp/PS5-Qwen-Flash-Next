# Interrupted audit and independent continuation

At 18:29 UTC on 2026-10-22, the recorded preparation PID and data-waiter PID
were absent. Their interactive execution sessions were also unavailable. Their
last progress records were at 16:50 UTC. No exit result was recovered; the reason
for their termination is unqualified. The console had not been accessed by
either job. The first status response mistakenly treated the stale progress as
live progress; subsequent inspection corrected that statement.

The writer had completed all 76 splits before the interruption. Its retained
and newly written payloads total 359,235,922,432 bytes. No complete audit or model
receipt existed. The old intent, progress, retention and copy-adapter records
remain preserved. Partial audit progress does not qualify any payload.

`tools/finish_conversion.py` reuses those completed writer outputs and repeats
the complete independent payload audit and final file hashes. It validates the
unchanged writer/copy provenance, original SHA checkpoint and frozen data-waiter
inputs before starting. Original and converted files remain under read-only OS
leases throughout verification. Output identities and all frozen sources must
still match before a complete v2 model receipt is published. Conversion is not
repeated. The audit and hash limits remain 24 hours and 12 hours, respectively;
the job has no console client, learned inference or automatic retries.

The audit and its finite data-only waiter now run with `DETACHED_PROCESS`,
`CREATE_NEW_PROCESS_GROUP` and `CREATE_BREAKAWAY_FROM_JOB`. Successful creation
and process identity were recorded. A later command verified both processes
after their launch commands had exited. These jobs are independent of the
interactive tool's process job; this does not guarantee survival of host failure
or successful model qualification.

The finite full-plan continuation waits for the exact identified data waiter to
positively complete and exit. It then uses the existing reviewed case preparer
and operator to perform fresh CPU/session/clock admission, temporary candidate
publication, one ordinary launch, native integrity/mapping/load and arithmetic
smoke, two fixed API requests with passive display, positive retirement, ordinary
close and exact original restoration/numerical readmission/final readback. Every
step has its own exclusive intent, deadline and terminal record. Changed sources,
failed data preparation or any failed/uncertain physical step prevent subsequent
actions. No automatic physical retry, forced close, GPU reset or release is
implemented. Original restoration remains a required result, not an assumed one.

All three deliverables in `execution-plan-20261022.md` remain required. At this
checkpoint full-model inference, displayed performance and final restoration
have not been performed. No intermediate host or data result is completion.
