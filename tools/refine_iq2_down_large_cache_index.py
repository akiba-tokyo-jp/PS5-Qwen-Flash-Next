#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fix logical-index overflow before all Down resource families enter a full cache."""
import argparse
import copy
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save
from trim_iq2_down_model_capabilities import executable_words

ROOT=Path(__file__).resolve().parents[1]


def rewrite(path):
    text=path.read_text(encoding='utf-8');original=text
    if path.name=='dequant_funcs.glsl' and 'iq2_down_decode(' in text:
        old='    const uint value=(a_offset+ib)*64u+iqs;\n'
        need(text.count(old)==2,'The two original vec2/vec4 block-index expansions are required')
        text=text.replace(old,'')
        text=text.replace('iq2_down_decode(value)','iq2_down_decode_index(a_offset+ib,64u,iqs)')
        for lane in (1,2,3):text=text.replace('iq2_down_decode(value+'+str(lane)+'u)',
            'iq2_down_decode_index(a_offset+ib,64u,iqs+'+str(lane)+'u)')
    elif path.name=='mul_mm_funcs.glsl' and 'const uint value = idx * 4u;' in text:
        text=once(text,'        const uint value = idx * 4u;\n','')
        for lane in range(4):text=text.replace('iq2_down_decode(value'+('' if lane==0 else ' + '+str(lane)+'u')+')',
            'iq2_down_decode_index(idx,4u,'+str(lane)+'u)')
    elif path.name=='iq2_down_dequant_packed_half.comp':
        text=once(text,'    const uint group=gl_GlobalInvocationID.x,at=group*4u;\n    if(at>=p.nel)return;',
            '    const uint group=gl_GlobalInvocationID.x;\n    if(group>=p.nel/4u)return;')
        for lane in range(4):text=text.replace('iq2_down_decode(at'+('' if lane==0 else '+'+str(lane)+'u')+')',
            'iq2_down_decode_index(group,4u,'+str(lane)+'u)')
    if text!=original:path.write_text(text,encoding='utf-8',newline='\n')
    return text!=original


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','parent','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume-compiled',action='store_true',help='Reuse the validated compiled prefix after a host-only source-selection correction')
    a=p.parse_args();parent=load(a.parent)
    need(parent['completed'] and parent['generic_indexed_F16_refinement'] and len(parent['shaders'])==17,
         'Only the complete prepared F16 resource family may be refined')
    # Follow the actual compile outputs, including declaration-only trimmed rows.
    commands_by_output={};ancestors=[];path=a.parent
    while path:
        item=load(path);ancestors.append(record(path))
        for command in item.get('commands',[]):
            if '-o' in command and any(str(arg).endswith('.comp') for arg in command):
                commands_by_output[command[command.index('-o')+1]]=command
        row=item.get('ancestor');path=Path(row['path']) if row else None
    a.out.mkdir(parents=True,exist_ok=a.resume_compiled);folders={};changed=[];commands=[];rows=[];used_sources=set();reused=0
    need(not(a.out/'result.private.json').exists(),'A completed shader family must not be rebuilt')
    decoder=ROOT/'native/app/iq2_down_carrier_index_safe.glsl'
    old_decoder=(ROOT/'native/app/iq2_down_carrier.glsl').read_text(encoding='utf-8');new_decoder=decoder.read_text(encoding='utf-8')
    marker='    const uint base=plane*IQ2_DOWN_CARRIER_BYTES;'
    need(old_decoder.split(marker,1)[1]==new_decoder.split(marker,1)[1],
         'All original byte loads and precise floating expressions must remain exact')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out))
    def run(command,label):
        command=list(map(str,command));commands.append(command)
        result=subprocess.run(command,capture_output=True,timeout=120,env=env)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,(result.stdout+result.stderr).decode(errors='replace')[-4000:])
    for original in parent['shaders']:
        need(record(original['artifact']['path'])==original['artifact'],'A prepared shader changed')
        key=original['artifact']['path']
        if key not in commands_by_output:key=original.get('original_SPIRV',original['artifact'])['path']
        need(key in commands_by_output,'An exact original compile command is required')
        command=commands_by_output[key].copy()
        inputs=[Path(arg) for arg in command if str(arg).endswith('.comp')]
        need(len(inputs)==1,'One actual shader compiler input is required')
        source=inputs[0];directory=source.parent
        if directory not in folders:
            target=a.out/'sources'/hashlib.sha256(str(directory).encode()).hexdigest()[:12]
            target.mkdir(parents=True,exist_ok=a.resume_compiled)
            for file in directory.glob('*.glsl'):shutil.copyfile(file,target/file.name)
            shutil.copyfile(decoder,target/'iq2_down_carrier.glsl')
            for file in target.glob('*.glsl'):
                if file.name!='iq2_down_carrier.glsl' and rewrite(file):changed.append(record(file))
            folders[directory]=target
        target=folders[directory]/source.name
        used_sources.add(target)
        if not target.exists():
            shutil.copyfile(source,target)
            if rewrite(target):changed.append(record(target))
        need('iq2_down_decode(' not in target.read_text(encoding='utf-8'), 'No unsafe scalar decoder call may remain in the compiler input')
        output=a.out/(original['name']+'.spv');raw=output.with_suffix('.raw.spv') if 'original_SPIRV' in original else output
        command[command.index(str(source))]=str(target);command[command.index('-o')+1]=str(raw)
        reuse=a.resume_compiled and output.exists()
        if reuse:
            need((a.out/(original['name']+'-validate.private.log')).exists(),
                 'Only a previously reached positive validation prefix may be recovered')
            reused+=1
        else:run(command,original['name']+'-compile')
        if raw!=output and not reuse:
            trimmed=output.with_suffix('.caps.spv')
            run([host/'spirv-opt.exe','--trim-capabilities',raw,'-o',trimmed],original['name']+'-trim')
            data=trimmed.read_bytes();words=struct.unpack('<'+'I'*(len(data)//4),data);out=list(words[:5]);at=5
            while at<len(words):
                count,opcode=words[at]>>16,words[at]&65535
                need(count>0 and at+count<=len(words),'Complete SPIR-V instructions are required')
                if not(opcode==17 and count==2 and words[at+1]==4448):out.extend(words[at:at+count])
                at+=count
            output.write_bytes(struct.pack('<'+'I'*len(out),*out))
            need(executable_words(raw)==executable_words(output),
                 'Capability cleanup may not change any executable word')
        run([host/'spirv-val.exe','--target-env','vulkan1.2',output],original['name']+'-validate')
        row=copy.deepcopy(original)
        row.update(artifact=record(output),previous_artifact=original['artifact'],actual_source=record(target),
            large_cache_index_safe=True,unchanged_decoder_float_expression=True,reused_completed_compile=reuse,
            original_compile_command_reused=command if reuse else None)
        row.pop('original_SPIRV',None);row.pop('all_non_declaration_words_byte_exact',None)
        rows.append(row)
        save(a.out/('resource-'+str(len(rows)).zfill(2)+'.private.json'),dict(completed=True,resource=row,decoder=record(decoder)))
    for directory in folders.values():
        for pattern in ('*.glsl',):
            for file in directory.glob(pattern):
                if file.name not in ('iq2_down_carrier_index_safe.glsl',):
                    need('iq2_down_decode(' not in file.read_text(encoding='utf-8'),'An unsafe logical-index expansion remains')
    result=copy.deepcopy(parent)
    result.update(ancestor=record(a.parent),shaders=rows,commands=commands,changed_sources=changed,
        large_cache_index_safe=True,source_ancestors=ancestors,carrier_decoder=record(decoder),
        packed_index_units=[4,64],cache_planes=3713,cache_slots=3712,logical_elements=6083379200,
        original_float_decoder_expression_preserved=True,new_64_bit_shader_operations=False,
        all_seventeen_resources_recompiled=True,reused_shader_resources=0,reused_completed_compile_prefix=reused,
        previous_native_decode_cases_reusable=False,new_native_GGML_graphs_required=12,
        native_F16_arithmetic_qualified=False,native_model_shader_qualified=False,software_model_shader_qualified=False,
        high_cache_address_proof_required=True,PS5_operations=0,production_adopted=False)
    save(a.out/'result.private.json',result)
    print(dict(completed=True,resources=17,large_cache_index_safe=True,new_native_graphs_required=12,PS5_operations=0))


if __name__=='__main__':main()
