# Hardware-bound performance host checkpoint

This is the initial host-only snapshot from2026-11-02. It is preserved as
historical evidence. Subsequent native comparisons, the adopted R1 deployment,
and open qualifications are in the
[current campaign results](native-performance-comparisons-20261102.md).

The campaign is **incomplete**. No new optimization has been adopted, and no new
PS5 speed or model-quality comparison has run. The owner confirms that recovery
is unavailable and asks for caution. Current production remains source
`2b683814c9b6ed18c13352963c0a989f9e4d0b15`, SELF
`56c29e9c871f5b068181675353c9098a4ff3513c29b00bb5dc4c1840897c0126`,
driver `872cc1264ad8ba5d6b888b092968fa5858a38c58` / `cumulative-idle`,
with persistent shader and pipeline caches disabled.

## Console prerequisite

Read-only scope63000 completed positively: compatibility runtime absent, zero
native owners, matching before/after process snapshots, helper PID retired and
both remote helper files removed. Initializer requests, title launches and GPU
calls were all zero. The previously interrupted initializer was not replayed.
These observations do not qualify native launch or clear its historical missing
return. No new recovery or unchanged refused-launch probe was submitted.

## Candidate dispositions

| Candidate | Work completed in this scope | Remaining status |
| --- | --- | --- |
| Q1: shared Expert Q8_0 to Q4_0 | All144 original BF16/control payloads authenticated; pinned and independent encoder bytes match; independent GGUF prefix/extent checks pass | Native source composition, relink, quality and speed unqualified |
| Q2: routed Gate/Up Q2_K to IQ2_XXS | All96 tensor row widths fit;15 synthetic codec cases pass C/Python decode equality and deterministic encoding | Real activation importance, indexed PS5 shader and model quality/speed missing |
| Q3: routed Down Q2_0 to IQ2_XXS | All48 widths checked:640 is incompatible with256-element blocks; padding to768 adds10% payload | Reject the direct-format and simple padding proposals; custom layouts/kernels remain separate research |
| R1: record/diagnostic cost | Optional request-end token synchronization implemented; short-write/EINTR/sync-failure/bounds controls pass; native POSIX adapter compiles | Default remains per-token; durability tradeoff and native whole-request speed unqualified |
| G1: GPU ranking/all-hit continuation | Actual final archive and bridge audited; old indirect-capability exclusion corrected | GPU-generated indirect capability and coherent miss/resume implementation unqualified |
| P1: post-trunk prefill output selection | Exact selected GDN/HC model source reconstructed; control/candidate PS5 objects compile | Engine integration, complete state/route equality and native timing pending |
| I1: Q2 staging/read overlap | Existing predictor audited:10-Expert geometry is incompatible with current2-Expert decode | New staging implementation and native demand-wait comparison absent |
| S1: persistent/prewarmed MTP | Existing auxiliary path audited; it clears state before each proposal | Persistent state, catch-up/rollback and whole-cost native comparison absent |

An audited prerequisite is not a completed implementation or a measured speed
result. G1/I1/S1 have not been tested as working new native implementations.

## Quantization evidence

Q1 changes exactly the three shared projections in each of48 trunk layers.
The conversion reads the authenticated **original BF16**, rather than requantizing
the existing Q8 bytes. Logical selected payload falls from250,675,200 to
132,710,400 bytes:117,964,800 bytes /112.5 MiB saved. The aligned candidate pack
is134,467,584 bytes; that physical pack size is separate from logical payload.

All144 encoded payloads are byte-identical between the pinned GGML encoder and
the independent C encoder. A separate parser checks48 GGUF prefixes covering
1171 tensors, all new pack ranges/hashes/padding and unchanged metadata for the
other1112 model tensors. The model still contains1256 tensors. This does not
rehash every unchanged model payload. Whole-weight NRMSE ranges0.0900747961 to
0.1217650355; current Q8's maximum is0.0079348565. Weight reconstruction error is
not a generated-answer quality score.

The generated tensor metadata retains the parent precision recipe and is
**not a deployable native model receipt**. Its source delta explicitly records
`native_source_integration_complete=false`. Existing109 Q4 tensors and the
unchanged parent parts need a checked composed native source plan, not a
replacement receipt that silently discards their overlays.

IQ2_XXS requires activation importance in the pinned quantizer. Uniform importance
was used only for15 invented codec fixtures, never for encoding real model
weights. Gate/Up row width2560 fits256-element blocks. Across96 tensors the
format-only payload would fall26,424,115,200 to20,761,804,800 bytes (21.4286%),
excluding alignment and other model data. This is a size calculation, not a
speed or accuracy result.

Down row width640 does not fit that format. Padding to768 would increase its
48-tensor payload from11,324,620,800 to12,457,082,880 bytes. Supporting another
layout would require matching activation/indexed-kernel changes; this is an
implementation constraint, not a physical hardware limitation.

## Non-quantization evidence

R1 keeps the default independently durable tokens. The explicit experimental
`request_end` policy writes the same complete JSONL records and synchronizes at
successful request close. In the256-record synthetic test, sync calls change
256 to1. No wall-time improvement is claimed. An interrupted request may lose
its unsynchronized tail. Short writes are completed without duplication; failed
or uncertain writes/synchronization latch failure and cannot become successful
through retry. Explicit close releases the owned descriptor even on a sync
failure. Bounds are configurable rather than represented as hardware limits.

P1 reconstructs the current model provider from the pinned source and existing
GDN/HC transformations. Its SHA256 matches the selected source
`e4cca6f236e35dcce4f3f992d35df49a453c70e962b95090f09458520b9ff02c`
before modification. The candidate retains the full last FFN/cache graph, then
selects output rows after the trunk while preserving masked/unmasked NextN
shapes. Both actual model-source units compile for PS5. No runnable app has been
relinked and no boundary-length, continuation, prefix or speculative state
comparison has run; compilation does not establish numerical equivalence.

G1's actual archive is
`a325dcd4584b1f1fccc6b46e90faa081ca86d18544aca610efea9e3ca3774f32`.
It defines `radv_CmdDispatchIndirect` / `radv_CmdDispatchIndirect2KHR` and does not
define `ps5vk_CmdDispatchIndirect`. The exact selected bridge forwards unwrapped
device entries to RADV. Matching Mesa source constructs a GPU address and emits
`PKT3_DISPATCH_INDIRECT`. Therefore the older lightweight `ps5vk` CPU-argument
screen in `post-top2-indirect-feasibility-20261101.json` is not evidence that the
current linked path lacks GPU-generated indirect dispatch. Native capability is
still untested. Existing scheduler-owned map reuse and same-generation idle
certificate reuse are already adopted features, not new gains in this scope.

I1 must stage predictions separately from authoritative cache residency, using
actual source/allocation leases and publishing only on real demand. Enabling
the existing10-Expert predictor unchanged would be a different and invalid
comparison. More read workers alone do not establish overlap for a layer with
zero or one miss.

S1 is distinct from the historical stateless MTP comparison, which took
26.33546% longer overall. Reusing auxiliary KV without tracking accepted bonus
tokens and rejection state would change the draft history incorrectly. A new
implementation must include prewarm/setup, catch-up, rollback and target
verification in whole-request timing. It has not been implemented or run here.

## Reproduction and retention

Use the checked-in tools, the pinned upstream tree, retained current provenance
and a fresh output directory. The tools perform conversion, synthetic numerical
checks and target compilation; none performs learned host-model inference.

1. `tools/build_performance_quantizer.py`: build the pinned host codec reference.
2. `tools/prepare_shared_q4.py` then `tools/check_shared_q4.py`: original-weight
   conversion and independent metadata/extent verification.
3. `tools/check_iq2_candidates.py`: exact current geometry and synthetic codec
   checks; no real IQ2 model is produced.
4. `tools/check_performance_ledger.py`: fault injection and native adapter compile.
5. `tools/prepare_prefill_post_trunk.py`: exact-source reconstruction and both
   model-source target compiles.
6. `tools/audit_performance_sources.py`: exact archive/bridge and remaining
   prerequisites. This is a source audit, not a native implementation test.

`tools/observe_performance_scope.py` records an explicitly requested fresh
read-only scope; it is not a recovery command. Scope63000 is consumed. Do not
replay an unchanged observation/launch or initialize the runtime automatically.

The initial standalone codec configure, missing exception flags in the first
adapter check, and inclusion of the49th MTP layer in the first IQ2 inventory
failed on the host. Their corrected checks pass. None was a PS5 execution.
CI, restart, forced close/reset and persistent caches were not used. After
recording this checkpoint,153 generated trial files (141,415,585 logical bytes)
were removed, including the temporary binaries and Q4 pack. Before/after whole
SHA256 checks match for all seven current PC deployment files, including the
expected SELF. The owned scratch directory is absent. No console operation was
needed for this retirement. Reproduction requires rebuilding the candidates;
the current deployment and required live model/startup assets are preserved.
