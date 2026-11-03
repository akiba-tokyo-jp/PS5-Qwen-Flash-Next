#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual model matvec resources against the existing paired references."""
import argparse
import os
from pathlib import Path
import subprocess
import time
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','shaders','component','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--software-ICD',type=Path,required=True)
    p.add_argument('--reuse-compiled-plan',type=Path)
    p.add_argument('--F32-input-only',action='store_true')
    p.add_argument('--completed-software-result',type=Path)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    build,component=load(a.shaders),load(a.component)
    need(build['completed'] and build['all_Q2_0_tensors_must_be_IQ2_carriers'] and component['completed'] and
         component['paired_down_carrier'] and record(component['GPU_cases']['path'])==component['GPU_cases'],
         'Actual compiled model resources and existing inverse-qualified carrier operands required')
    cases=[x for x in load(component['GPU_cases']['path'])['cases'] if x['width']==1]
    need(len(cases)==3 and {x['layer'] for x in cases}=={0,23,47},'All three original width-one references required')
    shaders=[]
    for row in build['shaders']:
        if not row['name'].startswith('mul_mat_vec_'):continue
        if a.F32_input_only and row['recipe']['defines']['B_TYPE']!='float':continue
        need(record(row['artifact']['path'])==row['artifact'],'The actual model SPIR-V changed')
        shaders.append(dict(row,indexed='_id_' in row['name'],half_input=row['recipe']['defines']['B_TYPE']=='float16_t'))
    need(len(shaders)==(6 if a.F32_input_only else 9),'The exact selected float model matvec variants are required')
    qualified_shader_count=len(shaders);reused_cases=[];completed_prefix=None
    if a.completed_software_result:
        previous=load(a.completed_software_result);old_root=a.completed_software_result.parent
        old_plan=load(old_root/'plan.private.json');old_manifest=load(old_plan['manifest']['path'])
        saved=load(old_root/'source-preserved-before-ABI-refinement.private.json')
        need(not previous['completed'] and not previous.get('unknown_completion') and
             record(old_plan['executable']['path'])==old_plan['executable'] and
             record(old_plan['manifest']['path'])==old_plan['manifest'] and
             old_plan['inputs'][:2]==[record(a.shaders),record(a.component)] and
             old_manifest==dict(shaders=shaders,cases=cases) and
             record(saved['snapshot']['path'])==saved['snapshot'] and
             all(saved['original'][k]==saved['snapshot'][k] for k in ('bytes','sha256')),
             'Exact returned prefix operands, executable and preserved source required')
        old_source=Path(saved['snapshot']['path']).read_text();new_source=(ROOT/'tools/check_iq2_down_model_shader_gpu.cpp').read_text()
        loop='    for(const auto&shader:manifest.at("shaders"))'
        old_line='        VkSpecializationMapEntry entries[]={{0,0,4},{1,4,4},{2,8,4}};std::uint32_t constants[]={32,1,1};'
        new_lines='''        VkSpecializationMapEntry entries[]={{0,0,4},{1,4,4},{2,8,4}};
        const bool no_shared=shader.at("name").get<std::string>().find("_no_shmem")!=std::string::npos;
        std::uint32_t constants[]={no_shared?subgroup.subgroupSize:32u,1,1};'''
        need(old_source.split('int main(')[0]==new_source.split('int main(')[0] and
             old_source[old_source.index(loop):].replace(old_line,new_lines)==new_source[new_source.index(loop):],
             'Only actual subgroup discovery and no-shared specialization may change the completed fixture')
        skip=[]
        for shader in shaders:
            rows=[x for x in previous['cases'] if x['shader']==shader['name']]
            if len(rows)!=3 or not all(x['passed'] and x['positive_fence'] and x['all_case_resources_retired'] for x in rows):break
            need('_no_shmem' not in shader['name'] and {x['layer'] for x in rows}=={0,23,47},
                 'Only the unchanged fixed32-lane completed prefix may be reused')
            skip.append(shader['name']);reused_cases.extend(rows)
        need(skip,'A nonempty positively completed prefix is required')
        shaders=[x for x in shaders if x['name'] not in skip];completed_prefix=record(a.completed_software_result)
    disassembler=a.workspace/'toolchain/msys-clang64/clang64/bin/spirv-dis.exe'
    capabilities=set()
    for row in shaders:
        decoded=subprocess.check_output([str(disassembler),row['artifact']['path'],'--no-header'],text=True)
        capabilities.update(line.split('OpCapability ',1)[1].strip() for line in decoded.splitlines() if 'OpCapability ' in line)
    need(capabilities<={'Shader','StorageBuffer16BitAccess','StorageBuffer8BitAccess','GroupNonUniform','GroupNonUniformArithmetic'},
         'Only explicitly supported actual SPIR-V capabilities are admitted')
    need16='StorageBuffer16BitAccess' in capabilities;need8='StorageBuffer8BitAccess' in capabilities
    a.out.mkdir(parents=True,exist_ok=False)
    desktop=ROOT/'tools/check_iq2_paired_down_gpu.cpp';prefix=desktop.read_text().split('Json check(API&a,')[0]
    before='        VkDeviceCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;'
    after='''        const auto features=reinterpret_cast<PFN_vkGetPhysicalDeviceFeatures2>(get(instance,"vkGetPhysicalDeviceFeatures2"));
        need(features,"Vulkan feature query required");
        VkPhysicalDeviceVulkan12Features available12{};available12.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES;
        VkPhysicalDeviceVulkan11Features available11{};available11.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES;available11.pNext=&available12;
        VkPhysicalDeviceFeatures2 available{};available.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;available.pNext=&available11;
        features(physical,&available);
        std::cerr<<"software_storage16_available="<<available11.storageBuffer16BitAccess<<" storage8_available="<<available12.storageBuffer8BitAccess<<'\\n';
        need((!MODEL_STORAGE16_REQUIRED||available11.storageBuffer16BitAccess)&&(!MODEL_STORAGE8_REQUIRED||available12.storageBuffer8BitAccess),
            "The software device lacks the actual SPIR-V storage features");
        VkPhysicalDeviceVulkan12Features enabled12{};enabled12.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES;
        // These actual SPIR-V modules declare storage access, not Float16/Int8 arithmetic capabilities.
        enabled12.storageBuffer8BitAccess=MODEL_STORAGE8_REQUIRED?VK_TRUE:VK_FALSE;
        VkPhysicalDeviceVulkan11Features enabled11{};enabled11.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES;
        enabled11.storageBuffer16BitAccess=MODEL_STORAGE16_REQUIRED?VK_TRUE:VK_FALSE;enabled11.pNext=&enabled12;
        VkDeviceCreateInfo di{};di.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;di.pNext=&enabled11;di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;'''
    prefix='#define MODEL_STORAGE16_REQUIRED '+str(int(need16))+'\n#define MODEL_STORAGE8_REQUIRED '+str(int(need8))+'\n'+once(prefix,before,after)
    api=a.out/'model_shader_desktop_API.private.h';api.write_text(prefix,encoding='utf-8',newline='\n')
    manifest=a.out/'cases.private.json';save(manifest,dict(shaders=shaders,cases=cases))
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    executable=a.out/'model-shader-software.exe';project_source=ROOT/'tools/check_iq2_down_model_shader_gpu.cpp'
    source=a.out/'model_shader_fixture.private.cpp';source.write_bytes(project_source.read_bytes())
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),
        '-I',str(ROOT/'native/app'),'-I',str(a.workspace/'toolchain/Vulkan-Headers/include'),'-I',str(up/'vendor'),
        str(source),'-o',str(executable)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    configuration=load(a.software_ICD);library=(a.software_ICD.parent/configuration['ICD']['library_path']).resolve()
    need(a.software_ICD.name=='vk_swiftshader_icd.json' and library.name=='vk_swiftshader.dll' and
         library.is_relative_to(a.software_ICD.parent.resolve()),'The exact installed software-only ICD is required')
    env['VK_DRIVER_FILES']=str(a.software_ICD.resolve())
    inputs=[record(a.shaders),record(a.component),record(desktop),record(source),record(api),record(ROOT/'native/app/iq2_paired_down.h')]
    reused=None
    if a.reuse_compiled_plan:
        previous=load(a.reuse_compiled_plan);root=a.reuse_compiled_plan.parent
        need(previous['completed'] and record(previous['executable']['path'])==previous['executable'] and
             record(previous['manifest']['path'])==previous['manifest'] and
             (root/'software.private.log').read_text().strip()=='Desktop instance creation failed VkResult=-9' and
             not(root/'software.private.json').exists(),'Only the positively returned pre-instance backend refusal may reuse its build')
        need(all(record(x['path'])==x for x in previous['inputs']) and
             [(x['bytes'],x['sha256']) for x in inputs]==[(x['bytes'],x['sha256']) for x in previous['inputs']] and
             record(manifest)['sha256']==previous['manifest']['sha256'],'Only identical already compiled sources and operands may be reused')
        executable=Path(previous['executable']['path']);command=previous['command'];reused=record(a.reuse_compiled_plan)
        inputs=previous['inputs']
    else:
        r=subprocess.run(command,capture_output=True,timeout=90,env=env);(a.out/'compile.private.log').write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-3500:])
    inputs += [record(a.software_ICD),record(library)]
    save(a.out/'plan.private.json',dict(completed=True,inputs=inputs,manifest=record(manifest),executable=record(executable),
        command=command,expected_shader_cases=len(shaders)*3,distinct64_row_tiles=len(shaders)*9,all2560_rows_claimed=False,
        completed_software_prefix=completed_prefix,reused_positive_cases=len(reused_cases),
        actual_SPIRV_capabilities=sorted(capabilities),required_storage16=need16,required_storage8=need8,
        reused_compiled_plan=reused,software_ICD=record(a.software_ICD),
        F32_inputs_reuse_original_F64_references=True,F16_inputs_use_independent_CPU_decoder_and_rounded_inputs=True,
        PS5_operations=0))
    if not a.execute:return
    output=a.out/'software.private.json';job=[str(executable),str(manifest),str(output)]
    with (a.out/'software.private.log').open('xb') as stream:
        child=subprocess.Popen(job,stdout=stream,stderr=subprocess.STDOUT,env=env);notice=0
        while child.poll() is None:
            if time.monotonic()>=notice:print(dict(actual_model_shader_software_running=True,PS5_operations=0),flush=True);notice=time.monotonic()+30
            time.sleep(1)
    need(child.returncode==0,'Software model-shader check returned failure; inspect the saved log')
    result=load(output)
    need(result['completed'] and result['all_GPU_resources_positively_retired'] and len(result['cases'])==len(shaders)*3 and
         all(x['passed'] and x['positive_fence'] and x['all_case_resources_retired'] and x['distinct_row_tiles']==3 for x in result['cases']),
         'All actual model matvec cases must pass and retire positively')
    save(a.out/'result.private.json',dict(completed=True,build=record(a.shaders),component=record(a.component),
        plan=record(a.out/'plan.private.json'),native=record(output),actual_model_matvec_shaders=qualified_shader_count,shape_cases=qualified_shader_count*3,
        distinct64_row_tiles=qualified_shader_count*9,F32_input_only=a.F32_input_only,all_outputs_passed=True,all_GPU_resources_positively_retired=True,
        completed_software_prefix=completed_prefix,reused_positive_cases=reused_cases,new_positive_cases=len(result['cases']),
        software_SPIRV_reference=True,physical_GPU_execution=False,other_four_resource_families_qualified=False,
        descriptor_plane_origin_native_qualified=False,PS5_operations=0,native_model_quality_or_speed_qualified=False))
    print(dict(completed=True,actual_model_matvec_shaders=qualified_shader_count,shape_cases=qualified_shader_count*3,
        distinct_row_tiles=qualified_shader_count*9,reused_cases=len(reused_cases),PS5_operations=0))


if __name__=='__main__':main()
