#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Redistribute verified shared-Q8 resident savings into 128 cache slots."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import recipes,literal
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 require(prior['cache_capacity1125']['active_slots']==1253 and prior['resident_shared_Q8']['saved_resident_payload_bytes']==221184000,'Exact shared-Q8/1253 parent required')
 slots=1381;budget=2123243520;transfer=601284608;single=716<<20
 require(transfer+(16<<20)<595968000+221184000,'Keep actual combined resident saving margin')
 command=prior['all_Q2_optimized_monitor']['commands'][1];parentdir=Path(command[command.index('-c')+1]).parent
 for name in ('device_buffer_budget.h','resident_output_q8_profile.h','resident_output_q8_cache_reset.h'):
  text=(parentdir/name).read_text()
  if name=='device_buffer_budget.h':text=once(text,'+ 396288000ull','+ 601284608ull');text=once(text,'model_postload_single_buffer = 648ull << 20','model_postload_single_buffer = 716ull << 20')
  elif name=='resident_output_q8_profile.h':
   text=once(text,'resident_output_Q8_cache_transfer=396288000','resident_output_Q8_cache_transfer=601284608');text=once(text,'resident_output_Q8_cache_budget=1926635520','resident_output_Q8_cache_budget=2123243520')
   text=once(text,'resident_output_Q8_cache_transfer<resident_output_Q8_payload_saving-(16ull<<20)','resident_output_Q8_cache_transfer<resident_output_Q8_payload_saving+221184000ull-(16ull<<20)')
  else:text=text.replace('1253','1381').replace('1254','1382')
  (a.out/name).write_text(text,newline='\n')
 scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-shared-Q8-cache1381-normal-v1',active_cache_slots=slots,cache_budget_bytes=budget,transferred_postload_quota_bytes=transfer,postload_single_buffer_bytes=single)
 model=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-shared-Q8-cache1381-model-v1',expected_active_Q2_slots=slots,cache_budget_bytes=budget)
 probation=dict(prior['output_Q8_normal']['probation_scope'],schema='ps5-qwen-shared-Q8-cache1381-probation-v1',active_cache_slots=slots,cache_budget_bytes=budget)
 ec=prior['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
 for before,after in ((prior['all_Q2_optimized_monitor']['scope'],scope),(prior['expert_q2_model']['scope'],model),(prior['output_Q8_normal']['probation_scope'],probation)):entry=once(entry,literal(before),literal(after))
 entry=once(entry,'reset.slots!=1253','reset.slots!=1381');entry=entry.replace('{"active_cache_slots",1253}','{"active_cache_slots",1381}')
 marker='                throw std::runtime_error("Complete checkpoint cannot retain original reserves");'
 entry=once(entry,marker,'                throw std::runtime_error("Complete checkpoint cannot retain original reserves: ledger_live="+std::to_string(ledger.live)+" limit="+std::to_string(qwen_app::model_postload_device_budget)+" growth="+std::to_string(rounded)+" Direct_available="+std::to_string(budget.available)+" Direct_reserve="+std::to_string(memory_budget.direct_reserve)+" Flexible_available="+std::to_string(observed_system_headroom())+" Flexible_reserve="+std::to_string(memory_budget.flexible_reserve));')
 cc=prior['routing_sharing']['commands'][1];cache=Path(cc[cc.index('-c')+1]).read_text().replace('1253','1381')
 en=prior['routing_sharing']['commands'][2]
 pc=next(c for c in recipes(prior)if c[c.index('-c')+1].endswith('padding.private.cpp'))
 padding=once(Path(pc[pc.index('-c')+1]).read_text(),'648ull<<20','716ull<<20')
 variants={'entry':(ec,entry),'cache':(cc,cache),'owner':(command,Path(command[command.index('-c')+1]).read_text()),'engine':(en,Path(en[en.index('-c')+1]).read_text()),'padding':(pc,padding)}
 result,commands,sources=link(a.parent,a.out,variants,[Path(__file__),*[a.out/n for n in ('device_buffer_budget.h','resident_output_q8_profile.h','resident_output_q8_cache_reset.h')]])
 for key in ('normal_performance','output_Q8_normal'):
  result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands);result[key].update(scope=scope,model_scope=model)
 result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'],actual_engine=sources['engine'],commands=[commands[k]for k in ('entry','owner','engine')])
 result['routing_sharing'].update(scope=scope,model_scope=model);result['routing_winners_normal'].update(scope=scope,model_scope=model,actual_entry=sources['entry'])
 result['resident_shared_Q8'].update(scope=scope,model_scope=model,cache_capacity_unchanged=False)
 result['shared_cache1381']=dict(actual_sources=sources,commands=commands,scope=scope,active_slots=slots,physical_planes=slots+1,cache_budget_bytes=budget,postload_single_buffer_bytes=single,total_actual_resident_saving_bytes=817152000,total_postload_quota_transferred=transfer,largest_bank_bytes=742963200,CPU_heap_bytes=512<<20,workspace_reservation_bytes=64<<20,original_Direct_reserve_bytes=512<<20,all_original_physical_and_completion_guards_retained=True,native_verification_pending=True)
 seal(result,a.workspace,a.cache,a.out);print('Shared-Q8 savings redistributed into 128 additional cache slots; native verification pending.')
if __name__=='__main__':main()
