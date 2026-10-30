#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Declare shared-FFN lifetimes before MoE and bind graph reuse to its epoch."""
import argparse,copy,hashlib,json,os,shlex,subprocess
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def arguments(command):
    args=shlex.split(command,posix=False)if isinstance(command,str)else command.copy()
    return [x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in args]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['delivery_overlap']['positive_fence_before_graph_pointer_restore'],'Qualified guarded overlap provider required');a.out.mkdir(parents=True,exist_ok=False);(a.out/'aux-tmp').mkdir()
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';db=json.loads((a.cache/'build/llama-ps5/compile_commands.json').read_text());model=up/'src/models/qwen4exp.cpp'
    text=model.read_text();begin=text.index('ggml_tensor * llama_model_qwen4exp::graph::build_layer_ffn(');end=text.index('\n// PLE n-gram',begin);original=text[begin:end]
    shared_begin=original.index('        ggml_tensor * ffn_shexp =');shared_end=original.index('        cur = ggml_add(ctx0, moe_out, ffn_shexp);');shared=original[shared_begin:shared_end].replace('        ggml_tensor * ffn_shexp =','        ffn_shexp =',1)
    moe_begin=original.index('    ggml_tensor * moe_out =');moe_end=original.index('    // shared experts,',moe_begin);moe=original[moe_begin:moe_end]
    body='''ggml_tensor * llama_model_qwen4exp::graph::build_layer_ffn(ggml_tensor * cur, const int il) {
    GGML_ASSERT(model.layers[il].ffn_gate_inp != nullptr);
    ggml_tensor * ffn_shexp = nullptr;
    if (model.layers[il].ffn_up_shexp != nullptr) {
'''+shared+'''        qwen_app_overlap_graph_set(ffn_shexp, il);
    }
'''+moe+'''    qwen_app_overlap_graph_cleared();
    if(ffn_shexp){cur=ggml_add(ctx0,moe_out,ffn_shexp);cb(cur,"ffn_out",il);}else cur=moe_out;
    return cur;
}
'''
    model_text=text[:begin]+body+text[end:];model_text=once(model_text,'#include "models.h"','#include "models.h"\nextern "C" void qwen_app_overlap_graph_set(ggml_tensor*,int);\nextern "C" void qwen_app_overlap_graph_cleared();')
    model_source=a.out/'qwen4exp.ordered.private.cpp';model_source.write_text(model_text,newline='\n')
    model_recipes=[r for r in db if 'Unity'in Path(r['file']).parts and model.as_posix()in Path(r['file']).read_text()];require(len(model_recipes)==1,'One exact current model unity required');model_recipe=model_recipes[0];unity=a.out/'ordered-model-unity.cxx';unity.write_text(once(Path(model_recipe['file']).read_text(),model.as_posix(),model_source.as_posix()),newline='\n')
    context_recipes=[r for r in db if r['file'].endswith('llama-context.cpp')];require(len(context_recipes)==1,'One selected context compile required');context_recipe=context_recipes[0];context_original=Path(context_recipe['file']);context=context_original.read_text()
    context=once(context,'#include "llama-context.h"','#include "llama-context.h"\nextern "C" bool qwen_app_overlap_graph_can_reuse();')
    context=once(context,'if (!graph_reuse_disable && gf_res_prev_active == res && res->can_reuse(gparams))','if (!graph_reuse_disable && qwen_app_overlap_graph_can_reuse() && gf_res_prev_active == res && res->can_reuse(gparams))')
    context_source=a.out/'ordered-context.private.cpp';context_source.write_text(context,newline='\n')
    # Verify the actual archive member, rather than assuming a compile-database
    # recipe is the provider selected by the current application.
    archive=Path(next(x for x in prior['link_command']if x.endswith('libllama.a')));args=arguments(context_recipe['command']);original_object=Path(context_recipe['directory'])/args[args.index('-o')+1]
    ar=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-ar.exe';member=subprocess.check_output([str(ar),'p',str(archive),'llama-context.cpp.o']);require(hashlib.sha256(member).hexdigest()==record(original_object)['sha256'],'Selected context archive member differs from compiled control')
    runtime=ROOT/'native/app/delivery_overlap.cpp';runtime_command=prior['delivery_overlap']['runtime_command'].copy();old_runtime_object=prior['delivery_overlap']['runtime_object']['path'];objects={};commands={}
    items=[('model',model_recipe,unity),('context',context_recipe,context_source),('runtime',dict(command=runtime_command,directory=str(ROOT)),runtime)]
    for i,(label,recipe,source)in enumerate(items):
        cmd=arguments(recipe['command']);cmd[cmd.index('-c')+1]=str(source);obj=a.out/(label+'.o');cmd[cmd.index('-o')+1]=str(obj)
        cmd[1:1]=['-I',str(up/'src'),'-I',str(up/'src/models'),'-I',str(ROOT/'native/app')]
        if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
        run=subprocess.run(cmd,cwd=recipe['directory'],capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'aux-tmp'),TEMP=str(a.out/'aux-tmp')));(a.out/f'aux-{label}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:]);commands[label]=cmd;objects[label]=record(obj);print(json.dumps(dict(ordered_auxiliary_step=i+1,total=3)),flush=True)
    seed=copy.deepcopy(prior);at=seed['link_command'].index(old_runtime_object);seed['link_command'][at]=objects['runtime']['path'];at=seed['link_command'].index(str(archive));seed['link_command'][at:at]=[objects['model']['path'],objects['context']['path']]
    # The qualified parent captured runtime v1 at the public source path. Its
    # immutable archived copy preserves that evidence while this link selects
    # runtime v2. Do not claim two different digests for one current input.
    old_source=prior['delivery_overlap']['runtime_source'];archived=a.parent.parent/'qualified-runtime-source.private.cpp'
    require(record(archived)['sha256']==old_source['sha256'],'Exact qualified parent runtime archive required')
    seed['inputs_before']=[r for r in seed['inputs_before']if Path(r['path'])!=Path(old_source['path'])]
    seed['inputs_before'].append(record(archived))
    frozen=[Path(__file__),model,model_source,Path(model_recipe['file']),unity,context_original,context_source,runtime,ROOT/'native/app/delivery_overlap_plan.h',original_object,archive,*[Path(x['path'])for x in objects.values()]];seed['inputs_before'] +=[record(x)for x in frozen];seed_path=a.out/'ordered-seed.private.json';write_json(seed_path,seed)
    graph_command=prior['normal_performance']['commands']['graph'];graph=Path(graph_command[graph_command.index('-c')+1]).read_text();graph='#include "ggml.h"\nextern "C" ggml_tensor*qwen_app_overlap_graph_take(int);\n'+graph
    graph=once(graph,'    ggml_build_forward_expand(gf, slots);','    ggml_build_forward_expand(gf, slots);\n    if(auto*shared=qwen_app_overlap_graph_take(il))ggml_build_forward_expand(gf,shared);')
    entry_command=prior['compile_commands'][0];entry=Path(entry_command[entry_command.index('-c')+1]).read_text();scope=dict(prior['cold_request']['scope'],mode='independent_shared_overlap_ordered',allocation_order='shared_after_slot_lookup_before_MoE',mode_epoch_bound_graph_reuse=True,workspace_limit_unchanged=True)
    entry=once(entry,literal(prior['cold_request']['scope']),literal(scope));result,jobs,actual=link(seed_path,a.out,dict(entry=(entry_command,entry),graph=(graph_command,graph)),frozen)
    for key in ('normal_performance','output_Q8_normal'):result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs)
    result['routing_sharing']['actual_sources']['graph']=actual['graph'];result['all_Q2_optimized_monitor']['actual_entry']=actual['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=actual['entry']
    result['cold_request'].update(scope=scope,actual_sources=actual,commands=jobs,normal_validation_pending=True,production_adopted=False)
    result['delivery_overlap'].update(scope=scope,runtime_source=record(runtime),runtime_object=objects['runtime'],runtime_command=commands['runtime'],allocation_order_qualified=False)
    result['ordered_overlap']=dict(scope=scope,actual_sources=actual,commands=jobs,auxiliary_objects=objects,auxiliary_commands=commands,model_source=record(model_source),model_unity=record(unity),context_source=record(context_source),original_context_archive_member_verified=True,mode_change_forces_graph_rebuild=True,original_driver_and_physical_memory_limits=True,live_alias_and_dependency_refusal_retained=True)
    seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='ordered_shared_lifetimes_and_mode_epoch',original_driver_reserves_and_visibility_guards=True,allocation_changes_priced_by_original_workspace_and_device_caps=True,live_alias_and_dependency_refusal_retained=True,context_control_archive_member_verified=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print('Changed shared lifetime order and mode-bound graph reuse built; native eligibility and benefit remain unqualified.')

if __name__=='__main__':main()
