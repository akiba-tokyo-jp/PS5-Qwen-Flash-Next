#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an explicit normal/API comparison with selected speed-follow-up providers."""
import argparse,copy,json
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','providers','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--attempts',type=int,choices=(6,8),required=True);p.add_argument('--rows',action='store_true');p.add_argument('--protect',action='store_true');a=p.parse_args()
 prior=json.loads(a.parent.read_text());providers=json.loads(a.providers.read_text());a.out.mkdir(parents=True,exist_ok=False)
 require(prior['resident_weight_normal']['active_slots']==3072 and providers['speed_followup']['requests']in(16,24),'Exact normal and finite comparison providers required')
 seed=copy.deepcopy(prior)
 for label,oldcmd,newcmd in (
  ('cache',prior['routing_sharing']['commands'][1],providers['routing_sharing']['commands'][1]),
  ('owner',prior['all_Q2_optimized_monitor']['commands'][1],providers['all_Q2_optimized_monitor']['commands'][1])):
  old=oldcmd[oldcmd.index('-o')+1];new=newcmd[newcmd.index('-o')+1];require(seed['link_command'].count(old)==1,'One exact provider replacement required');seed['link_command'][seed['link_command'].index(old)]=new
  for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
   seed[key]['actual_sources'][label]=providers['resident_weight_normal']['actual_sources'][label];seed[key]['commands'][label]=newcmd
  if label=='cache':seed['routing_sharing']['actual_sources'][label]=providers['routing_sharing']['actual_sources'][label];seed['routing_sharing']['commands'][1]=newcmd;seed['expert_q2_model']['actual_cache']=providers['expert_q2_model']['actual_cache']
  else:seed['all_Q2_optimized_monitor']['commands'][1]=newcmd;seed['all_Q2_optimized_monitor']['actual_owner']=providers['all_Q2_optimized_monitor']['actual_owner']
 rows={r['path']:r for r in seed['inputs_before']}
 for row in active_link_inputs(providers):
  if row['path']in rows:require(rows[row['path']]==row,'Ambiguous original provider input')
  rows[row['path']]=row
 seed['inputs_before']=list(rows.values())+[record(a.providers)];seed['cold_request']['source_header']=providers['cold_request']['source_header'];seed_path=a.out/'seed.private.json';write_json(seed_path,seed)
 ec=prior['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
 dirs=[Path(ec[ec.index('-c')+1]).parent]+[Path(ec[i+1])for i,x in enumerate(ec[:-1])if x=='-I']
 causal=next(f/'causal_expert_sharing.h'for f in dirs if(f/'causal_expert_sharing.h').is_file())
 text=causal.read_text();require('supported_sharing_prefill_width(e.prefill_batch_tokens())'in text and prior['cold_request']['scope']['prefill_tokens']==32,'Actual qualified prefill32 causal provider required')
 text=once(text,'attempts_<8','attempts_<'+str(a.attempts));h=a.out/'speed-causal.private.h';h.write_text(text,newline='\n')
 entry=once(entry,'#include "causal_expert_sharing.h"','#include "speed-causal.private.h"')
 scope=dict(schema='ps5-qwen-speed-normal-v1',maximum_requests=3,owned_rows=a.rows,prefill_decode_protection=a.protect,protection_cap=1536,maximum_speculative_attempts=a.attempts,original_reserves_preserved=True)
 entry=once(entry,'        const bool prefix_comparison=true;','        if(policy.at("native_speed_normal")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact bounded speed-normal profile required");\n        const bool prefix_comparison=true;')
 # literal() already returns a quoted JSON string suitable for Json::parse.
 entry='#include <cstdint>\nextern "C" void qwen_app_row_cache_select(bool,bool);\nextern "C" void qwen_app_protection_begin(bool,bool);\nextern "C" void qwen_app_protection_commit();\n'+entry
 entry=once(entry,'                resident_reset_empty_context(context,model,startup.admission_report);',
  '                qwen_app_row_cache_select('+str(a.rows).lower()+',ordinal==0);qwen_app_protection_begin('+str(a.protect).lower()+',ordinal==0);\n                resident_reset_empty_context(context,model,startup.admission_report);')
 entry=once(entry,'            },[&](const auto &token,const auto &m){','            },[&](const auto &token,const auto &m){\n                qwen_app_protection_commit();')
 entry=once(entry,'{"cache_slots",867}','{"cache_slots",3072}')
 entry=once(entry,'{"cache_reset_before_request",!prefix_comparison||!i||i%2!=0}','{"cache_reset_before_request",i==0}')
 entry=entry.replace('Same-policy independent full F32 and ordered routes','Different retained-cache state: complete finite vocabulary and complete actual routes')
 optimized=dict(prior['all_Q2_optimized_monitor']['scope'],maximum_speculative_attempts=a.attempts)
 entry=once(entry,literal(prior['all_Q2_optimized_monitor']['scope']),literal(optimized))
 result,jobs,sources=link(seed_path,a.out,dict(entry=(ec,entry)),[Path(__file__),a.parent,a.providers,h,causal])
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
 for key in ('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal','all_Q2_optimized_monitor'):result[key]['scope']=optimized
 result['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=sources['entry']
 result['speed_normal']=dict(scope=scope,causal_source=record(h),source_provider=record(a.providers),actual_sources=sources,commands=jobs,normal_API_display_qualification_pending=True,production_adopted=False)
 seal(result,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_speed_normal',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
