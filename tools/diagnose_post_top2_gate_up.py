#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Capture bounded actual graph metadata when the Gate/Up matcher selects no work."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
DIAG=r'''
namespace {
std::uint64_t post_gate_meta[512]{};
void post_gate_note(const ggml_cgraph*g){
 if(!qwen_gate_up_enabled.load()||post_gate_meta[0])return;
 for(int i=0;i<g->n_nodes;++i){const auto*a=g->nodes[i];if(a->op!=GGML_OP_MUL_MAT_ID||a->ne[0]!=640||a->ne[1]!=2||a->ne[2]>2)continue;
  unsigned at=1;post_gate_meta[at++]=i;post_gate_meta[at++]=g->n_nodes;
  for(int j=i;j<g->n_nodes&&j<i+5;++j){const auto*t=g->nodes[j];post_gate_meta[at++]=t->op;post_gate_meta[at++]=t->type;
   post_gate_meta[at++]=t->op==GGML_OP_GLU?ggml_get_glu_op(t):UINT64_MAX;
   for(int k=0;k<4;++k)post_gate_meta[at++]=t->ne[k];
   for(int k=0;k<4;++k)post_gate_meta[at++]=t->nb[k];
   post_gate_meta[at++]=ggml_is_contiguous(t);
   for(unsigned k=0;k<3;++k){const auto*s=t->src[k];post_gate_meta[at++]=s!=nullptr;if(!s)continue;
    post_gate_meta[at++]=s->op;post_gate_meta[at++]=s->type;post_gate_meta[at++]=ggml_is_contiguous(s);
    for(int d=0;d<4;++d)post_gate_meta[at++]=s->ne[d];for(int d=0;d<4;++d)post_gate_meta[at++]=s->nb[d];
    post_gate_meta[at++]=s==a->src[1];post_gate_meta[at++]=s==a->src[2];post_gate_meta[at++]=s==a;
   }
  }
  post_gate_meta[0]=at;return;
 }
}
}
extern "C" void qwen_post_gate_metadata(std::uint64_t*out){std::copy_n(post_gate_meta,512,out);}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text()
 marker='static ggml_status ggml_backend_vk_graph_compute(ggml_backend_t backend, ggml_cgraph * cgraph) {'
 gpu=once(gpu,marker,DIAG+'\n'+marker+'\n    post_gate_note(cgraph);')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,metadata_only_diagnostic=True,maximum_graph_metadata_words=512,additional_GPU_calls=0)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_post_gate_metadata(std::uint64_t*);\n'+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'            row["phase"]=phase;',
  '            std::uint64_t metadata[512]{};qwen_post_gate_metadata(metadata);row["Gate_Up_actual_graph_metadata"]=std::vector<std::uint64_t>(metadata,metadata+512);\n            row["phase"]=phase;')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,gpu)),[Path(__file__)])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);r['post_top2_gate_diagnostic']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seed=a.out/'linked-seed.private.json';write_json(seed,r)
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_actual_graph_metadata',candidate=record(a.out/'receipt.private.json'),additional_GPU_calls=0,shader_math_unchanged=True,PS5_operations=0))
if __name__=='__main__':main()
