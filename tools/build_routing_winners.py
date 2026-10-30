#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare actual compositions using the existing qualified native link recipe."""
import inspect
from pathlib import Path
import build_expert_routing_sharing as qualified
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
ORDER=[2,2,6,14,14,6,2]+[2,6,14]*3
SCOPE=dict(qualified.SCOPE,schema='ps5-qwen-routing-winners-composition-v1',maximum_requests=16,
 order=ORDER,counting_requests=7,quality_requests=9,quality_tasks=3,decode_Expert_counts=[6,6,6],
 decode_same_k_for_width_one_and_two=True,ranking_preferences_latched_per_verification_and_rejection=True)

def graph_source(text):
 text=qualified.graph_source(text).replace('#include "expert_routing_experiment.h"','#include "expert_routing_policy.h"')
 text=once(text,'n_tokens==1&&qwen_app_route_is_decode())','n_tokens<=2&&qwen_app_route_is_decode())')
 text=once(text,'qwen_app::experimental_expert_count','qwen_app::decode_policy_experts')
 text=once(text,'qwen_app_route_mode(),1','qwen_app_route_mode(),unsigned(n_tokens)')
 return once(text,'n_tokens==1&&qwen_app_route_is_decode()&&qwen_app_route_mode()==1',
  'n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy(qwen_app_route_mode()).cache_rank')

def entry_source(text,model_scope,IO_scope):
 text=qualified.entry_source(text,model_scope,IO_scope)
 text='#include "expert_routing_policy.h"\n'+text
 text=once(text,'request_count=20','request_count=16')
 text=once(text,'counting_modes[]={0,0,4,4,0}','counting_modes[]={2,2,6,14,14,6,2};\n        constexpr unsigned quality_modes[]={2,6,14}')
 text=once(text,'ordinal<5;const unsigned mode=counting?counting_modes[ordinal]:(ordinal-5)%5',
  'ordinal<7;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-7)%3]')
 text=once(text,'const unsigned task=counting?0:(ordinal-5)/5','const unsigned task=counting?0:(ordinal-7)/3')
 text=once(text,'if(mode==4)engine->enable_speculative_step_prototype','if(qwen_app::routing_policy(mode).sharing)engine->enable_speculative_step_prototype')
 text=once(text,'context,mode==4)','context,qwen_app::routing_policy(mode).sharing)')
 text=once(text,'counting&&mode==0','counting&&mode==2')
 return text

def main():
 # Reuse the same compiler/link/import/dispatch and immutable-input checks.
 # Every change is an exact source substitution; the generated sources are
 # independently hashed in the normal inherited receipt.
 qualified.SCOPE=SCOPE
 source=inspect.getsource(qualified.main)
 source=once(source,'maximum_requests=20,timed_requests=4','maximum_requests=16,timed_requests=6')
 source=once(source,'maximum_requests=20)','maximum_requests=16)')
 source=once(source,"added_files=[ROOT/'tools/build_expert_routing_sharing.py'", "added_files=[Path(__file__),ROOT/'native/app/expert_routing_policy.h',ROOT/'native/app/expert_routing_policy.cpp',ROOT/'native/app/causal_expert_sharing.h',ROOT/'tools/build_expert_routing_sharing.py'")
 a=source.index(" adapter=(ROOT/'native/app/expert_q2_speculative.h')")
 b=source.index(" write_source(a.out/'repeated_expert_speculation.private.h',adapter)",a)
 source=source[:a]+" adapter=(ROOT/'native/app/causal_expert_sharing.h').read_text()\n"+source[b:]
 source=source.replace("('routing',capture_cmd,record(ROOT/'native/app/expert_routing_experiment.cpp'),(ROOT/'native/app/expert_routing_experiment.cpp').read_text())",
  "('routing',capture_cmd,record(ROOT/'native/app/expert_routing_policy.cpp'),(ROOT/'native/app/expert_routing_policy.cpp').read_text())")
 env=dict(qualified.__dict__,__file__=__file__,SCOPE=SCOPE,graph_source=graph_source,entry_source=entry_source)
 exec(compile(source,__file__+'#qualified-composition-link','exec'),env);env['main']()
if __name__=='__main__':main()
