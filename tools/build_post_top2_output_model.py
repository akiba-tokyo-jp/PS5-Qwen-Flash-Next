#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the109-tensor overlay with the actual Top2 controller and GPU."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from qualify_post_top2_reporting import transform as reporting
from resident_all_q8 import placement
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','preparation','publication-plan','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());prep=json.loads(a.preparation.read_text());pub=json.loads(a.publication_plan.read_text())
    old=n['GDN_model_comparison']['scope'];require(old['candidate']=='Q4-cache3712-Top2','Actual Top2 parent required')
    require(prep['completed']and prep['selected_tensors']==109 and prep['reused_current_dense_Q4_tensors']==108 and
        prep['original_BF16_output_used']and pub['candidate_receipt']==prep['candidate'],'Exact audited109-tensor output overlay required')
    for r in [prep['parent'],prep['candidate']]:require(record(r['path'])==r,'Precision input changed')
    parent_raw=Path(prep['parent']['path']).read_text();candidate_raw=Path(prep['candidate']['path']).read_text()
    pm=json.loads(parent_raw);cm=json.loads(candidate_raw)
    largest=max(t['bytes']for t in cm['tensors']if placement(t['name'])=='device_weights')
    require(largest==357580800,'Actual new largest resident tensor must be output Q4')
    a.out.mkdir(parents=True,exist_ok=False)
    parent_pub=n['precision_candidate']['parent_publication'];require(record(parent_pub['path'])==parent_pub,'Original all-Q8 parent publication changed')
    pp=json.loads(Path(parent_pub['path']).read_text());root=json.loads(Path(pp['source_integrity']['path']).read_text())['source_directory']
    header=a.out/'precision-plan.private.h'
    header.write_text('#pragma once\nnamespace qwen_app {\n'+
        'inline constexpr const char*precision_parent_raw='+json.dumps(parent_raw)+';\n'+
        'inline constexpr const char*precision_candidate_raw='+json.dumps(candidate_raw)+';\n'+
        'inline constexpr const char*precision_parent_sha256='+json.dumps(prep['parent']['sha256'])+';\n'+
        'inline constexpr const char*precision_candidate_sha256='+json.dumps(prep['candidate']['sha256'])+';\n'+
        'inline constexpr const char*precision_parent_root='+json.dumps(root)+';\n'+
        'inline constexpr std::uint64_t precision_device_bytes='+str(prep['footprint']['device_weights'])+'ull;\n'+
        'inline constexpr std::uint64_t precision_expert_bytes='+str(prep['footprint']['mapped_experts'])+'ull;\n'+
        'inline bool precision_parent_file(const std::string&name){for(const char*p:{'+','.join(json.dumps(h['file'])for h in pm['resident_all_Q8_overlay']['headers'])+'})if(name==p)return true;return false;}\n'+
        'inline bool precision_selected_type(const std::string&name,int type){\n'+
        ''.join('if(name=='+json.dumps(c['name'])+')return type==2;\n'for c in cm['precision_overlay']['tensors'])+
        'return false;}\n}\n',newline='\n')
    rh=ROOT/'native/app/precision_overlay_receipt.h'
    receipt_header=once(rh.read_text(),'m.largest_device_tensor!=675430400ull','m.largest_device_tensor!=357580800ull')
    receipt_header='#include "output_plain_segments.h"\n'+receipt_header
    marker='        auto plan=std::find_if(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;});need(__LINE__,plan!=expert_q2_pending_segments.end());'
    receipt_header=once(receipt_header,marker,'''        if(std::none_of(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;})){
            const auto output=std::find_if(baseline.at("tensors").begin(),baseline.at("tensors").end(),[](const Json&t){return t.at("name")=="output.weight";});
            need(__LINE__,output!=baseline.at("tensors").end()&&output->at("file")==name&&output->at("type")=="Q8_0"&&output->at("bytes")==675430400ull&&file==result.logical.end()-1);
            std::vector<std::uint64_t>physical_bytes;for(const auto&p:result.physical){need(__LINE__,p.identity[5]==p.bytes);physical_bytes.push_back(p.bytes);}
            expert_q2_pending_segments.push_back({file->path,output_plain_segments(file->bytes,file->parts,physical_bytes)});
        }
'''+marker)
    typed_header=a.out/rh.name;typed_header.write_text(receipt_header,newline='\n')
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    new_precision=dict(n['precision_candidate']['scope'],selected_tensors=109,candidate_receipt_sha256=prep['candidate']['sha256'],saved_payload_bytes=prep['saved_payload_bytes'])
    entry=once(entry,literal(n['precision_candidate']['scope']),literal(new_precision))
    resident=dict(n['resident_all_Q8']['scope'],additional_payload_saved_bytes=prep['saved_payload_bytes'])
    entry=once(entry,literal(n['resident_all_Q8']['scope']),literal(resident))
    scope=dict(old,schema='ps5-qwen-post-top2-output-Q4-v1',candidate='output-Q4-replay',candidate_id=1,
        control_Experts=2,candidate_Experts=2,output_weight_type='Q4_0',reused_dense_Q4_tensors=108,
        changed_output_tensors=1,verification_width=2,attempt_cap=6,proposal_policy='selected_normal_single_latest',
        format_comparison_is_external=True,external_Q8_control_case=31600,internal_arms_are_same_format_replays=True,
        additional_output_saved_bytes=317849600,quality_changes_reported=True)
    entry=once(entry,literal(old),literal(scope));entry='#include "post_top2_causal.h"\n'+entry
    entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";',
        'arm==0?"output-Q4-control-replay":"output-Q4-candidate-replay";')
    entry=once(entry,'qwen_app::NextFiveCausalEngine causal(*engine,model,context,ordinal>=10);',
        'qwen_app::PostTop2CausalEngine causal(*engine,model,context,ordinal>=10,6);')
    entry=entry.replace('qwen_app::NextFiveCausalEngine&','qwen_app::PostTop2CausalEngine&')
    entry=once(entry,'            row["phase"]=phase;',
        '            row["actual_output_weight_type"]="Q4_0";row["actual_resident_device_weight_bytes"]='+str(prep['footprint']['device_weights'])+'ull;\n            row["phase"]=phase;')
    for text in ['row["output_weight_type"]="Q8_0"','{"output_weight_type","Q8_0"}']:
        entry=entry.replace(text,text.replace('Q8_0','Q4_0'))
    entry=reporting(entry)
    entry=once(entry,'const auto header=qwen_app::receipt_integer(file,"header_bytes");',
        '''const auto header=file.contains("header_bytes")?qwen_app::receipt_integer(file,"header_bytes"):
                        (file_index==76&&file.at("path")=="qwen-flash-next-bf16-00076-of-00076.gguf"&&
                         !plan->segments.empty()&&plan->segments.front().bytes==160?160ull:
                         throw std::runtime_error("Exact isolated output header boundary required"));''')
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry)),
        [Path(__file__),a.preparation,a.publication_plan,header,typed_header,rh,ROOT/'native/app/output_plain_segments.h',ROOT/'native/app/post_top2_causal.h',ROOT/'tools/qualify_post_top2_reporting.py'])
    update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope
    r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['resident_all_Q8']['scope']=resident
    r['precision_candidate'].update(scope=new_precision,preparation=record(a.preparation),publication_plan=record(a.publication_plan),
        actual_sources=sources,commands=jobs,native_verification_pending=True)
    r['post_top2_output_Q4']=dict(scope=scope,actual_sources=sources,commands=jobs,precision_plan=record(header),
        exact_typed_receipt=record(typed_header),external_Q8_reference_case=31600,original_Q8_model_preserved=True,
        actual_GPU_and_Expert_precision_unchanged=True,native_pending=True)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='output_Q4_actual_Top2_composition',
        candidate=record(a.out/'receipt.private.json'),scope=scope,original_driver_heap_and_completion_guards_preserved=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
