#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retest the previously F64-qualified two-token GDN kernel on the current model."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from qualify_post_top2_reporting import transform as reporting
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','fixture','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());f=json.loads(a.fixture.read_text());proof=json.loads(a.proof.read_text())
    require(proof['completed'] and proof['GPU_graphs']==216 and proof['F64_reference_all_outputs_passed'],'Existing complete F64 qualification required')
    require(n['lossless_shader_storage']['vulkan_object']['sha256']=='17cb982ec26903fcee469639592d5acd761acd6f883bc35135b9d665fc4b6ad2','Exact current GPU provider required')
    a.out.mkdir(parents=True,exist_ok=False);fc=f['GDN_conv_normalization_fixture'];headers=[]
    for row in f['four_next_fixture']['headers']:
        require(record(row['path'])==row,'Qualified fixture header changed');src=Path(row['path']);body=src.read_text()
        if 'backend'in src.name:body=once(body,'if(x->ne[0]==5&&!qwen_conv_norm_two_enabled.load','if(!planning&&x->ne[0]==5&&!qwen_conv_norm_two_enabled.load')
        target=a.out/src.name;target.write_text(body,newline='\n');headers.append(target)
    source=next(Path(x['path'])for x in fc['headers']if Path(x['path']).name=='qwen_conv_norm_spirv.private.h')
    target=a.out/source.name;target.write_bytes(source.read_bytes());headers.append(target)
    gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text()
    gpu=once(gpu,'#include "gdn_conv_norm_state.inc"','#include "gdn_conv_norm_two_state.private.inc"')
    gpu=once(gpu,'#include "gdn_conv_norm_planner_backend.private.inc"','#include "gdn_conv_norm_two_backend.private.inc"')
    model=n['GDN_model_graph_order'];oldmodel=Path(model['actual_model']['path']);body=once(oldmodel.read_text(),'if(n_seq_tokens==1&&n_seqs==1','if((n_seq_tokens==1||n_seq_tokens==2)&&n_seqs==1')
    newmodel=a.out/'qwen4exp.two-ordered.private.cpp';newmodel.write_text(body,newline='\n')
    unity=once(Path(model['actual_unity']['path']).read_text(),oldmodel.as_posix(),newmodel.as_posix())
    old=n['GDN_model_comparison']['scope'];scope=dict(old,schema='ps5-qwen-post-top2-two-token-v1',candidate='two-token-GDN-current-Top2',candidate_id=1,
        control_Experts=2,candidate_Experts=2,control_attempt_cap=6,candidate_attempt_cap=6,single_token_fusion_enabled_in_both_arms=True,
        potential_two_token_spans_preserved_while_disabled=True,prior_F64_graphs_reused=216)
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    entry='#include "post_top2_causal.h"\nextern "C" void qwen_app_conv_norm_two_select(bool);\nextern "C" std::uint64_t qwen_app_conv_norm_two_selections();\n'+entry
    entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_app_conv_norm_two_select(arm==1);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";','arm==0?"Top2-single-token-GDN":"Top2-two-token-GDN";')
    entry=once(entry,'qwen_app::NextFiveCausalEngine causal(*engine,model,context,ordinal>=10);','qwen_app::PostTop2CausalEngine causal(*engine,model,context,ordinal>=10,6);')
    entry=entry.replace('qwen_app::NextFiveCausalEngine&','qwen_app::PostTop2CausalEngine&')
    entry=once(entry,'const auto gdn_before=qwen_app_conv_norm_trial_selections();','const auto two_before=qwen_app_conv_norm_two_selections();const auto gdn_before=qwen_app_conv_norm_trial_selections();')
    entry=once(entry,'            row["phase"]=phase;','            row["two_token_pipeline_selections"]=qwen_app_conv_norm_two_selections()-two_before;\n            row["phase"]=phase;')
    entry=reporting(entry)
    variants=dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),gpu=(gc,gpu),model_graph=(model['command'],unity))
    r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),a.fixture,a.proof,newmodel,*headers,ROOT/'native/app/post_top2_causal.h',ROOT/'tools/qualify_post_top2_reporting.py'])
    update_sources(r,jobs,sources);r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
    r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['GDN_model_graph_order'].update(actual_model=record(newmodel),actual_unity=sources['model_graph'],object=record(jobs['model_graph'][jobs['model_graph'].index('-o')+1]),command=jobs['model_graph'])
    r['post_top2_two_token']=dict(scope=scope,actual_sources=sources,commands=jobs,qualification=record(a.proof),headers=[record(x)for x in headers])
    seed=a.out/'linked-seed.private.json';write_json(seed,r)
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
    r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='current_Top2_two_token_GDN',candidate=record(a.out/'receipt.private.json'),scope=scope,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
