#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Make independent one-token Q/K normalizations adjacent before head repeats."""
import argparse,copy,json,re,shlex
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 recipes=json.loads(Path(n['bounded_model_source_overrides']['original_compile_recipes']['path']).read_text())
 matches=[r for r in recipes if'Unity'in r['file']and'qwen4exp.cpp'in Path(r['file']).read_text()]
 require(len(matches)==1,'One complete upstream model unity provider required');recipe=matches[0];unity=Path(recipe['file']);body=unity.read_text()
 files=[Path(v)for v in re.findall(r'^#include "([^"]+)"',body,re.M)];model=next(v for v in files if v.name=='qwen4exp.cpp');text=model.read_text()
 needle='    k_conv = build_gdn_l2_norm(ctx0, k_conv, eps_norm);'
 patch='''
    // Schedule the two independent normalizations before either head repeat.
    // The scheduler then prices their real lifetimes before buffer allocation.
    // No operation, source, precision, recurrence or multi-token order changes.
    if(n_seq_tokens==1&&n_seqs==1&&head_k_dim==128&&num_k_heads==16&&num_v_heads==48&&conv_kernel_size==4){
        ggml_build_forward_expand(gf,q_conv);
        ggml_build_forward_expand(gf,k_conv);
    }
'''
 changed=once(text,needle,needle+'\n'+patch);generated=a.out/'qwen4exp.ordered.private.cpp';generated.write_text(changed,newline='\n')
 unitytext=once(body,model.as_posix(),generated.as_posix())
 command=shlex.split(recipe['command'],posix=False);command=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in command]
 original_object=Path(recipe['output']);require(original_object.is_file(),'Exact compiled original unity object required')
 command[command.index('-o')+1]=str(original_object)
 command+=['-I',str(model.parent)]
 seed=copy.deepcopy(n);archives=[v for v in seed['link_command']if Path(v).name=='libllama.a'];require(len(archives)==1,'One unchanged original model archive required')
 require(str(original_object)not in seed['link_command'],'Model unity override must be new')
 seed['link_command'].insert(seed['link_command'].index(archives[0]),str(original_object));seed['inputs_before'] +=[record(original_object),record(unity),*[record(v)for v in files]]
 path=a.out/'seed.private.json';write_json(path,seed)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,independent_single_token_QK_normalizations_scheduled_before_head_repeats=True,
  original_GPU_program_and_F64_qualified_dispatch_unchanged=True,original_model_archive_unchanged=True,model_graph_order_identical_in_ABBA_arms=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope))
 r,jobs,sources=link(path,a.out,dict(model_graph=(command,unitytext),entry=(ec,entry)),[Path(__file__),generated,unity,*files,model.parent/'models.h'])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['GDN_model_comparison']['scope']=scope;r['GDN_model_comparison']['actual_sources']['entry']=sources['entry'];r['GDN_model_comparison']['commands']['entry']=jobs['entry']
 r['GDN_model_graph_order']=dict(scope=scope,original_model=record(model),actual_model=record(generated),original_unity=record(unity),actual_unity=sources['model_graph'],object=record(jobs['model_graph'][jobs['model_graph'].index('-o')+1]),command=jobs['model_graph'],unchanged_original_archive=record(archives[0]),explicit_provider_before_archive=True)
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='independent_QK_model_graph_order_comparison',requests=14,
  original_model_payloads_and_GPU_shader_unchanged=True,buffer_scheduler_observes_real_lifetimes=True,original_driver_physical_OS_minimum_and_completion_preserved=True,
  candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
