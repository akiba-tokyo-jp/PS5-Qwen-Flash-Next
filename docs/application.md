# Application session development

The application has session control, a llama.cpp adapter, a web interface and an
HTTP transport. Development checks use only a host demo or API stubs. No real
model execution or console access is part of those checks. A complete linked
native application and full-model qualification are still outstanding.

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
python tools/build_preview.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
python tests/http_preview.py --workspace C:/Users/User/ps5-ai --cache D:/PS5-AI/qwen-flash-next
python -m unittest discover -s tests -v
```

The first command compiles and runs five deterministic fake-backend scenarios
and adapter API-stub checks on the host. It also compiles the session source into
a PS5 object. It neither links the driver nor deploys a release. The scenarios cover
streaming and timing, cancellation, context admission and integer overflow,
empty and split UTF-8 output, and quarantine for each backend operation.
The Python checks also prove that the current console restriction stops the
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

`native_main.cpp` checks the development restriction before backend initialization.
When future console work is permitted, it requires a conversion receipt, rejects
reduced-precision GGUF tensor types, checks the Qwen architecture and required
exact 64-bit PLE metadata, and uses the embedded original chat template. Failed
native admission retains resources for ordinary process close. The entry point
has compiled to an object only; it has not been linked or run on PS5.

`tools/convert_model.py` requires every original shard and verifies its size and
SHA256 before invoking the pinned BF16 converter. It records output file digests
and relative names in a model receipt. It performs no inference or transfer.
Full conversion has not run because original checkpoint acquisition is incomplete.
The future release must verify converted tensor layout/precision and transferred
file identities; a receipt alone is not a fresh console integrity check.

## Interface and HTTP transport

The web interface accepts a text conversation, streams output, supports stopping
and displays state, TTFT and generation rate. The explicit demo banner distinguishes
test text from model output. It inserts text through `textContent` and incrementally
decodes UTF-8 bytes, including fragments split across tokens.

`http_app.cpp` applies the original chat template using the pinned upstream Jinja
implementation. It supports text messages only; media and tool calls are rejected.
One owner worker drives the engine. HTTP threads submit, stream bounded event
queues and request cancellation; concurrent generation receives HTTP 409.
Routes are `GET /api/status`, `POST /api/generate` and `POST /api/cancel`.
The current application context limit is 4,096 tokens; larger requests are
rejected before they reach the model adapter.
Generation returns SSE; token bytes use base64 to preserve incomplete UTF-8.
Invalid chat input does not quarantine a healthy model. Disconnects request
cancellation at the next synchronous boundary.

The local preview binds only `127.0.0.1`. Its host HTTP checks cover assets,
invalid input, a complete stream, concurrent rejection, cancellation and invalid
chat recovery with the original template. These are demo checks, not Qwen results.

```powershell
D:/PS5-AI/qwen-flash-next/build/application-preview/app-demo.exe --demo C:/Users/User/ps5-ai/llm-work/PS5-Qwen-Flash-Next/web D:/PS5-AI/qwen-flash-next/model/chat_template.jinja 41027
```

## Remaining work

- Complete a native application link and platform startup integration after the
  driver dependency is qualified. The current products are objects and a host demo.
- Finish original checkpoint acquisition, BF16 conversion and layout verification.
- After driver qualification, measure native memory admission, required PLE and
  expert reads, complete generation, quality, cancellation and sustained residency.
- Keep release packaging and console qualification deferred under
  `config/development.json`. Application merges do not remove that restriction.
