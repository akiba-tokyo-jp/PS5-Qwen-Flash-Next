#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the exact compiled shader handoff overlay without console execution."""
from pathlib import Path
import argparse,json,os,subprocess,sys
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ('workspace','cache','shader-storage-manifest','native-build','out'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();C=a.cache;O=a.out;O.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(R/'tools'))
from shader_storage import record
m=json.loads(a.shader_storage_manifest.read_text())
h=a.workspace/'toolchain/msys-clang64/clang64/bin';engine=C/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
overlay=a.native_build/'shader-integrity-overlay'
native_receipt=json.loads((a.native_build/'receipt.private.json').read_text())
handoff=native_receipt['resident_shader_integrity_handoff']
if not handoff or not handoff['class_definition_header_byte_identical']:
 raise ValueError('The recorded native two-object overlay is required')
for row in handoff['inputs']+[r['object']for r in handoff['replacements']]:
 if record(row['path'])!=row:raise ValueError('Recorded native shader overlay input changed')
for key in ('pool','assembly','registry'):
 if record(m[key]['path'])!=m[key]:raise ValueError('Exact original shader fixture input changed')
for name in ('shader_file.h','shader_file_native.h'):
 if (overlay/name).read_bytes()!=(R/'native/app'/name).read_bytes():raise ValueError('Shader class definitions must remain byte-identical')
sample=next(x for x in m['shaders'] if x.get('encoding')=='prefix16_delta_columns')
defines={'QWEN_EXPECTED_SHADER_COUNT':m['shader_count'],'QWEN_EXPECTED_LOOKUP_COUNT':m['lookup_entries'],
 'QWEN_EXPECTED_STORED_BYTES':m['stored_bytes'],'QWEN_EXPECTED_OUTPUT_BYTES':m['maximum_shader_bytes'],
 'QWEN_EXPECTED_ORDERING_BYTES':m['maximum_ordering_buffer_bytes'],'QWEN_EXPECTED_SHADER_REGISTRY':json.dumps(m['registry_sha256']),
 'QWEN_CODEC_SAMPLE_DATA':sample['name']+'_data','QWEN_CODEC_SAMPLE_SIZE':sample['storage_bytes'],
 'QWEN_EXPECTED_FILE_SHA256':json.dumps(m['pool']['sha256']),'QWEN_EXPECTED_FILE_BYTES':m['stored_bytes'],
 'QWEN_EXPECTED_FILE_WINDOW':m['external_file_input_window_bytes']}
(O/'shader_codec_sample.h').write_text(''.join('#define '+k+' '+str(v)+'\n' for k,v in defines.items())+
 'struct qwen_bad_shader_frame {const char *mode;const unsigned char *data;size_t bytes;};\nstatic const qwen_bad_shader_frame bad_shader_frames[]={{"unused",nullptr,0}};\n')
src=(R/'tests/shader_assets.cpp').read_text().replace('const std::string mode=argv[1];',
 'const std::string selected=argv[1];const bool delegated=selected.rfind("delegate_",0)==0;const std::string mode=delegated?selected.substr(9):selected;')
src='#include <array>\n#include <cstdint>\nextern "C" void qwen_app_bind_same_launch_shader_integrity(const std::uint64_t*,std::uint64_t,const unsigned char*);\n'+src
anchor='    try{\n        if(external&&mode!="file_unverified")'
addition='''    try{
        if(delegated) {
            std::array<std::uint64_t,10> id{99,1,0100600,1,1,QWEN_EXPECTED_FILE_BYTES,11,0,11,0};
            std::array<unsigned char,32> digest{};const std::string sha=QWEN_EXPECTED_FILE_SHA256;
            for(unsigned i=0;i<32;++i)digest[i]=static_cast<unsigned char>(std::stoul(sha.substr(2*i,2),nullptr,16));
            if(mode=="bad_sha")digest[0]^=1;
            if(mode=="bad_identity")++id[1];
            qwen_app_bind_same_launch_shader_integrity(id.data(),QWEN_EXPECTED_FILE_BYTES,digest.data());
            if(mode=="duplicate_binding")qwen_app_bind_same_launch_shader_integrity(id.data(),QWEN_EXPECTED_FILE_BYTES,digest.data());
        }
        if(external&&mode!="file_unverified")'''
assert src.count(anchor)==1;src=src.replace(anchor,addition)
anchor='    const bool file_refusal='
addition='''    if(delegated&&(mode=="bad_sha"||mode=="bad_identity"||mode=="duplicate_binding")) {
        check(rejected&&shader_file_fixture_calls()==0,"Invalid delegated integrity was accepted or read payload");
        std::cout<<selected<<" rejected before payload IO\\n";return 0;
    }
    if(delegated)check(shader_file_fixture_calls()==0,"Delegated startup repeated the full payload scan");
'''
assert src.count(anchor)==1;src=src.replace(anchor,addition+anchor)
(O/'shader_assets_handoff.cpp').write_text(src)
receipt={'state':'running','console_requests':0,'GPU_calls':0,'steps':[], 'overlay':[record(overlay/x) for x in ('shader_file.cpp','shader_file_session.cpp','shader_file.h','shader_file_native.h')]}
env=dict(os.environ,PATH=str(h)+os.pathsep+os.environ.get('PATH',''))
def run(label,cmd):
 p=subprocess.run(list(map(str,cmd)),cwd=R,env=env,capture_output=True,timeout=180)
 (O/(label+'.private.log')).write_bytes(p.stdout+p.stderr);receipt['steps'].append({'name':label,'returncode':p.returncode})
 if p.returncode:raise RuntimeError((p.stdout+p.stderr).decode(errors='replace')[-3000:])
 print(label+' passed',flush=True)
try:
 run('assembly',[h/'clang++.exe','-c',m['assembly']['path'],'-o',O/'storage.o'])
 run('registry',[h/'clang++.exe','-std=c++17','-O2','-I',R/'native/app','-I',C/'build/llama-ps5/ggml/src/ggml-vulkan','-c',m['registry']['path'],'-o',O/'registry.o'])
 run('compile',[h/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',R/'tests/shader_codec_stubs','-I',R/'tests','-I',R/'native/app','-I',O,
  '-I',C/'build/llama-ps5/ggml/src/ggml-vulkan','-I',engine/'vendor','-I',engine/'vendor/hash',O/'shader_assets_handoff.cpp',R/'tests/shader_file_fixture.cpp',
  R/'native/app/shader_assets.cpp',overlay/'shader_file.cpp',overlay/'shader_file_session.cpp',R/'native/app/sha256_backend.cpp',O/'storage.o',O/'registry.o','-L',h.parent/'lib','-lz','-o',O/'check.exe'])
 for mode in ('on_demand','delegate_normal','delegate_bad_sha','delegate_bad_identity','delegate_duplicate_binding','delegate_file_changed_identity','delegate_file_frame_checksum'):
  run(mode,[O/'check.exe',mode,m['pool']['path']])
 receipt.update(state='passed',original_SPIRV_assets=m['shader_count'],lookup_entries=m['lookup_entries'],delegated_startup_payload_reads=0)
finally:(O/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
