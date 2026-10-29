# SPDX-License-Identifier: MIT
"""Reuse the bounded passive monitor with explicit all-Expert Q2 labels."""
from types import FunctionType
from expert_all_q2_model_source import SCOPE
from expert_q4_monitor_source import monitor_entry_source as qualified_monitor
from expert_q4 import require
MONITOR_SCOPE=dict(SCOPE,schema='ps5-qwen-expert-all-q2-monitor-comparison-v1',HTTP_requests=2,VideoOut_starts=1)
def monitor_entry_source(text):
 env=dict(qualified_monitor.__globals__,entry_source=lambda v:v,SCOPE=SCOPE,MONITOR_SCOPE=MONITOR_SCOPE)
 result=FunctionType(qualified_monitor.__code__,env)(text)
 replacements={
  'run_Q4_request':'run_all_Q2_request',
  'Q4 API observer disconnected':'All-Expert Q2 API observer disconnected',
  'Completed Q4 counting response':'Completed all-Expert Q2 counting response',
  'Measurable Q4 request':'Measurable all-Expert Q2 request',
  'ps5-qwen-Q4-displayed-frame-v1':'ps5-qwen-all-Expert-Q2-displayed-frame-v1',
  'Expert Q4_0 model ready':'Gate/Up Q2_K + Down Q2_0 MSE ready',
  'EXPERT Q4_0 / OTHER BF16 F32 / PASSIVE MONITOR':'GATE UP Q2_K / DOWN Q2_0 MSE / OTHER BF16 F32',
  'Q4_model_resident_passive_frame_completed':'all_Expert_Q2_model_resident_passive_frame_completed',
  'Q4 passive native presentation failed':'All-Expert Q2 passive native presentation failed',
  'Both Q4 API requests':'Both all-Expert Q2 API requests',
 }
 for before,after in replacements.items():require(before in result,'Qualified monitor marker changed: '+before);result=result.replace(before,after)
 return result
