# Application session development

All console operations are currently disabled after the later initialization
exit and failed shell-state admission. The owner cannot physically operate the
console. Native GPU modes also reject execution before backend initialization
pending allocator/lifecycle integration. Host implementation and checks continue;
see [the latest failure record](native-bf16-fixed-20261022.json).

The application has session control, a llama.cpp adapter, a web interface and an
HTTP transport. Development checks use only a host demo or API stubs. No real
model execution or console access is part of those checks. The real application now links to an intermediate
native PIE with the selected latest driver. The native monitor now packages to
an integrity-checked SELF; see [the host record](native-monitor-20261022.json).
Runtime admission and full-model qualification remain separate; see
[staged native validation](native-validation.md).

## Request ownership and events

`native/app/session.h` defines one session for one engine owner. The frontend
serializes `begin`, `advance` and `cancel` on that owner thread; other threads
queue requests and cancellation for it. Concurrent requests are rejected.
The frontend must render the pinned model's exact chat template before `begin`.
Token pieces are raw bytes, so transport must preserve UTF-8 split across tokens.

`begin` validates basic request fields without touching the backend. The first
`advance` tokenizes and checks prompt plus output capacity before prefill.
Subsequent calls emit one token at a time. End-of-generation and the output cap
complete the request. A terminal call returns a stable finished event without
repeating backend operations. On the output cap, the final token event carries
the completed state; the following call returns the finished event.

Cancellation takes effect at a synchronous backend boundary. A backend returns
only after its work has provably completed. A failure quarantines the session:
there is no cleanup, retry, reset, or subsequent request against that engine.
The model adapter retains uncertain resources for ordinary OS shutdown when
console work is authorized. The session stores a reference and does not destroy
or release the engine.

## Timing

All clocks use monotonic milliseconds. Tokenization and prefill have separate
durations. TTFT runs from request admission to the first generated non-EOG token.
It remains absent when no token is generated. Decode rate uses intervals after
the first token: `(generated_tokens - 1) / decode_seconds`. It remains absent
for fewer than two tokens or a zero-duration interval. Total request duration
includes successful backend finish. These definitions must accompany future
measurements; fake-backend timings are not model-performance evidence.

## Focused manual checks

```powershell
python tools/check_app.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next --out D:/PS5-AI/qwen-flash-next/build/application-session
python tools/check_expert_policy.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
python tools/build_preview.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
python tests/http_preview.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
python -m unittest discover -s tests -v
```

The first command compiles and runs five deterministic fake-backend scenarios
and adapter API-stub checks on the host. It also compiles the session source into
a PS5 object and checks actual memory-budget accounting, placement and overflow.
It neither links the driver nor deploys a release. The scenarios cover
streaming and timing, cancellation, context admission and integer overflow,
empty and split UTF-8 output, and quarantine for each backend operation.
The Python checks also prove that a disabled console policy stops the
console helper before any network, build, or directory creation.

## Qwen adapter and model preparation

`llama_engine.cpp` tokenizes, prefills in one-token microbatches, samples greedily,
checks logits for finite values, preserves raw token pieces and resets successful
requests. Each decode is synchronized. An uncertain result quarantines the
adapter and retains its resources. The model/context are borrowed from admission.
API stubs check call ordering, output resizing, non-finite rejection and failure
retention. These checks do not establish model quality or PS5 execution.

The streaming configuration selects mapped original weights, required lazy PLE
lookup, CPU-backed routed experts and a bounded device expert cache. F32 KV/state
and six CPU threads are initial settings, not a qualified memory budget. The
application loader patch disables eager mmap prefetch explicitly. Mapped pages,
the PLE working set and actual console virtual-memory limits remain unmeasured.

The [Strata/Maya policy](expert-policy.md) is connected to the actual expert-cache
planner/copy callback. It adds UMA admission, aged-frequency eviction, feasible
layer floors, active-set protection, bounded miss advice and telemetry. Both
patched engine sources compile to target objects on an isolated host copy.
Model performance remains unmeasured.

`native_main.cpp` checks the development restriction before backend initialization.
For a separately admitted inference mode, it requires a conversion receipt, rejects
reduced-precision GGUF tensor types, checks the Qwen architecture and required
exact 64-bit PLE metadata, and uses the embedded original chat template. Failed
native admission retains resources for ordinary process close. The entry point
is now included in the native SELF. Bounded native display/status execution now
passes. The separate BF16 initialization attempt failed and that mode is again
disabled. Full-model inference remains rejected. See
[the display record](native-display-20261022.json) and
[the failed BF16 record](native-bf16-20261022.json).

`tools/convert_model.py` requires every original shard and verifies its size and
SHA256 before invoking the pinned BF16 converter. It records output file digests
and relative names in a model receipt. It performs no inference or transfer.
Full conversion has not run because original checkpoint acquisition is incomplete.
The converter verifies its actual Python source tree against the pinned ZIP,
in addition to the original shards. Changed or extra Python modules are rejected
before execution. It has a finite process deadline, durable progress/failure
states and an atomically published receipt. Host-only preparation waits for the
existing downloader without starting another writer or touching the console.
The future release must verify converted tensor layout/precision and transferred
file identities; a receipt alone is not a fresh console integrity check.

## Interface and HTTP transport

The web interface is a read-only monitor. It contains no chat input, forms,
generation, cancellation or other operation controls. It fetches only
`GET /api/status` once per second and inserts text through `textContent`.
It displays CPU/GPU identity, logical CPU threads, sampled application CPU use,
startup GPU memory, server date/time, request state, generated tokens, TTFT,
elapsed time and generation tokens/s. CPU use is process CPU time divided by
wall time and available logical threads in a qualified provider. Native CPU use
is disabled because its provider clock units remain unqualified. GPU utilization remains unavailable
until a qualified counter exists; demos never invent hardware values.

The clock follows the server epoch and displays the browser's local timezone.
It does not establish host/console wall-clock synchronization.
During generation, tokens/s uses intervals in the last five seconds; after a
request, it shows the session decode average. The denominator excludes the first
token's prefill wait. All generated tokens, including reasoning, are counted.
The chart retains up to 60 polling samples. Cache counters are process totals
sampled at completed engine operations; page-advice bytes are not SSD traffic.
An explicit demo banner identifies synthetic requests and unsampled hardware;
the no-model banner says monitor only. Missing rates produce gaps in the chart.

The TV interface uses the same typed status snapshot through a CPU observer
once per second, without browser requests or backend calls on that observer.
It rasterizes into two fixed tiled VideoOut buffers. Host tests check first-frame
completion, every pixel address and retained no-retry faults. These are API-stub
checks, not hardware evidence. The native clock is explicitly labelled CONSOLE UTC.
The separate display/status record confirms bounded first-frame and HTTP
completion on the console; physical TV observation is not claimed.

`http_app.cpp` applies the original chat template using the pinned upstream Jinja
implementation. It supports text messages only; media and tool calls are rejected.
One owner worker drives the engine. HTTP threads submit, stream bounded event
queues and request cancellation; concurrent generation receives HTTP 409.
Routes are `GET /api/status`, `POST /api/generate` and `POST /api/cancel`.
Only external clients use the POST routes; the monitor never sends them.
The current application context limit is 4,096 tokens; larger requests are
rejected before they reach the model adapter.
Generation returns SSE; token bytes use base64 to preserve incomplete UTF-8.
Invalid chat input does not quarantine a healthy model. Disconnects request
cancellation at the next synchronous boundary.

The local preview binds only `127.0.0.1`. Its host HTTP checks cover read-only
assets, time and unknown hardware, live/completed metrics, invalid input, a
complete stream, concurrent rejection, cancellation and invalid chat recovery
with the original template. These are demo checks, not Qwen results.

```powershell
D:/PS5-AI/qwen-flash-next/build/application-preview/app-demo.exe --demo C:/Users/User/ps5-ai/llm-work/PS5-Qwen-Flash-Next/web D:/PS5-AI/qwen-flash-next/model/chat_template.jinja 41027
```

## Remaining work

- Host SELF conversion/packaging and bounded display/status admission pass.
  Qualify the separate no-display BF16 fixture and required model operations;
  preserve all failed startup attempts in the
  [display record](native-display-20261022.json).
- Finish original checkpoint acquisition, BF16 conversion and layout verification.
- After runtime admission, measure native memory admission, required PLE and
  expert reads, complete generation, quality, cancellation and sustained residency.
- Keep release deployment disabled and advance console qualification only through
  the allowed stage in `config/development.json`. Application merges do not remove
  that restriction.
