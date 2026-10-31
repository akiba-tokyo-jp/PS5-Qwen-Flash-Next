#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a coherent, phase-scoped application-padding limit experiment."""
import argparse,json,re,shlex
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal

ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-limit-margin-probe-v1',enabled=True,
 application_padding_steps=[256,'observed_OS_reserved',128,64,0],OS_minimum_preserved=True,
 OS_counter_writes=0,context_observed_transient_pages=41,context_unmeasured_padding_pages=0,
 original_physical_CPU_heap_ledger_and_completion_checks=True,source_identity_unchanged=True,
 maximum_requests=10,automatic_operation_retries=0,production_adoption=False)

DECL='''
extern "C" std::uint64_t qwen_limit_probe_extra(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" std::uint64_t qwen_limit_probe_context(std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void qwen_limit_probe_stage(unsigned);
extern "C" void qwen_limit_probe_snapshot(std::uint64_t*);
'''
IMPLEMENTATION='''
#include "limit_margin_probe.h"
namespace {qwen_app::LimitMarginProbe limit_probe;}
extern "C" std::uint64_t qwen_limit_probe_extra(std::uint64_t free,std::uint64_t minimum,std::uint64_t reserved,std::uint64_t legacy){return limit_probe.required(free,minimum,reserved,legacy)-minimum;}
extern "C" std::uint64_t qwen_limit_probe_context(std::uint64_t free,std::uint64_t minimum,std::uint64_t reserved){return limit_probe.required(free,minimum,reserved,64,41);}
extern "C" void qwen_limit_probe_stage(unsigned phase){limit_probe.phase(phase);}
extern "C" void qwen_limit_probe_snapshot(std::uint64_t*out){limit_probe.snapshot(out);}
'''
REPORT='''static Json limit_probe_report(){
 std::array<std::uint64_t,22>stats{};qwen_limit_probe_snapshot(stats.data());Json phases=Json::array();
 for(unsigned i=0;i<4;++i){auto*p=stats.data()+2+5*i;phases.push_back({{"phase",i+1},{"admission_calls",p[0]},{"legacy_refusals",p[1]},{"padding_reductions",p[2]},
  {"minimum_free_pages",p[3]==UINT64_MAX?Json(nullptr):Json(p[3])},{"minimum_selected_padding_pages",p[4]==UINT64_MAX?Json(nullptr):Json(p[4])}});}
 return {{"schema","ps5-qwen-limit-probe-result-v1"},{"active_phase",stats[0]},{"last_selected_padding_pages",stats[1]},{"phases",phases},
  {"OS_minimum_preserved",true},{"OS_counter_writes",0},{"original_physical_and_completion_checks",true},
  {"universal_physical_limit_established",false},{"application_padding_experiment",true}};
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--stable-inference',action='store_true',help='Keep loading/context predicates; select zero application inference padding before all requests')
    p.add_argument('--decode-only',action='store_true',help='Restrict the owned GDN trial to scalar-gate S_v128 single-token graphs')
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    scope=dict(SCOPE)
    scope['maximum_requests']=n.get('io_gpu_comparison',{}).get('requests',10)
    if a.stable_inference:scope.update(stable_inference_padding_pages=0,loading_and_context_padding_unchanged=True,adaptive_inference_padding=False,context_unmeasured_padding_pages=2)
    rows=[x for x in n['CPU_metadata_scope']['changed_sources']if x['object_path']in n['link_command']]
    sysrow=next(x for x in rows if Path(x['source']['path']).name=='system_memory.cpp')
    original_header=Path(sysrow['source']['path']).parent/'system_memory.h';text=original_header.read_text()
    line=next(x for x in text.splitlines()if x.strip().startswith('const auto extra='))
    changed=line.replace('const auto extra=','const auto original_extra=')+'\n    const auto extra=qwen_limit_probe_extra(s.kernel_free,s.kernel_minimum,s.kernel_reserved,original_extra);'
    text=once(text,line,changed);text=once(text,'namespace qwen_app {',DECL+'\nnamespace qwen_app {')
    header=a.out/'system_memory.probe.private.h';header.write_text(text,newline='\n')
    probe=ROOT/'native/app/limit_margin_probe.h';(a.out/probe.name).write_bytes(probe.read_bytes())
    names={original_header,ROOT/'native/app/system_memory.h',ROOT.with_name(ROOT.name+'-refill')/'native/app/system_memory.h'}
    for row in rows:
        parent=Path(row['source']['path']).parent
        if(parent/'system_memory.h').is_file():names.add(parent/'system_memory.h')
    overlay=a.out/'limit-headers.private.json'
    write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},
        roots=[dict(type='file',name=p.resolve().as_posix(),**{'external-contents':header.resolve().as_posix()})for p in sorted(names)]))
    commands={x['object_path']:x['command'].copy()for x in rows}
    for cmd in [n['compile_commands'][0],n['all_Q2_optimized_monitor']['commands'][1]]:
        commands[cmd[cmd.index('-o')+1]]=cmd.copy()
    entry_command=n['compile_commands'][0];entry_object=entry_command[entry_command.index('-o')+1]
    variants={};originals={}
    for i,(obj,recipe)in enumerate(commands.items()):
        source=Path(recipe[recipe.index('-c')+1]);code=source.read_text();label='entry'if obj==entry_object else 'app'+str(i)
        if source==Path(sysrow['source']['path']):code+=IMPLEMENTATION.replace('LimitMarginProbe limit_probe;','LimitMarginProbe limit_probe(true);')if a.stable_inference else IMPLEMENTATION
        if label=='entry':
            code=once(code,'static Json memory_backpressure_report()',REPORT+'\nstatic Json memory_backpressure_report()')
            code=once(code,'        qwen_native_stage("model_load_started_after_memory_admission");',
                '        if(policy.at("native_limit_margin_probe")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact limit-margin scope required");\n        qwen_limit_probe_stage(1);\n        qwen_native_stage("model_load_started_after_memory_admission");')
            code=once(code,'        const auto OS_scope_memory=qwen_app::observe_native_system_memory();',
                '        qwen_limit_probe_stage(2);\n        const auto OS_scope_memory=qwen_app::observe_native_system_memory();')
            if not a.stable_inference:
                code=once(code,'OS_scope_memory.kernel_free<1005','OS_scope_memory.kernel_free<qwen_limit_probe_context(OS_scope_memory.kernel_free,OS_scope_memory.kernel_minimum,OS_scope_memory.kernel_reserved)')
                code=once(code,'context_memory.kernel_free<context_floor+43','context_memory.kernel_free<qwen_limit_probe_context(context_memory.kernel_free,context_memory.kernel_minimum,context_memory.kernel_reserved)')
            request_line=re.findall(r'        constexpr unsigned request_count=\d+;',code)
            if len(request_line)!=1:raise ValueError('One finite comparison request count required')
            code=once(code,request_line[0],'        qwen_limit_probe_stage(3);\n'+request_line[0])
            code=once(code,'        engine.reset();llama_free(context);','        qwen_limit_probe_stage(4);\n        engine.reset();llama_free(context);')
            code=once(code,'write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-expert-all-q2-model-result-v1"}',
                'write_fresh_report(startup.admission_report,{{"limit_margin_probe",limit_probe_report()},{"schema","ps5-qwen-expert-all-q2-model-result-v1"}')
            code=once(code,'{"memory_backpressure",memory_backpressure_report()}',
                '{"limit_margin_probe",limit_probe_report()},{"memory_backpressure",memory_backpressure_report()}')
        recipe+=['-ivfsoverlay',str(overlay)]
        originals[label]=dict(source=record(source),original_object=obj)
        variants[label]=(recipe,code)
    gpu_item=None;manifest=None
    if a.decode_only:
        manifest=json.loads(Path(n['bounded_model_source_manifest']['path']).read_text())
        gpu_item=next(x for x in manifest['objects']if x['source'].endswith('ggml-vulkan.cpp'))
        command=gpu_item['command'];command=shlex.split(command,posix=False)if isinstance(command,str)else command.copy()
        command=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in command]
        src=Path(command[command.index('-c')+1]);text=once(src.read_text(),'if(qwen_gdn_selected&&si==3)',
            'if(qwen_gdn_selected&&si==3&&kda==0&&dst->src[2]->ne[2]==1)')
        originals['GPU']=dict(source=record(src),original_object=gpu_item['object']['path']);variants['GPU']=(command,text)
    result,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),probe,header,overlay,*sorted(names)])
    result['CPU_metadata_scope']['changed_sources']=[dict(original=originals[k]['source'],source=sources[k],
        object_path=jobs[k][jobs[k].index('-o')+1],command=jobs[k])for k in jobs if k not in('entry','GPU')]
    owner_object=n['all_Q2_optimized_monitor']['commands'][1];owner_object=owner_object[owner_object.index('-o')+1]
    owner=next(k for k,v in originals.items()if v['original_object']==owner_object)
    result['all_Q2_optimized_monitor'].update(actual_entry=sources['entry'],actual_owner=sources[owner])
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['all_Q2_optimized_monitor']['commands'][1]=jobs[owner]
    result['routing_winners_normal']['actual_entry']=sources['entry']
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
        result[key]['actual_sources'].update(entry=sources['entry'],owner=sources[owner]);result[key]['commands'].update(entry=jobs['entry'],owner=jobs[owner])
    if a.decode_only:
        from build_model_io import validate_overrides
        gpu_item.update(object=record(a.out/'GPU.o'),command=jobs['GPU'])
        manifest['sources'][gpu_item['source']]['patched_sha256']=sources['GPU']['sha256']
        mp=a.out/'model-io.private.json';write_json(mp,manifest)
        result['bounded_model_source_manifest']=record(mp)
        result['bounded_model_source_overrides']=validate_overrides(mp,Path(result['engine_receipt']['path']))
        result['lossless_shader_storage']['vulkan_object']=gpu_item['object'];result['inputs_before'].append(record(mp))
        result['io_gpu_comparison'].update(GPU_source=sources['GPU'],GPU_command=jobs['GPU'],decode_only=True)
    result['limit_margin_probe']=dict(scope=scope,header=record(header),overlay=record(overlay),
        probe_header=record(probe),recompiled_app_objects=len(variants),original_app_objects=originals,
        linked_objects={k:record(a.out/(k+'.o'))for k in jobs},production_adopted=False)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='explicit_application_padding_limit_probe',
        application_kernel_padding_changed=True,OS_minimum_preserved=True,OS_counter_writes=0,
        physical_CPU_heap_ledger_and_positive_completion_guards_preserved=True,
        CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,
        candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
