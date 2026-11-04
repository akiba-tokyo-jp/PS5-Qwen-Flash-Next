#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Select the smallest byte count already accepted by the unchanged owner."""
from build_speculative_batch_probe import once


def wrapper_text(source):
    changed = once(source, 'requested[i] = expected == 422400 ? 537600 : expected;',
                   'requested[i] = expected == 422400 ? 460800 : expected;')
    return once(changed,
        '        // unchanged. The cache uploads only the actual tensor\'s shorter prefix.',
        '        // unchanged. Use the smallest accepted request; its byte count is not\n'
        '        // tied to a projection role. Upload only the actual shorter prefix.')
