#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Enable the measured cache retention and row-delivery defaults in the normal app."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','retention-result','rows-result','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());retention=json.loads(a.retention_result.read_text());rows=json.loads(a.rows_result.read_text())
    require(retention['completed']and retention['total_time_reduction_percent']>0 and retention['all_contents_correct']and retention['ordinary_close_exact_restore'],'Closed measured cache retention winner required')
    require(rows['completed']and rows['matched_cache_slots']==3072 and rows['matched_total_reduction_percent']>0 and rows['all_full_F32_rows_ordered_routes_tokens_and_bytes_exact'],'Both-order same-cache exact row winner required')
    require(prior['resident_cache3072']['active_slots']==3072 and prior['resident_small_rows']['maximum_logical_rows']==8,'Normal3072-slot/row composition required')
    a.out.mkdir(parents=True,exist_ok=False)
    ec=prior['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();require('const unsigned request_count=3;'in entry,'Original normal three-request API/display path required')
    scope=dict(prior['all_Q2_optimized_monitor']['scope'],retained_expert_weights_default=True,small_rows_default=True,ordinary_full_F32_exact_required=False,ordinary_full_F32_finite_required=True,complete_actual_routes_required=True)
    model=dict(prior['expert_q2_model']['scope'],same_width_full_F32_and_routes_required=False,unlike_cache_full_F32_finite_and_routes_complete_required=True)
    resident=dict(prior['resident_all_Q8']['scope'],retained_expert_weights_default=True,small_rows_default=True)
    for before,after in ((prior['all_Q2_optimized_monitor']['scope'],scope),(prior['expert_q2_model']['scope'],model),(prior['resident_all_Q8']['scope'],resident)):entry=once(entry,literal(before),literal(after))
    entry=once(entry,'{"empty_expert_cache_before_independent_request",true}','{"empty_expert_cache_before_independent_request",false},{"request_state_still_empty",true}')
    require(entry.count('{"cache_initially_empty",!second}')==2,'Intent and result must declare actual retained cache state')
    entry=entry.replace('{"cache_initially_empty",!second}','{"cache_initially_empty",ordinal==0}')
    entry=once(entry,'if(ordinal==1&&e>1e-5+1e-5*std::abs(reference_logits[rows*columns+i]))value_error=true;','')
    begin=entry.index('            if(ordinal==1){const auto&a=routes[0],&b=routes[ordinal];');end=entry.index('            const auto p=engine->prefix_reuse_stats();',begin)
    entry=entry[:begin]+'            // Cache-aware ranking can select different routes after weight retention.\n'+entry[end:]
    entry=once(entry,'            row["same_tokens_as_independent"]=',
        '            row["Expert_weight_retention_enabled"]=qwen_app_weight_retention_selected();\n'
        '            row["cross_cache_F32_exact_required"]=false;\n'
        '            row["same_tokens_as_independent"]=')
    entry=once(entry,'{"full_F32_continuation_and_routes_passed",true}',
        '{"full_F32_continuation_and_routes_passed",true},{"full_F32_validation_scope","Different cache occupancy: complete finite vocabulary rows and complete actual routes; cold same-cache exact controls qualified separately"}')
    cc=prior['routing_sharing']['commands'][1];cache=Path(cc[cc.index('-c')+1]).read_text();cache=once(cache,'bool keep_weight_cache=false;','bool keep_weight_cache=true;')
    oc=prior['all_Q2_optimized_monitor']['commands'][1];owner=Path(oc[oc.index('-c')+1]).read_text();owner=once(owner,'bool small_rows_selected=false;','bool small_rows_selected=true;')
    result,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),cache=(cc,cache),owner=(oc,owner)),[Path(__file__),a.retention_result,a.rows_result])
    for key in ('normal_performance','output_Q8_normal'):
        result[key].update(scope=scope,model_scope=model);result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['expert_q2_model']['scope']=model;result['routing_sharing'].update(scope=scope,model_scope=model);result['routing_winners_normal'].update(scope=scope,model_scope=model,actual_entry=sources['entry'])
    result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'],actual_owner=sources['owner']);result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['all_Q2_optimized_monitor']['commands'][1]=jobs['owner']
    for key in ('cold_request','resident_all_Q8','resident_cache3072','resident_small_rows'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['resident_all_Q8']['scope']=resident;result['resident_cache3072']['retained_weights_default']=True;result['resident_small_rows']['candidate_default']=True
    if 'precision_candidate'in result:result['precision_candidate']['actual_sources'].update(sources);result['precision_candidate']['commands'].update(jobs)
    result['resident_weight_normal']=dict(actual_sources=sources,commands=jobs,retention_result=record(a.retention_result),row_result=record(a.rows_result),
        active_slots=3072,retained_weights_default=True,small_rows_default=True,request_and_KV_state_retained=False,
        arithmetic_same_cache_F32_exact_control_cases=[11760,12120],cross_cache_F32_finite_complete_and_same_counting_tokens_required=True,
        context_scope=dict(schema='ps5-qwen-resident-context-reuse-v1',enabled=True,original_contexts=1,empty_expert_cache_before_independent_request=False,request_state_still_empty=True,original_memory_reset_required=True,preserve_cumulative_counters=True,retain_all_original_bank_allocations=True,GPU_or_ordinary_floor_changes=0,all_original_precision_and_complete_F32_comparison_required=True,automatic_retries=0),
        normal_API_display_native_qualification_pending=True,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='measured_weight_retention_and_small_rows_normal_defaults',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,workspace_bytes=48<<20,cache_slots=3072,driver_unchanged=True,all_native_source_owner_and_GPU_completion_guards_preserved=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print('Measured defaults integrated; unlike-cache numerical scope explicit; normal qualification still required.')

if __name__=='__main__':main()
