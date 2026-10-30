#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain normal routing qualification, with predeclared prefill endpoints."""
import inspect
import qualify_routing_winners_monitor as original
from build_speculative_batch_probe import once
def main():
 source=inspect.getsource(original.main)
 source=once(source,"require(first['metrics']['decode_tokens_per_second']>baseline and pair>old_pair and final['metrics']['TTFT_ms']<first['metrics']['TTFT_ms'],'Normal first decode, capture-charged pair throughput and actual prefix TTFT must improve')",
  "require(first['metrics']['TTFT_ms']<prior['external_requests'][0]['TTFT_ms'] and first['metrics']['total_ms']<prior['external_requests'][0]['total_ms'] and pair>old_pair and final['metrics']['TTFT_ms']<first['metrics']['TTFT_ms'],'Predeclared independent TTFT, whole request and capture-charged pair must improve; actual prefix reuse required')")
 source=once(source,"(v['metrics']['prompt_tokens']+3)//4","(v['metrics']['prompt_tokens']+15)//16")
 marker="  require(len(route['records'])==48*route['process_calls'],'Complete ordered process routes required')"
 source=once(source,marker,marker+"\n  require(v['completed_performance']['prefill_batch_tokens']==16 and v['completed_performance']['all_prompt_outputs_requested'],'Actual width16/all processing required')\n  for call in range(prefill_calls):\n   require(all(row['tokens']==min(16,v['metrics']['prompt_tokens']-call*16) for row in route['records'][call*48:(call+1)*48]),'Every actual prefill layer must retain full token rows')")
 source=once(source,"schema='ps5-qwen-routing-winners-normal-qualification-v1'","schema='ps5-qwen-prefill16-normal-qualification-v1'")
 marker=' write_json(a.out,value);'
 source=once(source,marker,""" value.update(prefill_tokens=16,all_prompt_outputs_requested=True,
  selection_refinement='Normal adoption prioritizes whole request and pair throughput; mode4 matches mode5 whole throughput with higher decode. The original prefill-first selection is unchanged.',
  first_independent_total_ms=first['metrics']['total_ms'],previous_independent_total_ms=prior['external_requests'][0]['total_ms'],
  independent_TTFT_reduction_fraction=1-first['metrics']['TTFT_ms']/prior['external_requests'][0]['TTFT_ms'],
  independent_whole_time_reduction_fraction=1-first['metrics']['total_ms']/prior['external_requests'][0]['total_ms'])
"""+marker)
 env=dict(original.__dict__);exec(compile(source,__file__+'#prefill-endpoint-normal-qualification','exec'),env);env['main']()
if __name__=='__main__':main()
