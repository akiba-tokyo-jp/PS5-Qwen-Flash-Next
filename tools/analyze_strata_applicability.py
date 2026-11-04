#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind Strata eligibility conclusions to the selected sources and completed runtime."""
import argparse
from pathlib import Path

from analyze_headless_numerics import positive
from build_performance_quantizer import record
from start_success_route import load, need, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'case', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    selected = load(args.current / 'provenance/selected-entry-build.private.json')
    profile = load(selected['application_policy']['path'])
    entry = Path(profile['source']['path'])
    need(record(entry) == profile['source'], 'Selected original entry changed')
    text = entry.read_text(encoding='utf-8')
    flags = ('GGML_VK_DISABLE_INTEGER_DOT_PRODUCT', 'GGML_VK_DISABLE_COOPMAT', 'GGML_VK_DISABLE_COOPMAT2')
    need(all(text.count('setenv("' + flag + '","1",1)') == 1 for flag in flags) and 'unsetenv(' not in text,
         'The original floating-activation policy must precede and survive backend setup')
    rows = load(args.current / 'provenance/retained-relink-inputs.private.json')
    gpu = next(row for row in rows if Path(row['original_path']).name == 'gpu.o')
    gpu_row = {key: gpu[key] for key in ('path', 'bytes', 'sha256')}
    need(record(gpu_row['path']) == gpu_row, 'Actual selected GPU provider changed')
    need(all(flag.encode() in Path(gpu_row['path']).read_bytes() for flag in flags), 'Actual provider lacks an original mode switch')
    upstream = args.current.parent / 'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/ggml/src/ggml-vulkan/ggml-vulkan.cpp'
    vulkan = upstream.read_text(encoding='utf-8')
    needles = {
        'decode_regular': 'bool quantize_y = ctx->device->integer_dot_product',
        'prefill_indexed': 'const bool can_quantize_y = ctx->device->integer_dot_product',
        'prefill_regular_shared': 'const bool can_quantize_y = (ctx->device->integer_dot_product || ctx->device->coopmat_int_support)',
    }
    need(vulkan.count(needles['decode_regular']) == 2 and vulkan.count(needles['prefill_indexed']) == 1 and
         vulkan.count(needles['prefill_regular_shared']) == 1, 'Both vector and matrix consumer gates must remain explicit')
    result = load(args.case / 'result.private.json')
    for key in ('terminal', 'closure'):
        need(record(result[key]['path']) == result[key], 'Completed native applicability evidence changed')
    native, closed = load(result['terminal']['path']), load(result['closure']['path'])
    positive(native, closed)
    need(native['kind'] == 'Strata-applicability' and not native['timings_usable_for_performance'], 'One original-work observation required')
    per_request, previous = [], [0] * 8
    for condition, row in zip(('cold', 'retained', 'exact-prefix'), native['requests']):
        need(row['strata_integer_dot_disabled'], 'Original integer-dot mode was not retained at runtime')
        after = row['strata_stream_counts_after']
        delta = [a - b for a, b in zip(after, previous)]
        need(len(delta) == 8 and min(delta) >= 0 and delta[2] == delta[5] and
             delta[6] == row['streaming_delivery']['physical_reads'] and delta[7] == row['streaming_delivery']['groups'],
             'Count attempted waits and positive source callbacks separately')
        per_request.append(dict(condition=condition, stream_scopes=delta[0], independent_experts=delta[1],
            attempted_groups=delta[2], waits_beyond_first=delta[3], multiple_group_scopes=delta[4],
            existing_stream_waits=delta[5], positive_callbacks=delta[6], completed_groups=delta[7]))
        previous = after
    save(args.out, dict(completed=True, selected_entry=profile['source'], selected_GPU=gpu_row,
        selected_Vulkan_lineage=record(upstream), consumer_gate_occurrences={key: vulkan.count(value) for key, value in needles.items()},
        ST1=dict(disposition='ineligible-under-selected-arithmetic', existing_image_reuse_checked=True,
                 producer_written_image_checked=True, routed_and_shared_consumers_checked=True),
        ST2=dict(disposition='ineligible-under-selected-arithmetic', single_token_decode_checked=True, multi_token_prefill_checked=True),
        ST3=dict(upstream_GPU_event_ring_present=False, distinct_local_refinements=['group', 'readback'], runtime=per_request),
        original_activation_and_weight_precision_preserved=True, native_terminal=result['terminal'], closure=result['closure'],
        native_case_replayed=False, PS5_operations=0, performance_gain_claimed=False, production_adopted=False))
    print(dict(completed=True, ST1='ineligible', ST2='ineligible', ST3_wait_opportunities=[r['existing_stream_waits'] for r in per_request]))


if __name__ == '__main__':
    main()
