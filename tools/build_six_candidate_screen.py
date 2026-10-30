#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one finite, single-load prefill/output/graph-reuse comparison."""
import argparse, copy, json, os, shlex, subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import require, record, write_json
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch

ROOT = Path(__file__).resolve().parents[1]
COUNTING = [0, 0, 1, 1, 0, 0, 2, 2, 0, 0, 3, 3, 0, 0, 4, 4, 0]
ORDER = COUNTING + list(range(5)) * 3
SCOPE = dict(schema='ps5-qwen-six-candidate-screen-v1', enabled=True,
    maximum_requests=len(ORDER), order=ORDER, counting_requests=len(COUNTING),
    quality_requests=15, quality_tasks=3, model_loads=1, context_tokens=256,
    maximum_output_tokens=32, prefill_widths=[16],
    modes=['control', 'prefill_Top8', 'prefill_Top6', 'late_output', 'graph_reuse'],
    selected_routing_policy=6, decode_Experts=6, active_cache_slots=867,
    cache_budget_bytes=1333739520, selected_IO_flags=5,
    approximate_routing_changes_permitted=True, quality_changes_recorded_without_aborting=True,
    HTTP_requests=0, VideoOut_starts=0, automatic_retries=0,
    original_physical_heap_ledger_owner_completion_guards=True)

def entry_source(text, old, model_scope, io_scope):
    text = '#include "six_candidate_policy.h"\n' + text
    for before, after in ((old['scope'], SCOPE), (old['model_scope'], model_scope)):
        text = once(text, json.dumps(json.dumps(before, separators=(',', ':'))),
                    json.dumps(json.dumps(after, separators=(',', ':'))))
    text = once(text, 'setenv("LLAMA_GRAPH_REUSE_DISABLE","1",1)',
                'setenv("LLAMA_GRAPH_REUSE_DISABLE","0",1)')
    text = once(text, 'request_count=31', 'request_count=' + str(len(ORDER)))
    text = once(text, 'counting_modes[]={0,0,1,2,3,4,5,5,4,3,2,1,0}',
                'counting_modes[]={' + ','.join(map(str, COUNTING)) + '}')
    text = once(text, 'quality_modes[]={0,1,2,3,4,5}', 'quality_modes[]={0,1,2,3,4}')
    text = once(text, 'ordinal<13;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-13)%6]',
                'ordinal<17;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-17)%5]')
    text = once(text, 'const unsigned task=counting?0:(ordinal-13)/6',
                'const unsigned task=counting?0:(ordinal-17)/5')
    text = once(text, 'qwen_app_lean_prefill_configure(mode);',
                'qwen_app_six_configure(mode);\n            qwen_app_lean_prefill_configure(mode==3?5:4);')
    text = once(text, 'qwen_app::lean_prefill_policy(mode).width', '16')
    text = once(text, 'const auto selected=qwen_app::lean_prefill_policy(mode);',
                'const auto selected=qwen_app::lean_prefill_policy(mode==3?5:4);')
    text = once(text, 'completed.push_back(row);write_fresh_report(prefix+".result",row);',
                'row["actual_graph_reuses"]=qwen_app_six_reuse_count();\n            completed.push_back(row);write_fresh_report(prefix+".result",row);')
    return once(text, '{"graph_reuse_disabled_uniformly",true}',
                '{"graph_reuse_disabled_uniformly",false},{"graph_reuse_scoped_by_phase_and_policy",true}')

def routing_source(text):
    return '#include "six_candidate_policy.h"\n' + text + '''
namespace {
unsigned six_mode=0;const void*six_last_result=nullptr;
unsigned six_last_key=0;unsigned long long six_reuses=0;
unsigned six_key(){return (six_mode<<1)|unsigned(qwen_app_route_is_decode());}
}
extern "C" void qwen_app_six_configure(unsigned m){
    (void)qwen_app::six_candidate_policy(m);six_mode=m;
    six_last_result=nullptr;six_last_key=0;six_reuses=0;
}
extern "C" unsigned qwen_app_six_prefill_experts(){return qwen_app::six_candidate_policy(six_mode).prefill_experts;}
extern "C" bool qwen_app_six_late_output(){return qwen_app::six_candidate_policy(six_mode).late_output&&!qwen_app_route_is_decode();}
extern "C" bool qwen_app_six_can_reuse(const void*p){
    return qwen_app::six_candidate_policy(six_mode).graph_reuse&&six_last_result==p&&six_last_key==six_key();
}
extern "C" void qwen_app_six_note_inputs(const void*p){six_last_result=p;six_last_key=six_key();}
extern "C" void qwen_app_six_reused(){++six_reuses;}
extern "C" unsigned long long qwen_app_six_reuse_count(){return six_reuses;}
'''

def graph_source(text):
    text = '#include "six_candidate_policy.h"\n' + text
    text = once(text, '    const bool weight_before_ffn = arch == LLM_ARCH_LLAMA4;',
        '    if(n_expert==512&&n_expert_used==10&&!qwen_app_route_is_decode())\n'
        '        n_expert_used=qwen_app_six_prefill_experts();\n'
        '    const bool weight_before_ffn = arch == LLM_ARCH_LLAMA4;')
    text = once(text, 'void llm_graph_result::set_inputs(const llama_ubatch * ubatch) {',
        'void llm_graph_result::set_inputs(const llama_ubatch * ubatch) {\n    qwen_app_six_note_inputs(this);')
    text = once(text, 'bool llm_graph_result::can_reuse(const llm_graph_params & params) {',
        'bool llm_graph_result::can_reuse(const llm_graph_params & params) {\n'
        '    if(!qwen_app_six_can_reuse(this))return false;')
    start=text.index('bool llm_graph_result::can_reuse(')
    at=text.index('    return res;', start)
    return text[:at]+'    if(res)qwen_app_six_reused();\n'+text[at:]

def model_source(text):
    text = '#include "six_candidate_policy.h"\n' + text
    text = once(text, 'il == n_layer - 1 && crop_before_nextn(inp_out_ids)',
                'il == n_layer - 1 && crop_before_nextn(inp_out_ids) && !qwen_app_six_late_output()')
    return once(text, 'if (crop_after_nextn(inp_out_ids)) {',
                'if (crop_after_nextn(inp_out_ids) || qwen_app_six_late_output()) {')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());old=prior['routing_sharing']
    require(prior['lean_prefill']['scope']['maximum_requests']==31,'Completed headless width16 parent required')
    frozen=active_link_inputs(prior)+[r for r in prior['inputs_before'] if Path(r['path']).suffix=='.so']
    frozen += [record(a.parent),record(__file__),record(ROOT/'native/app/six_candidate_policy.h')]
    for row in frozen:require(record(row['path'])==row,'Qualified input changed')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    model_scope=dict(old['model_scope'],schema='ps5-qwen-six-screen-model-v1',maximum_requests=len(ORDER),
                     timed_requests=len(COUNTING)-1,selected_Experts='8_or_6_or_10_prefill_6_decode')
    # The completed parent retains its original source-observer scope. Its
    # per-request source counters do not control the finite cohort length.
    io_scope=copy.deepcopy(old['IO_scope'])
    sources=old['actual_sources'];commands=dict(zip(('entry','cache','engine','capture','routing','graph'),old['commands']))
    variants={'entry':entry_source(Path(sources['entry']['path']).read_text(),old,model_scope,io_scope),
              'routing':routing_source(Path(sources['routing']['path']).read_text()),
              'graph':graph_source(Path(sources['graph']['path']).read_text())}
    compilation=json.loads((a.cache/'build/llama-ps5/compile_commands.json').read_text())
    upstream=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    unity=next(r for r in compilation if Path(r['file']).name=='unity_8_cxx.cxx')
    unity_path=Path(unity['file']);unity_text=unity_path.read_text();frozen.append(record(unity_path))
    # The actual Flash-Next GGUF architecture is qwen4exp. Preserve the other
    # models in the original unity unit; do not benchmark an inactive override.
    for name in ('qwen4exp',):
        path=upstream/('src/models/'+name+'.cpp');source=a.out/(name+'.private.cpp')
        source.write_text(model_source(path.read_text()),newline='\n');frozen.append(record(path))
        unity_text=once(unity_text,path.as_posix(),source.as_posix())
    commands['unity_models']=[x[1:-1] if x.startswith('"')and x.endswith('"')else x
                              for x in shlex.split(unity['command'],posix=False)]
    variants['unity_models']=unity_text
    replacements={};jobs={};actual=dict(sources);added=[]
    for key,text in variants.items():
        source=a.out/(key+'.private.cpp');source.write_text(text,newline='\n');obj=a.out/(key+'.o');cmd=commands[key].copy()
        oldobj=cmd[cmd.index('-o')+1];oldsrc=Path(cmd[cmd.index('-c')+1]);cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
        # Preserve the qualified allocator/OS pricing header search order.
        # The old translation-unit directory supplied quoted private headers.
        cmd[1:1]=['-I',str(oldsrc.parent),'-I',str(a.out)]
        cmd += ['-I',str(ROOT/'native/app'),'-I',str(upstream/'src'),'-I',str(upstream/'src/models')]
        if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(key+'.private.d'))
        if key in sources:
            require(prior['link_command'].count(oldobj)==1,'One selected provider required');replacements[oldobj]=str(obj)
        jobs[key]=cmd;actual[key]=record(source);added.append(record(source))
    image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']]
    # Explicit model providers precede libllama; its untouched archive members remain controls.
    where=next(i for i,x in enumerate(link)if x.endswith('libllama.a'))
    link[where:where]=[str(a.out/'unity_models.o')]
    link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    for i,cmd in enumerate([*jobs.values(),link]):
        run=subprocess.run(cmd,capture_output=True,timeout=600,cwd=a.cache/'build/llama-ps5',env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(six_screen_build_step=i+1,total=len(jobs)+1)),flush=True)
    for row in frozen:require(record(row['path'])==row,'Frozen input changed during build')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[jobs['entry']],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/(key+'.o'))for key in jobs],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['expert_q2_model'].update(scope=model_scope,actual_entry=actual['entry'])
    receipt['all_Q2_IO_measurement'].update(scope=io_scope,entry=actual['entry'])
    receipt['all_Q2_bundle_comparison']=dict(scope=SCOPE)
    receipt['routing_sharing'].update(scope=SCOPE,model_scope=model_scope,IO_scope=io_scope,actual_sources=actual,
        commands=[jobs.get(k,commands[k])for k in ('entry','cache','engine','capture','routing','graph')])
    receipt['six_candidate_screen']=dict(scope=SCOPE,actual_sources={k:actual[k]for k in variants},
        model_commands=[jobs['unity_models']],model_sources=[record(a.out/'qwen4exp.private.cpp')],
        PS5_operations=0,production_adopted=False)
    target=a.out/'receipt.private.json';write_json(target,receipt)
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native imports/dispatch required')
    write_json(target,receipt);print('Finite four-candidate screen built; no console operations.',flush=True)

if __name__=='__main__':main()
