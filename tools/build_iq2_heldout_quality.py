#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the established three semantic tasks with an independently reset IQ2 model."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from audit_expert_all_q2_safety import body
from build_expert_quality_cohort import PROMPTS
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from iq2_up_model_scope import require_cache_layout
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]
CASES=['Japanese_instruction','arithmetic','extraction_JSON']


def derive(text,scope):
    changed=copy.deepcopy(scope)
    changed.update(original_cold_retained_exact_prefix_sequence=False,
        heldout_functional_quality=dict(schema='ps5-qwen-heldout-functional-v1',prompts=PROMPTS,cases=CASES,
            independent_context_per_prompt=True,maximum_output_tokens=32,requests=3,
            reused_established_quality_tasks=True,performance_measurement=False))
    literal=lambda obj:json.dumps(json.dumps(obj,separators=(',',':')))
    text=once(text,'Json::parse('+literal(scope)+')','Json::parse('+literal(changed)+')')
    text=once(text,'        const unsigned request_count=3;',
        '        const unsigned request_count=3;\n        const auto heldout_prompts=Json::parse('+json.dumps(json.dumps(PROMPTS))+');')
    text=once(text,'            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;',
        '            const bool second=false;')
    text=once(text,'            const bool reuse=ordinal>0;','            const bool reuse=false;')
    text=once(text,'            if(ordinal==1)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);',
        '            // Independent held-out prompts do not create a prefix handoff.')
    text=once(text,'qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32',
        'qwen_app::render_bounded_user_prompt(chat_template,heldout_prompts.at(ordinal).get<std::string>()),256,32')
    start=text.index('            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{')
    end=text.index('            qwen_app::CausalExpertSharingEngine causal',start)
    text=text[:start]+'''            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                qwen_load::CpuSpan measured(qwen_load::full_validation);
                if(!v||count!=columns||rows>=resident_reference_rows){geometry_error=true;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(v[i]))value_error=true;
                ++rows;if(!ordinal)++reference_rows;
            });
'''+text[end:]
    marker='            row["counting_quality_passed"]=counting_quality;'
    text=once(text,marker,marker+'row["counting_quality_applicable"]=false;row["heldout_quality_task"]=ordinal;row["heldout_prompt"]=heldout_prompts.at(ordinal);row["full_F32_logit_rows_checked_finite"]=rows;row["same_tokens_as_independent_applicable"]=false;')
    text=once(text,'{"full_F32_logit_rows_compared",ordinal?rows:0}','{"full_F32_logit_rows_compared",0}')
    text=once(text,'row["F32_comparison_scope"]=second?"Approximate cached routing and mixed width: complete finite vocabulary; differences disclosed":"Different retained-cache state: complete finite vocabulary and complete actual routes";',
        'row["F32_comparison_scope"]="Independent held-out prompts: all full-vocabulary rows finite";')
    text=once(text,'row["Expert_format"]="Gate_Up_Q2_K_Down_Q2_0_MSE";',
        'row["Expert_format"]='+json.dumps('normal P1' if scope['arm']=='control' else scope['kind'])+';')
    text=once(text,'{"timings_usable_for_performance",true}','{"timings_usable_for_performance",false}')
    return text,changed


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','model-build','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--arm',action='append',choices=('control','candidate'))
    a=p.parse_args();prior=load(a.model_build);need(prior['completed'],'The complete sealed model pair must already exist')
    a.out.mkdir(parents=True,exist_ok=False);commands=[];packages={};arms=a.arm or ['control','candidate']
    manifest=a.out/'production-manifest.private.json';shutil.copyfile(a.current/'deployment.private.json',manifest)
    need(len(arms)==len(set(arms)),'Each requested quality package is built once')
    def run(command,label):
        command=list(map(str,command));commands.append(command)
        child=subprocess.run(command,capture_output=True,timeout=600,cwd=ROOT,
            env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(child.stdout+child.stderr)
        need(child.returncode==0,'Quality package build stopped: '+label)
    for arm in arms:
        package_row=prior['packages'][arm];need(record(package_row['path'])==package_row,'The completed model package changed')
        parent=load(package_row['path']);effective=parent['effective_application_policy'];profile_row=effective['profile']
        need(record(profile_row['path'])==profile_row and effective['kind']=='headless-model-audit',
             'The exact compiled headless parent is required')
        profile=load(profile_row['path']);require_cache_layout(profile)
        need(profile['headless_audit_kind'] in ('Q2-IQ2-Up-model','Q2-IQ2-Gate-Up-model','Q3-IQ2-Down-model') and
             profile['performance_timings_usable'] and profile['overrides']['native_headless_model_audit']['arm']==arm and
             record(profile['source']['path'])==profile['source'],'Only the original completed IQ2 model pair may be derived')
        old_dir=Path(profile['source']['path']).parent;root=a.out/arm;root.mkdir()
        for path in old_dir.glob('*.h'):shutil.copyfile(path,root/path.name)
        original=Path(profile['source']['path']).read_text();text,scope=derive(original,profile['overrides']['native_headless_model_audit'])
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                     'model_file_identity','model_directory_identity','resident_reset_empty_context'):
            need(body(text,name)==body(original,name),'A model memory/identity/reset guard changed: '+name)
        source=root/'entry.private.cpp';source.write_text(text,newline='\n');obj=root/'entry.o'
        command=next(c.copy() for c in prior['commands'] if '-c' in c and c[c.index('-c')+1]==profile['source']['path'])
        flag='-ivfsoverlay';view=load(command[command.index(flag)+1])
        for row in view['roots']:
            local=root/Path(row['external-contents']).name
            if local.exists():row['external-contents']=local.resolve().as_posix()
        overlay=root/'selected-view.private.json';save(overlay,view)
        command=[str(root) if arg==str(old_dir) else arg for arg in command]
        command[command.index(flag)+1]=str(overlay);command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        if '-MF' in command:command[command.index('-MF')+1]=str(root/'entry.private.d')
        run(command,arm+'-entry')
        changed=copy.deepcopy(profile);changed.update(source=record(source),entry_artifact=record(obj),
            performance_timings_usable=False,heldout_quality_only=True,quality_parent_package=package_row,
            quality_production_manifest=record(manifest))
        changed['overrides']['native_headless_model_audit']=scope
        policy=root/'application-policy.private.json';save(policy,changed)
        need(record(parent['relink']['path'])==parent['relink'],'The complete parent link changed')
        linked=load(parent['relink']['path']);job=[sys.executable,'-B',ROOT/'tools/relink_retained_current.py',
            '--current',a.current,'--out',root/'link','--application-policy',policy]
        values=set(linked['replacements'].values())
        for name,path in linked['replacements'].items():
            job+=['--replace',Path(name).name+'='+str(obj if Path(name).name=='entry.o' else path)]
        for row in linked['new_inputs']:
            if row['path'] not in values:job+=['--add-object',row['path']]
        for flag in linked['link_command']:
            if flag.startswith('--wrap='):job+=['--link-flag='+flag]
        run(job,arm+'-link')
        identity=parent['required_bundle_identity_audit']['provider']
        run([sys.executable,'-B',ROOT/'tools/package_retained_current.py','--workspace',a.workspace,'--current',a.current,
            '--relink',root/'link/result.private.json','--out',root/'SELF','--formatter-from',
            a.current/'provenance/current-package.private.json','--identity-provider',identity['path']],arm+'-SELF')
        packages[arm]=record(root/'SELF/result.private.json')
    save(a.out/'result.private.json',dict(completed=True,model_build=record(a.model_build),packages=packages,commands=commands,
        prompts=PROMPTS,cases=CASES,reused_established_quality_tasks=True,independent_context_per_prompt=True,
        no_cross_prompt_logit_or_output_equality_claimed=True,original_memory_identity_reset_guards_preserved=True,
        performance_timings_usable=False,PS5_operations=0,native_quality_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,quality_packages=len(packages),new_tasks=0,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
