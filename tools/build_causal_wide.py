#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare causal fixed widths and adaptive depth in one matched resident cohort."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record
from build_speculative_speed import speed_loop,once,SCOPE as SPEED_SCOPE
from wide_verification_source import generate as wide_engine
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(SPEED_SCOPE,schema='ps5-qwen-causal-wide-speed-v1',maximum_requests=9,
    matched_arms_per_candidate=4,maximum_actual_attempts_per_request=8,
    fixed_control_maximum_actual_attempts=1,causal_span_tokens=3,adaptive_depth=True,active_cache_slots=53)


def loop_source():
    s=speed_loop().replace('routes.reserve(5)','routes.reserve(9)').replace('ordinal>=5','ordinal>=9')
    begin=s.index('            if(adaptive){')
    end=s.index('            if(reject||coverage)',begin)
    s=s[:begin]+'            if(adaptive)engine->enable_speculative_step_prototype(admit_checkpoint);\n'+s[end:]
    begin=s.index('            class CoverageControl final:')
    end=s.index('            qwen_app::FirstGeneration trial(adapter);',begin)
    s=s[:begin]+'''            const auto mode=kind=="fixed-two"?qwen_app::CausalWideMode::fixed_two:
                kind=="adaptive"?qwen_app::CausalWideMode::adaptive:qwen_app::CausalWideMode::fixed_four;
            qwen_app::CausalWideEngine adapter(*engine,context,mode,expected_ids,kind=="adaptive"?8:1);
'''+s[end:]
    s=s.replace('adaptive=(kind=="causal"||kind=="warmup")','adaptive=true')
    s=s.replace('captured.captures!=1','captured.captures!=engine->speculative_step_stats().attempts')
    s=s.replace('row["actual_single_attempt_policy"]=true;', 'row["actual_single_attempt_policy"]=kind!="adaptive";')
    s=s.replace('if(stats.attempts>1)throw', 'if(stats.attempts>(kind=="adaptive"?8u:1u))throw')
    marker='{"completed_performance",performance_difference(perf,*engine)},'
    s=once(s,marker,marker+'\n                {"controller_decisions",adapter.decisions()},{"controller_ns",adapter.decision_ns()},')
    begin=s.index('        run_arm(' ,s.index('            return stats.accepted;'))
    s=s[:begin]+'''        run_arm(7,"warmup",0);
        run_arm(7,"fixed-two",0);run_arm(7,"fixed-four",0);
        run_arm(7,"fixed-four",0);run_arm(7,"fixed-two",0);
        run_arm(7,"fixed-two",0);run_arm(7,"adaptive",0);
        run_arm(7,"adaptive",0);run_arm(7,"fixed-two",0);
        coverage_complete=coverage_complete&&completed.at(2).at("speculation").at("accepted").get<unsigned>()>0&&
            completed.at(3).at("speculation").at("accepted").get<unsigned>()>0;
'''
    return s


def entry_source(text):
    begin=text.index('        const auto run=policy.at("native_first_generation_validation")',text.index('int main('))
    end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    text='#include "causal_wide_engine.h"\n#include "resident_checkpoint_capacity.h"\n#include "six_bank_refill.h"\n'+text[:begin]+loop_source()+text[end:]
    text=text.replace('require_wide_verification_policy(policy);','require_causal_wide_policy(policy);')
    text=text.replace('{"width_four_native_qualification",true}',
        '{"width_four_native_qualification",false},{"active_cache_slots",53},{"six_demand_enabled",true},'
        '{"matched_ABBA_request_ordinals",Json::array({1,2,3,4})},{"adaptive_ABBA_request_ordinals",Json::array({5,6,7,8})},'
        '{"causal_policy_maximum_actual_attempts",8},{"fixed_policy_maximum_actual_attempts",1},{"causal_wide_comparison",true}')
    text=text.replace('{"all_three_rejection_positions_executed",true}','{"all_three_rejection_positions_executed",false}')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('parent','wide-native','behavior-result','application-recipe','wide-review','workspace','cache','out'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());wide=json.loads(a.wide_native.read_text())
    review=json.loads(a.wide_review.read_text());app=json.loads(a.application_recipe.read_text())
    if not review['passed']or not review['all_three_rejections_F32_exact']or not review['full_acceptance_executed']:
        raise ValueError('Closed complete width-four acceptance/rejection correctness is required')
    frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Actual causal speed dependency changed: '+r['path'])
    for key in('native_evidence','restoration_evidence'):
        if record(review[key]['path'])!=review[key]:raise ValueError('Completed width-four evidence changed')
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1])
    for path in template.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    source=a.out/'resident-causal-wide.private.cpp';source.write_text(entry_source(template.read_text()),newline='\n')
    workloads=copy.deepcopy(wide['wide_verification']['workloads'])
    behavior=json.loads(a.behavior_result.read_text())
    ordinary=next(r for r in behavior['requests']if r['group']==7 and r['arm']=='ordinary')
    if not ordinary['request_reset_completed']:raise ValueError('Closed original repeated-context reference required')
    workloads['requests'][7].update(expected_token_ids=ordinary['token_ids'],expected_output_bytes=ordinary['output_bytes'],expected_stop_reason=ordinary['stop_reason'])
    header=a.out/'speculative_behavior_policy.h';header.write_text('''#pragma once
#include "resident_comparison_policy.h"
inline void require_causal_wide_policy(const nlohmann::json&p){
 qwen_app::require_first_generation_policy(p,false);
 if(p.at("native_resident_comparison")!=nlohmann::json::parse(SCOPE)||
 p.at("native_speculative_workloads")!=nlohmann::json::parse(INPUTS)||
 p.at("native_prefill").at("tokens")!=4||p.at("native_padded_expert_cache").at("active_slots")!=53||p.contains("native_large_cache_scope")||
 p.contains("native_predictive_cache")||p.contains("native_model_free_speculation"))
 throw std::runtime_error("Exact causal-only fixed/adaptive width comparison required");
}
'''.replace('SCOPE',json.dumps(json.dumps(SCOPE,separators=(',',':')))).replace('INPUTS',json.dumps(json.dumps(workloads,separators=(',',':')))),newline='\n')
    names=('causal_wide_engine.h','adaptive_draft_depth.h','model_free_span.h','wide_draft_control.h')
    for name in names:(a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
    engine=a.out/'llama_engine.causal-wide.private.cpp';engine.write_text(wide_engine((ROOT/'native/app/llama_engine.cpp').read_text()),newline='\n')
    recipe=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    old_entry=command[command.index('-o')+1]
    prior_engine=prior['wide_verification']['commands'][0]
    old_engine=prior_engine[prior_engine.index('-o')+1]
    commands=[];objects=[]
    for c,src in((recipe,engine),(command,source)):
        c=c.copy();obj=a.out/(src.stem+'.o');c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        c[1:1]=['-I',str(a.out)];c+=['-I',str(template.parent),'-I',str(ROOT/'native/app')]
        commands.append(c);objects.append(obj)
    replacements={old_entry:str(objects[1]),old_engine:str(objects[0])}
    if any(prior['link_command'].count(k)!=1 for k in replacements):raise ValueError('Unique actual entry/engine replacements required')
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.wide_native,a.behavior_result,a.application_recipe,a.wide_review,Path(__file__),
        ROOT/'tools/wide_verification_source.py',ROOT/'tools/build_speculative_speed.py',ROOT/'native/app/llama_engine.cpp',
        template,source,engine,*a.out.glob('*.h'),*(ROOT/'native/app'/n for n in names))]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(causal_wide_build_step=i+1,total=3)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen causal width dependency changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects],
        causal_wide=dict(scope=SCOPE,workloads=workloads,commands=commands,actual_entry=record(source),actual_engine=record(engine),
            known_control_drafts=False,matched_fixed_widths=[2,4],adaptive_widths=[1,2,4],wide_correctness=record(a.wide_review)),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Causal width audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(causal_wide_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
