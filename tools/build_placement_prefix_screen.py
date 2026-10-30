#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare sealed supplemental Expert placement and complete common-prefix state."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

ROOT=Path(__file__).resolve().parents[1]
ORDER=[0,0,1,1,0]+[0,1]*3+[2,2,2,3,3,3,3,2,2]
RESET=[i for i in range(20) if i<11 or i in (11,12,14,16,18)]

def owner_source(text):
    text='#include "current_bundle.private.h"\n'+text
    start=text.index('int Q2_extra_fd=-1;')
    end=text.index('\nstd::unique_ptr<qwen_app::ResidentMappedSourceReader>',start)
    clone=text[start:end].replace('Q2_extra','Q2_current')
    text=text[:end]+clone+text[end:]
    text=once(text,'admit_Q2_bundle(window);admit_Q2_extra(window);',
              'admit_Q2_bundle(window);admit_Q2_extra(window);admit_Q2_current(window);')
    close='    Q2_bundle_fd=-1;Q2_bundle_verified=Q2_bundle_enabled=false;'
    text=once(text,close,close+'\n    if(!Q2_current_verified||Q2_current_fd<0||!ops.close_file(Q2_current_fd))throw std::runtime_error("Current bundle did not positively close");Q2_current_fd=-1;Q2_current_verified=Q2_current_mode=false;')
    marker='    if(!Q2_extra_mode)return -1;'
    text=once(text,marker,'''    if(Q2_current_mode){
        const auto current=std::lower_bound(std::begin(Q2_current_keys),std::end(Q2_current_keys),key);
        if(current!=std::end(Q2_current_keys)&&*current==key)
            return 1024+Q2_current_physical[std::size_t(current-std::begin(Q2_current_keys))];
    }
'''+marker)
    text=once(text,'const bool extra=first>=512;', 'const bool current=first>=1024,extra=first>=512&&!current;')
    text=once(text,'extra?Q2_extra_fd:Q2_bundle_fd,extra?Q2_extra_identity:Q2_bundle_identity',
              'current?Q2_current_fd:(extra?Q2_extra_fd:Q2_bundle_fd),current?Q2_current_identity:(extra?Q2_extra_identity:Q2_bundle_identity)')
    text=once(text,'Q2_bundle_hits+=n;if(extra)Q2_extra_hits+=n;',
              'Q2_bundle_hits+=n;if(extra)Q2_extra_hits+=n;if(current)Q2_current_hits+=n;')
    return text+'''
extern "C" void qwen_app_select_current_bundle(bool enabled){
 required().require_completed_window();ops.require_metadata_idle();
 if(!Q2_current_verified||Q2_current_fd<0)throw std::runtime_error("Unsealed current bundle");
 Q2_current_mode=enabled;
}
extern "C" std::uint64_t qwen_app_current_bundle_hits(){return Q2_current_hits;}
'''

def engine_source(text):
    text='extern "C" bool qwen_app_partial_prefix_enabled();\n'+text
    start=text.index('void LlamaEngine::prefill(');end=text.index('\nToken LlamaEngine::next()',start)
    text=text[:start]+(ROOT/'native/app/partial_prefix_prefill.inc').read_text()+text[end:]
    start=text.index('void LlamaEngine::enable_prefix_reuse(');end=text.index('\nvoid ',start+5)
    old=text[start:end];new=once(old,'prefill_tokens_!=4','(prefill_tokens_!=4&&prefill_tokens_!=16)')
    return text[:start]+new+text[end:]

def entry_source(text,old,scope,model_scope):
    text='''#include <cstdint>
extern "C" void qwen_app_select_current_bundle(bool);
extern "C" std::uint64_t qwen_app_current_bundle_hits();
namespace {bool common_prefix_enabled=false;}
extern "C" bool qwen_app_partial_prefix_enabled(){return common_prefix_enabled;}
'''+text
    for before,after in ((old['scope'],scope),(old['model_scope'],model_scope)):
        text=once(text,json.dumps(json.dumps(before,separators=(',',':'))),json.dumps(json.dumps(after,separators=(',',':'))))
    text=once(text,'request_count=32','request_count=20')
    text=once(text,'counting_modes[]={0,0,1,1,0,0,2,2,0,0,3,3,0,0,4,4,0}','counting_modes[]={0,0,1,1,0}')
    text=once(text,'quality_modes[]={0,1,2,3,4}','quality_modes[]={0,1}')
    text=once(text,'        std::uint64_t last_payload=0,saved_payload=0,observed_captures=0;',
              '        qwen_app::ResidentCheckpointCapacity prefix_capacity;\n        std::vector<float>prefix_reference(columns);\n        std::uint64_t last_payload=0,saved_payload=0,observed_captures=0;')
    text=once(text,'const auto rounded=qwen_app::checkpoint_replacement_growth(bytes,saved_payload);',
              'const auto rounded=prefix_capacity.new_allocation(context,bytes);')
    text=once(text,'const bool counting=ordinal<17;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-17)%5];\n            const unsigned task=counting?0:(ordinal-17)/5;',
        '''const bool counting=ordinal<5,prefix_trial=ordinal>=11;
            constexpr unsigned prefix_modes[]={2,2,2,3,3,3,3,2,2};
            const unsigned mode=counting?counting_modes[ordinal]:(prefix_trial?prefix_modes[ordinal-11]:quality_modes[(ordinal-5)%2]);
            const unsigned task=counting?0:(prefix_trial?3+(ordinal==13||ordinal==15||ordinal==17||ordinal==19):(ordinal-5)/2);
            const bool group_second=ordinal==13||ordinal==15||ordinal==17||ordinal==19;
            const bool reset_before=!group_second;
            common_prefix_enabled=mode==3;''')
    text=once(text,'            qwen_native_driver_begin();engine.reset();qwen_native_driver_complete();',
              '            if(reset_before){\n            qwen_native_driver_begin();engine.reset();qwen_native_driver_complete();')
    text=once(text,'qwen_app_six_configure(mode);','qwen_app_six_configure(0);')
    text=text.replace('qwen_app_lean_prefill_configure(mode==3?5:4);','qwen_app_lean_prefill_configure(4);')
    text=once(text,'            observed_captures=0;','            observed_captures=0;last_payload=0;saved_payload=0;')
    marker='            qwen_native_driver_complete();require_model_CPU_budget();\n\n            std::size_t rows=0;'
    text=once(text,marker,'''            qwen_native_driver_complete();require_model_CPU_budget();
            if(common_prefix_enabled)engine->enable_prefix_reuse(admit_checkpoint);
            }
            qwen_app_select_current_bundle(mode==1);
            qwen_app_lean_prefill_configure(4);qwen_app_route_begin(6);
            const auto current_hits_before=qwen_app_current_bundle_hits();
            const auto prefix_before=engine->prefix_reuse_stats();

            std::size_t rows=0;''')
    text=once(text,'std::size_t rows=0;double max_error=0;bool finite=true;',
              'std::size_t rows=0;double max_error=0,prefix_first_error=0;bool finite=true;')
    marker='                    if(!std::isfinite(v[i]))finite=false;'
    text=once(text,marker,marker+'''
                    if(prefix_trial&&group_second&&!rows){
                        if(ordinal==13)prefix_reference[i]=v[i];
                        else prefix_first_error=std::max(prefix_first_error,std::abs(double(v[i])-prefix_reference[i]));
                    }''')
    text=once(text,'            qwen_app::require_resident_context_counter_baseline(*previous,*cache);',
              '            if(reset_before)qwen_app::require_resident_context_counter_baseline(*previous,*cache);')
    marker='            const qwen_app::Request request{run+"-"+std::to_string(ordinal),qwen_app::render_bounded_user_prompt(chat_template,\n                counting?qwen_app::demo_prompt:quality_prompts[task]),256,32};'
    text=once(text,marker,'''            const std::string common_instruction="Follow this instruction carefully. Answer the arithmetic question at the end. Return only the decimal integer and no explanation. Arithmetic question: ";
            const auto prompt=prefix_trial?common_instruction+(group_second?"18 + 27":"17 + 26"):(counting?std::string(qwen_app::demo_prompt):quality_prompts[task]);
            const qwen_app::Request request{run+"-"+std::to_string(ordinal),qwen_app::render_bounded_user_prompt(chat_template,prompt),256,32};''')
    text=once(text,'            const auto prefill=qwen_app_lean_prefill_stats();const auto selected=qwen_app::lean_prefill_policy(mode==3?5:4);',
              '            const auto prefill=qwen_app_lean_prefill_stats();const auto selected=qwen_app::lean_prefill_policy(4);\n            const auto prefix_after=engine->prefix_reuse_stats();\n            const auto reused=prefix_after.request_hit?prefix_after.last_reused_prompt_tokens:0u;')
    text=text.replace('prefill.input_tokens!=result.metrics.prompt_tokens','prefill.input_tokens+reused!=result.metrics.prompt_tokens')
    text=once(text,'            row["actual_graph_reuses"]=qwen_app_six_reuse_count();', '''            row["actual_graph_reuses"]=qwen_app_six_reuse_count();
            row["cache_reset_before_request"]=reset_before;
            row["current_bundle_hits"]=qwen_app_current_bundle_hits()-current_hits_before;
            row["common_prefix"]={{"enabled",common_prefix_enabled},{"pair_second",group_second},{"reused_tokens",reused},
                {"captures",prefix_after.captures-prefix_before.captures},{"restores",prefix_after.restores-prefix_before.restores},
                {"capture_ns",prefix_after.capture_ns-prefix_before.capture_ns},{"restore_ns",prefix_after.restore_ns-prefix_before.restore_ns},
                {"suffix_first_full_vocabulary_logit_error",prefix_first_error}};
            if(prefix_after.captures>prefix_before.captures)prefix_capacity.completed(context,last_payload,result.request_reset_completed);''')
    text=once(text,'{"cache_reset_before_request",true}',
              '{"cache_reset_before_request",completed.at(i).at("cache_reset_before_request")}')
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','normal-parent','bundle','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());normal=json.loads(a.normal_parent.read_text());bundle=json.loads(a.bundle.read_text())
    require(bundle['completed']and bundle['verified_Experts']==28,'Sealed complete triplets required')
    require(record(bundle['selection']['path'])==bundle['selection'],'Sealed selection changed')
    selection=json.loads(Path(bundle['selection']['path']).read_text())['Experts'];pairs=sorted((r['layer'],r['expert'],i)for i,r in enumerate(selection))
    a.out.mkdir(parents=True,exist_ok=False)
    header=a.out/'current_bundle.private.h';row=bundle['output']
    path='/app0/'+row['path'].split('/PPSA99190/',1)[1]
    header.write_text('#pragma once\n#include <cstdint>\n#include <array>\ninline constexpr const char*Q2_current_path='+json.dumps(path)+';\n'
        +'inline constexpr const char*Q2_current_SHA256='+json.dumps(row['sha256'])+';\n'
        +'inline constexpr std::uint64_t Q2_current_expected_identity[]={'+','.join(map(str,row['identity']))+'};\n'
        +'inline constexpr std::array<unsigned,2>Q2_current_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e,i in pairs)+'};\n'
        +'inline constexpr unsigned Q2_current_physical[]={'+','.join(str(i)for l,e,i in pairs)+'};\n'
        +'inline bool Q2_current_mode=false;\n',newline='\n')
    budget=a.out/'device_buffer_budget.h';budget.write_text((ROOT/'native/app/device_buffer_budget.h').read_text().replace('model_internal_workspace_budget = 256ull << 20','model_internal_workspace_budget = 248ull << 20'),newline='\n')
    old=prior['routing_sharing'];scope=dict(old['scope'],schema='ps5-qwen-current-placement-prefix-v1',maximum_requests=20,order=ORDER,
        counting_requests=5,quality_requests=6,common_prefix_requests=9,reset_ordinals=RESET,supplemental_bundles=28,
        common_prefix_tokens=16,cache_budget_bytes=1333739520,graph_reuse_enabled=False)
    model_scope=dict(old['model_scope'],schema='ps5-qwen-current-placement-prefix-model-v1',maximum_requests=20,timed_requests=4,selected_Experts='10_prefill_6_decode')
    owner_cmd=prior['all_Q2_optimized_monitor']['commands'][1]
    variants={'entry':(prior['compile_commands'][0],entry_source(Path(old['actual_sources']['entry']['path']).read_text(),old,scope,model_scope)),
              'engine':(old['commands'][2],engine_source(Path(old['actual_sources']['engine']['path']).read_text())),
              'owner':(owner_cmd,owner_source(Path(owner_cmd[owner_cmd.index('-c')+1]).read_text()))}
    result,commands,sources=link(a.parent,a.out,variants,[Path(__file__),a.normal_parent,a.bundle,header,budget,ROOT/'native/app/partial_prefix_prefill.inc'])
    result['routing_sharing'].update(scope=scope,model_scope=model_scope)
    result['expert_q2_model']['scope']=model_scope;result['all_Q2_bundle_comparison']=dict(scope=scope)
    result['placement_prefix_screen']=dict(scope=scope,model_scope=model_scope,commands=commands,actual_sources=sources,
        bundle=record(a.bundle),PS5_operations=0,production_adopted=False)
    seal(result,a.workspace,a.cache,a.out);print('One-load placement and common-prefix comparison built; no console operations.')

if __name__=='__main__':main()
