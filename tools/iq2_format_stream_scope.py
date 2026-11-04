#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the four-lease cache and its unchanged owner to actual native IO evidence."""
from pathlib import Path

from build_performance_quantizer import record
from iq2_format_stream_cache import transform
from start_success_route import load, need

MODES = {'Q2-IQ2-Up-model': 'Up', 'Q2-IQ2-Gate-Up-model': 'Gate-Up', 'Q3-IQ2-Down-model': 'Down'}
OWNER_SHA256 = 'f87f931a6a537cf32f8e1d92678182cdbc8db5c9f624cdec84b009ed4e86b02e'


def require_compiled_stream(row, mode):
    need(mode in MODES.values() and record(row['path']) == row, 'One exact compiled format-stream provider is required')
    proof = load(row['path'])
    need(proof['completed'] and proof['mode'] == mode and proof['actual_selected_PS5_ABI_compiled'] and
         proof['source_leases'] == 4 and proof['existing_scratch_bytes'] == 8 << 20 and
         proof['new_workers'] == proof['new_GPU_buffers'] == 0 and
         proof['original_source_range_EOF_identity_overlap_and_completion_checks_unchanged'] and
         proof['completed_streamed_Experts_skipped_in_generic_loop'] and proof['adjacent_generic_fallback_preserved'] and
         not proof['whole_source_bytes_reduced_claimed'], 'The existing finite source ownership and fallback guards must remain exact')
    for key in ('baseline', 'source', 'artifact', 'transform', 'unchanged_original_source_owner'):
        need(record(proof[key]['path']) == proof[key], 'A compiled format-stream input changed')
    need(proof['unchanged_original_source_owner']['sha256'] == OWNER_SHA256,
         'The original qualified source owner must remain byte exact')
    baseline = load(proof['baseline']['path'])
    need(record(baseline['source']['path']) == baseline['source'] and
         Path(proof['source']['path']).read_text(encoding='utf-8') ==
         transform(Path(baseline['source']['path']).read_text(encoding='utf-8'), mode == 'Down'),
         'The actual compiled cache must equal the complete selected transformation')
    expected_flags = [] if mode == 'Down' else ['--wrap=qwen_app_try_Q2_stream']
    need(proof['required_link_flags'] == expected_flags, 'Only the explicit original stream API wrapper is admitted')
    if mode != 'Down':
        for key in ('wrapper', 'wrapper_source', 'wrapper_controls'):
            need(record(proof[key]['path']) == proof[key], 'The exact format-request wrapper inputs changed')
        controls = load(proof['wrapper_controls']['path'])
        need(controls['completed'] and controls['PS5_operations'] == 0 and
             {r['layout'] for r in controls['results']} == {1, 2} and
             all(r['completed'] and r['positives'] == 4 and r['destination_canaries_exact'] for r in controls['results']) and
             proof['actual_IQ2_upload_bytes'] == 422400 and proof['unused_requested_bytes_per_IQ2'] == 115200,
             'The exact completed wrapper controls and explicit overfetch accounting are required')
        for item in controls['inputs']:
            need(record(item['path']) == item, 'A wrapper boundary control input changed')
    else:
        need(proof['wrapper'] is None and proof['unused_requested_bytes_per_IQ2'] == 0, 'Down must use the unchanged accepted source requests')
    return proof


def require_stream_profile(profile):
    scope = profile['overrides']['native_headless_model_audit']
    row = scope.get('format_stream_provider')
    if row is None:
        return None
    need(scope['arm'] == 'candidate' and profile['headless_audit_kind'] in MODES,
         'Only a complete uniform IQ2 candidate may select format streaming')
    proof = require_compiled_stream(row, MODES[profile['headless_audit_kind']])
    need(not scope.get('Down_source_prefix_cache'), 'The prefix-plus-stream combination needs a separately compiled and bound provider')
    if scope['format_stream_observation_only']:
        if 'entry_artifact' in profile:
            observer = profile['qualification_observer']
            need(not profile['performance_timings_usable'] and observer and record(observer['path']) == observer,
                 'Unqualified streaming may run only with its actual qualification observer')
    else:
        evidence = scope['format_stream_IO_qualification']
        need(evidence and record(evidence['path']) == evidence, 'Timed streaming requires its exact native IO qualification')
        native = load(evidence['path'])
        need(native['completed'] and native['compiled_stream'] == row and
             native['model_receipt'] == scope['format_stream_model_receipt'] and
             native['arithmetic_qualification'] == scope['arithmetic_qualification'] and
             native['backend_environment'] == scope['backend_environment'] and
             native['all69_full_vocabulary_F32_rows_SHA256_exact'] and native['ordered_routes_exact'] and
             native['tokens_and_output_bytes_exact'] and native['all_ordinary_closes_and_exact_restores'] and
             native['same_quantized_model_compared'] and native['actual_streamed_groups'] > 0,
             'All69 actual rows, routes, outputs, streaming and ordinary restoration must match the same quantized model')
        for item in native['evidence']:
            need(record(item['path']) == item, 'Native stream equivalence evidence changed')
    if 'entry_artifact' in profile:
        need(profile['candidate_cache_provider'] == proof['artifact'] and profile['candidate_cache_source'] == proof['source'] and
             profile['model_layer']['model_receipt'] == scope['format_stream_model_receipt'],
             'The actual compiled cache and source model must match the qualified stream profile')
    return proof
