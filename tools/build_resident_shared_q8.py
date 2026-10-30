#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate the exact144 shared-Q8 overlays while retaining cache and driver."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
literal=lambda v:json.dumps(json.dumps(v,separators=(',',':')))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','publication','base-publication','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());publication=json.loads(a.publication.read_text());base_publication=json.loads(a.base_publication.read_text())
    require(publication['completed']and publication.get('header_prefixes_extracted_and_sealed')is True and publication['native_whole_SHA256_EOF_identities_passed']and base_publication['completed'],'Both immutable Q8 publications and zero-offset header prefixes must be positively sealed')
    for row in (publication['candidate'],publication['source_integrity'],base_publication['candidate'],base_publication['source_integrity']):require(record(row['path'])==row,'Q8 source publication changed')
    base_root=json.loads(Path(base_publication['source_integrity']['path']).read_text())['source_directory']
    a.out.mkdir(parents=True,exist_ok=False);header=a.out/'shared_Q8_base.private.h'
    header.write_text('#pragma once\ninline constexpr const char*shared_Q8_base_raw='+json.dumps(Path(base_publication['candidate']['path']).read_text())+';\n',newline='\n')
    scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-resident-shared-Q8-normal-v1',
        output_only_Q8_exception=False,shared_Expert_Q8_exception=True,shared_Q8_tensors=144,shared_Q8_saved_payload_bytes=221184000,
        original_except_output_weight_precision_and_driver_preserved=False,original_except_output_and_shared_weight_precision_and_driver_preserved=True)
    model_scope=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-resident-shared-Q8-model-v1',output_only_Q8_exception=False,
        shared_Expert_Q8_exception=True,non_Expert_except_output_precision_preserved=False,non_Expert_except_output_and_shared_precision_preserved=True)
    probation=dict(prior['output_Q8_normal']['probation_scope'],schema='ps5-qwen-resident-shared-Q8-probation-v1',output_only_Q8_exception=False,shared_Expert_Q8_exception=True)
    cmd=prior['compile_commands'][0];text=Path(cmd[cmd.index('-c')+1]).read_text()
    text='#include "resident_shared_q8_source.h"\n#include "shared_Q8_base.private.h"\n'+text
    for before,after in ((prior['all_Q2_optimized_monitor']['scope'],scope),(prior['expert_q2_model']['scope'],model_scope),(prior['output_Q8_normal']['probation_scope'],probation)):text=once(text,literal(before),literal(after))
    text=once(text,'std::optional<qwen_app::ResidentOutputQ8Receipt>','std::optional<qwen_app::ResidentSharedQ8Receipt>')
    text=once(text,'Expert_Q2_manifest.emplace(receipt,output_Q8_parent_raw);','Expert_Q2_manifest.emplace(receipt,shared_Q8_base_raw,output_Q8_parent_raw);')
    text=once(text,'qwen_app::resident_output_Q8_source_integrity(policy.at("native_first_generation_validation"),receipt,Json::parse(output_Q8_parent_raw),Expert_Q2_root,expected_mapped_files)',
        'qwen_app::resident_shared_Q8_source_integrity(policy.at("native_first_generation_validation"),receipt,Json::parse(shared_Q8_base_raw),Json::parse(output_Q8_parent_raw),'+json.dumps(base_root)+',Expert_Q2_root,expected_mapped_files)')
    text=once(text,'qwen_app::validate_resident_output_Q8_footprint(footprint,expected_mapped_files);','qwen_app::validate_resident_shared_Q8_footprint(footprint,expected_mapped_files);')
    text=once(text,'name==Expert_Q2_receipt->at("files").back().at("path")?Expert_Q2_root:',
        'qwen_app::resident_shared_Q8_file(*Expert_Q2_receipt,name)?Expert_Q2_root:name==Expert_Q2_receipt->at("files").back().at("path")?'+json.dumps(base_root)+':')
    text=once(text,'type==GGML_TYPE_Q8_0&&name&&!std::strcmp(name,"output.weight")',
        'type==GGML_TYPE_Q8_0&&name&&(!std::strcmp(name,"output.weight")||qwen_app::resident_shared_Q8_name(name))')
    text=text.replace('Only the admitted original, Expert Q2 and output-only Q8 types are accepted','Only original, Expert Q2 and admitted output/shared Q8 types are accepted')
    text=once(text,'{"non_Expert_except_output_precision_preserved",true},{"output_weight_type","Q8_0"}',
        '{"non_Expert_except_output_precision_preserved",false},{"non_Expert_except_output_and_shared_precision_preserved",true},{"output_weight_type","Q8_0"},{"shared_Expert_weight_type","Q8_0"}')
    text=text.replace('EXPERT Q2_K Q2_0 / OUTPUT Q8 / OTHER BF16 F32 / TOP6 CACHE','EXPERT Q2 / OUTPUT+SHARED Q8 / OTHER BF16 F32 / TOP6 CACHE')
    result,commands,sources=link(a.parent,a.out,{'entry':(cmd,text)},[Path(__file__),a.publication,a.base_publication,header,
        ROOT/'native/app/resident_shared_q8_receipt.h',ROOT/'native/app/resident_shared_q8_source.h',ROOT/'native/app/source_overlay.h'])
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands);result[key].update(scope=scope,model_scope=model_scope)
    result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model_scope
    result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry']);result['all_Q2_optimized_monitor']['commands'][0]=commands['entry']
    result['routing_sharing'].update(scope=scope,model_scope=model_scope);result['routing_winners_normal'].update(scope=scope,model_scope=model_scope,actual_entry=sources['entry'])
    result['resident_shared_Q8']=dict(scope=scope,model_scope=model_scope,actual_sources=sources,commands=commands,publication=record(a.publication),base_publication=record(a.base_publication),
        saved_resident_payload_bytes=221184000,selected_shared_tensors=144,all_routed_Expert_payloads_unchanged=True,cache_capacity_unchanged=True,
        CPU_gpu_owner_and_completion_guards_unchanged=True,native_GPU_verification_pending=True,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out);print('Exact144 shared-Q8 overlays integrated; normal GPU and quality verification pending.')
if __name__=='__main__':main()
