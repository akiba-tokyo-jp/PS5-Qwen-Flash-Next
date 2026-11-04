#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the original four source leases for explicitly sized IQ2 triplets."""
from build_speculative_batch_probe import once


def transform(source, down_carriers=False, prefix=False):
    from build_iq2_up_model import cache_text
    changed = cache_text(source, down_carriers)
    old = ('        if(false&&!six_refill){' if down_carriers else
           '        if(qwen_app_Q2_quad_enabled()&&!six_refill&&original_triplet){')
    # Streamed Experts must also be skipped by the generic loop when bundles
    # are disabled. Each delivered bit certifies all three positive callbacks.
    changed = once(changed, old,
        '        const bool format_stream_refill=qwen_app_Q2_quad_enabled()&&!six_refill;\n'
        '        if(format_stream_refill){')
    changed = once(changed,
        'const auto size=w->nb[2];if((size!=537600&&size!=460800)||g.banks[role]->nb[2]!=size||w->ne[2]!=512||(w->type!=GGML_TYPE_Q2_K&&w->type!=GGML_TYPE_Q2_0))',
        '''const auto size=w->nb[2];const bool format_bytes=
                        (w->type==GGML_TYPE_Q2_K&&size==537600)||
                        (w->type==GGML_TYPE_Q2_0&&size==460800)||
                        (w->type==GGML_TYPE_IQ2_XXS&&size==422400);
                    if(!format_bytes||g.banks[role]->nb[2]!=size||w->ne[2]!=512)''')
    if prefix:
        if not down_carriers:
            raise ValueError('The prefix refinement applies only to the complete Down carrier model')
        from iq2_down_prefix_cache import transform as prefix_transform
        changed = prefix_transform(changed)
    old_skip = '(six_refill||bundle_refill)'
    if changed.count(old_skip) < 4:
        raise ValueError('The actual selected generic delivered-state guards changed')
    return changed.replace(old_skip, '(six_refill||bundle_refill||format_stream_refill)')
