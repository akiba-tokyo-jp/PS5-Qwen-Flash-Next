#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve normal API/display retirement while admitting explicit cache retention."""
import argparse,json,math,sys
from pathlib import Path
import observe_expert_all_q2_monitor as ordinary
import observe_routing_winners_monitor as selected
from expert_q4 import require,record
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once

def retained_row(row,ordinal):
    return (row['full_F32_finite']and math.isfinite(row['maximum_absolute_logit_error'])and
        row.get('Expert_weight_retention_enabled')is True and row.get('cross_cache_F32_exact_required')is False and
        (row['same_tokens_as_independent']and 0<row['full_F32_logit_rows_compared']<=33 if ordinal==1 else True))

def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--routing-native-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a,remaining=p.parse_known_args()
    r=json.loads(a.routing_native_receipt.read_text());normal=r['resident_weight_normal'];scope=r['routing_winners_normal']['scope'];model=r['routing_winners_normal']['model_scope']
    require(normal['retained_weights_default']and normal['small_rows_default']and not normal['request_and_KV_state_retained']and scope['retained_expert_weights_default']and scope['ordinary_full_F32_finite_required'],'Exact qualified weight-retention numerical scope required')
    require(r['input_hashes_stable']and r['native_dispatch_audit']['passed']and not r['real_module_import_audit']['missing'],'Qualified actual native providers required')
    for row in active_link_inputs(r):require(record(row['path'])==row,'Selected native input changed')
    source=selected.observer_source()
    source=once(source,"row['full_F32_finite'] and (row['maximum_absolute_logit_error']<=1e-5 and row['same_tokens_as_independent'] if ordinal==1 else True)","retained_row(row,ordinal)")
    source=once(source,"result['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE'","result['Expert_format']==WEIGHT_MODEL_SCOPE['Expert_format']")
    old_bundles_disabled=r.get('precision_candidate',{}).get('old_mixed_bundles_disabled',False)
    def io(rows):
        if not old_bundles_disabled:return selected.validate_retained_io_cohort(rows)
        require(bool(rows)and all(x['flags']==5 and 0<=x['maximum_lifetime_quad_inflight']<=4 for x in rows),'Original bounded demand I/O selection required')
    env=dict(ordinary.__dict__,ROUTING_SCOPE=scope,WEIGHT_MODEL_SCOPE=model,retained_row=retained_row,validate_retained_io_cohort=io)
    sys.argv=[sys.argv[0],*remaining,'--out',str(a.out)];exec(compile(source,__file__+'#retained-weight-normal','exec'),env);env['main']()

if __name__=='__main__':main()
