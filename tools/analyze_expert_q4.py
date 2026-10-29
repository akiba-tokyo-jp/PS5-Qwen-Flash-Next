#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize closed actual-weight GPU Q4 components without a model speed claim."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import record,require,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('case','encoder','json','markdown'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=json.loads((a.case/'native-model-terminal.private.json').read_text());closed=json.loads((a.case/'restored-complete.private.json').read_text())
    encoder=json.loads(a.encoder.read_text())
    require(r['schema']=='ps5-qwen-expert-q4-fixture-result-v1' and r['completed'] and len(r['cases'])==27 and r['GPU_graphs']==324 and
        r['all_outputs_reference_valid'] and r['all_backends_positively_retired'] and r['source_descriptor_and_scratch_retired'] and
        r['device_ledger_live_bytes']==0 and r['source_workers_stopped'] and not r['quantized_activations'] and not r['model_loaded'],
        'Complete actual-weight Q4 component result required')
    require(closed['completed'] and closed['CPU_title_normally_closed'] and closed['exact_prior_configuration_restored'] and
        closed['full_native_readback_SHA256_identity_EOF_verified'] and not closed['production_adopted'],'Positive normal close and exact BF16 restoration required')
    widths=[]
    for width in (1,2,4):
        rows=[x for x in r['cases']if x['width']==width];require(len(rows)==9,'Every layer/projection group is required')
        item=dict(width=width,cases=9)
        for key in ('delivery_us','compute_us','delivery_and_compute_us'):
            values={fmt:[s[key]for row in rows for arm in row['arms']if arm['format']==fmt for s in arm['samples']]for fmt in ('BF16','Q4_0')}
            require(all(len(x)==36 and all(v>0 for v in x)for x in values.values()),'Four samples per format and case required')
            item[key]=dict(BF16_mean=statistics.mean(values['BF16']),Q4_0_mean=statistics.mean(values['Q4_0']),
                BF16_over_Q4_0_time=sum(values['BF16'])/sum(values['Q4_0']))
        widths.append(item)
    report=dict(schema='ps5-qwen-expert-q4-components-review-v1',completed=True,component_only=True,actual_model_tokens_per_second_measured=False,
        GPU_case=7560,formats=['BF16','Q4_0'],effective_Q4_bits_per_weight=4.5,matrices=27,GPU_cases=27,GPU_graphs=324,
        groups=dict(layers=[0,23,47],projections=['gate','up','down'],Experts=[0,257,511],selected_IDs=10,unique_IDs_per_graph=3),
        widths=widths,maximum_absolute_GPU_F64_reference_error=max(x['maximum_absolute_GPU_reference_error']for x in r['cases']),
        F32_activation_input_preserved=True,per_format_F64_reference=True,quantization_is_lossy=True,full_model_answer_quality_qualified=False,
        per_matrix_BF16_bytes=3276800,per_matrix_Q4_bytes=921600,Q4_over_BF16_payload_ratio=0.28125,
        theoretical_contiguous_Q4_slots_at_current_1333739520_byte_budget=481,actual_full_model_Q4_cache_qualified=False,
        PS5_CPU_encoder_matrices_exact=encoder['matrices'],PS5_CPU_mean_encode_ms=encoder['mean_encode_ns']/1e6,
        exact_BF16_restored=True,production_quantization_adopted=False,CI_runs=0,
        driver=dict(repository='akiba-tokyo-jp/PS5-Vulkan-Inference',revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',profile='cumulative-idle',
            native_archive_sha256='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925',persistent_caches_enabled=False))
    write_json(a.json,report)
    table='\n'.join('| '+str(x['width'])+' | '+ ' | '.join(f"{x[k]['BF16_over_Q4_0_time']:.4f}x"for k in('delivery_us','compute_us','delivery_and_compute_us'))+' |'for x in widths)
    a.markdown.write_text('''# Expert-only Q4 component qualification, 2026-10-29

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
'''+f"`{report['maximum_absolute_GPU_F64_reference_error']:.12g}`"+'''. This is arithmetic
correctness, not equality of Q4 and BF16 weights or model logits.

Each case uses four warmups and BF16/Q4/Q4/BF16 arms with two samples per arm.
The following ratios divide BF16 elapsed time by Q4 elapsed time. Delivery
includes Direct reads, tensor upload, synchronization and completion checks;
compute includes the graph and its positive completion checkpoint. Full payload
hash work is outside the timed delivery. These are component measurements,
not model tokens/s, cold SSD bandwidth or a whole-application speedup.

| Width | Delivery ratio | Compute ratio | Delivery + compute ratio |
| --- | --- | --- | --- |
'''+table+'''

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
'''+f"`{report['PS5_CPU_mean_encode_ms']:.6f} ms/matrix`"+'''. Host and console conversion
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
''',encoding='utf-8',newline='\n')
    print(json.dumps(dict(closed_Q4_GPU_cases=27,GPU_graphs=324,component_summary_written=True,model_speed_claim=False)),flush=True)

if __name__=='__main__':main()
