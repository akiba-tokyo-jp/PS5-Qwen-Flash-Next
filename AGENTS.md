# Project instructions

Write project documentation, diagrams, code comments and program messages in English.
Keep conversation in the owner's preferred language.

The objective is original-precision Qwen3.8-Flash-Next inference on one PS5.
Use the pinned original BF16 weights. Do not substitute a quantized checkpoint,
prune experts, omit required model components, or use learned PC/cloud inference
as a substitute for console inference. Host builds, metadata processing, format
conversion preserving precision, and offline numerical verification are allowed.

Use the owner's current PS5-Vulkan-Inference driver, with an explicit profile,
source revision and archive digest. Preserve the upstream licenses and notices.
Keep weights, runtime binaries, private console evidence, endpoints, credentials
and credential hashes outside commits. Build and model data belong on the data disk.

GitHub Actions and other CI must remain disabled. Use focused manual checks.
Do not spawn agents or delegate without the owner's explicit authorization.

## Current development restriction

Driver qualification is still in progress. Develop the application in this
private GitHub repository and use manual host builds and tests. Do not access
the PS5, inspect its processes, close applications, upload files, install,
launch, release, or run console validation during this phase. Do not change
the driver repository or advance its dependency pin as part of application work.
The existing driver pin is a development dependency, not a qualified release.
Resume console work only after driver qualification is confirmed complete.
An application merge or successful host test does not satisfy that condition.
Keep config/development.json in the restricted state until then.

Use one identified native GPU title. Close existing applications through the
ordinary OS path. Never force-kill, reset the GPU, change firmware, or release
uncertain in-flight resources. Record compilation, console execution and model
quality as separate outcomes. Do not present a fixture or model load as completed
full-model inference.
