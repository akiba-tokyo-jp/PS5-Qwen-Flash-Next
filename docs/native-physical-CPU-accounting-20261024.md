# Physical CPU accounting and explicit API failures

The compact-arena artifact completed the arithmetic smoke request on the PS5:
26 prompt tokens, output `4`, 91,023.55 ms to its first output, 94,619.27 ms total
and a completed request reset. A single output token has no decode-rate interval;
tokens/s remains unqualified. The model stayed loaded, the completed context was
recreated and the first native model-resident monitor frame completed.

The first external request was identified by its durable intent but failed its
CPU guard before entering its first GPU boundary. Its heap mapped/peak was
436,273,152 bytes, with zero libc fallbacks. The client received an empty stream;
the request was never retried. Prior GPU completion and the exact failure point
were verified from stable logs. Ordinary close, exact original restoration,
numerical readmission, normal close, final CPU guards and full original SELF
readback all passed.

The old heap allowance still subtracted 160,432,128 logical source-page bytes
from the 512 MiB CPU budget. That subtraction came from the former file-mapping
design. The current native source admission proves zero file-backed model mmap
calls and protected, fixed/no-overwrite source keys. Actual reads use one aligned
8 MiB Direct window. CPU scratch is tracked by the heap; Vulkan context buffers
retain their separate allocation budgets.

| Physical CPU accounting | Previous derived allowance | Current v4 scope |
| --- | ---: | ---: |
| Total planned CPU budget | 536,870,912 | 536,870,912 |
| Extra resident source-file pages | 160,432,128 assumed | 0 protected-key pages |
| Heap allowance | 376,438,784 | 536,870,912 |
| Direct read window | Included in heap | Included in heap, native ownership required |

The complete planned resident requirement stays 12,110,548,480 bytes. This corrects
double counting within the existing CPU budget. The logical addressed-row bound
remains a diagnostic limit. Native setup now verifies `ps5_heap_owns(window)`
before reporting source admission. Zero libc fallbacks, the 512 MiB total CPU
cap, 256 MiB Flexible reserve plus source metadata margin, kernel minimum plus
the larger of its reserved count or 4 MiB, platform margin, Direct reserve and
every device/workspace limit remain mandatory. Scope v4 names the new physical
accounting explicitly and rejects older scope bindings.

The host result verifier now checks the actual separate Flexible/kernel fields;
it no longer expects the retired `OS_free_bytes` aggregate. Its tests admit the
measured 416 MiB heap inside the original 512 MiB CPU budget and reject excess
heap, nonzero extra source residency, an unowned window or insufficient kernel/
Flexible reserves. Native source-provider, scope and application objects compile.

Backend exceptions now deliver a bounded `finished` / `failed` SSE event with a
quarantined, retained resource graph. The listener gives its existing observer
at most two seconds to receive it, then stops and propagates the original error.
It never retries inference or frees uncertain GPU resources. The once-only client
records an explicit failure separately from an empty/disconnected uncertain
stream. Host loopback checks cover two successful requests and failures before
the first event and after a token. The actual client consumer is tested for
explicit failure, empty uncertainty and normal completion, with one POST each.

These changes preserve the model, seven engine overlays, 160 MiB scheduler arena,
driver revision/profile and cache policy. Native link, module import audit and six
SELF segments passed. The distinct scope-v4 artifact subsequently completed full
external generation, actual frame review and every final restoration/readmission
gate. See [the complete physical result](native-full-generation-success-20261024.md)
for its exact executable identity, measurements and limits.
