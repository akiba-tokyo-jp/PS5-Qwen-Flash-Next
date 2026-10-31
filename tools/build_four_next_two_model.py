#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare causal two-token fusion while retaining one-token fusion in all arms."""
import argparse,copy,json
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','fixture','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());f=json.loads(a.fixture.read_text());proof=json.loads(a.proof.read_text());require(proof['completed']and proof['GPU_graphs']==216 and proof['F64_reference_all_outputs_passed'],'Complete216-graph F64 proof required');a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(n);before=seed['lossless_shader_storage']['vulkan_object'];after=f['lossless_shader_storage']['vulkan_object'];seed['link_command'][seed['link_command'].index(before['path'])]=after['path']
 for k in ('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[k]=f[k]
 seed['inputs_before']+=active_link_inputs(f)+[record(a.fixture),record(a.proof)];seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
 fc=f['GDN_conv_normalization_fixture'];gc=fc['commands']['gpu'];gpu=Path(fc['actual_sources']['gpu']['path']).read_text()
 backend=Path(next(x['path']for x in f['four_next_fixture']['headers']if Path(x['path']).name=='gdn_conv_norm_two_backend.private.inc'))
 text=once(backend.read_text(),'if(x->ne[0]==5&&!qwen_conv_norm_two_enabled.load','if(!planning&&x->ne[0]==5&&!qwen_conv_norm_two_enabled.load')
 generated=a.out/backend.name;generated.write_text(text,newline='\n')
 state=Path(next(x['path']for x in f['four_next_fixture']['headers']if Path(x['path']).name=='gdn_conv_norm_two_state.private.inc'));(a.out/state.name).write_bytes(state.read_bytes())
 spirv=Path(next(x['path']for x in fc['headers']if Path(x['path']).name=='qwen_conv_norm_spirv.private.h'));(a.out/spirv.name).write_bytes(spirv.read_bytes())
 model=n['GDN_model_graph_order'];oldmodel=Path(model['actual_model']['path']);body=once(oldmodel.read_text(),'if(n_seq_tokens==1&&n_seqs==1','if((n_seq_tokens==1||n_seq_tokens==2)&&n_seqs==1');newmodel=a.out/'qwen4exp.two-ordered.private.cpp';newmodel.write_text(body,newline='\n');unity=Path(model['actual_unity']['path']).read_text();unity=once(unity,oldmodel.as_posix(),newmodel.as_posix())
 old=n['GDN_model_comparison']['scope'];scope=dict(old,schema='ps5-qwen-two-token-fusion-model-v1',single_token_fusion_enabled_in_both_arms=True,two_token_candidate=True,causal_draft_limit=6,quality_forced_rejection=True,potential_two_token_spans_preserved_while_disabled=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "causal_rollback_engine.h"\nextern "C" void qwen_app_conv_norm_two_select(bool);\nextern "C" std::uint64_t qwen_app_conv_norm_two_selections();\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_app_conv_norm_trial_select(arm==1);','qwen_app_conv_norm_trial_select(true);qwen_app_conv_norm_two_select(arm==1);')
 entry=once(entry,'if(reuse)engine->enable_prefix_reuse(admit_checkpoint);','engine->enable_speculative_step_prototype(admit_checkpoint);');entry=entry.replace('qwen_app::CausalExpertSharingEngine','qwen_app::CausalRollbackEngine');entry=once(entry,'causal(*engine,model,context,second&&qwen_app::routing_policy(selected_policy).sharing)','causal(*engine,model,context,ordinal>=10)')
 entry=once(entry,'const auto gdn_before=qwen_app_conv_norm_trial_selections();','const auto gdn_before=qwen_app_conv_norm_trial_selections();const auto two_before=qwen_app_conv_norm_two_selections();')
 entry=once(entry,'            row["phase"]=phase;','            row["two_token_pipeline_selections"]=qwen_app_conv_norm_two_selections()-two_before;\n            row["phase"]=phase;')
 ec=ec.copy()+['-I',str(ROOT/'native/app')]
 r,jobs,sources=link(seedpath,a.out,dict(entry=(ec,entry),gpu=(gc,gpu),model_graph=(model['command'],unity)),[Path(__file__),a.fixture,a.proof,generated,state,spirv,newmodel,ROOT/'native/app/causal_rollback_engine.h'])
 for k in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[k]['actual_sources']['entry']=sources['entry'];r[k]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['GDN_model_comparison']['scope']=scope;r['GDN_model_comparison']['actual_sources'].update(sources);r['GDN_model_comparison']['commands'].update(jobs);r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
 r['GDN_model_graph_order'].update(actual_model=record(newmodel),actual_unity=sources['model_graph'],object=record(jobs['model_graph'][jobs['model_graph'].index('-o')+1]),command=jobs['model_graph'])
 r['four_next_two_model']=dict(scope=scope,actual_sources=sources,commands=jobs,proof=record(a.proof),headers=[record(x)for x in [generated,a.out/state.name,a.out/spirv.name]],model_comparison_pending=True)
 unsealed=a.out/'unsealed.private.json';write_json(unsealed,r)
 import subprocess,sys
 v=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600);(a.out/'provenance.private.log').write_bytes(v.stdout+v.stderr);require(v.returncode==0,v.stderr.decode(errors='replace')[-2500:]);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='two_token_causal_fusion_model',candidate=record(a.out/'receipt.private.json'),original_physical_OS_memory_workspace_and_completion=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
