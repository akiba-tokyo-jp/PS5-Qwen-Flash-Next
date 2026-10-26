#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package the separately audited weightless PLE title; never deploy or execute."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from build_preservation_integrity import record
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('workspace','cache','native','format-control','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.native.read_text());control=json.loads(a.format_control.read_text())
    if m.get('schema')!='ps5-qwen-isolated-PLE-build-v1'or m.get('link_returncode')!=0 or m.get('input_hashes_stable')is not True or m.get('model_loading_entry_points_absent')is not True or m.get('shared_shader_and_CPU_guards_extracted_verbatim')is not True:
        raise ValueError('Qualified independent PLE link required')
    if m['linked_driver']['archive_sha256']!='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925':
        raise ValueError('The unchanged qualified driver archive is required')
    dispatch=m['native_dispatch_audit']
    if dispatch.get('passed')is not True or dispatch.get('image_sha256')!=m['artifact']['sha256']or len(dispatch.get('required_physical_callbacks',[]))!=6:
        raise ValueError('Actual native dispatch table proof required')
    for row in m['inputs_before']+[m['artifact'],control['format_tool'],*control['format_tool_sources']]:
        if record(row['path'])!=row:raise ValueError('A qualified PLE build or format input changed')
    imported=audit(a.workspace,a.cache,a.native.parent)
    if imported['missing']or imported!=m['real_module_import_audit']:raise ValueError('Actual PLE import audit changed')
    a.out.mkdir(parents=True,exist_ok=False);llvm=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    tool=control['format_tool']['path'];image=m['artifact']['path'];pie=a.out/'application.pie.elf'
    converted,SELF,extracted=(a.out/name for name in('eboot.elf','eboot.bin','roundtrip.elf'))
    providers=[r for r in m['inputs_before']if r['path'].endswith('.so')and not Path(r['path']).name.endswith('_stub_weak.so')]
    commands=[('strip_debug',[str(llvm/'llvm-objcopy.exe'),'--strip-debug',image,str(pie)]),
        ('convert',[tool,'link','--in',str(pie),'--out',str(converted),*[v for r in providers for v in('--stub',r['path'])]]),
        ('self',[tool,'self','--sign','--in',str(converted),'--out',str(SELF)]),
        ('inspect',[tool,'self','--inspect','--file',str(SELF)]),
        ('extract',[tool,'self','--extract','--file',str(SELF),'--out',str(extracted)])]
    fixed=[record(Path(__file__)),record(a.native),record(a.format_control),*providers,control['format_tool']]
    env=dict(os.environ,PATH=str(a.workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
    for name,cmd in commands:
        r=subprocess.run(cmd,capture_output=True,timeout=120,env=env);(a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode or(name=='inspect'and b'integrity: valid'not in r.stdout):raise RuntimeError(name+' failed: '+r.stderr.decode(errors='replace')[-1800:])
    expected=bytearray(converted.read_bytes());expected[18:20]=struct.pack('<H',0x3e)
    if expected[7]in(0,3):expected[7]=9
    if struct.unpack_from('<H',expected,16)[0]==0:struct.pack_into('<H',expected,16,2)
    recovered=extracted.read_bytes();phoff=struct.unpack_from('<Q',expected,32)[0];phsize,count=struct.unpack_from('<HH',expected,54)
    if recovered[:phoff+phsize*count]!=expected[:phoff+phsize*count]:raise ValueError('Isolated PLE SELF header differs')
    segments=0
    for i in range(count):
        kind,_,offset,_,_,size=struct.unpack_from('<IIQQQQ',expected,phoff+i*phsize)
        if kind not in(1,2,0x61000000)or not size:continue
        if recovered[offset:offset+size]!=expected[offset:offset+size]:raise ValueError('Isolated PLE SELF segment differs')
        segments+=1
    if segments!=6 or SELF.stat().st_size>32<<20:raise ValueError('Exact six-segment bounded PLE SELF required')
    for row in fixed:
        if record(row['path'])!=row:raise ValueError('A frozen PLE packaging input changed')
    receipt=dict(schema='ps5-qwen-isolated-PLE-self-v1',SELF=record(SELF),native_pie=m['artifact'],converted_elf=record(converted),
        extracted_elf=record(extracted),native_link_receipt=record(a.native),format_tool=control['format_tool'],
        inputs=fixed,commands=commands,integrity_verified=True,roundtrip_segments_verified=segments,real_module_import_audit=imported,
        linked_driver=m['linked_driver'],native_dispatch_audit=dispatch,driver=m['driver'],model_loading_entry_points_absent=True,
        external_shader_file=control['external_shader_file'],PS5_operations=0,CI_runs=0,release_qualified=False,installed=False)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(isolated_PLE_SELF_packaged=True,bytes=SELF.stat().st_size,sha256=receipt['SELF']['sha256'],
        roundtrip_segments=segments,model_entry_points_absent=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
