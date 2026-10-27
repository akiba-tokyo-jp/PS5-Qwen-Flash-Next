# Native model result after lossless driver startup

The reduced-file candidate completed actual original-precision Flash-Next
inference on PS5 in case 3314. Expert-aware width-two verification ran once and
accepted its draft; both external requests produced the same 22 token IDs and
output bytes. This establishes that exercised path, not complete speculative
qualification or a speed winner. Rejection/restore and matched speed tests remain
unverified. Predictive GPU/model overlap remains unverified and is currently
execution unavailable. Do not describe this result as completion of the three
selected optimizations.

| Selected work | Actual evidence | Current decision |
| --- | --- | --- |
| OS I/O alternative | New native AIO comparison 3193 completed and lost 46.88% | Rejected; production retains its faster qualified I/O path |
| Predictive cache | Shipping persistent worker completed four jobs / twelve original BF16 role deliveries in 3225; native integration and result accounting are implemented | Model overlap and matched speed are execution unavailable under the current resource policy; keep default off |
| Expert-aware speculation | Model 3314 completed warmup plus both 22-token requests; five causal proposals, four ordinary decisions, one width-two acceptance; all final tokens/bytes exact | Exercised acceptance passed; zero rejected drafts; rejection/restore and matched speed remain unverified and currently execution unavailable |
| Lossless driver startup support | Small GPU 3280 restored all 673 tables, matched all 16 BF16/F32 outputs exactly and retired; full-model 3314 then completed | Startup support physically exercised; no production speed adoption |

## Artifact and exact implementation

Driver source remains `akiba-tokyo-jp/PS5-Vulkan-Inference`, revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
The overlay starts from native donor archive SHA256
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Original object instruction sections, relocation records and every untouched
archive occurrence are preserved. Persistent shader/pipeline caches stay disabled.

Build 3287 / package 3288 is a 19,236,759-byte SELF, SHA256
`c128f48038939b83893c7a6c7b335489158bfc4416adfb7e28d6ac98bb8313a2`.
The prior integrated candidate was 28,419,239 bytes. Native link/import audit,
SELF integrity, six segment roundtrips, actual linked cold-data geometry and
loader-visible converted metadata checks passed. Summed page-rounded PT_LOAD
memory increases by 19 pages; file-size savings are not treated as free RAM.

- `tools/driver_table_storage.py::audit_linked_storage()` checks the real final
  plan, every table pointer/hash, exclusive NOBITS destinations and permissions.
- `audit_converted_storage()` additionally checks 677 critical relative pointers
  in the converted ELF, exact scalar metadata, hashes, encoded bytes and complete
  writable non-executable table coverage. `package_native.py` and
  `package_mini_shader_memory.py` require both audits for this optional overlay.
- `native/app/native_main.cpp` restores constants after validating policy and
  retaining the failure-report path, before any Vulkan entry point.
- `native/app/driver_tables.cpp::restore_native_driver_tables()` uses bounded
  owned Direct-heap scratch, exact reconstruction, readonly protection, its
  operational-plus-512-page admission and no retry after failure.
- `native/app/llama_engine.cpp::next_with_one_draft()` performs original width-two
  target arithmetic and complete-state checkpoint handling. The independent
  expert-cost hooks select actual ordinary/width-two work; discarded work remains
  counted. Acceptance was exercised in 3314; rejection was not.
- Prediction's native worker, bank leases and extra-transfer accounting are
  documented in [the integration record](native-predictive-integration-20261027.md).

## Completed model observations

Warmup generated one token after a 44.831 s prefill. It is not a decode-speed
benchmark. CPU heap peak was 453,050,368 bytes. Both external requests used the
same original 30-token prompt, context 256, prefill four, 53 cache slots, original
BF16/F32 weights and F32 KV. All required experts and PLE remained enabled.

| Request | Condition | Generated tokens | Prefill, s | Decode, tok/s | Total, s |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Ordinary control; empty expert cache | 22 | 50.171486 | 0.390939601 | 106.486156 |
| 2 | Expert-aware verification; retained cache | 22 | 49.260189 | 0.403343875 | 103.907494 |

These cache conditions differ. Their speed ratio cannot establish a speculative
speedup, a cold-storage speedup, or a production gain. The controller performed
21 proposal checks: 16 had no draft; five had a causal draft; four retained
ordinary width; one performed width two and accepted. No rejection occurred.
All extra source work and checkpoint costs remain in completed performance data.
Reported source-read wall fractions include overlapping worker work and are not
isolated SSD latency or GPU-compute time.

Model/source/checkpoint/device owners positively retired, device ledger live
bytes were zero, and the listener stopped. One ordinary OS close was accepted;
exact owner absence was subsequently verified. A host exclusive-save collision
after that positive close was resumed using the identical existing owner proof;
no second close call occurred. The failure and resume receipts are retained.

The exact fastest SELF and all five prior settings were restored, with full
native SHA256/identity/EOF checks, both completed frames preserved in the same
required cohort, and fresh idle ownership. Installed SELF remains
`ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d`.
No native app, gateway, loaded model or unknown completion remains. No reboot,
reset, force-kill, manual release of uncertain GPU work, or CI was used.

## Remaining execution constraint, based on this actual model

The conservative CPU-only entry for 3314 was 8,178 pages: prior maximum CPU
decline 6,749 + 19 image-memory pages + operational floor 1,154 + variation 256.
It granted no GPU admission; the native 2,974-page startup target was unchanged.
The ten actual prelaunch observations were 8,298 pages.

| Completed boundary | Global free kernel pages |
| --- | ---: |
| Before model integrity | 3,421 |
| Before virtual-source rehearsal | 3,337 |
| After all source releases, before admission | 3,377 |
| After source admission | 3,373 |
| After indexed GPU fixture | 3,312 |
| After model load | 1,456 |
| After context creation | 1,415 |
| Final qualified backpressure observation | 2,221 |

These are global snapshots, not exclusive attribution or continuous minimum
measurements. Operational admission passed with zero pressure waits over 146,200
observations. The evidence does not support lowering GPU admission to fit the
next available snapshot: the observed GPU/load phase itself consumed 1,897 pages.

Prediction screen 3329 refused at 6,947 versus 8,178 pages, before any title or
GPU work. Newly completed closed-entry evidence was then preserved exactly once:
225,088 bytes, whole native SHA256/identity/EOF passed. An invalid FTP driver-log
size was recorded and not read. This is preservation, not a global reclaim API.

New resource pricing 3340 uses observed CPU decline 8,298 - 3,312 = 4,986 and a
predicted phase requirement `max(2974, 1154 + 1897 + 256) = 3307`, plus 256
variation and a separate provisional 256-page prediction-worker allowance:
`4986 + 3307 + 256 + 256 = 8805` pages. The read-only screen observed 6,891 and
refused with zero launches/GPU calls. The worker allowance and margins are chosen
policies, not physical hardware minima. The underlying runtime predicates remain
unchanged; a screen does not authorize bypassing them.

The independent prediction settings, exact-policy host check, result/route
review, ordinary close and restoration scripts are prepared. Their real-model
execution, the unexercised speculative rejection path, and matched A/B/B/A speed
qualification are **execution unavailable under the current resource policy**.
They are not successful tests, absent implementations, or proven physical
impossibilities. Reopen after supported owned-startup savings or materially
greater observed headroom; do not repeat refused scopes or depend on reboot.

The [allowlisted result](native-model-cold-start-20261027.json) binds actual
receipts by SHA256. Private console bindings, journals, endpoints, SDK content,
weights and binaries remain outside Git.
