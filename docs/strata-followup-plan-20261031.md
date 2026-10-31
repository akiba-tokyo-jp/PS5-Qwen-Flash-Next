# Strata follow-up: measured native integration

The four candidates are cache capacity, device checkpoint allocation/metadata
reuse, independent checkpoint copy batching, and single-token convolution/SiLU/
GDN-input normalization fusion. The original model payloads and authorized
Expert Q2/resident Q8 precision remain unchanged. The small PLE convolution stays
BF16; the trunk convolution used here is originally F32, not a PLE conversion.

Use driver revision `872cc1264ad8ba5d6b888b092968fa5858a38c58`,
`cumulative-idle`, original ABI, without persistent shader or pipeline caches.
Keep the original physical reserves, OS watermark, loading/context predicates,
512 MiB CPU cap, 48 MiB workspace cap, and every positive completion boundary.
Reboot is unavailable. A refused scope is consumed; reduce application-owned
consumption before proposing a different scope. Do not replay an unchanged
refusal or force a console reset, signal, GPU release, or recovery probe.

## Candidate endpoints

1. Compare 3072/3424 active cache slots in the same fully priced 3425-plane
   banks. Distinguish TTFT, decode, whole response, physical reads and calls.
   Both arms share the larger allocation; this isolates the active-capacity
   effect rather than reproducing the installed 3073-plane footprint.
   Keep decode-priority3072 as the production default if3424 regresses decode,
   even when its TTFT/whole-response improvement is real. Retain the implemented
   larger-cache experiment and disclose this tradeoff.
2. Retain device capacity in2 MiB bins within the original136 MiB checkpoint
   bound. Reuse the GGML metadata arena and vector capacity, including monotonic
   growth. Validate source identity, changed chunking, all bytes and canaries.
   Preserve unsupported-layout fallback and the existing context ABI.
3. Batch independent F32 copies within one capture or one restore, wait once
   for that copy group, and retain every original outer completion. Never batch
   across token dependencies. Verify all state bytes, complete F32 continuation,
   application cursor, ordered Expert routes, tokens and output.
4. Preserve convolution4, SiLU, RMS normalization with epsilon/128 and the
   subsequent F32 scale. Qualify all recurrent state/history/weights/snapshot
   canaries against F64, including zero and epsilon-dominated heads. The
   multi-token and unsupported-shape paths retain the original operations.
   Integrate eligible ranges in Vulkan's graph optimizer and its existing
   `add_alloc_dep` interface before allocation. Protect every member in generic
   real/view pulling passes; keep the original runtime overlap rejection.
   The original SPIR-V pool remains immutable. Admit the one additional shader
   by exact address, size and SHA256 before Vulkan use.

## Measurement and adoption

Use matched A-B-B-A cold/retained pairs on one model load. GPU decode is the
primary fusion endpoint: require positive effects in both temporal directions,
an average effect above that condition's measured A/A spread, and whole time
within the observed A/A variation. Do not invent a fixed percentage floor.
Separate fixture/operator time and deliberately injected state work from
ordinary model throughput. Never qualify a kernel whose execution counter is0.

All produced full-vocabulary rows must be finite. Byte-copy changes require
exact F32/routes/tokens/output; arithmetic fusion additionally uses the F64
oracle and four fixed semantic tasks. KL/top1 are diagnostics, and maximum
logit difference alone is not a rejection criterion. These finite tasks do not
establish general model quality or sustained-service reliability.

Commit the exact implementation before the normal relink. Complete the normal
three-request/API case, view both positively completed native frames, retire all
owners positively, close normally and restore the exact control. Finish the
declared observer POST/frame sequence before the read-only collector takes its
writer lease. Production placement then verifies both programs and both five-
setting sets through native whole SHA256, stable identity and EOF, with fresh
idle ownership. Preserve the immediate control and record actual relink source
revision separately from later documentation/placement commits. CI stays off.
