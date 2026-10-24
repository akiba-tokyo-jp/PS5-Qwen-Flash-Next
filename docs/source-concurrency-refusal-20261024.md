# Rejected two-read source candidate

The two-read candidate completed original-precision arithmetic `4`, but worsened
its direct-read wall interval from 81.865 to 237.555 seconds for the exact same
123,411,118,080 source bytes. It used 18,375 paired batches inside the unchanged
8 MiB source buffer. TTFT rose from 91.383 to 242.275 seconds. No speedup is
qualified, and this candidate is not adopted. See the
[sanitized result](source-concurrency-refusal-20261024.json).

The first external request returned an explicit failed terminal event when the
unchanged kernel free-page minimum plus extra reserve predicate rejected new
source I/O during its second input-token decode. The failed decode did not
complete. No request was retried. The application retained its resource graph,
stopped serving inference and waited for ordinary OS shutdown. Stable owned logs
and exact-owner CPU guards were collected without GPU operations. Ordinary OS
close, exact original SELF restoration, original numerical readmission, ordinary
shutdown, final CPU guards and whole original SELF readback all passed.

The completed arithmetic counters locate the regression in the two-read path;
they do not distinguish filesystem serialization, I/O scheduling and thread
handoff costs. The memory predicate refusal is separately established. It does
not prove a kernel leak or a specific filesystem defect. All original memory
reserves, BF16/F32 tensors, driver/archive and cache policy stayed unchanged.

The next candidate permits only one outstanding read. It overlaps the second
known-miss read with the first synchronous backend upload on the producer. It
records producer read/wait, worker read and worker dispatch intervals separately.
Worker intervals can overlap consumer intervals and must not be summed as
independent decode time. Physical comparison remains required.
