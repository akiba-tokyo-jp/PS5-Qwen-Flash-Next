#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check each distinct new generic binary against the existing wide F64 operands."""
import argparse
import os
from pathlib import Path
import subprocess
import struct
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'build', 'prior-software', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--resume-preparation',action='store_true')
    a = p.parse_args()
    built, prior = load(a.build), load(a.prior_software)
    need(built['generic_indexed_refinement'] and built['completed'] and
         prior['completed'] and prior['build'] == built['ancestor'], 'The exact completed thirteen-resource parent is required')
    old_plan = load(prior['plan']['path'])
    component = load(prior['component']['path'])
    cases = [c for c in load(component['GPU_cases']['path'])['cases'] if c['width'] in (30, 32)]
    need(len(cases) == 6, 'Three layers and both distinct wide shapes are required')
    new = [r for r in built['shaders'] if r['name'].startswith(('matmul_id_quant_', 'matmul_id_subgroup_quant_'))]
    unique = {}
    for row in new:
        need(record(row['artifact']['path']) == row['artifact'], 'A new generic binary changed')
        unique.setdefault(row['artifact']['sha256'], dict(row, indexed=True, half_input=False))
    need(len(new) == 2, 'Both new resource references are required')
    if a.resume_preparation:
        need(a.out.is_dir() and not any((a.out/n).exists() for n in
             ('plan.private.json','generic-software.exe','native.private.json','compile.private.log')),
             'Only pre-compilation software preparation with zero submitted GPU work may resume')
    else:
        a.out.mkdir(parents=True, exist_ok=False)
    host = a.workspace/'toolchain/msys-clang64/clang64/bin'
    specialized=[]
    for row in unique.values():
        target=a.out/(row['name']+'-Q2-only.spv')
        constants=' '.join(str(i)+':'+str(v) for i,v in enumerate([64,64,32,32,32,32,2,4,2,1,32,0,42]))
        command=[str(host/'spirv-opt.exe'),'--set-spec-const-default-value',constants,
            '--freeze-spec-const','--fold-spec-const-op-composite','-O',
            '--remove-unused-interface-variables','--eliminate-dead-variables','--trim-capabilities',
            row['artifact']['path'],'-o',str(target)]
        r=subprocess.run(command,capture_output=True,timeout=120)
        need(r.returncode==0,r.stderr.decode(errors='replace'))
        raw=target.read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw)
        rewritten=list(words[:5]);at=5
        while at<len(words):
            count,opcode=words[at]>>16,words[at]&65535
            # The validator must independently admit the absence of unused
            # Int8 and StorageBuffer8BitAccess after Q2 constant folding.
            if not(opcode==17 and count==2 and words[at+1] in (39,4448)):
                rewritten.extend(words[at:at+count])
            at+=count
        target.write_bytes(struct.pack('<'+'I'*len(rewritten),*rewritten))
        r=subprocess.run([str(host/'spirv-val.exe'),'--target-env','vulkan1.2',str(target)],capture_output=True,timeout=30)
        need(r.returncode==0,r.stderr.decode(errors='replace'))
        assembly=subprocess.check_output([str(host/'spirv-dis.exe'),str(target),'--no-header'],text=True)
        caps=[line.split('OpCapability ',1)[1].strip() for line in assembly.splitlines() if 'OpCapability ' in line]
        need(caps==['Shader'],'Only the Q2 specialization with original packed row coordinates may use the software device')
        specialized.append(dict(row,original_artifact=row['artifact'],artifact=record(target),specialization_command=command))
    api_row = next(r for r in old_plan['inputs'] if Path(r['path']).name == 'model_shader_desktop_API.private.h')
    need(record(api_row['path']) == api_row, 'The qualified desktop owner implementation changed')
    api = Path(api_row['path']).read_text().replace('#define MODEL_STORAGE8_REQUIRED 1', '#define MODEL_STORAGE8_REQUIRED 0')
    api = api.replace('#define MODEL_STORAGE16_REQUIRED 1', '#define MODEL_STORAGE16_REQUIRED 0')
    (a.out/'model_shader_desktop_API.private.h').write_text(api, newline='\n')
    text = (ROOT/'tools/check_iq2_down_model_shader_gpu.cpp').read_text()
    text = once(text, 'const unsigned selected=c.at("selected"),values=selected*2560u;',
        'const unsigned selected=c.at("selected"),width=c.at("width"),values=width*selected*2560u;')
    text = once(text, 'c.at("width")==1&&selected==2', '(width==30||width==32)&&selected==10')
    text = once(text, 'inputs.size()==selected*640*4&&', 'inputs.size()==width*selected*640*4&&')
    text = once(text, 'ids.size()==selected*4&&', 'ids.size()==width*selected*4&&')
    text = once(text, 'std::vector<std::uint32_t>indices(selected);', 'std::vector<std::uint32_t>indices(width*selected);')
    text = once(text, 'std::vector<float>input(selected*640);', 'std::vector<float>input(width*selected*640);')
    text = once(text, '    auto packed=weights;', '''    need(indexed&&!half_input,"Only the observed indexed F32 generic path is admitted");
    std::vector<std::vector<std::uint32_t>>tiles;std::vector<unsigned>experts;
    for(unsigned expert=0;expert<10;++expert){std::vector<std::uint32_t>rows;
        for(unsigned token=0;token<width;++token)for(unsigned slot=0;slot<selected;++slot)
            if(indices[token*selected+slot]==expert)rows.push_back(slot|(token<<16));
        for(unsigned at=0;at<rows.size();at+=32){
            tiles.emplace_back(rows.begin()+at,rows.begin()+std::min<unsigned>(rows.size(),at+32));experts.push_back(expert);}}
    const unsigned row_offset=1+2*unsigned(tiles.size());
    std::vector<std::uint32_t>row_map(row_offset+tiles.size()*32,0);row_map[0]=tiles.size();
    for(unsigned i=0;i<tiles.size();++i){row_map[1+2*i]=experts[i];row_map[2+2*i]=tiles[i].size();
        std::copy(tiles[i].begin(),tiles[i].end(),row_map.begin()+row_offset+i*32);}
    auto packed=weights;''')
    text = once(text, 'allocate(a,output.size()*4,output.data()),allocate(a,4,&zero),allocate(a,4,&zero),allocate(a,ids.size(),ids.data())',
        'allocate(a,output.size()*4,output.data()),allocate(a,ids.size(),ids.data()),allocate(a,row_map.size()*4,row_map.data())')
    text = text.replace('    const float zero=0;', '    ')
    begin = text.index('    std::array<std::uint32_t,13>push')
    end = text.index('    VkCommandPoolCreateInfo', begin)
    text = text[:begin] + '''    std::array<std::uint32_t,15>push{2560,width,640,640,640,2560,
        1638400,selected*640,selected*2560,selected,width,selected*4,selected,10,row_offset};
    const unsigned push_bytes=60;
''' + text[end:]
    text = once(text, 'for(unsigned row:{0u,1248u,2496u})a.vkCmdDispatchBase(command,row,0,0,64,selected,1);',
        'for(unsigned tile:{0u,19u,39u})a.vkCmdDispatchBase(command,tile,0,0,1,unsigned(tiles.size()),1);')
    text = once(text, '(row>=1248&&row<1312)', '(row>=1216&&row<1280)')
    text = text.replace('bindings[6]', 'bindings[5]').replace('i<6;++i', 'i<5;++i').replace('BUFFER,6}', 'BUFFER,5}')
    text = text.replace('bi[6]', 'bi[5]').replace('writes[6]', 'writes[5]').replace('a.device,6,writes', 'a.device,5,writes')
    text = text.replace('di.bindingCount=6', 'di.bindingCount=5').replace('SHADER_STAGE_COMPUTE_BIT,0,52', 'SHADER_STAGE_COMPUTE_BIT,0,60')
    begin = text.index('        VkSpecializationMapEntry entries[]')
    end = text.index('VkComputePipelineCreateInfo pi{};', begin)
    text = text[:begin] + '''        VkSpecializationMapEntry entries[13]{};
        std::uint32_t constants[]={64,64,32,32,32,32,2,4,2,1,32,0,42};
        for(unsigned i=0;i<13;++i)entries[i]={i,i*4,4};
        VkSpecializationInfo special{13,entries,sizeof(constants),constants};''' + text[end:]
    source, exe = a.out/'generic.private.cpp', a.out/'generic-software.exe'
    source.write_text(text, newline='\n')
    manifest = a.out/'cases.private.json'
    save(manifest, dict(shaders=specialized, cases=cases))
    vendor = Path(prior['component']['path']).parents[2]/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor'
    command = [str(host/'clang++.exe'), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
        '-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(a.workspace/'toolchain/Vulkan-Headers/include'),
        '-I',str(vendor),str(source),'-o',str(exe)]
    env = dict(os.environ, PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out),VK_DRIVER_FILES=old_plan['software_ICD']['path'])
    r = subprocess.run(command,capture_output=True,timeout=120,env=env)
    (a.out/'compile.private.log').write_bytes(r.stdout+r.stderr)
    need(r.returncode==0,r.stderr.decode(errors='replace')[-5000:])
    save(a.out/'plan.private.json',dict(build=record(a.build),prior_software=record(a.prior_software),
        source=record(source),API=record(a.out/'model_shader_desktop_API.private.h'),executable=record(exe),
        manifest=record(manifest),command=command,software_ICD=old_plan['software_ICD'],unique_shader_binaries=len(unique),PS5_operations=0))
    r = subprocess.run([str(exe),str(manifest),str(a.out/'native.private.json')],capture_output=True,env=env)
    (a.out/'run.private.log').write_bytes(r.stdout+r.stderr)
    need((a.out/'native.private.json').exists(),r.stderr.decode(errors='replace')[-4000:])
    native=load(a.out/'native.private.json')
    save(a.out/'result.private.json',dict(completed=r.returncode==0 and native['completed'],build=record(a.build),
        native=record(a.out/'native.private.json'),plan=record(a.out/'plan.private.json'),
        unique_shader_binaries=len(unique),qualified_resource_names=[r['name'] for r in new],
        distinct_cases=len(native['cases']),all_outputs_passed=all(r['passed'] for r in native['cases']),
        all_GPU_resources_positively_retired=native.get('all_GPU_resources_positively_retired',False),
        Q2_specialization_of_actual_new_SPIRV=True,original_other_type_branches_not_executed=True,
        software_SPIRV_reference=True,physical_GPU_execution=False,PS5_operations=0))
    need(r.returncode==0,r.stderr.decode(errors='replace')[-4000:])
    print(dict(completed=True,unique_binaries=len(unique),distinct_cases=len(native['cases']),PS5_operations=0))


if __name__ == '__main__':
    main()
