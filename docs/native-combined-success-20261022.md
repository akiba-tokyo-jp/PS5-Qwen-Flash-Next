# Physical BF16 computation, native display and local UTC admission

The physical PS5 completed one unchanged BF16 32x16/F32-vector graph with all
16 outputs exactly matching the reference, maximum absolute error 0, and the
fixed 1e-5 absolute/relative tolerances. The fixture interval was 119.072072 ms;
it is not model tokens/s. Positive device idle and completed-epoch retirement
preceded native VideoOut initialization. The first monitor frame completed with
two fixed 16 MiB buffers. No learned model was loaded.

The exact application source was
`e60e947e0954618a05543ee8ecbc3d041e3e1ee2`.
The source PIE SHA256 was
`b8993c2dc2602c62dde89661f94dca3a385ace3001ff48174532b11277f2ad59`;
the 58,299,159-byte SELF SHA256 was
`54c2803c6fce4a654f5c351878eb717dfa0f58c874868b14c0d868fa7630fea9`.
Host checks passed all 289 actual-module imports, six actual common Vulkan
callback targets, SELF integrity, six reconstructed segments and three embedded
SPIR-V modules. The prior successful no-display SELF was bound into the private
policy, which also fixed one graph, the 32 MiB display limit and display startup
only after the current graph's positive completion. Full inference was rejected.

The selected driver remained PS5-Vulkan-Inference revision
`872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`, final native
archive SHA256
`b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent caches remained disabled. As in
[the preceding compute admission](native-bf16-success-20261022.md), BF16 storage
was widened to F32 by the shader; native BF16 arithmetic was not advertised.

A fresh guarded CPU observer supplied a second-resolution device epoch within
a host observation interval. The application corrected its own UTC anchor and
advanced it monotonically, without setting the console system clock. Initial
uncertainty was 2,209 ms. Two HTTP 200 status responses from the same exact native
owner both fell within their host observation intervals plus that uncertainty;
their reported epoch advanced 1,388 ms. The native display and HTTP service use
the same clock. This admits short-interval calibration, not long-term drift.

The passive monitor reported 16 CPU threads, `PlayStation 5 GPU (RADV NAVI21)`
and startup memory information. GPU free/total values are startup samples, not
live utilization. CPU/GPU percentages and inference tokens/s remained unavailable.
The host raster was visually inspected separately; this console result uses
VideoOut's positive first-frame completion, not a captured TV screenshot.

The validation title was normally closed. Fresh unchanged CPU guards passed.
The exact original SELF was restored and fully read back, then ordinarily
launched once using a freshly generated native-only one-use credential.
Its 14 established numerical gates, 16 fusion checks and 20 selected kernel
checks passed. It was normally shut down without model load or generation.
Final fresh CPU observations confirmed unchanged boot/services, equal process
snapshots, zero native owners and no big application. A final full readback
matched original SHA256
`2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d`.
The two completed Qwen journals were copied with their metadata restored.
No force-kill, GPU reset, firmware change or ambiguous launch retry occurred.
The task retains its console reservation.

Manual host checks for this source passed 48 Python cases, 73 negative native
policy cases, real raster/tile/startup/clock tests, VideoOut failure-retention API
stubs and localhost HTTP/no-model rejection tests. None performs learned host
inference. The committed console/deployment flags and CI remain disabled.

Full original-model acquisition, checksumming, conversion, model mapping and
resident-memory admission remain separate requirements. No Qwen generation or
model tokens/s has been demonstrated. The historical failed attempts and shared
driver's failed LLM CPU-reference baseline remain preserved.
