#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate measured prefill reduction and route/phase/shape-guarded reuse."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','comparison','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());comp=json.loads(a.comparison.read_text());a.out.mkdir(parents=True,exist_ok=False)
 scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-normal-performance-v1',
  prefill_Experts=6,graph_reuse_disabled_for_policy=False,graph_reuse_key='selected_routing_bits_phase_and_original_graph_input_shapes')
 model_scope=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-normal-performance-model-v1',selected_Experts='6_prefill_6_decode')
 cmd=prior['compile_commands'][0];entry=Path(cmd[cmd.index('-c')+1]).read_text()
 entry='#include "normal_performance_policy.h"\n'+entry
 entry=once(entry,literal(prior['all_Q2_optimized_monitor']['scope']),literal(scope));entry=once(entry,literal(prior['expert_q2_model']['scope']),literal(model_scope))
 entry=once(entry,'if(setenv("LLAMA_GRAPH_REUSE_DISABLE","1",1))','qwen_app_six_configure(4);\n        if(setenv("LLAMA_GRAPH_REUSE_DISABLE","0",1))')
 entry=once(entry,'            std::uint64_t routing_before[3]{};', '            const auto graph_reuses_before=qwen_app_six_reuse_count();\n            std::uint64_t routing_before[3]{};')
 entry=once(entry,'            row["routing_policy"]=', '            row["actual_graph_reuses"]=qwen_app_six_reuse_count()-graph_reuses_before;\n            row["prefill_Experts"]=6;\n            row["routing_policy"]=')
 entry=once(entry,'{"graph_reuse_disabled_for_policy",true}','{"graph_reuse_disabled_for_policy",false}')
 routing=Path(comp['routing_sharing']['actual_sources']['routing']['path']).read_text().replace('#include "six_candidate_policy.h"','#include "normal_performance_policy.h"')
 routing=once(routing,'(six_mode<<1)|unsigned(qwen_app_route_is_decode())','(six_mode<<5)|(qwen_app_route_mode()<<1)|unsigned(qwen_app_route_is_decode())')
 graph=Path(comp['routing_sharing']['actual_sources']['graph']['path']).read_text().replace('#include "six_candidate_policy.h"','#include "normal_performance_policy.h"')
 variants={'entry':(cmd,entry),'routing':(prior['routing_sharing']['commands'][4],routing),'graph':(prior['routing_sharing']['commands'][5],graph)}
 result,commands,sources=link(a.parent,a.out,variants,[Path(__file__),a.comparison,ROOT/'native/app/normal_performance_policy.h'])
 result['expert_q2_model']['scope']=model_scope
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'])
 result['all_Q2_optimized_monitor']['commands'][0]=commands['entry']
 for key,index in (('routing',4),('graph',5)):
  result['routing_sharing']['commands'][index]=commands[key];result['routing_sharing']['actual_sources'][key]=sources[key]
 result['routing_sharing'].update(scope=scope,model_scope=model_scope)
 result['routing_winners_normal'].update(scope=scope,model_scope=model_scope,actual_entry=sources['entry'])
 result['normal_performance']=dict(scope=scope,model_scope=model_scope,actual_sources=sources,commands=commands,
  prefill_Experts=6,decode_Experts=6,checkpoint_and_full_prefix_behavior_unchanged=True,
  original_can_reuse_input_and_shape_checks_retained=True,normal_validation_pending=True,PS5_operations=0,production_adopted=False)
 seal(result,a.workspace,a.cache,a.out);print('Selected normal prefill/graph composition built; normal qualification remains separate.')

if __name__=='__main__':main()
