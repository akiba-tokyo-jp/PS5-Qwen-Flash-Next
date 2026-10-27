#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package only the independently audited CPU shader title with the qualified format tool."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from build_preservation_integrity import record
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('workspace','cache','native','format-control','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--driver-table-fixture',action='store_true',help='Package only the separately audited minimal cold-table GPU fixture')
    a=p.parse_args();m=json.loads(a.native.read_text());control=json.loads(a.format_control.read_text())
    if a.driver_table_fixture:
        if(m.get('schema')!='ps5-qwen-driver-table-fixture-link-v1'or not m.get('native_dispatch_audit',{}).get('passed')or
           m.get('GPU_graphs')!=1 or m.get('model_loaded')is not False or not m.get('lossless_driver_tables')):
            raise ValueError('An exact audited standalone cold-table fixture is required')
        from driver_table_storage import audit_linked_storage
        if audit_linked_storage(m['artifact']['path'],m['lossless_driver_tables'])!=m.get('lossless_driver_table_geometry'):
            raise ValueError('Actual relocated driver-table destinations must pass before packaging')
    elif m.get('CPU_only')is not True or m.get('driver_code_linked')is not False or m.get('model_engine_linked')is not False:
        raise ValueError('Independent CPU-only build required')
    for row in m['inputs_before']+[m['artifact'],control['format_tool'],*control['format_tool_sources']]:
        if record(row['path'])!=row:raise ValueError('A qualified build/format input changed')
    imported=audit(a.workspace,a.cache,a.native.parent)
    if imported['missing']or imported!=m['real_module_import_audit']:raise ValueError('CPU import audit changed')
    a.out.mkdir(parents=True,exist_ok=False);llvm=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    tool=control['format_tool']['path'];image=m['artifact']['path'];pie=a.out/'application.pie.elf'
    converted,SELF,extracted=(a.out/name for name in ('eboot.elf','eboot.bin','roundtrip.elf'))
    providers=[r for r in m['inputs_before']if r['path'].endswith('.so')]
    if a.driver_table_fixture:providers=[r for r in providers if not Path(r['path']).name.endswith('_stub_weak.so')]
    if any(Path(r['path']).name.endswith('_stub_weak.so')for r in providers):raise ValueError('Weak module stubs are forbidden')
    commands=[('strip_debug',[str(llvm/'llvm-objcopy.exe'),'--strip-debug',image,str(pie)]),
        ('convert',[tool,'link','--in',str(pie),'--out',str(converted),*[v for r in providers for v in ('--stub',r['path'])]]),
        ('self',[tool,'self','--sign','--in',str(converted),'--out',str(SELF)]),
        ('inspect',[tool,'self','--inspect','--file',str(SELF)]),
        ('extract',[tool,'self','--extract','--file',str(SELF),'--out',str(extracted)])]
    fixed=[record(Path(__file__)),record(a.native),record(a.format_control),*providers,control['format_tool']]
    env=dict(os.environ,PATH=str(a.workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
    for name,cmd in commands:
        r=subprocess.run(cmd,capture_output=True,timeout=120,env=env);(a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode or(name=='inspect'and b'integrity: valid'not in r.stdout):raise RuntimeError(name+' failed: '+r.stderr.decode(errors='replace')[-1500:])
    expected=bytearray(converted.read_bytes());expected[18:20]=struct.pack('<H',0x3e)
    if expected[7]in (0,3):expected[7]=9
    if struct.unpack_from('<H',expected,16)[0]==0:struct.pack_into('<H',expected,16,2)
    recovered=extracted.read_bytes();phoff=struct.unpack_from('<Q',expected,32)[0];phsize,count=struct.unpack_from('<HH',expected,54)
    if recovered[:phoff+phsize*count]!=expected[:phoff+phsize*count]:raise ValueError('CPU SELF roundtrip header differs')
    segments=0
    for i in range(count):
        kind,_,offset,_,_,size=struct.unpack_from('<IIQQQQ',expected,phoff+i*phsize)
        if kind not in (1,2,0x61000000)or not size:continue
        if recovered[offset:offset+size]!=expected[offset:offset+size]:raise ValueError('CPU SELF segment differs')
        segments+=1
    maximum=24<<20 if a.driver_table_fixture else 4<<20
    if segments!=6 or SELF.stat().st_size>maximum:raise ValueError('Exact six-segment bounded SELF required')
    for row in fixed:
        if record(row['path'])!=row:raise ValueError('A frozen CPU packaging input changed')
    receipt=dict(schema='ps5-qwen-mini-shader-self-v1',SELF=record(SELF),native_pie=m['artifact'],converted_elf=record(converted),
        extracted_elf=record(extracted),native_link_receipt=record(a.native),format_tool=control['format_tool'],
        inputs=fixed,commands=commands,integrity_verified=True,roundtrip_segments_verified=segments,real_module_import_audit=imported,
        CPU_only=True,driver_code_linked=False,model_engine_linked=False,external_shader_file=control['external_shader_file'],
        current_run_all_asset_bootstrap=m.get('current_run_all_asset_bootstrap',False),
        CPU_bootstrap_policy_controls=m.get('CPU_bootstrap_policy_controls'),
        GPU_calls=0,PS5_operations=0,CI_runs=0,release_qualified=False,installed=False)
    if a.driver_table_fixture:
        receipt.update(schema='ps5-qwen-driver-table-fixture-self-v1',CPU_only=False,driver_code_linked=True,
            model_engine_linked=True,full_model_execution=False,linked_driver=m['linked_driver'],
            lossless_driver_tables=m['lossless_driver_tables'],native_dispatch_audit=m['native_dispatch_audit'])
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_SELF_packaged=True,bytes=receipt['SELF']['bytes'],sha256=receipt['SELF']['sha256'],roundtrip_segments=segments,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
