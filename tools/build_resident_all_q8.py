#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate all resident Q8 weights with exact inherited source/owner guards."""
import argparse
import copy
import json
from pathlib import Path
from expert_q4 import require, record, write_json
from build_speculative_batch_probe import once
from scoped_native_variant import link, seal
from audit_expert_all_q2_safety import body
from resident_all_q8 import PARENT_SHA256

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','publication','parent-publication','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--host-build-before-publication',action='store_true',help='Compile from the sealed CPU publication plan; runtime still requires the complete native source seal')
    a=p.parse_args();prior=json.loads(a.parent.read_text());pub=json.loads(a.publication.read_text());parent_pub=json.loads(a.parent_publication.read_text())
    if a.host_build_before_publication:
        require(pub['completed_build'] and pub['CPU_only'] and pub['original_source_writes']==0,'Sealed new-only CPU publication plan required for the offline build')
        pub_candidate=pub['candidate_receipt'];publication_inputs=[pub_candidate]
    else:
        require(pub['completed'] and pub['header_prefixes_extracted_and_sealed'],'Complete native resident-Q8 publication required')
        pub_candidate=pub['candidate'];publication_inputs=[pub_candidate,pub['source_integrity']]
    require(parent_pub['candidate']['sha256']==PARENT_SHA256,'Exact installed shared-Q8 parent required')
    for row in [*publication_inputs,parent_pub['candidate'],parent_pub['source_integrity']]:require(record(row['path'])==row,'Resident Q8 ancestry changed')
    parent_raw=Path(parent_pub['candidate']['path']).read_text();parent_model=json.loads(parent_raw)
    parent_root=json.loads(Path(parent_pub['source_integrity']['path']).read_text())['source_directory']
    a.out.mkdir(parents=True,exist_ok=False)
    header=a.out/'resident_Q8_parent.private.h';header.write_text('#pragma once\ninline constexpr const char*all_Q8_parent_raw='+json.dumps(parent_raw)+';\ninline bool all_Q8_parent_file(const std::string&name){for(const char*p:{'+','.join(json.dumps(h['file']) for h in parent_model['resident_Q8_overlay']['headers'])+'})if(name==p)return true;return false;}\n',newline='\n')
    command=prior['compile_commands'][0];before=Path(command[command.index('-c')+1]).read_text();text='#include "resident_all_q8_source.h"\n#include "resident_Q8_parent.private.h"\n'+before
    text=once(text,'std::optional<qwen_app::ResidentSharedQ8Receipt>','std::optional<qwen_app::ResidentAllQ8Receipt>')
    text=once(text,'Expert_Q2_manifest.emplace(receipt,shared_Q8_base_raw,output_Q8_parent_raw);','Expert_Q2_manifest.emplace(receipt,all_Q8_parent_raw,shared_Q8_base_raw,output_Q8_parent_raw);')
    call='qwen_app::resident_shared_Q8_source_integrity(policy.at("native_first_generation_validation"),receipt,Json::parse(shared_Q8_base_raw),Json::parse(output_Q8_parent_raw),'
    text=once(text,call,'qwen_app::resident_all_Q8_source_integrity(policy.at("native_first_generation_validation"),receipt,Json::parse(all_Q8_parent_raw),Json::parse(shared_Q8_base_raw),Json::parse(output_Q8_parent_raw),')
    # Insert the unchanged shared-Q8 parent directory after the output-Q8 root.
    marker=',Expert_Q2_root,expected_mapped_files)) :'
    text=once(text,marker,','+json.dumps(parent_root)+',Expert_Q2_root,expected_mapped_files)) :')
    text=once(text,'qwen_app::validate_resident_shared_Q8_footprint(footprint,expected_mapped_files);','qwen_app::validate_resident_all_Q8_footprint(footprint,expected_mapped_files);')
    text=once(text,'qwen_app::resident_shared_Q8_file(*Expert_Q2_receipt,name)?Expert_Q2_root:',
        'qwen_app::resident_all_Q8_file(*Expert_Q2_receipt,name)?Expert_Q2_root:all_Q8_parent_file(name)?'+json.dumps(parent_root)+':')
    text=once(text,'(!std::strcmp(name,"output.weight")||qwen_app::resident_shared_Q8_name(name))','qwen_app::resident_all_Q8_name(name)')
    text=text.replace('Only original, Expert Q2 and admitted output/shared Q8 types are accepted','Only unchanged Expert Q2, resident Q8 and original nonresident/F32 types are accepted')
    text=text.replace('EXPERT Q2 / OUTPUT+SHARED Q8 / OTHER BF16 F32 / TOP6 CACHE','EXPERT Q2 / RESIDENT Q8 + PLE BF16 / TOP6 CACHE')
    scope=dict(schema='ps5-qwen-all-resident-Q8-normal-v1',remaining_resident_Q8_tensors=544,saved_resident_payload_bytes=3163852800,
        resident_BF16_tensors_remaining=1,resident_BF16_bytes_remaining=81920,PLE_convolution_BF16_preserved=True,Expert_Q2_payloads_unchanged=True,other_F32_weights_unchanged=True,mapped_embeddings_and_PLE_and_MTP_unchanged=True,
        input_type='F32',KV_type='F32',active_cache_slots=1381,cache_budget_bytes=2123243520,cache_redistribution=False,integer_dot=False,cooperative_matrix=False,
        physical_reserves_and_kernel_owner_completion_guards_preserved=True)
    literal=lambda v:json.dumps(json.dumps(v,separators=(',',':')))
    text=once(text,'        const auto policy = Json::parse(policy_file);','        const auto policy = Json::parse(policy_file);\n        if(policy.at("native_resident_all_Q8").at("scope")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact resident Q8 precision scope required");')
    oldscope=prior['all_Q2_optimized_monitor']['scope'];newscope=dict(oldscope,original_except_output_and_shared_weight_precision_and_driver_preserved=False,remaining_resident_Q8_exception=True)
    oldmodel=prior['expert_q2_model']['scope'];newmodel=dict(oldmodel,non_Expert_except_output_and_shared_precision_preserved=False,remaining_resident_Q8_exception=True)
    for old,new in ((oldscope,newscope),(oldmodel,newmodel)):text=once(text,literal(old),literal(new))
    text=text.replace('{"non_Expert_except_output_and_shared_precision_preserved",true}','{"non_Expert_except_output_and_shared_precision_preserved",false},{"resident_BF16_except_PLE_convolution_converted_to_Q8",true}')
    seed=copy.deepcopy(prior);seed_path=a.out/'seed.private.json';write_json(seed_path,seed)
    inputs=[Path(__file__),a.publication,a.parent_publication,header,seed_path,ROOT/'native/app/resident_all_q8_receipt.h',ROOT/'native/app/resident_all_q8_source.h']
    result,jobs,sources=link(seed_path,a.out,dict(entry=(command,text)),inputs)
    for k in ('normal_performance','output_Q8_normal'):
        result[k]['actual_sources'].update(sources);result[k]['commands'].update(jobs);result[k].update(scope=newscope,model_scope=newmodel)
    result['all_Q2_optimized_monitor'].update(scope=newscope,actual_entry=sources['entry']);result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    result['expert_q2_model']['scope']=newmodel;result['routing_sharing'].update(scope=newscope,model_scope=newmodel)
    result['routing_winners_normal'].update(scope=newscope,model_scope=newmodel,actual_entry=sources['entry'])
    result['cold_request']['actual_sources'].update(sources);result['cold_request']['commands'].update(jobs)
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(text,name)==body(before,name),'Original memory/identity/reset guard changed: '+name)
    result['resident_all_Q8']=dict(scope=scope,publication=record(a.publication),parent_publication=record(a.parent_publication),
        actual_sources=sources,commands=jobs,Expert_Q2_payloads_preserved=True,additional_weight_saved_bytes=3163852800,PLE_convolution_BF16_preserved=True,engine_archives_unchanged=True,
        host_compiled_before_native_publication=a.host_build_before_publication,complete_native_source_seal_required_before_GPU=True,native_GPU_verification_pending=True,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='all_resident_Q8_explicit_precision_source_audit',original_physical_and_kernel_guards_preserved=True,
        CPU_heap_limit_bytes=512<<20,workspace_bytes=48<<20,cache_slots=1381,Expert_Q2_payloads_unchanged=True,driver_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print('Resident-Q8 model and strict source/precision/footprint admission linked; native qualification pending.')


if __name__=='__main__':main()
