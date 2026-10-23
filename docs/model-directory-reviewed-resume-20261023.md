# Reviewed completion of model-directory preparation

The plan-bound CPU controller passed linking/import admission and completed its
physical `prepare` action. The following FTP `MKD` call returned normally, but
its canonical-path comparison was rejected. The old worker did not retain the
exact returned string. It stopped before marker upload or controller finalization;
the original failure and every execution intent remain unchanged.

A separate read-only review observed the exact `model` entry as a root-owned
directory containing only `.` and `..`. Management service identities and the
absence of a native title were checked. The creation command was not repeated.
With a new positive CPU observation, the reviewed continuation uploaded the
original 183-byte owner marker once and ran the existing controller's previously
unexecuted `finalize` action once. Its exact positive log, full marker readback
and final listing passed. The model directory is root-owned mode 0755 with a
mode-0644 marker, and the parent/web ownership was restored.

The ordinary directory sequence now independently checks the exact root-owned
parent-list entry and empty target before accepting a missing canonical path
from the FTP client. A different nonempty path, symlink, foreign owner, missing
or duplicate entry still rejects. Twenty-six directory/protocol tests passed.
No failed or uncertain write is automatically retried.

The original complete v2 receipt, transfer plan and controller were reused.
Data continuation 006 transfers all 76 containers using that original plan;
neither conversion nor a complete source-hash pass is repeated. Fresh CPU,
capacity and ownership admissions passed before transfer. Stream hashes remain
compared with the complete receipt, and independent native destination SHA is
still required before loading the model.

This reviewed data continuation emits a distinct completion-v2 record only after
every file and receipt is positively transferred and the final CPU guard passes.
It binds the original plan and reviewed directory completion rather than claiming
that the old failed worker succeeded. `prepare_first_case.py` checks those bindings,
retained failure, original marker and directory proof before its existing full
transfer/candidate/policy gates. Six metadata-binding regression tests and the
corresponding real directory/plan metadata check passed. These checks do not
establish a complete transfer or physical inference.

One finite full-plan continuation can wait for that exact data process's positive
completion and exit, then use the unchanged sealed candidate and unused physical
case 019. All original native SHA/mapping/memory, three fixed requests, passive
display, positive retirement and exact original restoration/readmission remain
required. No GPU or model execution has occurred at this transfer checkpoint.
