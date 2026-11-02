#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one headless real-target capture with sequential stateless/stateful MTP replay."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from check_headless_legacy_policy import check as check_legacy_policy
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','graph','context','shader-checks','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reverse',action='store_true');a=p.parse_args()
    base=load(a.base_entry);graph=load(a.graph);profile=load(base['application_policy']['path'])
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and graph['selected_object_byte_exact'],
         'Selected entry and byte-exact current graph required')
    for row in (profile['source'],base['entry'],base['reader'],graph['source'],graph['artifact']):need(record(row['path'])==row,'Selected input changed')
    retained=load(a.current/'provenance/retained-relink-inputs.private.json')
    selected=next(row for row in retained if Path(row['original_path']).name=='graph.o')
    need(all(selected[key]==graph['artifact'][key] for key in ('bytes','sha256')),'The reconstructed base graph must still be selected')
    context=load(a.context);checks=load(a.shader_checks)
    need(context['completed'] and context['selected_object_byte_exact'] and checks['completed'] and checks['all_selected_objects_byte_exact'],
         'Complete byte-exact current context and both shader checks required')
    for recovered in [context,*checks['providers'].values()]:
        for key in ('source','artifact'):need(record(recovered[key]['path'])==recovered[key],'Recovered source or object changed')
        actual=next(row for row in retained if row['path']==recovered['actual_provider']['path'])
        need(all(actual[key]==recovered['actual_provider'][key] for key in ('path','bytes','sha256')),'Recovered provider is no longer selected')
    a.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    names=('persistent_mtp_cursor.h','persistent_mtp_shadow.h','persistent_mtp_shadow.cpp')
    for name in names:shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    # This explicit application quota was already sufficient for the historical
    # one-context MTP slice (654442496-byte peak). Fresh physical/OS admission,
    # allocation accounting and all original reserves remain active.
    CPU=a.out/'model_cpu_budget.h';CPU.write_text((ROOT/'native/app/model_cpu_budget.h').read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    text='#include "persistent_mtp_shadow.h"\n'+original
    CPU_guard=body(original,'require_model_CPU_budget')
    text=once(text,CPU_guard,CPU_guard.replace('qwen_app::maximum_model_CPU_heap_bytes','(672ull<<20)'))
    scope=dict(schema='ps5-qwen-persistent-MTP-shadow-v1',kind='S1-MTP-shadow',requests=1,model_loads=1,HTTP_requests=0,VideoOut_starts=0,
        target_tokens_selected_by_auxiliary=0,actual_target_inputs_replayed_after_completion=True,maximum_simultaneous_auxiliary_contexts=1,
        auxiliary_contexts=2,maximum_proposals_per_arm=24,stateless_auxiliary_KV_clear_each_proposal=True,
        auxiliary_rollback_snapshots=0,target_rollback_snapshots=1,
        MTP_active_tensors=34,MTP_graph_capacity=1088,CPU_heap_check_provider_count=3,
        unused_cross_request_F32_copy_removed_bytes=33*248320*4,existing_row_finite_checks_preserved=True,
        persistent_auxiliary_KV_clear_once=True,first_auxiliary_arm=1 if a.reverse else 0,model_MTP_weights_loaded=True,
        MTP_layer=48,MTP_Experts_resident=True,trunk_Expert_CPU_placement_unchanged=True,auxiliary_KV_type='F32',
        CPU_heap_quota_bytes=672<<20,CPU_quota_is_application_policy_not_hardware_limit=True,
        legacy_initial_policy_CPU_budget_bytes=512<<20,legacy_gate_fixed_values_preserved=True,
        physical_OS_Flexible_Direct_and_positive_completion_guards_preserved=True,performance_timings_usable=False)
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        Json MTP_shadow_audit;\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact sequential persistent MTP shadow scope required");')
    placement=r'''
        std::vector<llama_model_tensor_buft_override>MTP_placements;
        if(!model_params.tensor_buft_overrides)throw std::runtime_error("Actual target Expert placement required");
        unsigned MTP_replaced=0;
        for(unsigned i=0;i<16;++i){
            const auto row=model_params.tensor_buft_overrides[i];
            if(!row.pattern){MTP_placements.push_back(row);break;}
            auto selected=row;
            if(std::string(row.pattern)==R"(\.ffn_(gate|up|down|gate_up)_exps\.weight$)"){
                selected.pattern=R"(^blk\.([0-9]|[1-3][0-9]|4[0-7])\.ffn_(gate|up|down|gate_up)_exps\.weight$)";++MTP_replaced;
            }
            MTP_placements.push_back(selected);
        }
        if(MTP_replaced!=1||MTP_placements.empty()||MTP_placements.back().pattern)
            throw std::runtime_error("One exact trunk-only CPU Expert override required");
        model_params.tensor_buft_overrides=MTP_placements.data();model_params.load_mtp=true;
'''
    marker='        auto model_params=qwen_app::streaming_model_params(ggml_backend_cpu_buffer_type());'
    text=once(text,marker,marker+placement)
    marker='            qwen_app::FirstGeneration trial(consumer);'
    replacement='''            qwen_app::MtpShadowBoundaries MTP_boundaries;
            MTP_boundaries.begin=qwen_native_driver_begin;MTP_boundaries.complete=qwen_native_driver_complete;
            MTP_boundaries.checkpoint=qwen_native_driver_checkpoint;MTP_boundaries.stage=qwen_native_stage;
            MTP_boundaries.guard=[]{require_model_CPU_budget();};
            MTP_boundaries.target_is_ordinary=[&]{return engine->speculative_step_stats().attempts==0;};
            qwen_app::PersistentMtpShadow shadow(consumer,model,context,std::move(MTP_boundaries),REVERSE);
            qwen_app::FirstGeneration trial(shadow);'''.replace('REVERSE','true' if a.reverse else 'false')
    text=once(text,marker,replacement)
    marker='            {qwen_load::CpuSpan measured(qwen_load::token_persistence);token_ledger.close();}'
    text=once(text,marker,'            MTP_shadow_audit=shadow.report();\n'+marker)
    next_policy=dict(profile['overrides']['native_next_five_normal'],steady_CPU_heap_limit_bytes=672<<20)
    pattern=r'if\(policy\.at\("native_next_five_normal"\)!=Json::parse\(("(?:\\.|[^"\\])*")\)\)'
    matches=list(re.finditer(pattern,text));need(len(matches)==1,'One actual next-five policy check required')
    parsed=json.loads(json.loads(matches[0][1]));need(parsed==profile['overrides']['native_next_five_normal'],'Actual compiled policy differs from selected profile')
    text=text[:matches[0].start(1)]+json.dumps(json.dumps(next_policy,separators=(',',':')))+text[matches[0].end(1):]
    text=headless_entry(text,scope['kind'],1,'MTP_shadow_audit',retain_reference=False)
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        candidate_body=body(text,name)
        if name=='require_model_CPU_budget':candidate_body=candidate_body.replace('(672ull<<20)','qwen_app::maximum_model_CPU_heap_bytes')
        need(body(original,name)==candidate_body,'A physical memory, identity or reset guard changed outside the explicit CPU quota')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    ec=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent);overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    CPU_name=(ROOT/'native/app/model_cpu_budget.h').resolve().as_posix()
    matches=[root for root in overlay['roots'] if root['name'].replace('\\','/').lower()==CPU_name.lower()]
    need(not matches,'The selected view must not contain an unaccounted CPU budget provider')
    overlay['roots'].append(dict(type='file',name=CPU_name,**{'external-contents':CPU.resolve().as_posix()}))
    view=a.out/'selected-view.private.json';save(view,overlay)
    legacy_check=check_legacy_policy(a.workspace,a.current,view,a.out/'legacy-policy-host-check')
    ec=[str(a.out) if x==old_view else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(view)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    gs=a.out/'graph.private.cpp';gt=Path(graph['source']['path']).read_text(encoding='utf-8')
    gt=once(gt,'if(n_expert==512&&n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy',
        'if(il<48&&n_expert==512&&n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy')
    gs.write_text(gt,encoding='utf-8',newline='\n');go=a.out/'graph.o';gc=graph['command'].copy()
    gc[gc.index('-c')+1]=str(gs);gc[gc.index('-o')+1]=str(go)
    if '-MF'in gc:gc[gc.index('-MF')+1]=str(a.out/'graph.private.d')
    extra_jobs=[];required_replacements={};supporting_inputs=[]
    ct=Path(context['source']['path']).read_text(encoding='utf-8')
    capacity='''uint32_t llama_context::graph_max_nodes(uint32_t n_tokens) const {
    if(cparams.ctx_type==LLAMA_CONTEXT_TYPE_MTP&&model.arch==LLM_ARCH_QWEN4EXP&&
       cparams.n_seq_max==1&&cparams.n_rs_seq==0&&cparams.n_ubatch==1&&!cparams.training&&model.loras.empty()){
        uint32_t active=2;
        for(const auto&item:model.tensors_by_name)if(item.first.rfind("blk.48.",0)==0)++active;
        if(active!=34||!sampling.samplers.empty())throw std::runtime_error("Exact32-tensor single MTP head required");
        const auto cap=std::max<uint32_t>(n_tokens*40,32u*active);
        char stage[192];std::snprintf(stage,sizeof(stage),"S1_MTP_graph_capacity nodes=%u active_tensors=%u n_tokens=%u auxiliary_rollback=0",cap,active,n_tokens);
        qwen_native_stage(stage);return cap;
    }
'''
    ct='#include <cstdio>\nextern "C" void qwen_native_stage(const char*);\n'+once(ct,'uint32_t llama_context::graph_max_nodes(uint32_t n_tokens) const {',capacity)
    cs=a.out/'context.private.cpp';cs.write_text(ct,encoding='utf-8',newline='\n');co=a.out/'context.o'
    cc=context['command'].copy();cc[cc.index('-c')+1]=str(cs);cc[cc.index('-o')+1]=str(co)
    if '-MF'in cc:cc[cc.index('-MF')+1]=str(a.out/'context.private.d')
    extra_jobs.append(cc);required_replacements['context.o']=co;supporting_inputs.append(record(cs))
    for name,recovered in checks['providers'].items():
        source_text=Path(recovered['source']['path']).read_text(encoding='utf-8')
        need(source_text.count('qwen_app::maximum_model_CPU_heap_bytes')==2,'Exactly two bounds in each selected shader CPU guard required')
        source_text=source_text.replace('qwen_app::maximum_model_CPU_heap_bytes','(672ull<<20)')
        ss=a.out/(Path(recovered['source']['path']).name);ss.write_text(source_text,encoding='utf-8',newline='\n');so=a.out/name
        sc=recovered['command'].copy();sc[sc.index('-c')+1]=str(ss);sc[sc.index('-o')+1]=str(so)
        if '-MF'in sc:sc[sc.index('-MF')+1]=str(a.out/(name+'.private.d'))
        extra_jobs.append(sc);required_replacements[name]=so;supporting_inputs.append(record(ss))
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    provider=a.out/'persistent-mtp-shadow.o';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    tc=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(up/'include'),
        '-I',str(up/'src'),'-I',str(up/'ggml/include'),'-I',str(up/'vendor'),'-c',str(a.out/'persistent_mtp_shadow.cpp'),'-o',str(provider)]
    need('p.n_seq_max=1;p.n_rs_seq=0;' in (a.out/'persistent_mtp_shadow.cpp').read_text(encoding='utf-8'),
         'The actual auxiliary implementation must disable rollback snapshots')
    commands=[tc,gc,ec,*extra_jobs]
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    application=dict(profile,kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
        overrides=dict(profile['overrides'],native_next_five_normal=next_policy,native_headless_model_audit=scope),
        model_and_GPU_topology_unchanged=False,headless_model_audit=True,model_and_GPU_guards_preserved=True,
        CPU_heap_quota_explicitly_repriced=True,headless_audit_kind=scope['kind'],headless_requests=1,
        successful_MTP_contract_verified=True,
        actual_legacy_policy_validator_passed=True,legacy_policy_host_check=record(a.out/'legacy-policy-host-check/result.private.json'),
        successful_MTP_contract=dict(auxiliary_rollback_snapshots=0,target_rollback_snapshots=1,
            active_MTP_tensors=34,MTP_graph_capacity=1088,CPU_heap_quota_bytes=672<<20,
            CPU_heap_check_provider_count=3,source_before_changes_byte_exact=True,
            context_source=record(cs),replacements={name:record(path) for name,path in required_replacements.items()},
            selected_context_proof=record(a.context),selected_shader_checks_proof=record(a.shader_checks)),
        native_performance_qualified=False,production_adopted=False)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),reader=base['reader'],
        provider=record(provider),graph=record(go),graph_source=record(gs),source=record(source),
        inputs=[record(a.out/name) for name in names]+[record(CPU),*supporting_inputs],commands=commands,
        required_replacements={name:record(path) for name,path in required_replacements.items()},PS5_operations=0,
        native_memory_geometry_or_accuracy_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,simultaneous_auxiliary_contexts=1,PS5_operations=0)))


if __name__=='__main__':main()
