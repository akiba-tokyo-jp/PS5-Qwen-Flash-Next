# Expert-only Q4 component qualification, 2026-10-29

This is the historical component checkpoint. The subsequent complete-model
conversion and actual PS5 inference comparison are recorded in
[the model report](expert-q4-model-20261029.md). Remaining-work descriptions
below describe the state at this component checkpoint.

The owner selected four-bit validation only. Q4_0 keeps 32 values in 18 bytes
including the FP16 scale (4.5 effective bits/value). Both original Expert row
widths, 640 and 2560, are divisible by 32; Q4_K's 256-value blocks do not divide
640. Every Expert and the original top-10 routing remain required. Non-Expert
weights and F32 KV remain unchanged.

## Closed PS5 component result

Case 7560 completed 27 actual-weight cases and 324 GPU graphs. It uses layers
0/23/47, gate/up/down, three original Experts per group, duplicate/edge IDs and
widths 1/2/4. BF16 and Q4 each match their own independently decoded F64
reference; the maximum absolute GPU/reference error was
`1.76573294874e-09`. This is arithmetic
correctness, not equality of Q4 and BF16 weights or model logits.

Each case uses four warmups and BF16/Q4/Q4/BF16 arms with two samples per arm.
The following ratios divide BF16 elapsed time by Q4 elapsed time. Delivery
includes Direct reads, tensor upload, synchronization and completion checks;
compute includes the graph and its positive completion checkpoint. Full payload
hash work is outside the timed delivery. These are component measurements,
not model tokens/s, cold SSD bandwidth or a whole-application speedup.

| Width | Delivery ratio | Compute ratio | Delivery + compute ratio |
| --- | --- | --- | --- |
| 1 | 1.1780x | 1.0742x | 1.1603x |
| 2 | 1.4094x | 0.9926x | 1.3343x |
| 4 | 1.3993x | 0.9820x | 1.3227x |

Both formats retain F32 activation input. The first fixture, case 7520,
returned a BF16-reference mismatch before the Q4 timing comparisons. Its BF16
control used generic matrix dispatch instead of the production-equivalent F32
indexed-vector path. The corrected fixture selects the existing indexed shader
for the explicit ten-slot control geometry. Numerical tolerance was unchanged.
Both cases normally closed and restored the exact BF16 production SELF and
five settings; the passing case positively retired all backend/source owners.

## Conversion and remaining model gates

An original Expert matrix occupies 3,276,800 bytes; Q4_0 occupies 921,600 bytes,
or 28.125%, before alignment. An independent host C encoder matched pinned
ggml Q4_0 bytes on all 27 matrices. A read-only PS5 CPU probe also matched all
27 complete payload SHA256 values, with mean encoding time
`6.515734 ms/matrix`. Host and console conversion
remain separate from learned inference.

`expert_q4_geometry.h` checks compressed block/read alignment and bounds. The
same 1,333,739,520-byte aggregate budget can theoretically hold 481 contiguous
Q4 slots plus the guard plane, versus 134 selected BF16 slots. This capacity
has not yet been qualified in a full Q4 model context. Rounding a padded Q4
stride only to 16 KiB is invalid because Vulkan indexes 18-byte blocks.

The strict separate Q4 receipt/footprint validator passed metadata controls and
six refusal controls. Full-model conversion, mixed-source loading, accepted
decode throughput and answer-quality comparison remain required before Q4
production adoption. The BF16 production remains the selected rollback/control.

## Source changes

- `tools/expert_q4.py`: pinned-format inventory, original samples and independent decode.
- `tools/expert_q4_quantize.c`: bounded independent BF16-to-Q4_0 encoder.
- `tools/convert_expert_q4.py`: separate host outputs, bounded batches and completed-file reuse.
- `native/qwen_flash_next/expert_q4_encode_probe.cpp`: read-only PS5 CPU byte conformance.
- `native/qwen_flash_next/expert_q4_local_convert.cpp`: separate CPU-only local copy with complete Direct part readback; never changes original sources.
- `native/app/expert_q4_fixture.cpp` and `tools/build_expert_q4_fixture.py`: actual-weight native GPU comparison, F32 input dispatch and positive retirement.
- `native/app/expert_q4_receipt.h`: separate 147-Expert / 1256-tensor mixed-precision gate; the original BF16 gate remains unchanged.
- `tests/expert_q4_geometry.cpp` and `tests/expert_q4_receipt.cpp`: manual native geometry, footprint and rejection controls.

Pinned llama.cpp: `0a1ef309cdbb9f2024f58a38fb4c42352c5db569`.
Driver: `872cc1264ad8ba5d6b888b092968fa5858a38c58`, `cumulative-idle`, native
archive `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
Persistent shader/pipeline caches and CI remain disabled.
