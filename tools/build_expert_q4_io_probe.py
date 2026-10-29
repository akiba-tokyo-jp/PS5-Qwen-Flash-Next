#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add completed I/O counters to the selected Q4 app; retain every GPU object."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]

def profile_entry(text):
    text='#include "expert_q4_io_profile.h"\n'+text
    at='using Json = nlohmann::json;'
    text=once(text,at,at+'''
static qwen_app::ExpertQ4IOProfile Q4_IO_profile;
extern "C" void qwen_app_profile_CPU_rows_begin(const char*name,std::uint64_t count,std::uint64_t stride){
    if(Q4_IO_profile.enabled)Q4_IO_profile.begin(name,count,stride,qwen_app::native_model_source_stats());
}
extern "C" void qwen_app_profile_CPU_rows_end(){
    if(Q4_IO_profile.enabled)Q4_IO_profile.end(qwen_app::native_model_source_stats());
}
''')
    text=once(text,'    if (source.schedule_enabled) result.update({', '''    if(Q4_IO_profile.live)throw std::runtime_error("Cannot snapshot an unfinished CPU row scope");
    for(unsigned kind=0;kind<3;++kind){const auto&v=Q4_IO_profile.totals[kind];
        const std::string prefix=kind==0?"token_embedding_":kind==1?"PLE_embedding_":"other_CPU_rows_";
        result[prefix+"rows"]=v.rows;result[prefix+"logical_bytes"]=v.logical;
        result[prefix+"physical_bytes"]=v.physical;result[prefix+"physical_calls"]=v.calls;
        result[prefix+"source_wait_ns"]=v.wait_ns;
    }
    if (source.schedule_enabled) result.update({''')
    text=once(text,'        const unsigned request_count=3;', '''        if(policy.at("native_Expert_Q4_IO_profile")!=Json({{"schema","ps5-qwen-Q4-completed-IO-profile-v1"},
            {"enabled",true},{"original_IO_and_GPU_work_unchanged",true},{"maximum_requests",3},
            {"per_token_completed_snapshots",true},{"CPU_row_name_attribution",true}}))
            throw std::runtime_error("Exact completed Q4 I/O measurement scope required");
        Q4_IO_profile.enabled=true;
        const unsigned request_count=3;''')
    text=once(text,'                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});',
        '                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms},\n'
        '                    {"completed_performance",performance_snapshot(*engine)},\n'
        '                    {"Expert_uploaded_bytes",engine->expert_cache_metrics()->uploaded_bytes}});')
    return once(text,'{"HTTP_requests",2},{"VideoOut_starts",1}',
        '{"completed_IO_profile",true},{"IO_or_GPU_operations_added",false},{"HTTP_requests",2},{"VideoOut_starts",1}')

def profile_ops(text):
    text='#include <cstdint>\nextern "C" void qwen_app_profile_CPU_rows_begin(const char*,std::uint64_t,std::uint64_t);\nextern "C" void qwen_app_profile_CPU_rows_end();\n'+text
    text=once(text,'        for (int64_t row = 0; row < ggml_nelements(ids); ++row) {',
        '        qwen_app_profile_CPU_rows_begin(src0->name,ggml_nelements(ids),bytes);\n        for (int64_t row = 0; row < ggml_nelements(ids); ++row) {')
    return once(text,'            qwen_app_model_source_chunk_completed();\n        }\n        return;',
        '            qwen_app_model_source_chunk_completed();\n        }\n        qwen_app_profile_CPU_rows_end();\n        return;')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['expert_q4_model']['passive_monitor'],'Selected Q4 passive application required')
    frozen=active_link_inputs(prior)+[record(a.parent),record(__file__),record(ROOT/'native/app/expert_q4_io_profile.h')]
    for row in frozen:require(record(row['path'])==row,'Selected Q4 input changed')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    c=prior['compile_commands'][0].copy();old_entry=Path(c[c.index('-c')+1]);old_object=c[c.index('-o')+1]
    source=a.out/'Q4-IO-entry.private.cpp';source.write_text(profile_entry(old_entry.read_text()),newline='\n')
    obj=a.out/'entry.o';c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(obj);c+=['-I',str(old_entry.parent)]
    if '-MF'in c:c[c.index('-MF')+1]=str(a.out/'entry.private.d')
    external=json.loads(Path(prior['shader_resource_manifest']['path']).read_text())
    embedded=json.loads(Path(external['embedded_control']['path']).read_text())
    io_rows=[json.loads(Path(embedded[key]['path']).read_text())for key in('parent_model_io','extended_model_io')]
    row=next(r for r in io_rows[1]['objects']if r['source']=='ggml/src/ggml-cpu/ops.cpp')
    old_ops_object=row['object']['path'];ops_source=Path(row['command'].split(' -c ',1)[1].split(' -I',1)[0].strip('"'))
    ops=a.out/'Q4-IO-CPU-rows.private.cpp';ops.write_text(profile_ops(ops_source.read_text()),newline='\n');ops_obj=a.out/'CPU-rows.o'
    command=row['command'].replace(str(ops_source),str(ops)).replace(old_ops_object,str(ops_obj))
    require(str(ops)in command and str(ops_obj)in command,'Exact CPU row compile substitution required')
    # The old logical source uses local quoted headers; retain its include root.
    command+=' -I'+subprocess.list2cmdline([str(ops_source.parent)])
    frozen +=[record(old_entry),record(ops_source),record(source),record(ops)]
    replacements={old_object:str(obj),old_ops_object:str(ops_obj)}
    for old in replacements:require(prior['link_command'].count(old)==1,'One exact selected object must be replaced')
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    for i,args in enumerate((c,command,link)):
        r=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(Q4_IO_build_step=i+1,total=3)),flush=True)
    for row in frozen:require(record(row['path'])==row,'Measurement source changed during compilation')
    records=[];key='ggml/src/ggml-cpu/ops.cpp';vulkan='ggml/src/ggml-vulkan/ggml-vulkan.cpp'
    for label,data,role in zip(('parent','extended'),io_rows,('parent_model_io','extended_model_io')):
        row=next(r for r in data['objects']if r['source']==key)
        row.update(object=record(ops_obj),command=command,actual_source=record(ops),logical_source_before_VFS=record(ops))
        data['sources'][key]['patched_sha256']=record(ops)['sha256']
        folder=a.out/label;folder.mkdir();view=folder/'source'/vulkan;view.parent.mkdir(parents=True)
        view.write_bytes((Path(embedded[role]['path']).parent/'source'/vulkan).read_bytes())
        path=folder/'model-io.private.json';write_json(path,data);validate_overrides(path,prior['engine_receipt']['path']);records.append(record(path))
    replace={embedded['parent_model_io']['path']:records[0],embedded['extended_model_io']['path']:records[1],old_ops_object:record(ops_obj)}
    def updated(rows):return[replace.get(r['path'],r)for r in rows]
    embedded.update(parent_model_io=records[0],extended_model_io=records[1],inputs=updated(embedded['inputs'])+[record(ops),record(ops_obj)])
    ep=a.out/'embedded-shader.private.json';write_json(ep,embedded);replace[external['embedded_control']['path']]=record(ep)
    external.update(parent_model_io=records[0],extended_model_io=records[1],embedded_control=record(ep),inputs=updated(external['inputs'])+[record(ops),record(ops_obj)])
    xp=a.out/'external-shader.private.json';write_json(xp,external)
    storage=validate_shader_resources(xp,records[1]['path'],prior['engine_receipt']['path'])
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[c],link_command=link,source_parent=record(a.parent),
        inputs_before=prior['inputs_before']+frozen+[record(obj),record(ops_obj)]+records+[record(ep),record(xp)],
        bounded_model_source_manifest=records[1],bounded_model_source_overrides=io_rows[1],
        shader_resource_manifest=record(xp),lossless_shader_storage=storage,
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['expert_q4_model']['IO_profile']=dict(actual_entry=record(source),actual_CPU_rows=record(ops),
        original_IO_and_GPU_work_unchanged=True,per_token_completed_snapshots=True,CPU_row_name_attribution=True,
        CPU_row_compile_command=command,diagnostic_only=True,production_adopted=False)
    receipt['expert_q4_model']['actual_entry']=record(source)
    target=a.out/'receipt.private.json';write_json(target,receipt)
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Actual import/callback audit required')
    write_json(target,receipt);print(json.dumps(dict(Q4_IO_measurement_built=True,PS5_operations=0,CI_runs=0)),flush=True)
if __name__=='__main__':main()
