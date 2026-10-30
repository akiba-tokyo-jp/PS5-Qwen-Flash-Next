#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate the sealed output-only Q8 exception and compare 867/997 slots."""
import argparse,copy,json
from pathlib import Path
from expert_q4 import require,record
from build_speculative_batch_probe import once
from build_six_candidate_screen import SCOPE as OLD_SCOPE,COUNTING as OLD_COUNTING
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
COUNTING=[0,0,1,1,0];ORDER=COUNTING+[0,1]*3
SCOPE=dict(OLD_SCOPE,schema='ps5-qwen-output-Q8-cache-screen-v1',maximum_requests=11,order=ORDER,
    counting_requests=5,quality_requests=6,modes=['Q8_867_slots','Q8_997_slots'],
    active_cache_slots=[867,997],physical_cache_planes=998,cache_budget_bytes=1533419520,
    output_weight_type='Q8_0',saved_resident_payload_bytes=595968000,transferred_postload_quota_bytes=199680000,
    integer_activation_quantization_disabled=True,cooperative_matrix_paths_disabled=True,
    additional_physical_allocations_require_original_Direct_and_system_reserves=True)

def force_float_inputs(text):
    start=text.index('int main(int argc, char ** argv) {')
    at=text.index('    try {',start)+len('    try {')
    return text[:at]+'''\n        if(setenv("GGML_VK_DISABLE_INTEGER_DOT_PRODUCT","1",1)||
           setenv("GGML_VK_DISABLE_COOPMAT","1",1)||setenv("GGML_VK_DISABLE_COOPMAT2","1",1))
            throw std::runtime_error("Output Q8 requires original floating activation inputs");
'''+text[at:]

def cache_source(text):
    text='#include "resident_output_q8_cache_reset.h"\n'+text
    marker='struct moe_cache_slru {'
    text=once(text,marker,'namespace {unsigned output_Q8_selected_slots=997;}\nextern "C" unsigned qwen_app_output_Q8_slots(){return output_Q8_selected_slots;}\n'+marker)
    text=once(text,'g.n_slots < 867','g.n_slots < 997')
    text=once(text,'groups[0].n_slots!=(groups[0].ref[0]->type==GGML_TYPE_Q2_K?867:int(qwen_app::selected_padded_cache_geometry().active_slots))',
        '(groups[0].n_slots!=867&&groups[0].n_slots!=997)')
    text=once(text,'qwen_app::reset_expert_all_q2_cache_metadata(g.slru,unsigned(g.layers.size()))',
        'qwen_app::reset_resident_output_Q8_cache(g.slru,unsigned(g.layers.size()),output_Q8_selected_slots)')
    text=once(text,'            ++result.groups;result.maps+=g.layers.size();result.slots+=g.n_slots;',
        '            g.n_slots=int32_t(output_Q8_selected_slots);\n            ++result.groups;result.maps+=g.layers.size();result.slots+=g.n_slots;')
    text=text.replace('u.slot>=867','u.slot>=int(output_Q8_selected_slots)').replace('u.slots[item]>=867','u.slots[item]>=int(output_Q8_selected_slots)')
    return text+'''
extern "C" void qwen_app_select_output_Q8_slots(unsigned slots){
 if((slots!=867&&slots!=997)||!resident_reuse_enabled||!resident_reuse_owner||resident_reuse_thread!=std::this_thread::get_id())
    throw std::runtime_error("Output Q8 slot selection requires the original idle producer");
 qwen_app_complete_predictive_expert();output_Q8_selected_slots=slots;
}
'''

def entry_source(text,old,model_scope,parent_root):
    text='#include "resident_output_q8_source.h"\n#include "resident_output_q8_profile.h"\n#include "output_Q8_parent.private.h"\nextern "C" void qwen_app_select_output_Q8_slots(unsigned);\nextern "C" unsigned qwen_app_output_Q8_slots();\n'+text
    for before,after in ((old['scope'],SCOPE),(old['model_scope'],model_scope)):
        text=once(text,json.dumps(json.dumps(before,separators=(',',':'))),json.dumps(json.dumps(after,separators=(',',':'))))
    text=once(text,'std::optional<qwen_app::ExpertAllQ2Receipt>','std::optional<qwen_app::ResidentOutputQ8Receipt>')
    text=once(text,'Expert_Q2_manifest.emplace(receipt);','Expert_Q2_manifest.emplace(receipt,output_Q8_parent_raw);')
    text=once(text,'qwen_app::expert_all_q2_source_integrity(policy.at("native_first_generation_validation"),receipt,Expert_Q2_root,expected_mapped_files)',
        'qwen_app::resident_output_Q8_source_integrity(policy.at("native_first_generation_validation"),receipt,Json::parse(output_Q8_parent_raw),Expert_Q2_root,expected_mapped_files)')
    text=once(text,'qwen_app::validate_expert_all_q2_footprint(footprint,expected_mapped_files);',
        'qwen_app::validate_resident_output_Q8_footprint(footprint,expected_mapped_files);')
    text=once(text,'if(Expert_Q2_receipt)return qwen_app::expert_q2_logical_path(*Expert_Q2_receipt,Expert_Q2_root,name);',
        'if(Expert_Q2_receipt)return qwen_app::expert_q2_logical_path(*Expert_Q2_receipt,\n'
        '        name==Expert_Q2_receipt->at("files").back().at("path")?Expert_Q2_root:'+json.dumps(parent_root)+',name);')
    text=once(text,'        const auto buffer_type=ggml_backend_dev_buffer_type(device);',
        '        memory_budget.expert_cache=qwen_app::resident_output_Q8_cache_budget;\n        const auto buffer_type=ggml_backend_dev_buffer_type(device);')
    text=once(text,'reset.slots!=867','reset.slots!=qwen_app_output_Q8_slots()')
    text=once(text,'request_count=32','request_count=11')
    text=once(text,'counting_modes[]={'+','.join(map(str,OLD_COUNTING))+'}','counting_modes[]={0,0,1,1,0}')
    text=once(text,'quality_modes[]={0,1,2,3,4}','quality_modes[]={0,1}')
    text=once(text,'ordinal<17;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-17)%5]',
        'ordinal<5;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-5)%2]')
    text=once(text,'const unsigned task=counting?0:(ordinal-17)/5','const unsigned task=counting?0:(ordinal-5)/2')
    text=once(text,'            resident_reset_empty_context(context,model,startup.admission_report);',
        '            qwen_app_select_output_Q8_slots(mode?997:867);\n            resident_reset_empty_context(context,model,startup.admission_report);')
    text=once(text,'qwen_app_six_configure(mode);','qwen_app_six_configure(0);')
    text=text.replace('qwen_app_lean_prefill_configure(mode==3?5:4);','qwen_app_lean_prefill_configure(4);')
    text=text.replace('const auto selected=qwen_app::lean_prefill_policy(mode==3?5:4);','const auto selected=qwen_app::lean_prefill_policy(4);')
    text=once(text,'row["actual_graph_reuses"]=qwen_app_six_reuse_count();',
        'row["actual_graph_reuses"]=qwen_app_six_reuse_count();row["actual_active_slots"]=qwen_app_output_Q8_slots();row["output_weight_type"]="Q8_0";')
    return force_float_inputs(text)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','normal-parent','publication','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());normal=json.loads(a.normal_parent.read_text())
    published=json.loads(a.publication.read_text());require(published['completed']and published['native_whole_SHA256_EOF_identities_passed'],'New Q8 assets must be sealed before integration')
    seal_proof=json.loads(Path(published['source_integrity']['path']).read_text());require(record(published['source_integrity']['path'])==published['source_integrity'],'Q8 native source proof changed')
    parent_path=a.cache/'Expert-all-Q2-receipt-8652.json';raw=parent_path.read_text();require(record(parent_path)['sha256']=='efd101c3661e6eb81f17306c43fc41b361f94aa58495f2025401659228163191','Pinned original parent required')
    old=prior['routing_sharing'];model_scope=dict(old['model_scope'],schema='ps5-qwen-output-Q8-model-screen-v1',maximum_requests=11,timed_requests=4,
        selected_Experts='10_prefill_6_decode',non_Expert_precision_preserved=False,output_only_Q8_exception=True,
        expected_active_Q2_slots=997,cache_budget_bytes=1533419520)
    a.out.mkdir(parents=True,exist_ok=False)
    header=a.out/'output_Q8_parent.private.h';header.write_text('#pragma once\ninline constexpr const char*output_Q8_parent_raw='+json.dumps(raw)+';\n',newline='\n')
    budget=a.out/'device_buffer_budget.h';text=(ROOT/'native/app/device_buffer_budget.h').read_text()
    text=once(text,'model_postload_device_budget = 1792ull << 20','model_postload_device_budget = (1792ull << 20) + 199680000ull')
    text=once(text,'model_internal_workspace_budget = 256ull << 20','model_internal_workspace_budget = 248ull << 20');budget.write_text(text,newline='\n')
    oldseal=json.loads((a.cache/'build/Expert-all-Q2-seal-8650/source-integrity.private.json').read_text())
    entry_cmd=prior['compile_commands'][0];cache_cmd=old['commands'][1];owner_cmd=prior['all_Q2_optimized_monitor']['commands'][1]
    variants={'entry':(entry_cmd,entry_source(Path(old['actual_sources']['entry']['path']).read_text(),old,model_scope,oldseal['source_directory'])),
        'cache':(cache_cmd,cache_source(Path(old['actual_sources']['cache']['path']).read_text())),
        'owner':(owner_cmd,Path(owner_cmd[owner_cmd.index('-c')+1]).read_text())}
    inputs=[Path(__file__),a.normal_parent,a.publication,Path(published['source_integrity']['path']),parent_path,header,budget,
        ROOT/'native/app/resident_output_q8_receipt.h',ROOT/'native/app/resident_output_q8_source.h',
        ROOT/'native/app/resident_output_q8_cache_reset.h',ROOT/'native/app/resident_output_q8_profile.h']
    result,commands,sources=link(a.parent,a.out,variants,inputs)
    result['routing_sharing'].update(scope=SCOPE,model_scope=model_scope)
    result['expert_q2_model']['scope']=model_scope;result['all_Q2_bundle_comparison']=dict(scope=SCOPE)
    result['output_Q8_screen']=dict(scope=SCOPE,model_scope=model_scope,actual_sources=sources,commands=commands,
        source_integrity=published['source_integrity'],candidate_receipt=published['candidate'],
        device_quota_transfer=dict(actual_resident_payload_saving=595968000,postload_transfer=199680000,
            original_physical_reserves_retained=True,single_buffer_limit=512<<20),PS5_operations=0,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out);print('Sealed output Q8 and cache-capacity comparison built; no console operations.')
if __name__=='__main__':main()
