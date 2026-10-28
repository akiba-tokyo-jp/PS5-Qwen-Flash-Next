#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare matched 128-slot causal speed work only after both correctness gates."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record
from build_speculative_behavior import LOOP

ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-resident-speculative-speed-v1',enabled=True,CPU_startup_calibration=False,
    CPU_preparation_uses_operational_floor=True,maximum_requests=5,warmup_requests=1,matched_arms_per_candidate=4,
    forced_rejection_requests=0,context_tokens=256,prefill_tokens=4,active_cache_slots=128,maximum_output_tokens=32,
    model_loads=1,GPU_start_reference_pages=3563,HTTP_requests=0,VideoOut_starts=0,legacy_transport_scope_overridden=True,
    all_original_precision_preserved=True,automatic_retries=0,performance_adoption_enabled=False,
    maximum_actual_attempts_per_request=1,six_demand_enabled=True,known_control_drafts_enabled=False,
    warmup_preallocates_real_completed_snapshot=True,prefix_reuse_enabled=False)

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('One exact speed source boundary required: '+old[:90])
    return text.replace(old,new,1)

def speed_loop():
    text=LOOP
    text=text.replace('routes.reserve(28)','routes.reserve(5)').replace('ordinal>=28','ordinal>=5')
    text=once(text,'        const auto run=policy.at("native_first_generation_validation")',
        '        qwen_app::configure_native_six_bank_refill(true);\n        const auto run=policy.at("native_first_generation_validation")')
    marker='        bool all_exact=true,forced_rejection_passed=true,coverage_complete=true;'
    text=once(text,marker,marker+'''
        qwen_app::ResidentCheckpointCapacity checkpoint_capacity;
        std::uint64_t last_requested_snapshot=0,last_new_snapshot=0;
''')
    text=once(text,'            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);',
        '            const auto rounded=checkpoint_capacity.new_allocation(context,bytes);\n            last_requested_snapshot=bytes;last_new_snapshot=rounded;')
    text=once(text,'const bool control=kind=="ordinary",adaptive=kind=="causal",reject=kind=="forced-rejection",coverage=kind=="accepted-coverage";',
        'const bool control=ordinal==0,adaptive=(kind=="causal"||kind=="warmup"),reject=false,coverage=false;')
    text=once(text,'struct Cost {qwen_app::OnlineExpertVerification planner;std::uint64_t source=0;};',
        'struct Cost {qwen_app::OnlineExpertVerification planner;std::uint64_t source=0;bool used=false;};')
    text=once(text,'hooks.choose=[state](int pending,int draft){return state->planner.choose(pending,draft);};',
        'hooks.choose=[state](int pending,int draft){return state->used?1:state->planner.choose(pending,draft);};')
    text=once(text,'hooks.verified=[state](bool accepted,double capture,double restore){state->planner.verified(accepted,capture,restore);};',
        'hooks.verified=[state](bool accepted,double capture,double restore){state->planner.verified(accepted,capture,restore);state->used=true;};')
    marker='            const auto stats=engine->speculative_step_stats();double maximum=0;'
    text=once(text,marker,'''            const auto captured=engine->checkpoint_validation_stats();
            if(captured.captures){
                if(captured.captures!=1||captured.maximum_payload_bytes!=last_requested_snapshot)
                    throw std::runtime_error("One actual positively completed snapshot required");
                checkpoint_capacity.completed(context,last_requested_snapshot,true);
            }
'''+marker)
    marker='            const auto perf=performance_snapshot(*engine);'
    text=once(text,marker,'''            qwen_six_bank_refill_stats delivery_before{};
            qwen_app_six_bank_refill_counters(&delivery_before);
'''+marker)
    marker='            const bool rejection_ok=!reject||'
    text=once(text,marker,'''            qwen_six_bank_refill_stats delivery_after{};
            qwen_app_six_bank_refill_counters(&delivery_after);
            if(delivery_after.batches<delivery_before.batches||delivery_after.reads<delivery_before.reads||
               delivery_after.logical_bytes<delivery_before.logical_bytes)
                throw std::runtime_error("Six-demand process-global counters regressed");
            const auto delivery_batches=delivery_after.batches-delivery_before.batches;
            const auto delivery_reads=delivery_after.reads-delivery_before.reads;
            const auto delivery_bytes=delivery_after.logical_bytes-delivery_before.logical_bytes;
            if(!qwen_app_six_bank_refill_enabled()||!delivery_batches||delivery_reads!=6*delivery_batches||!delivery_bytes)
                throw std::runtime_error("Actual complete six-demand ownership required in every timed arm");
            const bool matches_frozen_ordinary=result.token_ids==input.at("expected_token_ids").get<std::vector<std::int32_t>>()&&
                result.output_bytes==input.at("expected_output_bytes").get<std::vector<unsigned char>>()&&
                result.stop_reason==input.at("expected_stop_reason");
            exact=exact&&matches_frozen_ordinary;
'''+marker)
    text=text.replace('{"speed_measurement",false}','{"speed_measurement",ordinal!=0}')
    marker='            completed.push_back(row);write_fresh_report(prefix+".result",row);'
    text=once(text,marker,'''            if(ordinal==0&&stats.accepted!=1)coverage_complete=false;
            row["checkpoint_capacity"]={{"logical_payload_bytes",adaptive?last_requested_snapshot:0},
                {"new_allocation_bytes",adaptive?last_new_snapshot:0},{"same_original_context",true}};
            row["F32_reference_role"]="causal_warmup_diagnostic_only";
            row["matches_frozen_ordinary"]=matches_frozen_ordinary;
            row["six_demand"]={{"batches",delivery_batches},{"reads",delivery_reads},{"logical_bytes",delivery_bytes}};
            row["actual_single_attempt_policy"]=true;
            if(stats.attempts>1)throw std::runtime_error("Bounded causal speed policy exceeded one attempt");
'''+marker)
    begin=text.index('        for(unsigned group=0;group<8;++group){')
    text=text[:begin]+'''        run_arm(0,"warmup",0);
        run_arm(0,"ordinary",0);
        run_arm(0,"causal",0);
        run_arm(0,"causal",0);
        run_arm(0,"ordinary",0);
        coverage_complete=coverage_complete&&completed.at(2).at("speculation").at("accepted")==1&&completed.at(3).at("speculation").at("accepted")==1;
'''
    return text

def entry_source(base,reference):
    marker='        const auto *chat_template=llama_model_chat_template(model,nullptr);'
    head=base[:base.index(marker)]
    begin=head.index('        qwen_app::require_resident_additional_policy(policy,"prefix");')
    end=head.index('\n',head.index('Exact independently qualified prefix/delivery combination required',begin))
    head=head[:begin]+'        require_speculative_speed_policy(policy);'+head[end:]
    middle=reference[reference.index(marker):reference.index('        const auto run=policy.at("native_first_generation_validation")',reference.index(marker))]
    tail=reference[reference.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',reference.index(marker)):]
    tail=tail.replace('if(ledger.live||!forced_rejection_passed)','if(ledger.live)')
    tail=tail.replace('{"all_original_tokens_and_bytes_exact",true},{"forced_rejection_and_full_F32_restore_passed",true}',
        '{"all_original_tokens_and_bytes_exact",all_exact},{"causal_warmup_and_candidate_acceptance_passed",coverage_complete},'
        '{"timing_Expert_cache_start","empty"},{"causal_policy_maximum_actual_attempts",1},{"known_control_drafts_used",false},'
        '{"matched_ABBA_request_ordinals",Json::array({1,2,3,4})},{"active_cache_slots",128},{"six_demand_enabled",true}')
    return '#include "speculative_speed_policy.h"\n#include "speculative_batch_probe.h"\n'+head+middle+speed_loop()+tail

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('parent','reference','application-recipe','behavior-review','probe-review','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();behavior=json.loads(a.behavior_review.read_text());probe=json.loads(a.probe_review.read_text())
    if not behavior['summary']['passed']or not probe['summary']['passed']:raise ValueError('Both closed native correctness gates must pass first')
    for row in(behavior['native_evidence'],behavior['restore_evidence'],probe['native_evidence'],probe['restore_evidence']):
        if record(row['path'])!=row:raise ValueError('Required completed correctness evidence changed')
    native_behavior=json.loads(Path(behavior['native_evidence']['path']).read_text())
    if any(row['speculation']['attempts']>1 for row in native_behavior['requests']if row['arm']=='causal'):
        raise ValueError('The single-attempt policy needs focused changed-input qualification for any previously multi-attempt input')
    prior=json.loads(a.parent.read_text());reference=json.loads(a.reference.read_text());app=json.loads(a.application_recipe.read_text())
    frozen=list({row['path']:row for row in prior['inputs_before']+reference['inputs_before']+[prior['artifact'],reference['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Exact 128-slot or numerical-gate input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();base=Path(command[command.index('-c')+1])
    original_reference=Path(reference['compile_commands'][0][reference['compile_commands'][0].index('-c')+1])
    source=a.out/'resident-comparison-speculative-speed.private.cpp';source.write_text(entry_source(base.read_text(),original_reference.read_text()),newline='\n')
    for path in base.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    for name in('speculative_batch_probe.h','logit_difference.h'):(a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
    engine=a.out/'llama_engine.cache128.private.cpp';engine_text=(ROOT/'native/app/llama_engine.cpp').read_text()
    engine_text=once(engine_text,'if(selected_padded_cache_geometry().active_slots!=53)',
        'if(selected_padded_cache_geometry().active_slots!=53&&selected_padded_cache_geometry().active_slots!=128)')
    engine.write_text(engine_text,newline='\n')
    inputs=next(row for row in json.loads((a.cache/'bounded-workload-metadata-2543/manifest.private.json').read_text())['workloads']if row['name']=='counting')
    ordinary_path=a.cache/'hardware-first-generation-5720/native-arm0.result.private.json'
    ordinary=json.loads(ordinary_path.read_text())
    if not ordinary['request_reset_completed']or len(ordinary['token_ids'])!=22:
        raise ValueError('Original closed ordinary counting reference required')
    inputs=dict(requests=[dict(name='counting-speed',prompt=inputs['prompt'],rendered_prompt=inputs['rendered_prompt'],prompt_token_ids=inputs['prompt_token_ids'],
        expected_token_ids=ordinary['token_ids'],expected_output_bytes=ordinary['output_bytes'],expected_stop_reason=ordinary['stop_reason'])])
    header=a.out/'speculative_speed_policy.h'
    header.write_text('''#pragma once
#include "first_generation_policy.h"
inline void require_speculative_speed_policy(const nlohmann::json&p){
 qwen_app::require_first_generation_policy(p,false);
 if(p.at("native_resident_comparison")!=nlohmann::json::parse(SCOPE_LITERAL)||
 p.at("native_speculative_workloads")!=nlohmann::json::parse(INPUTS_LITERAL)||
 p.at("console_operations_enabled")!=true||p.at("console_validation_enabled")!=true||p.at("deployment_enabled")!=false||
 p.at("allowed_modes")!=nlohmann::json::array({"first-generation-validation"})||
 p.at("native_padded_expert_cache").at("active_slots")!=128||!p.contains("native_large_cache_scope")||
 p.contains("native_prefix_validation")||p.contains("native_model_free_speculation")||p.contains("native_speculative_same_batch_probe"))
 throw std::runtime_error("Exact previously qualified 128-slot causal speed scope required");
}
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(SCOPE,separators=(',',':')))).replace('INPUTS_LITERAL',json.dumps(json.dumps(inputs,separators=(',',':')))),newline='\n')
    engine_command=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    old_engine=next(x for x in prior['link_command']if Path(x).name.startswith('llama_engine-')and x.endswith('.o'))
    old_main=command[command.index('-o')+1];objects=[];commands=[]
    for i,(c,src)in enumerate(((engine_command,engine),(command,source))):
        obj=a.out/f'{i}.o';c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        c[1:1]=['-I',str(a.out)];c+=['-I',str(base.parent),'-I',str(ROOT/'native/app')];commands.append(c);objects.append(obj)
    helper=next(x for x in reference['link_command']if Path(x).name=='1.o'and 'speculative-same-batch-'in x)
    link=[str(objects[0])if x==old_engine else str(objects[1])if x==old_main else x for x in prior['link_command']]
    link.insert(link.index(str(objects[0])),helper);image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen+=[record(x)for x in(a.parent,a.reference,a.application_recipe,a.behavior_review,a.probe_review,ordinary_path,Path(__file__),
        ROOT/'tools/build_speculative_behavior.py',ROOT/'native/app/llama_engine.cpp',ROOT/'native/app/llama_engine.h',source,engine,base,original_reference,*a.out.glob('*.h'))]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(causal_speed_build_step=i+1,total=3)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen causal speed dependency changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,source_parent=record(a.parent),
        inputs_before=frozen+[record(x)for x in objects],speculative_speed_qualification=dict(scope=SCOPE,workloads=inputs,
            actual_entry=record(source),actual_engine=record(engine),commands=commands,prior_probe=record(a.probe_review),prior_behavior=record(a.behavior_review),
            original_engine_class_layout_unchanged=True,original_driver_and_ggml_objects_unchanged=True,
            real_snapshot_preallocated_by_completed_causal_warmup=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Causal speed native import/dispatch audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(causal_speed_host_build_completed=True,PS5_calls=0)),flush=True)

if __name__=='__main__':main()
