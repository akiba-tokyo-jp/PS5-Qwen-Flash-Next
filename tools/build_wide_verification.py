#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a default-off full width-four acceptance/rejection qualification."""
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
from build_speculative_behavior import generate as behavior_entry, SCOPE as BEHAVIOR_SCOPE
from build_speculative_batch_probe import once
from wide_verification_source import generate as wide_engine

ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(BEHAVIOR_SCOPE,maximum_requests=5,forced_rejection_requests=3)


def entry_source(text):
    text=behavior_entry(text)
    text='#include "wide_draft_control.h"\n'+text
    text=text.replace('require_speculative_behavior_policy(policy);','require_wide_verification_policy(policy);')
    text=once(text,'unsigned forced_position){','unsigned forced_position,unsigned mismatch=3){')
    text=once(text,'            const auto draft=coverage?correct:(correct==0?1:0);','''            std::array<std::int32_t,3> wide{};
            if(!control) {
                if(reference_ids.size()<forced_position+4)throw std::runtime_error("Four complete original target tokens required");
                for(unsigned i=0;i<3;++i)wide[i]=reference_ids.at(forced_position+i);
                if(reject){if(mismatch>2)throw std::runtime_error("A specific rejected suffix is required");wide[mismatch]=wide[mismatch]==0?1:0;}
            }
            (void)correct;
''')
    text=once(text,'unsigned position,calls=0;int draft;', 'unsigned position,calls=0;std::array<std::int32_t,3> drafts;')
    text=once(text,'unsigned p,int d):e(v),context(c),force(f),position(p),draft(d){}',
        'unsigned p,std::array<std::int32_t,3> d):e(v),context(c),force(f),position(p),drafts(d){}')
    text=once(text,'qwen_app::Token next()override{return force&&calls++==position?e.next_with_one_draft(draft):e.next();}',
        '''qwen_app::Token next()override{
                    if(force&&calls++==position){qwen_app::wide_draft_control.arm(&e,drafts);return e.next_with_one_draft(drafts[0]);}
                    return e.next();
                }''')
    text=once(text,'}adapter(*engine,context,force_possible,forced_position,draft);',
        '}adapter(*engine,context,force_possible,forced_position,wide);')
    text=text.replace('stats.queued_bonus_samples==1&&exact','stats.queued_bonus_samples==3&&exact')
    text=once(text,'{"forced_rejection_F32_restore_passed",rejection_ok}',
        '{"verified_width",control?1:4},{"accepted_draft_prefix",control?Json(nullptr):Json(qwen_app::wide_draft_control.last_prefix())},{"forced_rejection_F32_restore_passed",rejection_ok}')
    begin=text.index('        for(unsigned group=0;group<8;++group){')
    end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    text=text[:begin]+'''        run_arm(0,"ordinary",0);
        run_arm(0,"accepted-coverage",4);
        for(unsigned rejected=0;rejected<3;++rejected)run_arm(0,"forced-rejection",4,rejected);
        coverage_complete=coverage_complete&&accepted_total==1&&rejected_total==3;
'''+text[end:]
    text=text.replace('{"all_eight_native_inputs_executed",true}',
        '{"all_three_rejection_positions_executed",true},{"width_four_native_qualification",true}')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('parent','workloads','application-recipe','workspace','cache','out'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());app=json.loads(a.application_recipe.read_text())
    workloads=json.loads(a.workloads.read_text())
    if len(workloads['requests'])!=8 or not workloads['ordinary_metadata_control_token_ids_match']:
        raise ValueError('The original frozen eight-input tokenizer manifest is required')
    frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('An actual frozen parent dependency changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    entry_command=prior['compile_commands'][0].copy();template=Path(entry_command[entry_command.index('-c')+1])
    for path in template.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    source=a.out/'resident-wide-verification.private.cpp';source.write_text(entry_source(template.read_text()),newline='\n')
    header=a.out/'speculative_behavior_policy.h'
    header.write_text('''#pragma once
#include "resident_comparison_policy.h"
inline void require_wide_verification_policy(const nlohmann::json&p){
 qwen_app::require_first_generation_policy(p,false);
 if(p.at("native_resident_comparison")!=nlohmann::json::parse(SCOPE)||
 p.at("native_speculative_workloads")!=nlohmann::json::parse(INPUTS)||
 p.at("native_wide_verification")!=nlohmann::json({{"width",4},{"known_control_drafts",true},{"speed_adoption",false}})||
 p.at("native_prefill").at("tokens")!=4||p.at("native_padded_expert_cache").at("active_slots")!=53||
 p.contains("native_large_cache_scope")||p.contains("native_prefix_validation")||p.contains("native_predictive_cache")||
 p.contains("native_model_free_speculation")||p.contains("native_speculative_same_batch_probe"))
 throw std::runtime_error("Exact five-request wide verification scope required");
}
'''.replace('SCOPE',json.dumps(json.dumps(SCOPE,separators=(',',':'))))
    .replace('INPUTS',json.dumps(json.dumps(dict(requests=workloads['requests']),separators=(',',':')))),newline='\n')
    new_inputs=[ROOT/'native/app/wide_draft_control.h',ROOT/'tools/wide_verification_source.py',
        ROOT/'tools/build_speculative_behavior.py',ROOT/'native/app/llama_engine.cpp',ROOT/'native/app/llama_engine.h']
    (a.out/'wide_draft_control.h').write_bytes(new_inputs[0].read_bytes())
    engine=a.out/'llama_engine.wide.private.cpp';engine.write_text(wide_engine(new_inputs[3].read_text()),newline='\n')
    recipe=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    old_entry=entry_command[entry_command.index('-o')+1]
    prior_engine=prior['speculative_same_batch_qualification']['commands'][0]
    old_engine=prior_engine[prior_engine.index('-o')+1]
    if prior['link_command'].count(old_engine)!=1:raise ValueError('One actual parent engine object required')
    commands=[];objects=[]
    for c,src in((recipe,engine),(entry_command,source)):
        c=c.copy();obj=a.out/(src.stem+'.o');c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        c[1:1]=['-I',str(a.out)];c+=['-I',str(template.parent),'-I',str(ROOT/'native/app')]
        commands.append(c);objects.append(obj)
    replacements={old_entry:str(objects[1]),old_engine:str(objects[0])}
    # The parent probe object is unused; it is retained unchanged in the link.
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf'
    link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.workloads,a.application_recipe,Path(__file__),template,source,engine,*new_inputs,*a.out.glob('*.h'))]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(wide_build_step=i+1,total=3)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('A frozen wide verification input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects],
        wide_verification=dict(scope=SCOPE,workloads=dict(requests=workloads['requests']),actual_entry=record(source),
            actual_engine=record(engine),commands=commands,policy=record(header),known_control_coverage_only=True,
            rejected_partial_prefix_restores_full_state=True,engine_class_layout_unchanged=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Wide import/dispatch audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(wide_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
