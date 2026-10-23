# Bounded native scheduler metadata

The allocator-observation artifact loaded the complete original model and passed
its positive device-idle checkpoint. It recorded 3,401,433,088 available native
Direct bytes and 8,771,944,448 owned bytes, while the raw Vulkan estimate was zero.
Context construction returned, including a complete 7,184-node graph reservation,
then the CPU/Flexible admission check rejected it before generation. The complete,
stable driver log contained no worker initialization. The owner was ordinarily
closed, the exact original SELF restored and numerically readmitted, then normally
closed with final CPU guards and a complete original SELF readback.

The old combined exception did not persist the failing heap/Flexible values.
Do not claim that it measured the exact excess. The replacement records separate
post-load and post-context observations and reports heap mapped/peak/limit/fallback
values or Flexible available/required values without changing those limits.

Source inspection found a separate concrete over-allocation: the scheduler sized
its tensor-copy metadata for the nominal graph capacity, treating every capacity
slot as a potential split with 30 inputs. For the pinned 1,256-tensor model,
the existing graph capacity remains 40,192. The actual host ABI allocation formula
requests 812,503,536 bytes, exceeding the unchanged 376,438,784-byte CPU heap limit
before the remaining heap allocations are counted.

The application overlay now allocates one 192 MiB scheduler metadata arena.
The graph/hash capacities, all model tensors, experts, nodes and operators remain
unchanged. Before constructing scheduler copies, it checks the complete active
graph against the fixed arena using `ggml_tensor_overhead()`, including alignment
and metadata objects, plus graph overhead. Overflow, empty graphs, insufficient
space and parallel scheduler copies are rejected. The native application already
uses one serialized producer and one scheduler copy. No smaller model, reduced
precision, partial graph or smaller system reserve is substituted.

The actual GGML metadata allocator used exactly 158,936,784 bytes for the
conservative 7,184-node bound, within the 201,326,592-byte arena. The actual patched
scheduler executed three complete 7,184-node CPU fixture graphs with all 48 output
values exact. Zero/overflow/excess-capacity cases were rejected. These are host
metadata and synthetic arithmetic checks, with no model payload reads, learned
host inference or GPU calls. Only the scheduler object was rebuilt; six unchanged
model-I/O objects and the pinned driver archive were reused.

The diagnostic-only case was superseded before any title launch. The distinct
scheduler artifact must still pass real context/cache admission, generation,
external requests, actual monitor-frame review, positive resource retirement,
normal close and every original restoration/readmission gate. Full-model tokens/s
and task quality remain unqualified until those results exist.
