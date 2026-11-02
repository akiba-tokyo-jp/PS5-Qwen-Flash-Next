#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate the sealed additional Q1 layer into the admitted current entry."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','preparation','publication','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();base=load(args.base_entry);prep=load(args.preparation);pub=load(args.publication)
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and pub['completed'] and
         pub['preparation']==record(args.preparation) and pub['whole_new_bytes_and_all_parent_identities_qualified'],
         'The changed bounded CPU entry and positively sealed Q1 layer are required')
    profile=load(base['application_policy']['path']);need(record(base['application_policy']['path'])==base['application_policy'],'Base application profile changed')
    for row in (base['entry'],base['reader'],profile['source'],prep['parent'],prep['candidate'],pub['source_integrity']):
        need(record(row['path'])==row,'Actual source, provider, model or native seal changed')
    parent=Path(prep['parent']['path']).read_text(encoding='utf-8');candidate=Path(prep['candidate']['path']).read_text(encoding='utf-8')
    current=load(args.current/'qwen-runtime/development.json');gate=current['native_first_generation_validation']
    need(gate['model_receipt_sha256']==prep['parent']['sha256'],'The Q1 parent must be the actually selected model')
    parent_seal=json.loads(gate['precision_source_integrity']['raw']);seal=load(pub['source_integrity']['path'])
    need(seal['parent_model_receipt_sha256']==prep['parent']['sha256'] and seal['model_receipt_sha256']==prep['candidate']['sha256'],
         'The exact two complete model layers must match the native publication')
    args.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,args.out/header.name)
    generated=args.out/'shared-Q4-plan.private.h';model=load(prep['candidate']['path'])
    generated.write_text('#pragma once\nnamespace qwen_app {\n'+
        'inline constexpr const char*shared_Q4_parent_raw='+json.dumps(parent)+';\n'+
        'inline constexpr const char*shared_Q4_candidate_raw='+json.dumps(candidate)+';\n'+
        'inline constexpr const char*shared_Q4_candidate_sha256='+json.dumps(prep['candidate']['sha256'])+';\n'+
        'inline constexpr const char*shared_Q4_parent_root='+json.dumps(parent_seal['source_directory'])+';\n'+
        'inline bool shared_Q4_selected_type(const std::string&name,int type){if(type!=2)return false;\n'+
        ''.join('if(name=='+json.dumps(t['name'])+')return true;\n' for t in model['shared_Q4_overlay']['tensors'])+
        'return false;}\n}\n',encoding='utf-8',newline='\n')
    original=Path(profile['source']['path']).read_text(encoding='utf-8');text=original
    transformations=[('#include "precision_overlay_receipt.h"','#include "shared_q4_overlay_receipt.h"'),
        ('std::optional<qwen_app::PrecisionOverlayReceipt>','std::optional<qwen_app::SharedQ4Receipt>'),
        ('qwen_app::precision_file(*Expert_Q2_receipt,name)','qwen_app::shared_Q4_file(*Expert_Q2_receipt,name)'),
        ('qwen_app::precision_selected_type(name,int(type))','(qwen_app::precision_selected_type(name,int(type))||qwen_app::shared_Q4_selected_type(name,int(type)))'),
        ('qwen_app::precision_source_integrity(','qwen_app::shared_Q4_source_integrity('),
        ('qwen_app::validate_precision_footprint(footprint,expected_mapped_files);','qwen_app::validate_shared_Q4_footprint(footprint,expected_mapped_files);')]
    for old,new in transformations:text=once(text,old,new)
    text=once(text,'{"shared_Expert_weight_type","Q8_0"}','{"shared_Expert_weight_type","Q4_0"}')
    scope=dict(schema='ps5-qwen-additional-shared-Q4-qualification-v1',selected_tensors=144,total_Q4_matrices=253,
        parent_recipe_sha256=prep['parent']['sha256'],candidate_recipe_sha256=prep['candidate']['sha256'],
        saved_device_weight_bytes=117964800,encoded_from_original_BF16=True,prior_109_matrix_layer_unchanged=True,
        routed_Expert_weights_routing_state_cache_and_driver_preserved=True,
        semantic_mismatch_recorded_before_ordinary_retirement=True,normal_quality_or_speed_not_yet_qualified=True)
    literal=lambda value:json.dumps(json.dumps(value,separators=(',',':')))
    next_scope=dict(current['native_next_five_normal'],resident_precision=
        '253 matrices (109 current large matrices and 144 shared Expert projections) Q4_0; remaining resident Q8_0 except original PLE BF16 and F32')
    need(text.count(literal(current['native_next_five_normal']))==3,'The exact three effective current contracts are required')
    text=text.replace(literal(current['native_next_five_normal']),literal(next_scope))
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_shared_Q4")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact additional shared-Q4 scope required");')
    # Finite outputs with different lengths/answers are quality negatives.
    # Preserve all real shape, resource, checkpoint and request-reset guards.
    text=once(text,'                    else if(ordinal==1)geometry_error=true;','                    // Different completed answer length is recorded separately for this weight candidate.')
    text=once(text,'if(!result.request_reset_completed||geometry_error||value_error||!rows||\n               (ordinal==1&&rows!=reference_rows))',
        'if(!result.request_reset_completed||geometry_error||value_error||!rows)')
    text=once(text,'            else if(ordinal==1&&(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes))\n                throw std::runtime_error("Original additional tokens or bytes differ");',
        '            // Cross-cache output equality is reported below and is not a resource-completion predicate.')
    text=once(text,'row["same_tokens_as_independent"]=result.token_ids==reference_ids&&result.output_bytes==reference_bytes;',
        'row["same_tokens_as_independent"]=result.token_ids==reference_ids&&result.output_bytes==reference_bytes;\n'
        '            row["full_F32_rows_aligned_with_independent"]=rows==reference_rows;row["additional_shared_Q4_candidate"]=true;')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(text,name),'An original memory, identity or reset guard changed')
    for call in ('qwen_native_driver_begin()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()',
                 'llama_init_from_model(','trial.run(','qwen_app::begin_completed_expert_routes()'):
        need(original.count(call)==text.count(call),'Model or GPU ownership-call topology changed')
    source=args.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n')
    command=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent)
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(args.out/Path(root['external-contents']).name).resolve().as_posix()
    typed=(ROOT/'native/app/precision_overlay_receipt.h').resolve().as_posix()
    need(not any(r['name']==typed for r in overlay['roots']),'The generated current typed view must have one selected alias')
    overlay['roots'].append(dict(type='file',name=typed,**{'external-contents':(args.out/'precision_overlay_receipt.h').resolve().as_posix()}))
    selected=args.out/'selected-view.private.json';save(selected,overlay)
    command=[str(args.out) if v==old_view else v for v in command];command[command.index('-ivfsoverlay')+1]=str(selected)
    obj=args.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'entry.private.d')
    result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    application=dict(completed=True,kind='Q1-shared',entry_artifact=record(obj),source=record(source),token_sync_policy='request_end',
        overrides=dict(native_next_five_normal=next_scope,native_resident_main_SELF=profile['overrides']['native_resident_main_SELF'],native_shared_Q4=scope),
        CPU_SELF_provider=profile['CPU_SELF_provider'],model_and_GPU_topology_unchanged=True,
        model_weight_precision_changed=True,model_layer=dict(kind='additional-shared-Q4',parent_recipe_sha256=prep['parent']['sha256'],
            model_receipt=prep['candidate'],application_model_receipt=seal['source_directory']+'/model-receipt.json',
            source_policy=pub['policy'],publication=record(args.publication)),native_performance_qualified=False,PS5_operations=0)
    path=args.out/'application-policy.private.json';save(path,application)
    save(args.out/'result.private.json',dict(completed=True,application_policy=record(path),entry=record(obj),command=command,
        preparation=record(args.preparation),publication=record(args.publication),parent_entry=base['entry'],
        actual_additional_weight_tensors=144,all_original_memory_identity_reset_and_GPU_ownership_guards_preserved=True,
        source=record(source),header=record(ROOT/'native/app/shared_q4_overlay_receipt.h'),generated_plan=record(generated),
        target_compiled=True,PS5_operations=0,native_quality_or_speed_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,additional_Q4_matrices=144,total_Q4_matrices=253,
        original_memory_identity_reset_and_GPU_ownership_guards_preserved=True,PS5_operations=0,production_adopted=False)))


if __name__=='__main__':main()
