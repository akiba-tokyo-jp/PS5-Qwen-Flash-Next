#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove unused SPIR-V declarations without changing executable instructions."""
import argparse
import copy
from pathlib import Path
import struct
import subprocess
from build_performance_quantizer import record
from start_success_route import load,need,save


def executable_words(path):
    raw=Path(path).read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw);out=[];at=5
    while at<len(words):
        count,opcode=words[at]>>16,words[at]&65535
        need(count>0 and at+count<=len(words),'Complete SPIR-V instruction required')
        if opcode not in (10,17):out.extend(words[at:at+count])
        at+=count
    return words[:5],out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','shaders','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--remove-unused-storage8',action='store_true')
    p.add_argument('--new-generic-resources-only',action='store_true')
    a=p.parse_args();old=load(a.shaders);need(old['completed'],'A complete validated shader set is required')
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin';commands=[]
    result=copy.deepcopy(old)
    for row in result['shaders']:
        if a.new_generic_resources_only:
            need(old.get('generic_indexed_refinement') and old['reused_shader_resources']==13,
                 'Only the separately qualified thirteen-resource prefix may be reused')
            if row['name'] not in ('matmul_id_quant_f32_fp32','matmul_id_subgroup_quant_f32_fp32'):
                continue
        source=row['artifact'];need(record(source['path'])==source,'The original shader changed')
        target=a.out/(row['name']+'.spv')
        trimmed=target.with_suffix('.trim.spv') if a.remove_unused_storage8 else target
        jobs=[('trim',[str(host/'spirv-opt.exe'),'--trim-capabilities',source['path'],'-o',str(trimmed)])]
        for label,job in jobs:
            commands.append(job);r=subprocess.run(job,capture_output=True,timeout=30)
            (a.out/(row['name']+'-'+label+'.private.log')).write_bytes(r.stdout+r.stderr)
            need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-2000:])
        if a.remove_unused_storage8:
            raw=trimmed.read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw);rewritten=list(words[:5]);at=5
            while at<len(words):
                count,opcode=words[at]>>16,words[at]&65535
                # SPIR-V StorageBuffer8BitAccess is4448. The validator below
                # must accept its absence; a genuinely required capability refuses.
                if not(opcode==17 and count==2 and words[at+1]==4448):rewritten.extend(words[at:at+count])
                at+=count
            target.write_bytes(struct.pack('<'+'I'*len(rewritten),*rewritten))
        job=[str(host/'spirv-val.exe'),'--target-env','vulkan1.2',str(target)];commands.append(job)
        r=subprocess.run(job,capture_output=True,timeout=30);(a.out/(row['name']+'-validate.private.log')).write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-2000:])
        need(executable_words(source['path'])==executable_words(target),
             'Only capability/extension declarations may change; every other word and header must remain exact')
        row.update(original_SPIRV=source,artifact=record(target),all_non_declaration_words_byte_exact=True)
    result.update(ancestor=record(a.shaders),capability_trim_commands=commands,
        only_unused_capability_extension_declarations_changed=True,all_non_declaration_words_byte_exact=True,
        unused_storage8_absence_accepted_by_Vulkan_SPIRV_validator=a.remove_unused_storage8,
        software_model_shader_qualified=False,native_model_shader_qualified=False,PS5_operations=0)
    if a.new_generic_resources_only:
        result.update(ancestor=old['ancestor'],generic_untrimmed_build=record(a.shaders))
    save(a.out/'result.private.json',result);print(dict(completed=True,shaders=len(result['shaders']),all_executable_words_exact=True,PS5_operations=0))


if __name__=='__main__':main()
