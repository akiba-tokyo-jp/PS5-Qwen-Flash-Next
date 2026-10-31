#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate exact676-key placement and an optional measured decode GDN winner."""
import argparse,json
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from build_limit_margin_probe import DECL,IMPLEMENTATION,REPORT
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('parent','providers','comparison','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--gpu',action='store_true');a=p.parse_args()
    n=json.loads(a.parent.read_text());providers=json.loads(a.providers.read_text());measured=json.loads(a.comparison.read_text())
    require(measured['completed']and measured['placement_eligible'],'Closed exact positive stable-policy placement comparison required')
    require(not a.gpu or measured['decode_GDN_eligible'],'Measured whole-model decode GDN gain required')
    a.out.mkdir(parents=True,exist_ok=False)
    seed=json.loads(a.parent.read_text())
    if a.gpu:
        before=seed['lossless_shader_storage']['vulkan_object'];after=providers['lossless_shader_storage']['vulkan_object']
        require(seed['link_command'].count(before['path'])==1,'One original GPU provider required')
        seed['link_command'][seed['link_command'].index(before['path'])]=after['path']
        for k in('bounded_model_source_manifest','bounded_model_source_overrides','lossless_shader_storage'):seed[k]=providers[k]
        rows={r['path']:r for r in seed['inputs_before']}
        for r in active_link_inputs(providers):
            if r['path']in rows:require(rows[r['path']]==r,'Unambiguous GPU dependency required')
            rows[r['path']]=r
        seed['inputs_before']=list(rows.values())
    seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
    rows=[r for r in n['CPU_metadata_scope']['changed_sources']if r['object_path']in n['link_command']]
    sysrow=next(r for r in rows if Path(r['source']['path']).name=='system_memory.cpp')
    original_header=Path(sysrow['source']['path']).parent/'system_memory.h'
    text=original_header.read_text();line=next(x for x in text.splitlines()if x.strip().startswith('const auto extra='))
    text=once(text,line,line.replace('const auto extra=','const auto original_extra=')+'\n    const auto extra=qwen_limit_probe_extra(s.kernel_free,s.kernel_minimum,s.kernel_reserved,original_extra);')
    text=once(text,'namespace qwen_app {',DECL+'\nnamespace qwen_app {')
    header=a.out/'system_memory.winner.private.h';header.write_text(text,newline='\n')
    probe=ROOT/'native/app/limit_margin_probe.h';(a.out/probe.name).write_bytes(probe.read_bytes())
    names={original_header,ROOT/'native/app/system_memory.h',ROOT.with_name(ROOT.name+'-refill')/'native/app/system_memory.h'}
    for row in rows:
        parent=Path(row['source']['path']).parent
        if(parent/'system_memory.h').is_file():names.add(parent/'system_memory.h')
    overlay=a.out/'winner-headers.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=f.resolve().as_posix(),**{'external-contents':header.resolve().as_posix()})for f in sorted(names)]))
    ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1]
    commands={r['object_path']:r['command'].copy()for r in rows}
    for c in(ec,oc):commands[c[c.index('-o')+1]]=c.copy()
    entry_object=ec[ec.index('-o')+1];owner_object=oc[oc.index('-o')+1]
    pc=providers['all_Q2_optimized_monitor']['commands'][1]
    owner_path=Path(pc[pc.index('-c')+1]);owner=owner_path.read_text()
    directories=[owner_path.parent]+[Path(pc[i+1])for i,x in enumerate(pc[:-1])if x=='-I']
    packed=next(d/'io-current-bundle.private.h'for d in directories if(d/'io-current-bundle.private.h').is_file())
    bundle=once(packed.read_text(),'Q2_trial_mode=false','Q2_trial_mode=true')
    (a.out/'limit-winner-bundle.private.h').write_text(bundle,newline='\n')
    owner=once(owner,'#include "io-current-bundle.private.h"','#include "limit-winner-bundle.private.h"')
    scope=dict(schema='ps5-qwen-limit-winner-normal-v1',maximum_requests=3,Expert_supplemental_triplets=256,
        total_bundled_Experts=676,stable_inference_padding_pages=0,original_loading_context_and_physical_checks=True,
        scalar_single_token_GDN=a.gpu,cache_slots=3072,original_model_payloads=True,automatic_retries=0)
    optimized=dict(n['all_Q2_optimized_monitor']['scope'],supplemental_bundles=256,total_bundled_Experts=676)
    variants={};originals={}
    for i,(obj,command)in enumerate(commands.items()):
        src=Path(command[command.index('-c')+1]);code=src.read_text();label='entry'if obj==entry_object else 'owner'if obj==owner_object else 'app'+str(i)
        if obj==owner_object:
            code=owner;command=pc.copy();command[command.index('-o')+1]=owner_object
        if src==Path(sysrow['source']['path']):code+=IMPLEMENTATION.replace('LimitMarginProbe limit_probe;','LimitMarginProbe limit_probe(true);')
        if label=='entry':
            code=once(code,json.dumps(json.dumps(n['all_Q2_optimized_monitor']['scope'],separators=(',',':'))),json.dumps(json.dumps(optimized,separators=(',',':'))))
            code=once(code,'static Json memory_backpressure_report()',REPORT+'\nstatic Json memory_backpressure_report()')
            code=once(code,'        qwen_native_stage("model_load_started_after_memory_admission");',
                '        if(policy.at("native_limit_defaults")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact measured limit defaults required");\n        qwen_native_stage("model_load_started_after_memory_admission");')
            code=once(code,'        const unsigned request_count=3;','        qwen_limit_probe_stage(3);\n'+('        qwen_app_gdn_trial_select(true);\n'if a.gpu else '')+'        const unsigned request_count=3;')
            code=once(code,'write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-expert-all-q2-model-result-v1"}',
                'write_fresh_report(startup.admission_report,{{"limit_margin_probe",limit_probe_report()},{"schema","ps5-qwen-expert-all-q2-model-result-v1"}')
            code=once(code,'{"memory_backpressure",memory_backpressure_report()}','{"limit_margin_probe",limit_probe_report()},{"memory_backpressure",memory_backpressure_report()}')
            if a.gpu:
                code='extern "C" void qwen_app_gdn_trial_select(bool);\nextern "C" void qwen_app_gdn_trial_release();\n'+code
                code=once(code,'engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_native_driver_complete();',
                    'engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_app_gdn_trial_release();qwen_native_driver_complete();')
        command+=['-ivfsoverlay',str(overlay)];variants[label]=(command,code);originals[label]=dict(source=record(src),object_path=obj)
    r,jobs,sources=link(seedpath,a.out,variants,[Path(__file__),a.comparison,a.providers,probe,header,overlay,packed,a.out/'limit-winner-bundle.private.h',*sorted(names)])
    r['CPU_metadata_scope']['changed_sources']=[dict(original=originals[k]['source'],source=sources[k],object_path=jobs[k][jobs[k].index('-o')+1],command=jobs[k])for k in jobs if k!='entry']
    for k in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
        r[k]['actual_sources'].update(entry=sources['entry'],owner=sources['owner']);r[k]['commands'].update(entry=jobs['entry'],owner=jobs['owner'])
    r['all_Q2_optimized_monitor'].update(actual_entry=sources['entry'],actual_owner=sources['owner']);r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['all_Q2_optimized_monitor']['commands'][1]=jobs['owner'];r['routing_winners_normal']['actual_entry']=sources['entry']
    for k in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal','all_Q2_optimized_monitor'):r[k]['scope']=optimized
    r['normal_performance']['current_placement']=dict(complete_triplets=256,total_bundled_Experts=676,measured_comparison=record(a.comparison),immutable_header=record(a.out/'limit-winner-bundle.private.h'),actual_owner=sources['owner'],normal_validation_pending=True)
    r['limit_defaults']=dict(scope=scope,comparison=record(a.comparison),probe_header=record(probe),header=record(header),overlay=record(overlay),packed_header=record(a.out/'limit-winner-bundle.private.h'),actual_sources=sources,commands=jobs,normal_qualification_pending=True,production_adopted=False)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='measured_limit_winner_normal',original_loading_context_and_physical_checks=True,stable_inference_padding_pages=0,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
