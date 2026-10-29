#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the qualified bounded monitor transport on an admitted mixed entry."""
from types import FunctionType
from expert_q2_model_source import SCOPE
from expert_q4_monitor_source import monitor_entry_source as qualified_monitor
from expert_q4 import require

MONITOR_SCOPE=dict(SCOPE,schema='ps5-qwen-expert-q2-monitor-comparison-v1',HTTP_requests=2,VideoOut_starts=1)


def monitor_entry_source(text):
    # The parent has already passed Q2/composite source admission. Reuse only
    # the monitor transformation, without applying Q4 admission a second time.
    environment=dict(qualified_monitor.__globals__,entry_source=lambda value:value,
                     SCOPE=SCOPE,MONITOR_SCOPE=MONITOR_SCOPE)
    result=FunctionType(qualified_monitor.__code__,environment)(text)
    replacements={
        'run_Q4_request':'run_Q2_request',
        'Q4 API observer disconnected':'Mixed Expert API observer disconnected',
        'Completed Q4 counting response':'Completed mixed Expert counting response',
        'Measurable Q4 request':'Measurable mixed Expert request',
        'ps5-qwen-Q4-displayed-frame-v1':'ps5-qwen-Q2-mixed-displayed-frame-v1',
        'Expert Q4_0 model ready':'Gate/Up Q2_K + Down Q4_0 ready',
        'EXPERT Q4_0 / OTHER BF16 F32 / PASSIVE MONITOR':'GATE UP Q2_K / DOWN Q4_0 / OTHER BF16 F32',
        'Q4_model_resident_passive_frame_completed':'Q2_mixed_model_resident_passive_frame_completed',
        'Q4 passive native presentation failed':'Mixed Expert passive native presentation failed',
        'Both Q4 API requests':'Both mixed Expert API requests',
    }
    for before,after in replacements.items():
        require(before in result,'The qualified monitor marker changed: '+before)
        result=result.replace(before,after)
    return result
