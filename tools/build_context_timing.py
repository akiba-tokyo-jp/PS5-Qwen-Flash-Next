#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure graph construction, allocation and compute wall time by input width."""
import argparse,copy,json,shlex
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['calls','reuse_checks_ns','reuse_hits','graph_build_calls','graph_build_ns','graph_allocate_calls','graph_allocate_ns','set_inputs_ns','graph_compute_ns','maximum_graph_nodes','maximum_graph_metadata_bytes']
def context_source(text):
    text='#include "profile_clock.h"\n#include <array>\n#include <stdexcept>\nnamespace {std::array<std::uint64_t,33> qwen_graph_timing{};}\nextern "C" void qwen_app_graph_timing(std::uint64_t*out){if(!out)throw std::invalid_argument("Missing graph timing target");std::copy(qwen_graph_timing.begin(),qwen_graph_timing.end(),out);}\n'+text
    start=text.index('llm_graph_result * llama_context::process_ubatch(');end=text.index('\n}\n',start)+3;part=text[start:end]
    part=once(part,'    if (mctx && !mctx->apply()) {','    auto*c=qwen_graph_timing.data()+11*(ubatch.n_tokens==1?0:ubatch.n_tokens==2?1:2);++c[0];\n    if (mctx && !mctx->apply()) {')
    part=once(part,'    if (!graph_reuse_disable && gf_res_prev_active == res && res->can_reuse(gparams)) {',
        '    const auto check_started=qwen_app::ProfileClock::now();\n    const bool reused=!graph_reuse_disable && gf_res_prev_active == res && res->can_reuse(gparams);\n    c[1]+=qwen_app::profile_elapsed_ns(check_started);\n    if (reused) {++c[2];')
    part=once(part,'        gf = model.build_graph(gparams);','        ++c[3];{qwen_app::ProfileScope timing(c[4]);gf = model.build_graph(gparams);}\n        if(gf){c[9]=std::max<std::uint64_t>(c[9],ggml_graph_n_nodes(gf));c[10]=std::max<std::uint64_t>(c[10],ggml_tensor_overhead()*res->get_max_nodes()+ggml_graph_overhead_custom(res->get_max_nodes(),false));}')
    part=once(part,'        if (!ggml_backend_sched_alloc_graph(sched.get(), gf)) {','        ++c[5];bool allocated=false;{qwen_app::ProfileScope timing(c[6]);allocated=ggml_backend_sched_alloc_graph(sched.get(),gf);}\n        if (!allocated) {')
    part=once(part,'        res->set_inputs(&ubatch);','        {qwen_app::ProfileScope timing(c[7]);res->set_inputs(&ubatch);}')
    part=once(part,'    const auto status = graph_compute(res->get_gf(), ubatch.n_tokens > 1);','    ggml_status status;{qwen_app::ProfileScope timing(c[8]);status=graph_compute(res->get_gf(),ubatch.n_tokens>1);}')
    return text[:start]+part+text[end:]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--reuse-entry-build',type=Path)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    recipes=a.cache/'build/llama-ps5/compile_commands.json';recipe=next(r for r in json.loads(recipes.read_text())if r['file'].endswith('/llama-context.cpp'))
    source=Path(recipe['file']);obj=Path(recipe['output']);require(obj.is_file(),'Exact original context object required')
    command=shlex.split(recipe['command'],posix=False);command=[c[1:-1]if c.startswith('"')and c.endswith('"')else c for c in command];command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(ROOT/'native/app')]
    seed=copy.deepcopy(prior);archive=next(x for x in seed['link_command']if x.endswith('libllama.a'));i=seed['link_command'].index(archive)
    seed['link_command'].insert(i,str(obj));seed['inputs_before'].append(record(obj));seed_path=a.out/'context-seed.private.json';write_json(seed_path,seed)
    entry_cmd=prior['compile_commands'][0];entry=Path(entry_cmd[entry_cmd.index('-c')+1]).read_text()
    entry='#include <cstdint>\nextern "C" void qwen_app_graph_timing(std::uint64_t*);\n'+entry
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t graph_before[33]{};qwen_app_graph_timing(graph_before);\n            const auto perf=performance_snapshot(*engine);')
    marker='            row["actual_graph_reuses"]='
    entry=once(entry,marker,'            std::uint64_t graph_after[33]{};qwen_app_graph_timing(graph_after);Json graph_timings=Json::array();\n            const char*timing_names[]={'+','.join(json.dumps(f)for f in FIELDS)+'};\n            for(unsigned band=0;band<3;++band){Json b={{"width",band==0?Json(1):band==1?Json(2):Json("prefill")}};for(unsigned f=0;f<11;++f){const auto n=11*band+f;b[timing_names[f]]=f<9?graph_after[n]-graph_before[n]:graph_after[n];}graph_timings.push_back(b);}\n            row["graph_timing"]={{"bands",graph_timings},{"wall_intervals_are_nested",true},{"GPU_timestamps",false},{"additional_GPU_operations",0}};\n'+marker)
    variants={'context':(command,context_source(source.read_text()))};inputs=[Path(__file__),a.parent,recipes,source,ROOT/'native/app/profile_clock.h']
    reused=None
    if a.reuse_entry_build:
        src=a.reuse_entry_build/'entry.private.cpp';object=a.reuse_entry_build/'entry.o'
        require(src.read_text()==entry and object.stat().st_size>0,'Only a byte-identical already compiled entry can be reused')
        oldobj=entry_cmd[entry_cmd.index('-o')+1];seed['link_command'][seed['link_command'].index(oldobj)]=str(object)
        inputs +=[src,object];seed['inputs_before'] +=[record(src),record(object)]
        reused=entry_cmd.copy();reused[reused.index('-c')+1]=str(src);reused[reused.index('-o')+1]=str(object)
        reused[1:1]=['-I',str(Path(entry_cmd[entry_cmd.index('-c')+1]).parent),'-I',str(a.reuse_entry_build)]
        write_json(seed_path,seed)
    else:variants['entry']=(entry_cmd,entry)
    result,commands,sources=link(seed_path,a.out,variants,inputs)
    if reused:
        commands['entry']=reused;sources['entry']=record(a.reuse_entry_build/'entry.private.cpp')
        result['compile_commands']=[reused];result['expert_q2_model']['actual_entry']=sources['entry']
        result['routing_sharing']['actual_sources']['entry']=sources['entry'];result['routing_sharing']['commands'][0]=reused
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];result['routing_winners_normal']['actual_entry']=sources['entry']
    result['context_timing']=dict(actual_sources=sources,commands=commands,original_context=record(source),original_object=record(obj),fields=FIELDS,widths=[1,2,'prefill'],GPU_timestamp_queries=False,additional_GPU_operations=0,original_graph_reuse_and_allocation_conditions_unchanged=True)
    seal(result,a.workspace,a.cache,a.out);print('Width-specific graph CPU/wall timing built without graph, GPU operation or precision changes.')
if __name__=='__main__':main()
