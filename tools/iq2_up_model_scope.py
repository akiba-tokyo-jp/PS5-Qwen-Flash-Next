#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject partial IQ2 layouts before an unchanged single-group cache can launch."""
from start_success_route import need


def require_cache_layout(profile):
    if profile.get('headless_audit_kind') != 'Q2-IQ2-Up-model':
        return
    scope = profile['overrides']['native_headless_model_audit']
    need(scope['arm'] in ('control', 'candidate') and scope['selected_cache_slots'] == 3712 and
         scope['explicit_F32_profile'] == dict(GGML_VK_DISABLE_MMVQ='1', GGML_VK_DISABLE_F16='1'),
         'The exact original slot count and qualified F32 backend profile are required')
    expected = [] if scope['arm'] == 'control' else list(range(48))
    need(scope['IQ2_Up_layers'] == expected,
         'Partial IQ2 Up layouts create multiple cache groups and cannot use the unchanged single-group reset; '
         'require the full48-layer uniform layout before any publication or launch')
