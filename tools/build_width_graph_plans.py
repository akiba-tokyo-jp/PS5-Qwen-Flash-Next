#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain CPU width1/2 topology; reallocate every reactivated GPU schedule."""
import argparse,copy,json,shlex
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=r'''
namespace {
struct WidthEntry{llm_graph_result*result=nullptr;qwen_app::WidthGraphBindings bindings;};
struct WidthRegistry{
 llama_context*context;std::thread::id owner=std::this_thread::get_id();bool enabled=false;
 std::unique_ptr<llm_graph_result>two;std::array<WidthEntry,3>entries;
 std::uint64_t reactivations=0,captures=0,invalidations=0,peak=0;
 explicit WidthRegistry(llama_context*c):context(c){}
};
// Lazy CPU metadata only: no new pre-main constructor or GPU owner.
WidthRegistry*width_registry=nullptr;
WidthRegistry&width_owner(llama_context*c){
 if(!width_registry)width_registry=new WidthRegistry(c);
 if(width_registry->context!=c||width_registry->owner!=std::this_thread::get_id())
   throw std::runtime_error("Width plans require the sole original context/producer");
 return*width_registry;
}
qwen_app::WidthGraphBindings&width_bindings(llama_context*c,llm_graph_result*r){
 auto&owner=width_owner(c);for(auto&e:owner.entries)if(e.result==r)return e.bindings;
 for(auto&e:owner.entries)if(!e.result){e.result=r;return e.bindings;}
 throw std::runtime_error("Width topology exceeds its three result arenas");
}
llm_graph_result*width_select(llama_context*c,unsigned tokens,bool outputs,llm_graph_result*base){
 auto&owner=width_owner(c);if(!owner.enabled||tokens!=2||!outputs)return base;
 if(!owner.two)owner.two.reset(new llm_graph_result(base->get_max_nodes()));return owner.two.get();
}
void width_capture(llama_context*c,llm_graph_result*r,ggml_cgraph*gf){
 auto&owner=width_owner(c);width_bindings(c,r).capture(gf->nodes,gf->n_nodes,gf->leafs,gf->n_leafs);++owner.captures;
 std::uint64_t retained=owner.two?ggml_tensor_overhead()*owner.two->get_max_nodes()+ggml_graph_overhead_custom(owner.two->get_max_nodes(),false):0;
 for(const auto&e:owner.entries)retained+=e.bindings.retained_bytes();owner.peak=std::max(owner.peak,retained);
}
void width_invalidate(llama_context*c){
 if(!width_registry)return;auto&owner=width_owner(c);
 for(auto&e:owner.entries){e.bindings.clear();e.result=nullptr;}owner.two.reset();++owner.invalidations;
}
void width_retire(llama_context*c){if(width_registry&&width_registry->context==c){delete width_registry;width_registry=nullptr;}}
}
extern "C" void qwen_app_select_width_graph_plans(llama_context*c,bool enabled){width_owner(c).enabled=enabled;}
extern "C" void qwen_app_width_graph_stats(llama_context*c,std::uint64_t*out){
 if(!out)throw std::runtime_error("Missing width graph counters");const auto&o=width_owner(c);
 out[0]=o.reactivations;out[1]=o.captures;out[2]=o.invalidations;out[3]=o.peak;
}
extern "C" unsigned qwen_app_width_graph_live_contexts(){return width_registry?1:0;}
'''
def context_source(text):
    text='#include "width_graph_bindings.h"\n#include "ggml-impl.h"\n'+text
    at=text.index('llama_context::llama_context(');text=text[:at]+REGISTRY+'\n'+text[at:]
    start=text.index('llama_context::~llama_context()');end=text.index('\n}',start)+2
    part=once(text[start:end],'    synchronize();','    synchronize();\n    width_retire(this);');text=text[:start]+part+text[end:]
    require(text.count('    for (auto & res : gf_res_prev) {')==3,'Exact three original graph invalidation boundaries required')
    text=text.replace('    for (auto & res : gf_res_prev) {','    width_invalidate(this);\n    for (auto & res : gf_res_prev) {')
    start=text.index('llm_graph_result * llama_context::process_ubatch(');end=text.index('\n}\n',start)+3;part=text[start:end]
    part=once(part,'    auto * res = get_gf_res_prev();','    auto * res = width_select(this,ubatch.n_tokens,n_outputs>0,get_gf_res_prev());')
    part=once(part,'    if (!graph_reuse_disable && gf_res_prev_active == res && res->can_reuse(gparams)) {',
        '''    auto&saved=width_bindings(this,res);
    const bool reactivate=!graph_reuse_disable&&width_owner(this).enabled&&gf_res_prev_active!=res&&saved.valid();
    if(reactivate){ggml_backend_sched_synchronize(sched.get());saved.restore_after_positive_sync();}
    if (!graph_reuse_disable && (gf_res_prev_active == res||reactivate) && res->can_reuse(gparams)) {
        if(reactivate){
            gf_res_prev_active=nullptr;ggml_backend_sched_reset(sched.get());
            ggml_backend_sched_set_eval_callback(sched.get(),cparams.cb_eval,cparams.cb_eval_user_data);
            if(!ggml_backend_sched_alloc_graph(sched.get(),gf)){ret=GGML_STATUS_ALLOC_FAILED;return nullptr;}
            gf_res_prev_active=res;++width_owner(this).reactivations;
        }''')
    part=once(part,'        res->reset();','        saved.clear();res->reset();')
    part=once(part,'        if (!ggml_backend_sched_alloc_graph(sched.get(), gf)) {','        width_capture(this,res,gf);\n        if (!ggml_backend_sched_alloc_graph(sched.get(), gf)) {')
    return text[:start]+part+text[end:]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--reuse-entry-build',type=Path)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    recipes=a.cache/'build/llama-ps5/compile_commands.json';recipe=next(r for r in json.loads(recipes.read_text())if r['file'].endswith('/llama-context.cpp'));source=Path(recipe['file']);obj=Path(recipe['output'])
    command=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in shlex.split(recipe['command'],posix=False)];command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(ROOT/'native/app'),'-I',str(a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/ggml/src')]
    seed=copy.deepcopy(prior);archive=next(x for x in seed['link_command']if x.endswith('libllama.a'));seed['link_command'].insert(seed['link_command'].index(archive),str(obj));seed['inputs_before'].append(record(obj))
    seed_path=a.out/'width-seed.private.json';write_json(seed_path,seed)
    cmd=prior['compile_commands'][0];entry=Path(cmd[cmd.index('-c')+1]).read_text();entry='#include <cstdint>\nstruct llama_context;\nextern "C" void qwen_app_select_width_graph_plans(llama_context*,bool);\nextern "C" void qwen_app_width_graph_stats(llama_context*,std::uint64_t*);\nextern "C" unsigned qwen_app_width_graph_live_contexts();\n'+entry
    entry=once(entry,'            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;','            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;\n            qwen_app_select_width_graph_plans(context,second);')
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t width_before[4]{};qwen_app_width_graph_stats(context,width_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["actual_graph_reuses"]=',
        '            std::uint64_t width_after[4]{};qwen_app_width_graph_stats(context,width_after);\n            row["width_graph_plans"]={{"enabled",second},{"reactivations",width_after[0]-width_before[0]},{"new_topologies",width_after[1]-width_before[1]},{"invalidations",width_after[2]-width_before[2]},{"retained_CPU_metadata_peak_bytes",width_after[3]},{"GPU_schedule_reallocated_after_positive_sync",true}};\n            row["actual_graph_reuses"]=')
    marker='        if(qwen_app_resident_cache_reuse_live_owners())throw std::runtime_error("Original cache reset owner was not retired");'
    entry=once(entry,marker,marker+'\n        if(qwen_app_width_graph_live_contexts())throw std::runtime_error("Width graph CPU owner was not retired");')
    variants={'context':(command,context_source(source.read_text()))}
    inputs=[Path(__file__),a.parent,recipes,source,ROOT/'native/app/width_graph_bindings.h'];reused=None
    if a.reuse_entry_build:
        src=a.reuse_entry_build/'entry.private.cpp';obj_entry=a.reuse_entry_build/'entry.o'
        require(src.read_text()==entry and obj_entry.stat().st_size>0,'Only an identical compiled entry may be reused')
        seed['link_command'][seed['link_command'].index(cmd[cmd.index('-o')+1])]=str(obj_entry)
        inputs +=[src,obj_entry];seed['inputs_before'] +=[record(src),record(obj_entry)]
        reused=cmd.copy();reused[reused.index('-c')+1]=str(src);reused[reused.index('-o')+1]=str(obj_entry)
        reused[1:1]=['-I',str(Path(cmd[cmd.index('-c')+1]).parent),'-I',str(a.reuse_entry_build)]
        write_json(seed_path,seed)
    else:variants['entry']=(cmd,entry)
    result,commands,sources=link(seed_path,a.out,variants,inputs)
    if reused:
        commands['entry']=reused;sources['entry']=record(a.reuse_entry_build/'entry.private.cpp')
        result['compile_commands']=[reused];result['expert_q2_model']['actual_entry']=sources['entry']
        result['routing_sharing']['actual_sources']['entry']=sources['entry'];result['routing_sharing']['commands'][0]=reused
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];result['routing_winners_normal']['actual_entry']=sources['entry']
    result['width_graph_plans']=dict(actual_sources=sources,commands=commands,original_context=record(source),additional_CPU_arenas_maximum=1,
        original_can_reuse_parameter_and_input_checks_retained=True,positive_sync_before_binding_restore=True,restored_GPU_schedules_always_reallocated=True,
        original_memory_invalidation_and_context_destructor_boundaries_retained=True,enabled_only_for_final_repeated_consumer=True,PS5_operations=0,native_verification_pending=True)
    seal(result,a.workspace,a.cache,a.out);print('CPU-only width topology retention built; every reactivation retains original checks and redoes GPU allocation after positive sync.')
if __name__=='__main__':main()
