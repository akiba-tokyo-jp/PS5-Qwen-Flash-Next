#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the real pre-publication cache-layout gate, including a partial-layer refusal."""
import copy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from iq2_up_model_scope import require_cache_layout


def profile(arm, layers):
    return dict(headless_audit_kind='Q2-IQ2-Up-model', overrides=dict(native_headless_model_audit=dict(
        arm=arm, IQ2_Up_layers=layers, selected_cache_slots=3712,
        explicit_F32_profile=dict(GGML_VK_DISABLE_MMVQ='1', GGML_VK_DISABLE_F16='1'))))


def main():
    require_cache_layout(dict(headless_audit_kind='I1-relative-model-prefetch'))
    require_cache_layout(profile('control', []))
    require_cache_layout(profile('candidate', list(range(48))))
    cases = [profile('candidate', [0]), profile('candidate', list(range(47))),
             profile('candidate', list(range(47))+[46]), profile('candidate', list(reversed(range(48)))),
             profile('control', [0])]
    wrong = profile('candidate', list(range(48)))
    wrong['overrides']['native_headless_model_audit']['selected_cache_slots'] = 4000
    cases.append(wrong)
    wrong = profile('candidate', list(range(48)))
    wrong['overrides']['native_headless_model_audit']['explicit_F32_profile']['GGML_VK_DISABLE_F16'] = '0'
    cases.append(wrong)
    for case in cases:
        try:
            require_cache_layout(case)
        except RuntimeError:
            continue
        raise AssertionError('An incompatible cache/backend layout reached publication')
    print(dict(completed=True, positive_controls=3, negative_controls=len(cases), PS5_operations=0))


if __name__ == '__main__':
    main()
