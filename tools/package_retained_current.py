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


def audit_identity_provider(relink,provider_path):
    from native_dispatch import ELF
    provider=json.loads(Path(provider_path).read_text(encoding='utf-8-sig'))
    linked_inputs=relink['new_inputs']+relink.get('inputs',[])
    same_provider=any(all(row[k]==provider['artifact'][k] for k in ('bytes','sha256')) for row in linked_inputs)
    if not provider['completed'] or provider['executable_bytes'] or not same_provider or len(provider['inputs'])!=3:
        raise ValueError('Exact data-only identity provider must be part of the actual relink')
    if record(provider['artifact']['path'])!=provider['artifact']:raise ValueError('Identity provider changed')
    image=Path(relink['artifact']['path'])
    if record(image)!=relink['artifact']:raise ValueError('Relinked image changed')
    linked=ELF(image)
    for row in provider['inputs']:
        if linked.symbol_data(row['symbol'])!=struct.pack('<10Q',*row['identity']):
            raise ValueError('Actual linked identity data differs from the finalized native input')
    return dict(provider=record(provider_path),linked_definitions_verified=3,
                original_owner_unchanged=provider['original_owner_unchanged'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','relink','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--formatter-from',type=Path,help='Reuse a verified formatter from a completed retained package')
    parser.add_argument('--identity-provider',type=Path,help='Audit restored-input data definitions in the actual linked ELF')
    parser.add_argument('--CPU-libc-heap-bytes',type=int,help='Separate CPU-only8MiB libc parameter experiment')
    parser.add_argument('--bounded-CPU-startup-control',type=Path,help='Separate full-link CPU-only8MiB no-extension startup experiment; never model admission')
    parser.add_argument('--bounded-CPU-startup-heap-bytes',type=int,choices=(4<<20,8<<20),default=8<<20)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    if args.CPU_libc_heap_bytes is not None and args.bounded_CPU_startup_control:raise ValueError('One distinct CPU parameter scope required')
    if args.bounded_CPU_startup_heap_bytes!=8<<20 and not args.bounded_CPU_startup_control:raise ValueError('A changed startup heap requires its exact CPU-only control')
    load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    package=load(args.current/'provenance/receipt.private.json')
    prior=load(args.current/'provenance/native-link.receipt.private.json')
    relink=load(args.relink);image=Path(relink['artifact']['path'])
    if record(image)!=relink['artifact']:raise ValueError('Relinked image changed')
    identity_audit=None
    if args.identity_provider:
        identity_audit=audit_identity_provider(relink,args.identity_provider)
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
    for row in prior.get('formatter_stubs',prior['inputs_before']):
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
    libc_parameter_policy=None
    bounded_startup_policy=None
    early_model=bool(relink.get('early_model_CPU_tables'))
    early_tables=relink.get('early_CPU_tables') or relink.get('early_model_CPU_tables')
    if early_model:
        from early_model_table_scope import require as require_early_model
        require_early_model(relink)
    elif early_tables:
        from price_cpu_startup_original_reader import require_CPU_profile
        CPU_control,CPU_profile=require_CPU_profile(early_tables['original_CPU_package']['path'])
        if record(early_tables['original_CPU_package']['path'])!=early_tables['original_CPU_package'] or \
           relink['effective_application_policy']!=CPU_control['effective_application_policy'] or \
           not early_tables['strict_failure_park_before_original_application_CXX']:
            raise ValueError('Only the original constant-one full-link CPU fixture may use the new zero hole')
    for name,job in jobs:
        result=subprocess.run(job,capture_output=True,timeout=180,env=env)
        (args.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
        if name=='convert' and args.CPU_libc_heap_bytes is not None:
            if relink.get('CPU_only') is not True or relink.get('driver_code_linked') is not False:
                raise ValueError('Explicit libc policy is limited to the independent CPU-only fixture')
            from libc_parameter_policy import bind_heap
            original_converted=converted.read_bytes()
            bounded,libc_parameter_policy=bind_heap(original_converted,args.CPU_libc_heap_bytes)
            (args.out/'default-libc-parameters.elf').write_bytes(original_converted)
            converted.write_bytes(bounded)
        if name=='convert' and args.bounded_CPU_startup_control:
            from price_cpu_startup_original_reader import require_CPU_profile
            from bounded_CPU_startup_parameters import bind
            control,CPU_profile=require_CPU_profile(args.bounded_CPU_startup_control)
            if control['relink']!=record(args.relink) or CPU_profile['headless_audit_kind']!='CPU-startup-staging-memory':
                raise ValueError('The exact completed full-link CPU fixture must be reused without code changes')
            old_command=next(command for label,command in control['commands'] if label=='convert')
            old_converted=Path(old_command[old_command.index('--out')+1]);original_converted=converted.read_bytes()
            if original_converted!=old_converted.read_bytes():raise ValueError('The complete default converted CPU ELF must reproduce exactly')
            bounded,bounded_startup_policy=bind(original_converted,args.bounded_CPU_startup_heap_bytes)
            bounded_startup_policy.update(control_package=record(args.bounded_CPU_startup_control),control_converted_ELF=record(old_converted))
            (args.out/'default-libc-parameters.elf').write_bytes(original_converted);converted.write_bytes(bounded)
        if name=='convert' and early_tables:
            if args.CPU_libc_heap_bytes is not None or args.bounded_CPU_startup_control:
                raise ValueError('The early-table CPU fixture has exactly its qualified eight-MiB parameter scope')
            from bounded_CPU_startup_parameters import bind
            from external_zero_layout import exclude_converted
            original_converted=converted.read_bytes()
            default,early_conversion_proof=exclude_converted(original_converted,early_tables['layout']['begin'],early_tables['layout']['end'])
            (args.out/'original-zero-tail-converted.elf').write_bytes(original_converted)
            bounded,bounded_startup_policy=bind(default,8<<20)
            if early_model:
                bounded_startup_policy.update(CPU_only_before_model_source_and_GPU=False,
                    finite_model_qualification_pending=True,original_tracked_CPU_heap_limit_unchanged=True)
            early_tables=dict(early_tables,converted_zero_hole_proof=early_conversion_proof)
            (args.out/'default-libc-parameters.elf').write_bytes(default);converted.write_bytes(bounded)
            bounded_startup_policy.update(control_package=early_tables['original_CPU_package'],
                original_CPU_completion=early_tables['original_CPU_completion'],
                control_converted_ELF=record(args.out/'default-libc-parameters.elf'),early_owned_zero_scope=True)
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
    if early_tables:
        reference=early_tables['control_native']
        if record(reference['path'])!=reference:raise ValueError('The full original table control changed')
        geometry=audit_converted_storage(Path(reference['path']),converted,prior['lossless_driver_tables'],
            (early_tables['layout']['begin'],early_tables['layout']['end']))
    else:geometry=None if relink.get('CPU_only') else audit_converted_storage(image,converted,prior['lossless_driver_tables'])
    external_rodata=None
    if relink.get('external_rodata_probe'):
        if not relink.get('CPU_only') or relink.get('driver_code_linked'):
            raise ValueError('The new external-rodata scope is limited to the driver-free CPU prototype')
        external_rodata=relink['external_rodata_probe']
        begin=external_rodata['layout']['begin'];end=begin+external_rodata['layout']['bytes']
        for i in range(count):
            header=struct.unpack_from('<IIQQQQQQ',expected,phoff+i*stride)
            if header[0]==1 and header[3]<end and begin<header[3]+header[6]:
                raise ValueError('The formatter recreated LOAD coverage of the exclusive cold-data hole')
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
    if relink.get('required_bundle_restore'):report['required_bundle_restore']=relink['required_bundle_restore']
    if identity_audit:report['required_bundle_identity_audit']=identity_audit
    if relink.get('effective_application_policy'):report['effective_application_policy']=relink['effective_application_policy']
    if libc_parameter_policy:report['CPU_libc_parameter_policy']=libc_parameter_policy
    if bounded_startup_policy:report['CPU_startup_libc_parameter_policy']=bounded_startup_policy
    if external_rodata:report['external_rodata_probe']=external_rodata
    if early_tables:report['early_model_CPU_tables' if early_model else 'early_CPU_tables']=early_tables
    (args.out/'result.private.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('relink','SELF','preferred_formatter_sources','formatter','commands','driver_table_geometry','effective_application_policy')}))


if __name__=='__main__':main()
