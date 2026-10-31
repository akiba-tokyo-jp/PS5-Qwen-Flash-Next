#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink a precisely bound weight overlay without changing driver or reserves."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from audit_expert_all_q2_safety import body
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','preparation','publication','parent-publication','workspace','cache','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());prep=json.loads(a.preparation.read_text())
    pub=json.loads(a.publication.read_text());parent_pub=json.loads(a.parent_publication.read_text())
    require(prep['completed']and pub['candidate_receipt']==prep['candidate']and
            pub['parent_receipt']==parent_pub['candidate']==prep['parent'],'Exact overlay and published control required')
    for row in (prep['parent'],prep['candidate'],parent_pub['source_integrity']):require(record(row['path'])==row,'Precision source ancestry changed')
    a.out.mkdir(parents=True,exist_ok=False)
    parent_raw=Path(prep['parent']['path']).read_text();candidate_raw=Path(prep['candidate']['path']).read_text()
    parent_model=json.loads(parent_raw);candidate=json.loads(candidate_raw);changes=candidate['precision_overlay']['tensors']
    original_root=json.loads(Path(parent_pub['source_integrity']['path']).read_text())['source_directory']
    # GGML format identifiers are pinned by the same source revision as the
    # compiled tensor providers. Read only the explicit enum values here.
    import sys,types
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    pkg=types.ModuleType('gguf');pkg.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.constants import GGMLQuantizationType as Type
    header=a.out/'precision-plan.private.h'
    header.write_text('#pragma once\nnamespace qwen_app {\n'+
        'inline constexpr const char*precision_parent_raw='+json.dumps(parent_raw)+';\n'+
        'inline constexpr const char*precision_candidate_raw='+json.dumps(candidate_raw)+';\n'+
        'inline constexpr const char*precision_parent_sha256='+json.dumps(prep['parent']['sha256'])+';\n'+
        'inline constexpr const char*precision_candidate_sha256='+json.dumps(prep['candidate']['sha256'])+';\n'+
        'inline constexpr const char*precision_parent_root='+json.dumps(original_root)+';\n'+
        'inline constexpr std::uint64_t precision_device_bytes='+str(prep['footprint']['device_weights'])+'ull;\n'+
        'inline constexpr std::uint64_t precision_expert_bytes='+str(prep['footprint']['mapped_experts'])+'ull;\n'+
        'inline bool precision_parent_file(const std::string&name){for(const char*p:{'+
        ','.join(json.dumps(h['file'])for h in parent_model['resident_all_Q8_overlay']['headers'])+'})if(name==p)return true;return false;}\n'+
        'inline bool precision_selected_type(const std::string&name,int type){\n'+
        ''.join('if(name=='+json.dumps(c['name'])+')return type=='+str(int(Type[c['type']]))+';\n'for c in changes)+
        'return false;}\n}\n',newline='\n')
    ec=prior['compile_commands'][0];before=Path(ec[ec.index('-c')+1]).read_text()
    text='#include "precision_overlay_receipt.h"\n'+before
    text=once(text,'std::optional<qwen_app::ResidentAllQ8Receipt>','std::optional<qwen_app::PrecisionOverlayReceipt>')
    text=once(text,'qwen_app::resident_all_Q8_source_integrity(policy.at(', 'qwen_app::precision_source_integrity(policy.at(')
    text=once(text,'qwen_app::validate_resident_all_Q8_footprint(footprint,expected_mapped_files);',
                    'qwen_app::validate_precision_footprint(footprint,expected_mapped_files);')
    text=once(text,'qwen_app::resident_all_Q8_file(*Expert_Q2_receipt,name)?Expert_Q2_root:',
        'qwen_app::precision_file(*Expert_Q2_receipt,name)?Expert_Q2_root:'+
        'qwen_app::precision_parent_file(name)?'+json.dumps(original_root)+':')
    text=once(text,'!(type==GGML_TYPE_Q8_0&&name&&qwen_app::resident_all_Q8_name(name))',
        '!(name&&((type==GGML_TYPE_Q8_0&&qwen_app::resident_all_Q8_name(name))||qwen_app::precision_selected_type(name,int(type))))')
    if prep['mode']=='dense-Q4':
        text=once(text,'Expert_Q2_manifest->tensor_ne(name,type==GGML_TYPE_Q8_0?',
            'Expert_Q2_manifest->tensor_ne(name,type==GGML_TYPE_Q4_0?"Q4_0":type==GGML_TYPE_Q8_0?')
    new_resident=dict(prior['resident_all_Q8']['scope'],additional_precision_exception=prep['mode'],
        additional_payload_saved_bytes=prep['saved_payload_bytes'],
        Expert_Q2_payloads_unchanged=prep['mode']!='expert-Q2_0',
        other_F32_weights_unchanged=prep['mode']!='router-Q8')
    text=once(text,literal(prior['resident_all_Q8']['scope']),literal(new_resident))
    scope=dict(schema='ps5-qwen-explicit-precision-candidate-v1',mode=prep['mode'],
        selected_tensors=prep['selected_tensors'],candidate_receipt_sha256=prep['candidate']['sha256'],
        control_receipt_sha256=prep['parent']['sha256'],saved_payload_bytes=prep['saved_payload_bytes'],
        PLE_convolution_BF16_preserved=True,F32_activation_and_KV_preserved=True,
        CPU_heap_physical_kernel_and_completion_guards_preserved=True,driver_unchanged=True,
        active_cache_slots=prior['all_Q2_optimized_monitor']['scope']['active_cache_slots'],
        cache_budget_bytes=prior['all_Q2_optimized_monitor']['scope']['cache_budget_bytes'])
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_precision_candidate")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact precision candidate scope required");')
    variants={'entry':(ec,text)}
    if prep['mode']=='expert-Q2_0':
        require(prep['footprint']['mapped_experts']==48*512*1382400,'Exact all-Q2_0 active Expert payload required')
        text=once(text,'misses*1536000ull+result.predictive_bytes','misses*1382400ull+result.predictive_bytes')
        text=text.replace('Gate_Up_Q2_K_Down_Q2_0_MSE','Gate_Up_Q2_0_ref_Down_Q2_0_MSE')
        text=text.replace('Gate/Up Q2_K + Down Q2_0 MSE ready','Gate/Up Q2_0 + Down Q2_0 MSE ready')
        # Never use an old mixed-format bundle for the new Gate/Up payloads.
        text=text.replace('qwen_app_select_Q2_bundle(true)','qwen_app_select_Q2_bundle(false)')
        text=text.replace('qwen_app_select_current_bundle(true)','qwen_app_select_current_bundle(false)')
        variants['entry']=(ec,text)
        cc=prior['routing_sharing']['commands'][1];cache=Path(cc[cc.index('-c')+1]).read_text()
        cache=cache.replace('537600','460800').replace('GGML_TYPE_Q2_K','GGML_TYPE_Q2_0')
        variants['cache']=(cc,cache)
    result,jobs,sources=link(a.parent,a.out,variants,
        [Path(__file__),a.preparation,a.publication,a.parent_publication,header,ROOT/'native/app/precision_overlay_receipt.h'])
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry']
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    result['routing_winners_normal']['actual_entry']=sources['entry']
    result['resident_all_Q8']['scope']=new_resident
    if prep['mode']=='expert-Q2_0':
        for key in ('expert_q2_model','routing_sharing','routing_winners_normal','output_Q8_normal','normal_performance'):
            for name in ('scope','model_scope','probation_scope'):
                if name in result[key]and result[key][name].get('Expert_format')=='Gate_Up_Q2_K_Down_Q2_0_MSE':
                    result[key][name]['Expert_format']='Gate_Up_Q2_0_ref_Down_Q2_0_MSE'
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(text,name)==body(before,name),'Original memory/identity/reset guard changed: '+name)
    result['precision_candidate']=dict(scope=scope,preparation=record(a.preparation),
        publication_plan=record(a.publication),parent_publication=record(a.parent_publication),
        actual_sources=sources,commands=jobs,complete_native_seal_required_before_GPU=True,
        old_mixed_bundles_disabled=prep['mode']=='expert-Q2_0',native_verification_pending=True)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='explicit_weight_precision_overlay',
        original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,
        workspace_bytes=48<<20,cache_slots=1381,driver_unchanged=True,
        original_request_reset_and_GPU_retirement_guards_preserved=True,
        candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
