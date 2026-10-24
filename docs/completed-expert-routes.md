# Bounded completed expert-route observation

The optional native observer records IDs already downloaded by the actual MoE
cache. It wraps the linked `ggml_backend_tensor_get_async` and
`ggml_backend_synchronize` calls and delegates each original operation exactly
once. It adds no GPU download, kernel, source read or routing decision.

Only the existing cache's flattened `ffn_moe_topk` I32 input is eligible. The
observer checks the original 10-expert selection, one to four causal tokens,
48 ordered text layers, the same backend and producer, and both returned
original calls before copying IDs into bounded CPU storage. Internal provider
synchronization and synchronization on another thread cannot consume a sample.

The private validation policy is opt-in and requires all five fields:

```json
{
  "schema": "ps5-qwen-completed-expert-routes-policy-v1",
  "enabled": true,
  "maximum_records": 4608,
  "require_complete_48_layer_processes": true,
  "additional_GPU_downloads": 0
}
```

The fixed 4,608-record allocation holds 96 completed process calls and consumes
377,856 bytes before vector/owner metadata. It is charged to the existing CPU
heap; no limit or reserve changes. Completed requests retain only compact raw
rows, rather than the capture's unused capacity or per-row JSON allocations.
Three bounded raw reports remain in that tracked heap until every request,
model/GPU retirement and source-worker shutdown have completed. Only then are
JSON objects created and their sidecars written. Existing token, performance,
failure and monitor records keep their original timing. There is no per-expert
file logging in the read path.

A metadata mismatch quarantines observation and produces an explicit failed
capture while preserving the original inference calls. An original provider
exception still propagates through the original GPU failure/quarantine path.
A failed capture cannot qualify cache replay. Optional host metadata collection
also cannot obstruct ordinary close/restoration after the independent original
numerical, source and GPU retirement validators have passed.

`tools/expert_route_result.py` requires complete causal/layer coverage, distinct
top-k IDs within every token, exact owner/run/reset bindings and agreement with
actual hit/miss/upload counters. Replay must match all three original counter
sets before comparing another cache policy at the same 53-slot capacity. IDs,
owners, raw traces and console locations remain private.

The actual GGML host checks cover 21 conditions, including real argsort,
contiguous and reshape metadata, partial batches, wrong dimensions/order/owner,
overflow, reentrant provider synchronization, original-call failures and three
independently retained compact batches with no aliasing or unused capacity. PS5
entry compilation, native import/SELF checks and linked disassembly separately
verify both cache-to-wrapper and wrapper-to-original call paths. Host checks
alone do not establish physical observation or comparative speed.
