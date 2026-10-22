# Bounded synthetic CPU hash timing

The complete original payload is approximately 359 GB. Its native SHA
verification deadline needs a measured CPU cost before full-file admission.
`tools/build_model_hash_probe.py` builds a separate CPU-only timing payload;
it does not load model weights, read file payloads, initialize Vulkan or launch
a native title. Only its exclusive task-owned result log is written.

The probe reuses the exact compiled SHA256 object from the previously qualified
native application. This preserves the production implementation and compiler
optimization, rather than comparing a different crypto library. The source is
the pinned engine's unchanged public-domain Igor Pavlov implementation.
Independent Python SHA256 supplies the expected digest of one synthetic 1 MiB
byte-pattern buffer. Every pass verifies that digest. At most 512 passes run,
with a 10-second target and 15-second completed-boundary deadline. Guarded native
timer storage rejects clobber, invalid fields, reversal and insufficient timing.

Host API checks passed for the actual probe source, including wrong digests and
timer faults. The native payload linked with the established credential-preserving
CPU helper CRT. All 14 dynamic imports resolve through the exact previously
audited real runtime providers; weak SDK exports cannot satisfy that check.
The initial host build lacked a host-only include path; its failed output is
preserved separately. No console operation occurred during either host build.

Physical execution requires the existing unchanged reservation/restoration proof,
fresh idle CPU/boot/service guards, a source-stable probe manifest, and the exact
known credential-preserving CRT hashes. Execute the new nonce once. Require its
complete matching result and another fresh unchanged CPU observation afterward.
Hold the model data writer lease so this short probe cannot overlap subsequent
directory preparation or transfer. The original SELF and app directories are
untouched. Any uncertain result remains preserved without automatic retry.

This measures hashing of cached synthetic RAM only. Disk throughput and complete
model integrity remain unmeasured. A whole-payload time extrapolation is a
compute-only estimate; it must not become a file-integrity or inference result.
