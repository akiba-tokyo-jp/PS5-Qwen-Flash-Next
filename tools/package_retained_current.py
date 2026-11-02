#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package a retained-input relink with the exact qualified native formatter."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct

from build_performance_quantizer import record
from driver_table_storage import audit_converted_storage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','relink','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--formatter-from',type=Path,help='Reuse a verified formatter from a completed retained package')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    package=load(args.current/'provenance/receipt.private.json')
    prior=load(args.current/'provenance/native-link.receipt.private.json')
    relink=load(args.relink);image=Path(relink['artifact']['path'])
    if record(image)!=relink['artifact']:raise ValueError('Relinked image changed')
    actual_sources=[];source_dir=args.workspace/'driver-work/PS5-Vulkan-Inference/tooling/native'
    for row in package['format_tool_sources']:
        path=source_dir/Path(row['path']).name;value=record(path)
        if value['bytes']!=row['bytes'] or value['sha256']!=row['sha256']:
            raise ValueError('Preferred driver source does not match the qualified formatter: '+path.name)
        actual_sources.append(value)
    sources=[source_dir/Path(s).name for s in package['format_tool_compile'] if str(s).endswith('.cpp')]
    host=args.workspace/'toolchain/msys-clang64/clang64/bin';tool=args.out/'ps5-native-tool.exe'
    command=[str(host/'clang++.exe'),'-std=c++20','-O2',*map(str,sources),'-lz','-o',str(tool)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out),TEMP=str(args.out))
    jobs=[('compile_formatter',command)]
    if args.formatter_from:
        control=load(args.formatter_from)
        if record(control['formatter']['path'])!=control['formatter'] or control['preferred_formatter_sources']!=actual_sources:
            raise ValueError('Completed formatter binary or source differs')
        tool=Path(control['formatter']['path']);jobs=[]
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    mapping={r['original_path']:r for r in retained}
    stubs=args.out/'stubs';stubs.mkdir();imports=[]
    used_CPU_stubs={r['sha256'] for r in relink.get('inputs_before',[]) if r['path'].endswith('.so')}
    for row in prior['inputs_before']:
        if row['path'].endswith('.so') and not Path(row['path']).name.endswith('_stub_weak.so'):
            if relink.get('CPU_only') and row['sha256'] not in used_CPU_stubs:continue
            existing=mapping.get(row['path'],row);checked=record(existing['path'])
            if checked['sha256']!=row['sha256'] or checked['bytes']!=row['bytes']:
                raise ValueError('Original import stub changed')
            target=stubs/Path(row['path']).name
            if not target.exists():shutil.copyfile(existing['path'],target)
            if record(target)['sha256']!=row['sha256']:raise ValueError('Import stub snapshot differs')
            if target not in imports:imports.append(target)
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    stripped=args.out/'application.pie.elf';converted=args.out/'eboot.elf';executable=args.out/'eboot.bin';roundtrip=args.out/'roundtrip.elf'
    jobs += [('strip',[str(llvm/'llvm-objcopy.exe'),'--strip-debug',str(image),str(stripped)]),
             ('convert',[str(tool),'link','--in',str(stripped),'--out',str(converted),
                         *[v for p in imports for v in ('--stub',str(p))]]),
             ('self',[str(tool),'self','--sign','--in',str(converted),'--out',str(executable)]),
             ('inspect',[str(tool),'self','--inspect','--file',str(executable)]),
             ('extract',[str(tool),'self','--extract','--file',str(executable),'--out',str(roundtrip)])]
    for name,job in jobs:
        result=subprocess.run(job,capture_output=True,timeout=180,env=env)
        (args.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    expected=bytearray(converted.read_bytes());expected[18:20]=struct.pack('<H',0x3e)
    if expected[7] in (0,3):expected[7]=9
    if struct.unpack_from('<H',expected,16)[0]==0:struct.pack_into('<H',expected,16,2)
    recovered=roundtrip.read_bytes();phoff=struct.unpack_from('<Q',expected,32)[0]
    stride,count=struct.unpack_from('<HH',expected,54)
    if recovered[:phoff+stride*count]!=expected[:phoff+stride*count]:raise ValueError('Normalized SELF roundtrip header differs')
    checked=0
    for i in range(count):
        kind,_,offset,_,_,size=struct.unpack_from('<IIQQQQ',expected,phoff+i*stride)
        if kind not in (1,2,0x61000000) or not size:continue
        if recovered[offset:offset+size]!=expected[offset:offset+size]:raise ValueError('SELF roundtrip segment differs')
        checked+=1
    if b'integrity: valid' not in (args.out/'inspect.private.log').read_bytes():raise ValueError('SELF integrity inspection failed')
    geometry=None if relink.get('CPU_only') else audit_converted_storage(image,converted,prior['lossless_driver_tables'])
    self_record=record(executable)
    if relink.get('CPU_only') and self_record['bytes']>4<<20:raise ValueError('CPU-only SELF exceeds its independent bound')
    if relink['baseline_relink'] and self_record['sha256']!=package['SELF']['sha256']:
        raise ValueError('Baseline SELF is not byte-identical to the deployed current program')
    report=dict(completed=True,relink=record(args.relink),SELF=self_record,
                exact_current_SELF_reproduced=relink['baseline_relink'],normalized_SELF_roundtrip_equal=True,
                roundtrip_segments_verified=checked,
                CPU_only=relink.get('CPU_only',False),driver_code_linked=not relink.get('CPU_only',False),
                preferred_formatter_sources=actual_sources,formatter=record(tool),commands=jobs,
                driver_table_geometry=geometry,driver_revision=relink['driver_revision'],driver_profile=relink['driver_profile'],
                persistent_caches=False,PS5_operations=0,native_quality_or_speed_measured=False,production_adopted=False)
    (args.out/'result.private.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('relink','SELF','preferred_formatter_sources','formatter','commands','driver_table_geometry')}))


if __name__=='__main__':main()
