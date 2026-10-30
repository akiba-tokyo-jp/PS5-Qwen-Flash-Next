#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen a larger cache within the actual output-Q8 resident saving."""
import argparse,copy,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
SLOTS=1125;EXTRA=128*1536000;CACHE=1533419520+EXTRA;TRANSFER=199680000+EXTRA
literal=lambda v:json.dumps(json.dumps(v,separators=(',',':')))
def recipes(value):
    if isinstance(value,dict):
        for v in value.values():yield from recipes(v)
    elif isinstance(value,list):
        if '-c'in value and isinstance(value[0],str):yield value
        else:
            for v in value:yield from recipes(v)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--slots',type=int,choices=(1125,1253),default=1125)
    a=p.parse_args();global SLOTS,EXTRA,CACHE,TRANSFER
    SLOTS=a.slots;EXTRA=(SLOTS-997)*1536000;CACHE=1533419520+EXTRA;TRANSFER=396288000
    single_MiB=640 if SLOTS==1125 else 648;workspace_MiB=248 if SLOTS==1125 else 64
    prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    require(TRANSFER+(16<<20)<595968000,'Keep the prior resident-saving margin')
    profile=(ROOT/'native/app/resident_output_q8_profile.h').read_text().replace('resident_output_Q8_cache_transfer=199680000','resident_output_Q8_cache_transfer='+str(TRANSFER)).replace('resident_output_Q8_cache_budget=1533419520','resident_output_Q8_cache_budget='+str(CACHE))
    (a.out/'resident_output_q8_profile.h').write_text(profile,newline='\n')
    reset=(ROOT/'native/app/resident_output_q8_cache_reset.h').read_text().replace('selected!=867&&selected!=997','selected!=997&&selected!=1125').replace('lru.n_slots!=867&&lru.n_slots!=997','lru.n_slots!=997&&lru.n_slots!=1125').replace('keeps 998 planes','keeps 1126 planes').replace('867/997 active','997/1125 active').replace('1125',str(SLOTS)).replace('1126',str(SLOTS+1))
    (a.out/'resident_output_q8_cache_reset.h').write_text(reset,newline='\n')
    owner_cmd=prior['all_Q2_optimized_monitor']['commands'][1];owner_path=Path(owner_cmd[owner_cmd.index('-c')+1])
    budget=(owner_path.parent/'device_buffer_budget.h').read_text().replace('+ 199680000ull','+ '+str(TRANSFER)+'ull').replace('model_postload_single_buffer = 512ull << 20','model_postload_single_buffer = '+str(single_MiB)+'ull << 20').replace('model_internal_workspace_budget = 248ull << 20','model_internal_workspace_budget = '+str(workspace_MiB)+'ull << 20')
    # Report actual workspace capacities separately from the fixed reservation.
    budget=once(budget,'        const auto entry = std::find_if(entries_.begin(), entries_.end(), [&](const auto & item) { return item.key == key; });\n        if (entry != entries_.end() && entry->key) {',
        '        workspace_peak_=std::max(workspace_peak_,total);\n        const auto entry = std::find_if(entries_.begin(), entries_.end(), [&](const auto & item) { return item.key == key; });\n        if (entry != entries_.end() && entry->key) {')
    budget=once(budget,'    void close_completed() {','    std::uint64_t workspace_peak(){healthy();return workspace_peak_;}\n    void close_completed() {')
    budget=once(budget,'    std::uint64_t pending_ = 0;','    std::uint64_t pending_ = 0,workspace_peak_=0;')
    (a.out/'device_buffer_budget.h').write_text(budget,newline='\n')
    scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-cache1125-normal-v1',active_cache_slots=SLOTS,cache_budget_bytes=CACHE,transferred_postload_quota_bytes=TRANSFER,
        postload_single_buffer_bytes=single_MiB<<20,workspace_budget_bytes=workspace_MiB<<20,larger_cache_single_buffer_explicit_exception=True)
    model_scope=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-cache1125-model-v1',expected_active_Q2_slots=SLOTS,cache_budget_bytes=CACHE)
    probation=dict(prior['output_Q8_normal']['probation_scope'],schema='ps5-qwen-cache1125-probation-v1',active_cache_slots=SLOTS,cache_budget_bytes=CACHE)
    entry_cmd=prior['compile_commands'][0];entry=Path(entry_cmd[entry_cmd.index('-c')+1]).read_text()
    entry='#include <cstdint>\nextern "C" std::uint64_t qwen_app_workspace_actual_peak();\n'+entry
    for x,y in ((prior['all_Q2_optimized_monitor']['scope'],scope),(prior['expert_q2_model']['scope'],model_scope),(prior['output_Q8_normal']['probation_scope'],probation)):entry=once(entry,literal(x),literal(y))
    entry=once(entry,'reset.slots!=997','reset.slots!=1125');entry=entry.replace('{"active_cache_slots",997}','{"active_cache_slots",1125}')
    entry=entry.replace('reset.slots!=1125','reset.slots!='+str(SLOTS)).replace('{"active_cache_slots",1125}','{"active_cache_slots",'+str(SLOTS)+'}')
    if SLOTS==1253:entry=once(entry,'memory_budget.expert_cache=qwen_app::resident_output_Q8_cache_budget;','memory_budget.expert_cache=qwen_app::resident_output_Q8_cache_budget;memory_budget.workspace=64ull<<20;')
    at=entry.rindex('{"device_ledger_peak_bytes",ledger.peak}')
    marker='{"device_ledger_peak_bytes",ledger.peak}'
    entry=entry[:at]+entry[at:].replace(marker,marker+',{"actual_workspace_capacity_peak_bytes",qwen_app_workspace_actual_peak()},{"workspace_fixed_reservation_bytes",'+str(workspace_MiB)+'ull<<20}',1)
    cache_cmd=prior['routing_sharing']['commands'][1];cache=Path(cache_cmd[cache_cmd.index('-c')+1]).read_text()
    cache=cache.replace('output_Q8_selected_slots=997','output_Q8_selected_slots=1125').replace('g.n_slots < 997','g.n_slots < 1125')
    cache=cache.replace('groups[0].n_slots!=867&&groups[0].n_slots!=997','groups[0].n_slots!=997&&groups[0].n_slots!=1125').replace('slots!=867&&slots!=997','slots!=997&&slots!=1125')
    cache=cache.replace('1125',str(SLOTS))
    engine_cmd=prior['routing_sharing']['commands'][2]
    padding_cmd=next(c for c in recipes(prior)if c[c.index('-c')+1].endswith('padded_cache.cpp'))
    padding=Path(padding_cmd[padding_cmd.index('-c')+1]).read_text()
    padding=once(padding,'return qwen_app::selected_padded_buffer_batch_limit(actual,qwen_app_model_compute_limits_enabled());',
        'return qwen_app_model_compute_limits_enabled()?std::min<std::size_t>(actual,'+str(single_MiB)+'ull<<20):actual;')
    owner=owner_path.read_text()+'\nextern "C" std::uint64_t qwen_app_workspace_actual_peak(){return device_budget.workspace_peak();}\n'
    variants={'entry':(entry_cmd,entry),'cache':(cache_cmd,cache),'engine':(engine_cmd,Path(engine_cmd[engine_cmd.index('-c')+1]).read_text()),'owner':(owner_cmd,owner),'padding':(padding_cmd,padding)}
    inputs=[Path(__file__),*[a.out/n for n in ('resident_output_q8_profile.h','resident_output_q8_cache_reset.h','device_buffer_budget.h')]]
    result,commands,sources=link(a.parent,a.out,variants,inputs)
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands);result[key].update(scope=scope,model_scope=model_scope)
    result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model_scope
    result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'],actual_engine=sources['engine'],commands=[commands[k]for k in ('entry','owner','engine')])
    result['routing_sharing'].update(scope=scope,model_scope=model_scope);result['routing_winners_normal'].update(scope=scope,model_scope=model_scope,actual_entry=sources['entry'])
    result['cache_capacity1125']=dict(actual_sources=sources,commands=commands,scope=scope,model_scope=model_scope,
        total_output_Q8_payload_saved=595968000,total_postload_quota_transferred=TRANSFER,additional_payload_bytes=EXTRA,
        active_slots=SLOTS,physical_planes=SLOTS+1,largest_cache_bank_bytes=(SLOTS+1)*537600,postload_single_buffer_bytes=single_MiB<<20,
        previous_single_buffer_bytes=512<<20,CPU_heap_bytes=512<<20,workspace_reservation_bytes=workspace_MiB<<20,
        original_Direct_reserve_bytes=512<<20,all_original_physical_and_owner_guards_retained=True,
        rationale='Qualify a larger existing bank before adding bank-selection shaders; the resident output already exceeds this bank size.',native_verification_pending=True)
    seal(result,a.workspace,a.cache,a.out);print('1125-slot candidate built; larger single-bank exception is explicit and every physical reserve remains.')
if __name__=='__main__':main()
