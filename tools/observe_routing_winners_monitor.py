#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain the normal owner/API/frame protocol for the selected routing policy."""
import argparse,inspect,json,sys
from pathlib import Path
import observe_expert_all_q2_monitor as ordinary
from expert_q4 import require,record
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
def validate_retained_io_cohort(rows):
 require(bool(rows) and all(row['flags']==5 and 0<=row['maximum_lifetime_quad_inflight']<=4 for row in rows),'Bounded retained I/O selection required')
 require(all(any(row[key]>0 for row in rows)for key in ('adjacent_calls_saved','extra_bundled_Experts','quad_batches')) and max(row['maximum_lifetime_quad_inflight']for row in rows)==4,'Each retained I/O optimization must execute across the cohort when applicable')

def observer_source():
 source=inspect.getsource(ordinary.main)
 marker="    b=json.loads(a.binding.read_text());host=b['host'];owner=b['native_binding'];run=owner['run_id'];remote=b['report_remote']"
 source=once(source,marker,marker+"\n    require(b.get('routing_winners_scope')==ROUTING_SCOPE,'Exact selected routing scope binding required')")
 source=once(source,"row['maximum_absolute_logit_error']<=1e-5,",
  "row['full_F32_finite'] and (row['maximum_absolute_logit_error']<=1e-5 and row['same_tokens_as_independent'] if ordinal==1 else True),")
 marker="        frame=json.loads(download('.arm'+str(ordinal)+'.display.json'))"
 source=once(source,marker,"""        policy=row['routing_policy'];io=row['io_optimization']
        require(policy['bits']==ROUTING_SCOPE['selected_routing_policy'] and policy['decode_Experts']==6 and policy['preferences_latched_per_target_event'],'Actual selected decode policy required')
        if ROUTING_SCOPE['cached_ranking']:require(policy['rank_calls']>0 and policy['resident_scores']>0,'Actual cached ranking must execute')
        require(io['flags']==5 and 0<=io['maximum_lifetime_quad_inflight']<=4,'Bounded retained I/O policy required')
        retained_io.append(io)
        if ordinal==2:
            require(row['prefix']['request_hit'] and row['prefix']['last_reused_prompt_tokens']==30,'Actual complete prompt restoration required')
            if ROUTING_SCOPE['maximum_speculative_attempts']:
                s=row['speculation'];c=row['checkpoint']
                require(s['attempts']>1 and s['attempts']==s['accepted']+s['rejected'] and s['queued_bonus_samples']==s['accepted'] and c['captures']==s['attempts'] and c['restores']==s['rejected'],'Every repeated verification/rollback and delivered bonus must reconcile')
"""+marker)
 source=once(source,"    last=status();require(","""    validate_retained_io_cohort(retained_io)
    last=status();require(""")
 source=once(source,'    streams=[];frames=[]','    streams=[];frames=[];retained_io=[]')
 source=once(source,"result['source_windows']==result['source_completed_windows']", "result['source_windows']==result['source_completed_windows'] and result['routing_winners_policy']==ROUTING_SCOPE['selected_routing_policy'] and result['graph_reuse_disabled_for_policy']==ROUTING_SCOPE['graph_reuse_disabled_for_policy']")
 return once(source,"result['active_cache_slots']==867","result['active_cache_slots']==ROUTING_SCOPE['active_cache_slots']")

def main():
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--routing-native-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a,remaining=p.parse_known_args()
 receipt=json.loads(a.routing_native_receipt.read_text());selected=receipt['routing_winners_normal'];scope=selected['scope']
 require(receipt['input_hashes_stable']and receipt['native_dispatch_audit']['passed']and not receipt['real_module_import_audit']['missing'],'Qualified normal providers and native dispatch required')
 for row in active_link_inputs(receipt):require(record(row['path'])==row,'Sealed normal link input changed')
 source=observer_source()
 env=dict(ordinary.__dict__,ROUTING_SCOPE=scope,validate_retained_io_cohort=validate_retained_io_cohort);sys.argv=[sys.argv[0],*remaining,'--out',str(a.out)]
 exec(compile(source,__file__+'#selected-policy-observer','exec'),env);env['main']()
if __name__=='__main__':main()
