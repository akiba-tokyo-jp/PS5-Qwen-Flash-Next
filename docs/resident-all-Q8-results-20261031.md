# Resident Q8 with the original BF16 PLE convolution

Normal/API/display case11480 and the eight-request fixed-task case11520 completed
on PS5, normally closed and restored the exact57043cbe control and its settings.
Placement11560 subsequently installed SELF
`bd390b921eaf6cfee9057cfd01ab1b03ecc48b171c0501a2807b999375dcca49`
(20065607bytes). Current and immediate-control programs plus both five-setting
sets pass native whole SHA256/identity/EOF before and after placement:12 files.
Ownership is finalized and fresh idle is confirmed. The title, gateway and model
remain inactive. The finite validation binding is consumed; a future launch
requires a fresh case. Every selected conversion, qualification and placement
stage is complete.

The544 remaining resident BF16 matrices become Q8_0. Routed Expert Gate/Up Q2_K
and Down Q2_0 MSE payloads remain exact. The single small resident convolution
`blk.1.ple_conv1d.weight` remains original BF16[4,10240],81920bytes. All F32
tensors, mapped input embeddings, lazy PLE lookup data and MTP remain unchanged.
The effective model has689 Q8_0,21 BF16,399 F32,98 Q2_K and49 Q2_0 tensors.
Twenty of the remaining BF16 tensors are outside the resident placement.

| Measurement | Installed control10970 | Resident Q8 case11480 |
|---|---:|---:|
| Resident weight payload / model GPU copy bytes | 7,937,953,280 | 4,774,100,480 |
| Independent decode, tok/s | 3.717603 | 3.955124 |
| Independent TTFT, seconds | 5.719974 | 5.591661 |
| Independent total, seconds | 11.635879 | 11.155669 |
| Exact-repeat decode, tok/s | 5.261777 | 5.595078 |
| Exact-repeat TTFT, milliseconds | 62.107778 | 63.070404 |
| Exact-repeat total, seconds | 4.609774 | 4.354448 |
| Active Expert cache slots | 1381 | 1381 |

The resident payload saving is3,163,852,800bytes, approximately2.947 GiB. Native
GPU upload counters, after subtracting the unchanged fixture copy, independently
reconcile both payload totals. This measures model copy/payload bytes, not the
whole system's RAM saving. The cache was deliberately kept unchanged.

Independent decode improves6.389% and repeat decode6.334% in these short cohorts.
Independent whole time decreases4.127%. Repeat TTFT increases0.963ms. The control
is the historical10970 cohort: this is not a fresh matched ABBA comparison or a
sustained performance guarantee. Identical three-response counting tokens/bytes
pass. Same-policy independent full-vocabulary F32 difference is0. The final
unlike cache/causal-width comparison is finite, maximum4.203896, with identical
counting output; it is not a BF16-versus-Q8 logit comparison. A complete cross-
precision logit difference was not measured.

Counting, Japanese, arithmetic and JSON contents pass8/8. Every task starts
with empty application caches and is repeated once; same-profile full F32
differences are0 and ordered Expert routes match. Strict raw formatting is6/8:
both JSON replies retain Markdown code fences, as in the control. Outputs are
not normalized by the application. These four short tasks do not establish
broad reasoning quality or sustained service qualification.

CPU heap peak503382016bytes, transient device ledger peak2472542208bytes and
workspace peak8388608bytes stay within their unchanged512 MiB,2480332800byte
and48 MiB limits. The transient ledger is separate from resident model weights
and must not be interpreted as total GPU allocation. Original physical/kernel,
owner and positive completion guards remain. Both actual native display frames
were viewed: CPU/GPU identifiers, synchronized UTC time, token speed and the
Q8/BF16-PLE caption are visible; unavailable utilization counters remain dashes.

The driver stays at `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`,
actual linked archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remain disabled. Quantizer sources are pinned
to `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`. The model receipt is
`8b67b85e6cb2f3fd910e900b0299c3325d8717814f0ffab9ef505cab1dfc686b`.

All544 Q8 payload hashes,50 serialized headers, every unchanged tensor and the
complete1256-tensor source mapping pass host checks. Native CPU publication
seals59 new files in four bounded batches with whole SHA256/identity/EOF and
positive8 MiB Direct retirement. A verified, host-archived, unreferenced3.34GB
legacy interrupted transfer was reclaimed; current model sources were retained.
This changed the actual storage state after staging failures. Reported statfs
availability alone did not explain the earlier ENOSPC responses.

The normal runner encountered a reused host output name before launch. It
reused the completed upload and used a fresh verifier, without retransmission.
The headless collector's historical output-delivery column was absent; the
completed eight-request result was collected as headless without repeating any
inference or changing numerical/answer gates. All failures and recovery evidence
remain private. No CI, agents, reboot, forced signals or GPU reset were used.

Machine-readable measurements are in
`resident-all-Q8-results-20261031.json`; final placement is recorded in
`resident-all-Q8-adoption-20261031.json`. Production admission checks that exact
completed report through `tools/resident_all_q8_production.py`.
