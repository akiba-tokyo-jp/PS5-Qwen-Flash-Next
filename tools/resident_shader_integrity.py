#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""App-only shader integrity handoff overlay; original sources/ABI stay intact."""
import json,os,subprocess
from pathlib import Path
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def build(parent,out):
    out=Path(out);out.mkdir()
    names=('shader_file.h','shader_file_native.h','shader_file.cpp','shader_file_session.cpp')
    originals={name:ROOT/'native/app'/name for name in names}
    for path in originals.values():
        expected=next(r for r in parent['inputs_before']+parent['application_sources']+parent['application_headers']if Path(r['path'])==path)
        if record(path)!=expected:raise ValueError('Original shader session input changed')
    (out/'shader_file.h').write_bytes(originals['shader_file.h'].read_bytes())
    (out/'shader_file_native.h').write_bytes(originals['shader_file_native.h'].read_bytes())
    file_source=originals['shader_file.cpp'].read_text()
    declaration='extern "C" bool qwen_app_try_same_launch_shader_integrity(std::uint64_t,const unsigned char*,const std::uint64_t*);\n'
    file_source=file_source.replace('#include "shader_file.h"','#include "shader_file.h"\n'+declaration,1)
    anchor='unchanged();sha256_t hash;sha256_init(&hash);'
    if file_source.count(anchor)!=1:raise ValueError('Unique original shader file SHA verification boundary required')
    file_source=file_source.replace(anchor,'''unchanged();
        if(qwen_app_try_same_launch_shader_integrity(file_bytes_,expected.data(),sealed_.data())) {
            unchanged();stats_.verified=true;return;
        }
        sha256_t hash;sha256_init(&hash);''')
    (out/'shader_file.cpp').write_text(file_source,newline='\n')
    session=originals['shader_file_session.cpp'].read_text()
    anchor='TrackedOps source;';assert session.count(anchor)==1
    session=session.replace(anchor,anchor+'''
bool resident_integrity_ready=false;
std::array<std::uint64_t,10> resident_shader_identity{};
std::thread::id resident_integrity_owner;
''')
    session='#include <algorithm>\n#include <thread>\n'+session
    anchor='namespace qwen_app {\nbool native_shader_file_registered()'
    if session.count(anchor)!=1:raise ValueError('Unique original shader session boundary required')
    setter='''extern "C" void qwen_app_bind_same_launch_shader_integrity(const std::uint64_t *identity,
        std::uint64_t bytes,const unsigned char *sha) {
    if(!identity||!sha||resident_integrity_ready||started.load()||failed.load()||registration_fault.load()||
       !plan||bytes!=plan->bytes||identity[5]!=bytes||!identity[0]||!identity[1]||std::memcmp(sha,plan->sha256,32))
        throw std::runtime_error("Same-launch shader integrity differs from the compiled resource plan");
    std::copy(identity,identity+10,resident_shader_identity.begin());
    resident_integrity_owner=std::this_thread::get_id();resident_integrity_ready=true;
}
extern "C" bool qwen_app_try_same_launch_shader_integrity(std::uint64_t bytes,
        const unsigned char *sha,const std::uint64_t *identity) {
    if(!resident_integrity_ready)return false;
    if(!identity||!sha||!started.load()||!plan||failed.load()||registration_fault.load()||
       resident_integrity_owner!=std::this_thread::get_id()||bytes!=plan->bytes||std::memcmp(sha,plan->sha256,32)||
       !identity[0]||!resident_shader_identity[0])
        throw std::runtime_error("Fresh original shader integrity producer required");
    for(unsigned i=1;i<10;++i)if(identity[i]!=resident_shader_identity[i])
        throw std::runtime_error("Same-launch shader descriptor identity differs");
    return true;
}
'''
    session=session.replace(anchor,setter+'\n'+anchor)
    (out/'shader_file_session.cpp').write_text(session,newline='\n')
    frozen=[record(path)for path in [Path(__file__),*originals.values(),*[out/name for name in names]]]
    replacements=[]
    for name in ('shader_file.cpp','shader_file_session.cpp'):
        prefix=name.removesuffix('.cpp')+'-'
        candidates=[Path(x)for x in parent['link_command']if Path(x).name.startswith(prefix)and x.endswith('.o')]
        if len(candidates)!=1:raise ValueError('One actual original shader object required: '+name)
        old=candidates[0];origin=old.parent.parent/'receipt.private.json';recipes=json.loads(origin.read_text())
        command=next(c.copy()for c in recipes['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name==name)
        compile_origin=Path(command[command.index('-o')+1])
        if record(compile_origin)['sha256']!=record(old)['sha256']:
            raise ValueError('Original compile recipe object is not the byte-identical linked object')
        generated=out/name;object_path=out/(name+'.o')
        command[command.index('-c')+1]=str(generated);command[command.index('-o')+1]=str(object_path)
        command+=['-I',str(ROOT/'native/app')]
        frozen += [record(origin),record(compile_origin)]
        result=subprocess.run(command,capture_output=True,timeout=120,
            env=dict(os.environ,TMP=str(out.parent/'tmp'),TEMP=str(out.parent/'tmp')))
        (out/(name+'.compile.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-3000:])
        replacements.append(dict(original_object=record(old),object=record(object_path),command=command,
            original_compile_object=record(compile_origin),original_recipe=record(origin)))
    if frozen!=[record(r['path'])for r in frozen]:raise ValueError('Shader handoff overlay input changed')
    return dict(replacements=replacements,inputs=frozen,
        class_definition_header_byte_identical=True,class_fields_and_virtual_layout_unchanged=True,
        per_use_frame_read_and_original_SPIRV_SHA256_code_unchanged=True,
        original_application_sources_unmodified=True,production_default_changed=False)
