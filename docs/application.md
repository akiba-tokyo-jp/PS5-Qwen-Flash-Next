# Application and monitor

The source contains a native frontend, a single-owner session, a llama.cpp
adapter, a streaming HTTP interface and read-only browser/TV monitors.
[Current status](project-status.md) describes the selected configuration and
unresolved latest console session. This page is an interface/ownership guide,
not a claim that a service is currently running.

## Request ownership

`native/app/session.h` gives one owner thread the engine. The frontend serializes
`begin`, `advance` and cancellation; other threads queue requests. Concurrent
generation is rejected. Input validation and context/output bounds are checked
before model processing. The real frontend renders the pinned chat template;
model token bytes must survive incomplete UTF-8 boundaries.

Request resets and exact-prefix reuse are explicit. Retained expert weights do
not imply retained KV/recurrent request state. Disconnect cancellation occurs
at a synchronous boundary, not by releasing uncertain in-flight GPU resources.

## HTTP interface

| Route | Purpose |
| --- | --- |
| `GET /api/status` | Read-only session/monitor snapshot |
| `POST /api/generate` | External client generation request |
| `POST /api/cancel` | External client cancellation request |

Generation uses server-sent events. Token payloads are base64-encoded to retain
raw byte boundaries. The adapter accepts the implemented text-message shape;
media/tool input is not admitted by this text-only interface. Concurrent
generation receives HTTP 409. Invalid input does not quarantine a healthy model.
Inspect `native/app/http_app.cpp` for the source-level request/event contract.

The browser monitor has no chat input or operation controls. It polls only
status and renders text through `textContent`; external clients use the POST
routes. This development transport is not a public hosted API or an authenticated
internet deployment. Host demos bind loopback; remote exposure is not part of
the documented quick start.

## Observability

The status snapshot can report identity, UTC source, request state, generated
tokens, TTFT, decode rate and completed expert-cache counters. Unknown hardware
values remain unavailable. Native CPU-use clock units and GPU utilization are
not qualified counters; the interface must not invent them.

During a request, the monitor uses a rolling rate; after completion it reports
the session decode average. Benchmark reports use
`(generated_tokens - 1) * 1000 / decode_ms`. TTFT/prefill are separate. Page advice
is not measured SSD traffic, and cumulative cache counters are not device utilization.

The clock identifies its source and calibration uncertainty. Application-local
UTC anchoring does not write the console system clock. Browser-local timezone
rendering is separate from the monotonic timing used for metrics.

The native TV renderer uses fixed VideoOut buffers and checks flip completion
before reuse. Display-only validation does not initialize a model/Vulkan backend.
A successful first-frame/API-stub test is not a fresh physical TV observation.
The later selected-profile timing cases are headless; they do not requalify TV
behavior simply by completing inference.

## Host preview and native builds

`tools/build_preview.py` builds the explicit synthetic demo and cross-compiles
application objects. Its demo banner distinguishes synthetic output from Qwen
inference. It supplies no measured PS5 hardware utilization. The builder still
needs the selected Windows toolchain, SDK and pinned upstream source.
See [getting started](getting-started.md) for parameterized commands.

Native linking connects the actual allocator/lifecycle/static-dispatch provider.
Compilation, packaging, model admission, numerical checks and ordinary resource
retirement are separate milestones. [Native validation](native-validation.md)
preserves those gates. [Performance](performance.md) describes the completed
short-task evidence and its quality limits.

The previous development narrative is preserved in
[the pre-cleanup revision](https://github.com/akiba-tokyo-jp/PS5-Qwen-Flash-Next/blob/ba28680ddd86f2bb3d892755a5981fe30593b96b/docs/application.md).
Its acquisition/inference-pending statements are historical, not current status.
