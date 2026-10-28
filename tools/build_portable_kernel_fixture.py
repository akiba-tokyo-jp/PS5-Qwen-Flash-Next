#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build three finite portable GPU comparisons with original immutable shaders."""
import argparse,copy,json,os,re,shutil,subprocess
from pathlib import Path
from shader_storage import record,patch_vulkan,validate_storage
from external_shader_storage import validate_shader_resources
from build_model_io import validate_overrides
from build_speculative_batch_probe import once
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-portable-kernel-fixture-v1',model_loads=0,synthetic_not_model_speed=True,
    widths=[1,2,4],candidates=['router-large-workgroup','shared-input-packed-projection','contiguous-gate-sigmoid-multiply'],
    cases=9,maximum_GPU_graphs=400,CPU_deadline_seconds=120,reference='F64',quantization=False,automatic_retries=0)


def workgroup_source(text):
    text='extern "C" unsigned qwen_app_portable_workgroup_mode();\n'+text
    begin=text.index('static vk_pipeline ggml_vk_get_dequantize_mul_mat_vec(')
    end=text.index('static vk_pipeline ggml_vk_get_dequantize_mul_mat_vec_id(',begin)
    body=text[begin:end]
    body=once(body,'    if (b_type == GGML_TYPE_Q8_1) {\n        if (ctx->device->vendor_id',
        '''    if(qwen_app_portable_workgroup_mode()&&ctx->device->vendor_id==VK_VENDOR_ID_AMD&&
       a_type==GGML_TYPE_F32&&b_type==GGML_TYPE_F32&&m==512&&k==2560&&num_cols<=4)
        dmmv_wg=DMMV_WG_SIZE_LARGE;
    if (b_type == GGML_TYPE_Q8_1) {
        if (ctx->device->vendor_id''')
    return text[:begin]+body+text[end:]


def entry_source(text):
    text='#include "portable_kernel_fixture.h"\n'+text
    marker='        qwen_app::require_first_generation_policy(policy,false);'
    text=once(text,marker,marker+'''
        if(policy.at("native_portable_kernel_fixture")!=Json::parse(SCOPE))
            throw std::runtime_error("Exact finite portable-kernel experiment required");'''.replace('SCOPE',json.dumps(json.dumps(SCOPE,separators=(',',':')))))
    start=text.index('    const auto probe=qwen_app::admit_padded_bank_layout(path,')
    end=text.index('    for(;;)(void)usleep(1000000);',start)
    text=text[:start]+'''    auto report=qwen_app::run_portable_kernel_fixture(qwen_native_driver_checkpoint,qwen_native_stage);
    if(model_file_identity(path,512ull<<20)!=identity)throw std::runtime_error("Original source identity changed during the portable fixture");
    require_model_CPU_budget();const auto ledger=qwen_app::native_model_device_stats();
    if(ledger.live||ledger.peak>1792ull<<20)throw std::runtime_error("Portable fixture did not retire every device owner");
    qwen_native_driver_complete();qwen_app::stop_native_model_sources();
    report.update({{"pid",getpid()},{"run_id",policy.at("native_first_generation_validation").at("run_id")},
        {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
        {"source_workers_stopped",true},{"device_ledger_live_bytes",ledger.live},{"device_ledger_peak_bytes",ledger.peak},
        {"driver_revision","872cc1264ad8ba5d6b888b092968fa5858a38c58"},{"profile","cumulative-idle"},
        {"persistent_caches_enabled",false},{"VM_after_GPU_and_retirement",diagnostic_VM_population()}});
    write_fresh_report(startup.admission_report+".portable-kernels",report);
    qwen_native_stage("portable_kernels_completed_model_not_loaded_waiting_for_ordinary_close");
'''+text[end:]
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--reuse-providers',type=Path)
    a=p.parse_args();prior=json.loads(a.parent.read_text());frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen unloaded fixture input changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    external=json.loads(Path(prior['shader_resource_manifest']['path']).read_text());embedded=json.loads(Path(external['embedded_control']['path']).read_text())
    origin=Path(embedded['parent_model_io']['path']);parent=json.loads(origin.read_text());extended=json.loads(Path(embedded['extended_model_io']['path']).read_text())
    key='ggml/src/ggml-vulkan/ggml-vulkan.cpp'
    original=(origin.parent/'source'/key).read_text();control=workgroup_source(original);provider=patch_vulkan(control)
    backend_commands=[];objects=[];new_manifests=[]
    def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n');return record(path)
    for label,data,text in(('parent',parent,control),('extended',extended,provider)):
        directory=a.out/label;source=directory/'source'/key;source.parent.mkdir(parents=True);source.write_text(text,newline='\n')
        data=copy.deepcopy(data);row=next(r for r in data['objects']if r['source']==key);command=row['command'];obj=directory/'ggml-vulkan.cpp.o'
        if not isinstance(command,str):raise ValueError('The captured actual Vulkan compile command is required')
        actual_source=source
        if a.reuse_providers:
            actual_source=a.reuse_providers/label/'source'/key
            obj=a.reuse_providers/label/'ggml-vulkan.cpp.o'
            if actual_source.read_text()!=text or not obj.is_file():raise ValueError('Completed provider content differs from the new build')
            frozen +=[record(actual_source),record(obj),record(a.reuse_providers/f'{len(objects)}.private.log')]
        command,count=re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',lambda _: '-o '+subprocess.list2cmdline([str(obj)]),command)
        if count!=1:raise ValueError('One native Vulkan output required')
        command,count=re.subn(r'(?<=\s)-c\s+(?:"[^"]+"|\S+)',lambda _: '-c '+subprocess.list2cmdline([str(actual_source)]),command)
        if count!=1:raise ValueError('One native Vulkan source required')
        backend_commands.append(command);objects.append(obj)
        row.update(command=command,actual_source=record(actual_source));data['sources'][key]['patched_sha256']=record(source)['sha256']
        new_manifests.append((directory/'model-io.private.json',data,row,source))
    entry=Path(prior['additional_cache_layout']['actual_entry']['path']);main_src=a.out/'portable-kernel-entry.private.cpp';main_src.write_text(entry_source(entry.read_text()),newline='\n')
    jobs=[];extra_objects=[]
    for i,src in enumerate((main_src,ROOT/'native/app/portable_kernel_fixture.cpp')):
        c=prior['compile_commands'][0].copy();obj=a.out/f'app-{i}.o';c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        if '-MF'in c:c[c.index('-MF')+1]=str(a.out/f'app-{i}.private.d')
        c[1:1]=['-I',str(a.out)];c+=['-I',str(entry.parent)]
        jobs.append(c);extra_objects.append(obj)
    oldmain=prior['compile_commands'][0][prior['compile_commands'][0].index('-o')+1]
    oldbackend=prior['lossless_shader_storage']['vulkan_object']['path']
    if prior['link_command'].count(oldmain)!=1 or prior['link_command'].count(oldbackend)!=1:raise ValueError('Unique actual entry and provider replacement required')
    link=[str(extra_objects[0])if x==oldmain else str(objects[1])if x==oldbackend else x for x in prior['link_command']]
    link.insert(link.index(str(extra_objects[0])),str(extra_objects[1]));image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,Path(__file__),ROOT/'native/app/portable_kernel_fixture.cpp',ROOT/'native/app/portable_kernel_fixture.h',entry,main_src,*(x[3]for x in new_manifests))]
    for i,c in enumerate(backend_commands+jobs+[link]):
        if i<2 and a.reuse_providers:
            print(json.dumps(dict(completed_provider_reused=i,source_hash_exact=True)),flush=True);continue
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(portable_kernel_build_step=i+1,total=5)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen portable fixture dependency changed')
    for i,(path,data,row,source)in enumerate(new_manifests):row['object']=record(objects[i]);write(path,data);validate_overrides(path,prior['engine_receipt']['path'])
    parent_row,extended_row=[record(x[0])for x in new_manifests]
    replace={embedded['parent_model_io']['path']:parent_row,embedded['extended_model_io']['path']:extended_row,oldbackend:record(objects[1])}
    def updated(rows):return [replace.get(r['path'],r)for r in rows]
    embedded=copy.deepcopy(embedded);embedded.update(parent_model_io=parent_row,extended_model_io=extended_row,vulkan_object=record(objects[1]),inputs=updated(embedded['inputs'])+[record(x[3])for x in new_manifests]+[record(x)for x in objects])
    embedded_row=write(a.out/'embedded-shader.private.json',embedded);replace[external['embedded_control']['path']]=embedded_row
    external=copy.deepcopy(external);external.update(parent_model_io=parent_row,extended_model_io=extended_row,vulkan_object=record(objects[1]),embedded_control=embedded_row,inputs=updated(external['inputs'])+[record(x[3])for x in new_manifests]+[record(x)for x in objects])
    external_row=write(a.out/'external-shader.private.json',external)
    storage=validate_shader_resources(external_row['path'],extended_row['path'],prior['engine_receipt']['path'])
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=jobs,link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects+extra_objects]+[parent_row,extended_row,embedded_row,external_row],
        bounded_model_source_manifest=extended_row,bounded_model_source_overrides=json.loads(Path(extended_row['path']).read_text()),shader_resource_manifest=external_row,lossless_shader_storage=storage,
        portable_kernel_fixture=dict(scope=SCOPE,actual_entry=record(main_src),commands=backend_commands+jobs,original_shaders_preserved=True,actual_parent_and_extended_providers_compiled=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Portable fixture native audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(portable_kernel_native_build_complete=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
