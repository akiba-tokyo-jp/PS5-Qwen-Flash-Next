#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package matched headless full-model sort arms from completed component evidence."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','provider','software-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--F32-observer',type=Path)
    p.add_argument('--three-ordinary-control',action='store_true',help='Package only an unchanged target control for the separate S1 lifetime cohort')
    p.add_argument('--prefill-refinement',type=Path,help='Package a separate bounded P1 tail-width comparison with the same original request sequence')
    a=p.parse_args();provider=load(a.provider);proof=load(a.software_proof)
    need(provider['completed'] and provider['physical_sort_lanes']==128 and provider['new_arena_controls']==104 and
         provider['new_shader_lease_controls']==10 and provider['GPU_executable_sections_byte_exact'] and
         proof['completed'] and proof['build']==record(a.provider) and proof['positive_fences']==64 and proof['full_indices_and_ties_exact'],
         'Completed distinct lease, real GGML and changed software-sort evidence required')
    for row in provider['inputs']:need(record(row['path'])==row,'A qualified source changed')
    for key in ('graph','GPU','state','shader_data','shader_wrapper','shader'):need(record(provider[key]['path'])==provider[key],'A native fused provider changed')
    selected=load(a.current/'provenance/selected-entry-build.private.json');original=load(selected['application_policy']['path'])
    need(record(original['source']['path'])==original['source'],'Selected actual source changed')
    a.out.mkdir(parents=True,exist_ok=False);old_dir=Path(original['source']['path']).parent
    for header in old_dir.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    text=Path(original['source']['path']).read_text(encoding='utf-8')
    need(not(a.prefill_refinement and a.three_ordinary_control),'One explicit ordinary or P1 comparison scope required')
    prefill=load(a.prefill_refinement) if a.prefill_refinement else None
    if prefill:
        need(prefill['completed'] and prefill['cold_output_tail_rows']==8 and len(prefill['new_selector_controls'])==16 and
             prefill['actual_PS5_ABI_compiled'] and all(record(r['path'])==r for r in prefill['source_inputs']),
             'The distinct eight-row selector must have completed all new controls')
    scope=dict(schema='ps5-qwen-fused-full-sort-model-v1',kind='G1-fused-full-sort',requests=3,model_loads=1,
        HTTP_requests=0,VideoOut_starts=0,maximum_output_tokens_per_request=32,original_cold_retained_exact_prefix_sequence=True,
        full_bitonic_tie_order=True,physical_sort_lanes=128,partial_TopK=False,extra_rank_multiply_nodes=0,
        coefficients_and_output_share_disjoint_GPU_ranges=True,driver_code_changed=False,persistent_caches=False)
    if a.three_ordinary_control:
        scope=dict(schema='ps5-qwen-ordinary-target-control-v1',kind='S1-ordinary-target-control',requests=3,model_loads=1,
            HTTP_requests=0,VideoOut_starts=0,maximum_output_tokens_per_request=32,all_three_requests_ordinary=True,
            auxiliary_contexts=0,MTP_process_calls=0,original_target_graph_and_GPU_unchanged=True,driver_code_changed=False,persistent_caches=False)
        text=once(text,'            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;',
            '            const bool second=false; // Matched ordinary target requests for the S1 cohort.')
        text=once(text,'            const bool reuse=ordinal>0;',
            '            const bool reuse=false; // No prefix snapshot is consumed by this ordinary-only cohort.')
        text=once(text,'            if(ordinal==1)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);',
            '            // Ordinary-only requests do not certify a final prefix consumer.')
    if prefill:
        scope=dict(schema='ps5-qwen-cold-tail-eight-headless-v1',kind='P1-tail-eight',requests=3,model_loads=1,
            HTTP_requests=0,VideoOut_starts=0,maximum_output_tokens_per_request=32,cold_output_tail_rows=8,
            original_cold_retained_exact_prefix_sequence=True,later_output_selection_unchanged=True,
            driver_code_changed=False,persistent_caches=False)
        text='extern "C" void qwen_P1_select_request(unsigned,bool);\n'+once(text,
            '            const auto &result=trial.run(request,[&](const auto &bound){',
            '            qwen_P1_select_request(ordinal,policy.at("native_P1_headless_arm").get<unsigned>()==1);\n'+
            '            const auto &result=trial.run(request,[&](const auto &bound){')
        text=once(text,'        const auto policy = Json::parse(policy_file);',
            '        const auto policy = Json::parse(policy_file);\n        if(policy.at("native_P1_headless_arm").get<unsigned>()>1)throw std::runtime_error("One bounded P1 control or candidate arm required");')
        text=once(text,'std::size_t rows=0;double max_error=0;bool geometry_error=false,value_error=false;',
            'std::size_t rows=0;double max_error=0,first_error=0;bool geometry_error=false,value_error=false;')
        text=once(text,'max_error=std::max(max_error,e);}',
            'max_error=std::max(max_error,e);if(!rows)first_error=std::max(first_error,e);}')
        text=once(text,'{"maximum_absolute_logit_error",max_error},',
            '{"maximum_absolute_logit_error",max_error},{"first_row_maximum_absolute_logit_error",first_error},')
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact fused full-sort model scope required");')
    text=headless_entry(text,scope['kind'],3,'Json{{"completed",true},{"original_three_request_scope",true},{"requests",completed}}')
    if not a.F32_observer:text=once(text,'{"timings_usable_for_performance",false}','{"timings_usable_for_performance",true}')
    baseline=Path(original['source']['path']).read_text(encoding='utf-8')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
        need(body(baseline,name)==body(text,name),'An original memory, identity, context or SELF guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    command=next(c for c in selected['commands'] if '-c' in c and c[c.index('-c')+1].endswith('entry.private.cpp')).copy()
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:
        path=a.out/Path(root['external-contents']).name
        if path.exists():root['external-contents']=path.resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    command=[str(a.out) if value==str(old_dir) else value for value in command]
    command[1:1]=['-I',str(a.out)];command[command.index('-ivfsoverlay')+1]=str(view)
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(entry)
    if '-MF' in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
    def run(job,label):
        completed=subprocess.run(list(map(str,job)),capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(completed.stdout+completed.stderr)
        need(completed.returncode==0,(completed.stdout+completed.stderr).decode(errors='replace')[-4000:])
    run(command,'entry-compile');packages={}
    current_package=load(a.current/'provenance/current-package.private.json');identity=current_package['required_bundle_identity_audit']['provider']
    observer=load(a.F32_observer) if a.F32_observer else None
    if observer:need(observer['completed'] and observer['qualification_only'] and record(observer['artifact']['path'])==observer['artifact'],'Unchanged full-row observer required')
    for arm in (('control',) if a.three_ordinary_control else ('control','candidate')):
        profile=copy.deepcopy(original);profile.update(kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
            model_and_GPU_topology_unchanged=False,model_and_GPU_guards_preserved=True,headless_model_audit=True,
            headless_audit_kind=scope['kind'],headless_requests=3,overrides=dict(original['overrides'],native_headless_model_audit=scope),
            G1_fused_provider=record(a.provider),G1_software_proof=record(a.software_proof),G1_arm=arm,
            performance_timings_usable=not bool(observer),production_adopted=False,native_performance_qualified=False)
        if a.three_ordinary_control:
            for key in ('G1_fused_provider','G1_software_proof','G1_arm'):profile.pop(key)
        if prefill:
            for key in ('G1_fused_provider','G1_software_proof','G1_arm'):profile.pop(key)
            profile.update(P1_refinement=record(a.prefill_refinement),P1_arm=arm)
            profile['overrides']['native_P1_headless_arm']=int(arm=='candidate')
        policy=a.out/(arm+'-policy.private.json');save(policy,profile)
        flags=provider['link_flags'] if arm=='candidate' else provider['link_flags'][:-1]
        if a.three_ordinary_control:flags=[]
        if prefill:flags=['--wrap='+n for n in ('llama_process','llama_sampler_apply','llama_sampler_sample')]
        if not prefill:need(flags[-1]=='--wrap=qwen_app_prepare_shader_code' if arm=='candidate' else '--wrap=qwen_app_prepare_shader_code' not in flags,'Only candidate redirects the shader resource lease')
        job=[sys.executable,'-B',ROOT/'tools/relink_retained_current.py','--current',a.current,'--out',a.out/(arm+'-link'),
            '--replace','entry.o='+str(entry),'--replace','early-SELF.o='+original['CPU_SELF_provider']['artifact']['path'],
            '--application-policy',policy]+['--link-flag='+f for f in flags]
        if not(a.three_ordinary_control or prefill):job+=['--add-object',provider['state']['path']]
        if prefill:job+=['--add-object',prefill['selector']['path'],'--replace','model_graph.o='+prefill['model_provider_reused']['path']]
        elif arm=='candidate':job+=['--replace','graph.o='+provider['graph']['path'],'--replace','gpu.o='+provider['GPU']['path'],
            '--add-object',provider['shader_data']['path'],'--add-object',provider['shader_wrapper']['path']]
        if observer:job+=['--add-object',observer['artifact']['path']]+['--link-flag='+f for f in observer['link_flags']]
        run(job,arm+'-link')
        run([sys.executable,'-B',ROOT/'tools/package_retained_current.py','--workspace',a.workspace,'--current',a.current,
            '--relink',a.out/(arm+'-link/result.private.json'),'--out',a.out/(arm+'-SELF'),
            '--formatter-from',a.current/'provenance/current-package.private.json','--identity-provider',identity['path']],arm+'-SELF')
        packages[arm]=record(a.out/(arm+'-SELF/result.private.json'))
    save(a.out/'result.private.json',dict(completed=True,provider=record(a.provider),software_proof=record(a.software_proof),
        entry=record(entry),source=record(source),packages=packages,F32_qualification=bool(observer),
        original_native_guards_unchanged=True,component_checks_replayed=0,PS5_operations=0,native_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,packages=len(packages),F32_qualification=bool(observer),three_ordinary_target_control=a.three_ordinary_control,PS5_operations=0)))


if __name__=='__main__':main()
