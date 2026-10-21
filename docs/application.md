# Application session development

This component implements application control flow independently of the driver.
It does not load a model, perform learned host inference, or access a console.
The production llama.cpp adapter and frontend transport remain to be implemented.

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
The future native adapter must retain uncertain resources for ordinary OS
shutdown when console work is authorized. The current class stores a reference
and does not destroy or release the engine.

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
python tools/check_app.py --workspace C:/Users/User/ps5-ai --out D:/PS5-AI/qwen-flash-next/build/application-session
python -m unittest discover -s tests -v
```

The first command compiles and runs five deterministic fake-backend scenarios
on the host, then compiles only the session source into a PS5 object. It neither
links the driver nor creates or deploys a native release. The scenarios cover
streaming and timing, cancellation, context admission and integer overflow,
empty and split UTF-8 output, and quarantine for each backend operation.
The Python checks also prove that the current console restriction stops the
console helper before any network, build, or directory creation.

## Next application work

- Implement the model adapter with the required PLE lookup and bounded expert
  streaming. Resolve eager expert prefetch before any full-model loading.
- Add frontend request transport, incremental UTF-8 rendering and visible
  request state using the session events.
- Keep release packaging and console qualification deferred under
  `config/development.json`. Application merges do not remove that restriction.
