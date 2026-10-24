# Lossless embedded shader storage

The native CPU phase control lost3628 free16KiB pages during five seconds
without journal writes or virtual reservations. A subsequent256 journal-only
lines changed none of the observed VM populations. The unchanged2974-page
startup target refused before the actual rehearsal. See
[the measured control](native-CPU-phase-20261024.json). This rules out those
later operations as necessary triggers in this case. It does not identify the
kernel backing object. The controller's colliding failure-record name bypassed
its cleanup; separately reviewed ordinary close, exact original restoration,
full readback and fresh idle CPU guards subsequently passed. The next controller
must bind six cleanup and four exception-path controls to its final source.

The current native image contains38712204 bytes of original SPIR-V in1527
resources. Host analysis found a lossless framed representation of12838336
bytes. Reducing the image is an application-footprint experiment, not a proven
solution to kernel memory pressure or an inference throughput result.

The application keeps every original shader, entry point, feature choice and
instruction. The generated resource provider is separate from the seven-object
model I/O manifest and replaces only the Vulkan shader-input bridge and its
resource definitions. The driver, engine archives, model weights, precision,
memory predicates, reserves, wait bounds and persistent-cache policy remain
unchanged. Persistent shader and pipeline caches stay disabled.

Before Vulkan initialization, the native CPU gate restores every original
resource and compares its full SHA256 and byte count. It also checks every
selection-table pointer and length against the original source and compiled
archive. Some original external-length tables are filled by static constructors;
their on-disk zero values must be distinguished from unsupported null entries.

One fixed tracked Direct buffer holds the largest original shader. Standard
inflate symbols come from the unchanged selected archive, with a separate native
ABI and complete CPU roundtrip gate. No model or source-read buffer is added.
The decoder holds an exclusive lease across restoration and the existing
CreateShaderModule call. The actual linked Mesa common module provider copies
pCode before returning success. Only that positive completion permits reuse.
Failed or unknown ownership quarantines the codec and retains its backing until
ordinary OS close. No retry, fallback, resource eviction or memory reclamation
is introduced. All original startup and whole-rehearsal gates still follow.

Host packaging and codec controls do not qualify native CPU execution, memory
recovery or full-model generation. A distinct native CPU case must precede a
distinct complete inference comparison and original restoration sequence.
