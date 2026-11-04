#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure only the differing prefill row, reusing the completed P1 continuation proof."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','refinement','measured-package','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();refined=load(a.refinement);package=load(a.measured_package);profile=load(package['effective_application_policy']['profile']['path'])
    need(refined['completed'] and len(refined['new_selector_controls'])==16 and profile['P1_arm']=='candidate' and
         profile['entry_artifact']==refined['entries']['candidate']['entry'] and record(profile['source']['path'])==profile['source'],
         'The exact completed cold-only P1 source and selector are required')
    a.out.mkdir(parents=True,exist_ok=False);old_dir=Path(profile['source']['path']).parent
    for header in old_dir.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    contract=ROOT/'native/app/first_generation.h';base_contract=contract.read_text(encoding='utf-8')
    short=base_contract[base_contract.index('class FirstGeneration {'):base_contract.rindex('\n};')+3]
    short=short.replace('FirstGenerationResult','KEEP_RESULT').replace('FirstGeneration','PrefillRowGeneration').replace('KEEP_RESULT','FirstGenerationResult')
    short=once(short,'request.max_output_tokens != first_output_tokens','request.max_output_tokens != 1')
    short=once(short,'i < first_output_tokens','i < 1')
    diagnostic=a.out/'prefill_row_generation.h'
    diagnostic.write_text('// SPDX-License-Identifier: MIT\n#pragma once\n#include "first_generation.h"\nnamespace qwen_app {\n'+short+'\n}\n',encoding='utf-8',newline='\n')
    scope=dict(schema='ps5-qwen-prefill-row-difference-v1',kind='P1-prefill-row-difference',requests=3,
        model_loads=1,HTTP_requests=0,VideoOut_starts=0,maximum_output_tokens_per_request=1,
        all_three_requests_ordinary=True,first_prefill_crop=True,later_prefill_crop=False,
        original_first_row_F32_comparator_used=True,reference_rows=1,vocabulary_columns=248320,
        decode_continuation_not_replayed=True,performance_timings_usable=False)
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(original,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact prefill row difference scope required");')
    text=once(text,'            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;',
        '            const bool second=false; // Three ordinary prefills; no exact-prefix replay in this diagnostic.')
    text=once(text,'            const bool reuse=ordinal>0;',
        '            const bool reuse=ordinal==1; // Only the second comparator needs its original prefix-capture shape.')
    text=once(text,'            if(ordinal==1)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);',
        '            // The diagnostic has no final exact-prefix consumer.')
    text=once(text,'qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32};',
        'qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,1};')
    text=once(text,'        std::vector<float> reference_logits(resident_reference_rows*columns);',
        '        std::vector<float> reference_logits(columns);')
    start=text.index('            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{')
    end=text.index('            qwen_app::CausalExpertSharingEngine causal',start)
    before=text[start:end];after=once(before,'rows>=resident_reference_rows','rows>=1')
    text=text[:start]+after+text[end:]
    text=once(text,'{"maximum_output_tokens",32}});','{"maximum_output_tokens",1}});')
    text='#include "prefill_row_generation.h"\n'+once(text,'qwen_app::FirstGeneration trial(','qwen_app::PrefillRowGeneration trial(')
    text=headless_entry(text,scope['kind'],3,'Json{{"completed",true},{"only_prefill_and_first_token",true},{"requests",completed}}')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
        need(body(original,name)==body(text,name),'An original physical, identity, context or SELF guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    command=refined['commands'][3].copy()
    need('-c' in command and command[command.index('-c')+1]==profile['source']['path'],'Exact compiled measured candidate command required')
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:
        candidate=a.out/Path(root['external-contents']).name
        if candidate.is_file():root['external-contents']=candidate.resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    command=[str(a.out) if value==str(old_dir) else value for value in command]
    command[command.index('-ivfsoverlay')+1]=str(view);command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(entry)
    if '-MF' in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
    done=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(done.stdout+done.stderr)
    need(done.returncode==0,done.stderr.decode(errors='replace')[-4000:])
    host=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin';test=a.out/'short-request-controls.exe'
    check=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),
        str(ROOT/'tests/prefill_row_generation_test.cpp'),'-o',str(test)]
    environment=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for label,job in [('compile-controls',check),('execute-controls',[str(test)])]:
        checked=subprocess.run(job,capture_output=True,env=environment,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(checked.stdout+checked.stderr)
        need(checked.returncode==0,(checked.stdout+checked.stderr).decode(errors='replace')[-3000:])
    application=copy.deepcopy(profile);application.update(kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),model_and_GPU_topology_unchanged=False,
        headless_model_audit=True,model_and_GPU_guards_preserved=True,headless_audit_kind=scope['kind'],headless_requests=3,
        original_P1_refinement=record(a.refinement),original_P1_measured_package=record(a.measured_package),
        native_performance_qualified=False,production_adopted=False)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),source=record(source),
        reader=profile['CPU_SELF_provider']['artifact'],provider=refined['selector'],
        required_replacements={'model_graph.o':refined['model_provider_reused']},
        required_link_flags=['--wrap='+n for n in ('llama_process','llama_sampler_apply','llama_sampler_sample')],
        existing_F32_comparator_body_unchanged_except_single_row_bound=True,earlier_selector_controls_replayed=0,
        diagnostic_request_contract=record(diagnostic),original_request_contract=record(contract),new_short_request_controls=8,
        commands=[command],PS5_operations=0,native_numeric_difference_qualified=False,production_adopted=False))
    print(dict(completed=True,prefills=3,output_tokens_per_request=1,decode_replays=0,PS5_operations=0))


if __name__=='__main__':main()
