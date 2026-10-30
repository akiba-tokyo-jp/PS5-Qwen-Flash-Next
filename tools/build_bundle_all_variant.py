#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare four single-bundle lanes against serial larger bundle coalescing."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior.get('delivery_pool_fix',{}).get('legacy_original_targets_preserved_at_depth2_3_4'),'Fixed legacy targets required');a.out.mkdir(parents=True,exist_ok=False)
 commands=dict(entry=prior['compile_commands'][0],cache=prior['routing_sharing']['commands'][1],owner=prior['all_Q2_optimized_monitor']['commands'][1]);source={k:Path(c[c.index('-c')+1]).read_text()for k,c in commands.items()}
 scope=dict(prior['cold_request']['scope'],candidate_modes=[0,1,2,3,4,5,6],all_bundle_lane_comparison=True)
 entry=once(source['entry'],literal(prior['cold_request']['scope']),literal(scope))
 owner=once(source['owner'],'if(mode>5)throw','if(mode>6)throw');owner=once(owner,'if(delivery_mode!=1)return false;','if(delivery_mode!=1&&delivery_mode!=6)return false;')
 cache=once(source['cache'],'if(qwen_app_delivery_mode()==1){','if(qwen_app_delivery_mode()==1||qwen_app_delivery_mode()==6){')
 marker='if((at&&qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[selected[at-1]].expert))==index-1)||(at+1<chosen&&qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[selected[at+1]].expert))==index+1))break;'
 cache=once(cache,marker,'if(qwen_app_delivery_mode()!=6&&((at&&qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[selected[at-1]].expert))==index-1)||(at+1<chosen&&qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[selected[at+1]].expert))==index+1)))break;')
 root=Path(__file__).resolve().parents[1];result,jobs,actual=link(a.parent,a.out,{k:(commands[k],v)for k,v in dict(entry=entry,owner=owner,cache=cache).items()},[Path(__file__),root/'native/app/delivery_read_pool.h'])
 for key in ('normal_performance','output_Q8_normal'):result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs)
 result['all_Q2_optimized_monitor']['actual_entry']=actual['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=actual['entry']
 for key in ('cold_request','delivery_followup'):result[key].update(scope=scope);result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs)
 result['delivery_followup']['modes']['6']='parallel_bundles_including_previously_coalesced';seal(result,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bundle_parallel_vs_larger_coalescing',original_memory_identity_driver_and_completion_guards=True,original2MiB_lanes_and8MiB_total_scratch=True,original_scheduling_eligibility_required=True,payload_bytes_unchanged=True,request_count_may_increase=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
 print('All-bundle lane comparison built; physical byte payload unchanged, request/coalescing tradeoff explicit.')

if __name__=='__main__':main()
