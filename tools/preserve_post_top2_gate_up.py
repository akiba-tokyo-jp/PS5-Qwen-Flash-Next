#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Protect the qualified Top2 fusion span through both Vulkan reorder passes."""
import argparse,json,re,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_post_top2_submission import gpu_source
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text()
 dep=re.search(r'#include "([^"\n]*expert_gate_up_backend.inc)"',gpu);require(dep is not None,'Exact qualified Gate/Up provider include required');old_backend=Path(dep[1]);body=old_backend.read_text()
 body=once(body,'static bool qwen_gate_up_match(','static bool qwen_gate_up_shape(')
 body=once(body,'if(!qwen_gate_up_enabled.load()||first+2>=g->n_nodes)','if(first+2>=g->n_nodes)')
 body=once(body,'static void qwen_gate_up_dispatch(','''static bool qwen_gate_up_match(const ggml_cgraph*g,int first){return qwen_gate_up_enabled.load()&&qwen_gate_up_shape(g,first);}
static void qwen_gate_up_dispatch(''')
 backend=a.out/'expert_gate_up_backend.inc';backend.write_text(body,newline='\n');gpu=once(gpu,dep[0],'#include '+json.dumps(backend.resolve().as_posix()))
 gpu='#include <cstdint>\nnamespace {std::uint64_t post_gate_planner[2]{};}\nextern "C" void qwen_post_gate_plan_stats(std::uint64_t*out){std::copy_n(post_gate_planner,2,out);}\n'+gpu
 # Keep potential spans while the control is active as well, because graph
 # reuse would otherwise retain a reordered graph for the candidate arm.
 gpu=once(gpu,'    const auto qwen_protected=qwen_conv_norm_protected_ranges(ctx,graph);',
  '    auto qwen_protected=qwen_conv_norm_protected_ranges(ctx,graph);\n    for(int start=0;start+2<graph->n_nodes;++start)if(qwen_gate_up_shape(graph,start)){++post_gate_planner[0];for(int j=0;j<3;++j)qwen_protected[start+j]=true;}')
 marker='        if(qwen_conv_norm_preserve_plan(ctx,graph,params,new_order,used,used_node_set,first_unused))continue;'
 gpu=once(gpu,marker,'''        if(qwen_gate_up_shape(graph,first_unused)&&!used[first_unused]&&!used[first_unused+1]&&!used[first_unused+2]){
            add_pattern_alloc_deps({GGML_OP_MUL_MAT_ID,GGML_OP_MUL_MAT_ID,GGML_OP_GLU},first_unused+2);
            if(keep_pattern({GGML_OP_MUL_MAT_ID,GGML_OP_MUL_MAT_ID,GGML_OP_GLU})){++post_gate_planner[1];continue;}
        }
'''+marker)
 gpu=gpu_source(gpu,40,256,256)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='protected_two_Expert_Gate_Up',metadata_only_diagnostic=False,
  protect_complete_spans_in_both_reorder_passes=True,preserve_spans_in_control_for_graph_reuse=True,external_input_allocation_dependencies_preserved=True,
  common_submission_node_cap=256,actual_candidate_dispatch_required=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_post_gate_plan_stats(std::uint64_t*);\n'+entry;entry=once(entry,literal(old),literal(scope))
 marker='            row["Gate_Up_pipeline_selections"]=qwen_app_gate_up_trial_selections()-gate_up_before;'
 entry=once(entry,marker,marker+'''std::uint64_t planned[2]{};qwen_post_gate_plan_stats(planned);row["Gate_Up_planner_candidates_and_kept"]=std::vector<std::uint64_t>(planned,planned+2);
            if((arm==0&&qwen_app_gate_up_trial_selections()!=gate_up_before)||(arm==1&&qwen_app_gate_up_trial_selections()==gate_up_before))throw std::runtime_error("Actual Gate/Up selection coverage failed");''')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,gpu)),[Path(__file__),old_backend,backend])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);r['post_top2_gate_plan']=dict(scope=scope,actual_sources=sources,commands=jobs,backend=record(backend))
 seed=a.out/'linked-seed.private.json';write_json(seed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='Top2_fusion_complete_range_and_input_lifetime_protection',candidate=record(a.out/'receipt.private.json'),
  qualified_shader_bytes_and_dispatch_geometry_unchanged=True,actual_dispatch_enforced=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
