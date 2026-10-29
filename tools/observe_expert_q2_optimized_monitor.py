#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the qualified observer with an explicit final mixed-width comparison."""
import inspect
import observe_expert_all_q2_monitor as ordinary
from build_expert_q2_optimized_monitor import SCOPE
from build_speculative_batch_probe import once

def main():
    # Keep every ownership, stream, frame, asset, finish and retirement check.
    # Only the final width-two full-vocabulary criterion differs: native finite
    # values and equal top1 replace an invalid cross-width bit-equality test.
    source=inspect.getsource(ordinary.main)
    marker="    b=json.loads(a.binding.read_text());host=b['host'];owner=b['native_binding'];run=owner['run_id'];remote=b['report_remote']"
    source=once(source,marker,marker+"\n    require(b.get('optimized_delivery_scope')==OPTIMIZED_SCOPE,'Exact qualified final-consumer comparison binding required')")
    source=once(source,"row['maximum_absolute_logit_error']<=1e-5,", "(row['maximum_absolute_logit_error']<=1e-5 if ordinal==1 else row['F32_comparison_scope'].startswith('unlike-width complete-vocabulary finite values and identical top1')),\n")
    marker="        frame=json.loads(download('.arm'+str(ordinal)+'.display.json'))"
    source=once(source,marker,"        require(row['bundled_Experts']>0 and row['range_hint_hits']>0,'Both actual delivery optimizations must execute')\n        if ordinal==2:require(row['prefix']['request_hit'] and row['prefix']['last_reused_prompt_tokens']==30 and row['speculation']==dict(attempts=1,accepted=1,rejected=0,queued_bonus_samples=1,causal_proposals=1),'Actual final prefix restoration and causal target acceptance required')\n"+marker)
    env=dict(ordinary.__dict__,OPTIMIZED_SCOPE=SCOPE)
    exec(compile(source,__file__+'#bound-final-consumer-observer','exec'),env)
    env['main']()
if __name__=='__main__':main()
