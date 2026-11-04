#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the compiled prefix cache to its unchanged decoder and byte accounting."""
from pathlib import Path

from build_performance_quantizer import record
from iq2_down_large_cache_scope import require_provider
from iq2_down_prefix_cache import PLANE_BYTES, PREFIX_BYTES, transform
from start_success_route import load, need


def require_compiled_prefix(row, provider_row):
    provider = require_provider(provider_row)
    need(record(row['path']) == row, 'The compiled Down prefix provider changed')
    proof = load(row['path'])
    need(proof['completed'] and proof['actual_selected_PS5_ABI_compiled'] and
         proof['provider'] == provider_row and proof['large_cache_index_proof'] == provider['large_cache_index_proof'] and
         proof['original_source_and_GPU_slot_stride'] == PLANE_BYTES == 460800 and
         proof['source_upload_prefix_bytes'] == PREFIX_BYTES == 425024 and
         proof['unused_tail_bytes_omitted'] == 35776 and proof['selected_cache_slots'] == 3712 and
         proof['actual_upload_byte_statistics_preserved'] and proof['independent_omitted_padding_counter'] and
         proof['original_adjacent_bulk_path_preserved'] and proof['existing_pair_pipeline_reused'] and
         proof['source_descriptor_identity_and_completion_guards_preserved'] and proof['GPU_shader_resources_unchanged'] and
         proof['new_weight_files'] == proof['new_weight_transfers'] == 0,
         'Only unreachable padding may be omitted; actual transfers and existing source ownership remain explicit')
    for name in ('baseline', 'transform', 'source', 'artifact'):
        need(record(proof[name]['path']) == proof[name], 'A compiled prefix-cache input changed')
    baseline = load(proof['baseline']['path'])
    need(record(baseline['source']['path']) == baseline['source'], 'The selected cache source changed')
    from build_iq2_up_model import cache_text
    expected = transform(cache_text(Path(baseline['source']['path']).read_text(encoding='utf-8'), True))
    need(Path(proof['source']['path']).read_text(encoding='utf-8') == expected,
         'The actual compiled cache must equal the exact prefix-only source transformation')
    return proof
