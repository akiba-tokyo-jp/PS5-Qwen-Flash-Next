# Expert-only Q4 production qualification

Subsequent [post-Q4 bottleneck measurement](expert-q4-io-attribution-20261029.md)
quantifies decode-only source waiting and named non-Expert row reads. Its
diagnostic is not adopted; this selected application/settings were restored.

The Expert-only Q4_0 candidate passed the complete native model comparison,
the passive monitor/API application and production placement. The same PS5
produced correct counting answers in all six requests, with complete same-Q4
vocabulary rows and ordered Expert routes matching on independent repeats.
This is finite counting qualification; broad reasoning quality is not established.

| Request (0 is warmup; 1/2 are API requests) | Decode tok/s | TTFT seconds | Total seconds |
| --- | --- | --- | --- |
| 0 | 0.866724 | 22.614 | 47.916 |
| 1 | 0.869380 | 21.170 | 46.399 |
| 2 | 0.870236 | 21.219 | 46.421 |

Normal API decode is **0.869808 tok/s**, versus **0.419813 tok/s**
in the earlier same-console BF16 controls: **2.0719x**.
The isolated Q4 model measured 0.871504 tok/s. Decode counts accepted transitions
after the first token and excludes prefill. Every timed request starts with empty
Expert metadata. Physical request reads fell from 183.1945 GB to 44.9198 GB in
the model comparison; those counters cover both prefill and decode.

Only the 147 routed Expert tensors are quantized. All 512 Experts/layer and
top-10 routing remain; non-Expert BF16/F32 payloads, F32 activation inputs and
F32 KV remain unchanged. Q4_0 stores 32 weights in 18 bytes, including scales
(4.5 effective bits/weight). All 75,264 matrices and complete changed physical
parts passed SHA256/readback; unchanged tensors retain their exact source bytes.
The mixed model is 181,985,183,872 logical GGUF bytes, including reused original
files. No 8-bit comparison, CPU matrix fallback or learned host inference was used.

The same 1,333,739,520-byte cache budget holds 481 Q4 slots plus one guard plane.
This profile uses compressed contiguous delivery. The BF16-specific padded
six-demand path and its prefix/speculative integration remain preserved in the
BF16 rollback; they are disabled in this Q4 profile and are not claimed qualified
under the changed precision. Independent repeats compare Q4 with Q4, not lossy
Q4 logits with BF16 logits.

Both 1920x1080 native CPU rasters were inspected after positive VideoOut
completion. CPU/GPU identity, calibrated date/time and measured token rates
are legible; there are no chat controls. Utilization percentages remain unavailable.
Both API streams match durable native token/output records. Source/model/GPU
owners positively retired, the exact owner normally closed, BF16 restored for
verification, and the proven Q4 executable plus all five settings were then
placed with full native SHA256/identity/EOF readback. Previous BF16 and older
rollback executables were verified. Title, gateway and model are now inactive.

Selected SELF: `98a573396af615f754fe4286c6600ccf5596b8fad9d4ab00b99d7e9295dfd8fa` (17,370,183 bytes).
Previous BF16: `80c28a95e993458c54b5fbf73fe59accde17dd8302dd49a9aeecf367e617739c`.
The finite run binding is consumed; a new launch requires fresh admission.
This does not certify an unbounded service or general model-answer quality.

## Implementation and reproducible source locations

- `tools/expert_q4_quantize.c`: original BF16 to pinned Q4_0 block encoder.
- `native/qwen_flash_next/expert_q4_local_convert.cpp`: bounded CPU conversion, original/unchanged tensor hashes and full Direct part readback.
- `native/app/expert_q4_receipt.h` and `expert_q4_source_integrity.h`: all 1,256 tensors, mixed precision, 76 logical splits and exact namespace/source admission.
- `native/app/expert_q4_cache_reset.h`: strict 481-slot metadata reset, complete inverse-map validation and retained original GPU banks.
- `tools/build_expert_q4_model_providers.py`: preserve original BF16 dispatch byte-for-byte; only Q4 disables activation quantization and retains F32 inputs.
- `tools/expert_q4_model_source.py::entry_source` / `cache_source`: complete mixed split loader, compressed cache accounting and full repeated Q4 logits/routes.
- `tools/expert_q4_monitor_source.py::monitor_entry_source`: original passive VideoOut/API transport, precise Q4 labeling, bounded generation and matching frame completion.
- `tools/build_expert_q4_model.py` / `build_expert_q4_monitor.py`: immutable relink ancestry, actual ELF loader/callback/import audits and qualified provider reuse.
- `tools/relink_expert_q4_monitor_label.py`: only the fixed CPU raster precision label changes; every inference/cache/driver object is retained byte-for-byte.
- `tools/observe_expert_q4_monitor.py`: durable once-only API intents, ordered stream checks, exact frames, identity and positive retirement.
- `tools/analyze_expert_q4_model.py` / `report_expert_q4_adoption.py`: separate component/model/application evidence and guarded public adoption reporting.

llama.cpp: `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`.
Driver: `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches and CI remain disabled. Cases 7640/7660/7700/
7740/7780 remain their original failed results with ordinary teardown and exact
restoration; corrected model case 7820 and final application case 7920 are
separate successful observations. Case 7860 passed the inference/API/retirement
checks; visual review found its stale fixed BF16 header. The final label-only
relink retains all inference/cache/driver objects and is qualified separately.
Application source revision: `00ee9fa2fd0919eb838e51648f30fbf307ce421d`.
