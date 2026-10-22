# BF16 Vulkan fixture passed on the physical PS5

The corrected application executed one BF16 32x16 matrix/F32-vector graph on
the physical PS5. All 16 F32 outputs matched the independently checked reference
exactly, with maximum absolute error 0. The unchanged absolute and relative
tolerances were both 1e-5. The reported fixture interval was 117.013471 ms;
this includes a small admission operation and is not model tokens/s.

The application source was `f645d9303f105e363d00dc42fd72c4d3a25cb476`.
The packaged SELF SHA256 was
`5c808d43cbe49f5d790707cc7fd67055b8de3e4bc1aa860c57ffa30c9ea6d427`;
the source PIE SHA256 was
`e009510a752e6e313d7e492dc13a98a556325d1a83c628aad1c7fa69d2cc9507`.
The application retained the selected native Vulkan archive with
`--whole-archive` and passed the six actual callback-target checks before
packaging. This qualified the application link correction described in
[the dispatch discovery](native-dispatch-discovery-20261022.md).

The driver source remained PS5-Vulkan-Inference at
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
The final native archive SHA256 remained
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader and pipeline caches were disabled. The device reported
`PlayStation 5 GPU (RADV NAVI21)`, 32-wide subgroups and no native BF16 arithmetic
feature. The admitted shader preserves BF16 storage and widens values to F32
for arithmetic; this result does not claim native BF16 matrix units.

CPU prerequisites, sole AGC8 ownership, Vulkan discovery and backend setup,
upload, compute, synchronization, readback, positive device-idle confirmation
and completed-epoch retirement all passed. The measured 250 ms sleep interval
was 250.115427 ms. Native VideoOut was disabled for this compute admission.
Persistent driver allocations remained owned until ordinary title close.

The passive monitor returned HTTP 200 twice from the same verified native owner.
It reported 16 logical CPU threads and startup GPU memory information. The
reported epoch advanced 10,962 ms between samples. CPU/GPU utilization and
generation tokens/s stayed unavailable. The device wall clock differed from
the host by approximately 11 minutes; UTC accuracy is not qualified by this test.
Combined native VideoOut and Vulkan execution is also a separate remaining gate.

The candidate was normally closed. The exact original executable was restored
and fully read back, ordinarily launched with a newly generated native-only
one-use credential, numerically readmitted, then normally shut down. Its
14 established numerical gates, 16 fusion checks and 20 selected kernel checks
passed. A fresh CPU-only observer confirmed the unchanged boot and management
services, equal process snapshots, no native title and no active big application.
A final complete original-executable readback matched SHA256
`2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d`.
No force-kill, GPU reset, firmware change or ambiguous execution retry occurred.
The task's console reservation remains held for subsequent staged validation.

No learned model was loaded or executed in this fixture. Full Qwen inference,
resident-memory admission and tokens/s remain unqualified. Original checkpoint
acquisition, complete checksumming and precision-preserving conversion continue
as a separate bounded host preparation batch. Earlier failed attempts and the
shared driver's failed LLM CPU-reference baseline remain preserved.

See [the machine-readable result](native-bf16-success-20261022.json).
