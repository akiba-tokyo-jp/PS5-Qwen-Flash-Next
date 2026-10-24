# Physical PS5 original-weight operation admission

The distinct no-display candidate passed one original-weight BF16 matvec plus
F32 RMS/SiLU graph on the physical PS5. All 5,136 outputs passed finite checks,
the unchanged per-cell `1e-5 + 1e-5 * abs(reference)` bound and normalized RMSE
at most `0.01`. This is component admission, not complete Qwen inference.

| Operation | Outputs | Maximum absolute error | Normalized RMSE (ratio) |
| --- | ---: | ---: | ---: |
| Original BF16 2560x16/F32 matvec | 16 | 7.450580596923828e-8 | 4.377481132072667e-8 |
| F32 RMS normalization | 2,560 | 9.887169261091344e-8 | 6.589840031667897e-8 |
| F32 SiLU | 2,560 | 1.4858969255016063e-7 | 1.0101010878474527e-7 |

The 81,920-byte slice is unchanged original BF16: expert 0, gate rows 0..15,
2,560 columns. Its complete original source shard was independently hashed
before extraction. PS5 scalar-double references cover the matvec; all RMS/SiLU
outputs were additionally checked against an independent analytic calculation
on the host using the deterministic nonlearned input. No learned PC/cloud
forward evaluation occurred. BF16 storage widens to F32 in the shader.

The diagnostic interval was **194.824848 ms**, covering CPU reference/setup,
upload, one graph, readbacks and numeric metrics before deferred retirement.
It is neither isolated GPU-kernel time nor tokens/s. The application observed
positive device idle, a quiet producer and matching completion-epoch retirement.
Two passive HTTP 200 samples came from the same exact owner; reported UTC
advanced 1,767 ms, with 2,779 ms initial calibration uncertainty. No model was
loaded, no generation request was sent, and tokens/s remained unavailable.
Native display was disabled in this stage; the earlier combined display result
remains a separate admission.

Runtime source is `fb941b0492b5ee7e3697c1b0c1f3e021cd4f4abf`, unchanged through
this test. Host linker controls are from `3ea28c3`; the successful link used one
worker and an explicit 1,800-second host deadline. The earlier 600-second host
link failure is preserved and caused no console launch. No console timeout or
numerical threshold changed.

The native PIE SHA256 is
`78b087402539d0551067e1494965d6fa43fd96f4d0e6373aba60c82442478768`.
The 58,339,495-byte SELF SHA256 is
`5abd9fab586ed30431ddf26a95a1a112065f2958c6cbbd0a41b107a62c67da47`.
All 289 actual-module imports, six callback-table targets, SELF integrity, six
segment roundtrips, three linked BF16 variants and both actual F32 RMS/SiLU
SPIR-V modules passed. The selected source remains PS5-Vulkan-Inference
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, native archive
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches remained disabled.

The server rejected a read-only FTP `LIST` directed at a file during staging.
The completed transfer was not repeated. Parent-directory listing supplied the
same required regular-file/readability checks, and full payload/configuration
readbacks passed before publication. This protocol limitation and its evidence
are preserved; it caused no GPU attempt or relaxed gate.

The validation title was normally closed. The exact original executable was
restored, numerically readmitted, normally closed and verified again by fresh
unchanged boot/service/process guards plus a complete post-shutdown readback.
No native owner remained. Both owned Qwen journals were captured with their
metadata restored. No gateway, image generation, force-kill, GPU reset or
ambiguous execution retry occurred. The task retains the reservation.

Whole-checkpoint preparation, complete model transfer/mapping/residency, all
remaining Qwen operations, model quality and tokens/s remain unqualified.
The shared historical LLM CPU-reference NRMSE remains 1.159915%, failing its
fixed 1% limit. Committed console/deployment flags, release and CI stay disabled.
Raw readbacks, logs, addresses, credentials, binaries and weights stay outside
Git. The adjacent JSON is a sanitized summary of this completed scope.
