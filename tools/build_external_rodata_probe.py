#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a driver-free, deterministic cold-rodata CPU qualification image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from audit_native_imports import audit
from build_performance_quantizer import record
from external_rodata_layout import externalize, verify_repacked
from native_dispatch import ELF
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'control', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    old = load(a.control)
    need(old['completed'] and old['CPU_only'] and not old['driver_code_linked'] and
         not old['model_engine_linked'] and old['named_descriptor_controls']==5,
         'Completed independent CPU-only source controls required')
    old_inputs = {Path(row['path']).name:row for row in old['inputs_before']}
    reused = []
    for row in old['inputs_before']:
        if Path(row['path']).suffix in ('.a','.o','.so') or Path(row['path']).name in (
                'loader_probe_context.h','launch_integrity.h','launch_integrity_native.h',
                'app_named_stat.h','libc_parameter_policy.py','test_libc_parameter_policy.py',
                'loader_probe_context_test.c','app_named_stat_test.c','sha256.c'):
            need(record(row['path'])==row, 'A reused CPU input changed'); reused.append(row)
    payload = bytes(range(256)) * (32768)
    payload_path = a.out/'cold-rodata.bin'; payload_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    fnv = 14695981039346656037
    for value in payload: fnv=((fnv^value)*1099511628211)&((1<<64)-1)
    application = '/app0/qwen-runtime/cold-rodata-'+digest[:24]+'.bin'
    (a.out/'cold_rodata_manifest.h').write_text('#define COLD_BYTES 8388608u\n#define COLD_PATH '+json.dumps(application)+
        '\n#define COLD_FNV64 UINT64_C('+str(fnv)+')\nstatic const unsigned char cold_digest[32]={'+
        ','.join(str(v) for v in bytes.fromhex(digest))+'};\n', newline='\n')
    (a.out/'payload.S').write_text('.section .qwen_external_rodata,"a",@progbits\n.balign 65536\n'+
        '.global qwen_cold_payload,qwen_cold_payload_end\nqwen_cold_payload:\n.incbin '+json.dumps(payload_path.as_posix())+
        '\nqwen_cold_payload_end:\n.section .note.GNU-stack,"",@progbits\n', newline='\n')
    script=a.out/'payload.ld'
    script.write_text('SECTIONS { .qwen_external_rodata : ALIGN(65536) { KEEP(*(.qwen_external_rodata)) } } INSERT AFTER .rodata;\n', newline='\n')
    llvm=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    sha=Path(old_inputs['sha256.c']['path']); sha_object=Path(old['artifact']['path']).parent/'sha256.o'
    # The old SHA object is compared with its actual recorded compile recipe.
    sha_job=next(job for job in old['commands'] if '-c' in job and job[job.index('-c')+1]==str(sha))
    need(Path(sha_job[sha_job.index('-o')+1])==sha_object, 'Actual retained SHA object required')
    common=[str(llvm/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk),
        '-std=gnu11','-O2','-fPIC','-fno-stack-protector','-fno-plt','-fno-builtin-malloc','-fno-builtin-free',
        '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-I',str(ROOT/'native/qwen_flash_next'),'-I',str(ROOT/'native/app'),'-I',str(sha.parent),'-I',str(a.out)]
    source=ROOT/'native/app/CPU_loader_footprint.c'; restore=ROOT/'native/app/cold_rodata_probe.c'
    jobs=[common+['-DQWEN_COLD_RODATA_PROBE=1','-c',str(source),'-o',str(a.out/'probe.o')],
          common+['-c',str(restore),'-o',str(a.out/'restore.o')],
          [str(llvm/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-c',str(a.out/'payload.S'),'-o',str(a.out/'payload.o')]]
    control_image=a.out/'control.pie.elf'; image=a.out/'external.pie.elf'
    link=[]
    for value in old['link_command']:
        if value==old['artifact']['path']:value=str(control_image)
        if value==str(Path(old['artifact']['path']).parent/'probe.o'):value=str(a.out/'probe.o')
        if value.startswith('-Map='):value='-Map='+str(a.out/'native-link.private.map')
        link.append(value)
    link[1:1]=[str(a.out/'restore.o'),str(a.out/'payload.o'),'-T',str(script)]
    jobs.append(link)
    env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(jobs):
        run=subprocess.run(job,capture_output=True,timeout=90,env=env)
        (a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(not run.returncode,run.stderr.decode(errors='replace')[-4000:])
    original=ELF(control_image); begin=original.symbols['qwen_cold_payload']['value']
    end=original.symbols['qwen_cold_payload_end']['value']; need(end-begin==len(payload),'Exact linked payload required')
    raw,layout=externalize(original.data,begin,len(payload),payload)
    intermediate=a.out/'excluded.pie.elf';intermediate.write_bytes(raw)
    remove=[str(llvm/'llvm-objcopy.exe'),'--remove-section=.qwen_external_rodata',str(intermediate),str(image)]
    run=subprocess.run(remove,capture_output=True,timeout=30);jobs.append(remove)
    (a.out/'remove-section.private.log').write_bytes(run.stdout+run.stderr)
    need(not run.returncode,run.stderr.decode(errors='replace')[-4000:])
    layout.update(verify_repacked(original.data,image.read_bytes(),begin,payload))
    array=original.symbols['__init_array_start']['value']; array_end=original.symbols['__init_array_end']['value']
    ctors=[original.pointer(at) for at in range(array,array_end,8)]
    expected=[original.symbols[name]['value'] for name in ('restore_cold_rodata','check_cold_rodata_constructor')]
    need(ctors==expected, 'Restore and verification must precede every other constructor')
    for name in ('qwen_native_bootstrap','_start','_init','restore_cold_rodata','check_cold_rodata_constructor'):
        s=original.symbols[name]; need(s['value']+s['size']<=begin or end<=s['value'],'Startup code must remain loaded')
    receipt=dict(artifact=record(image),inputs_before=reused,runtime_providers=old['runtime_providers'])
    save(a.out/'receipt.private.json',receipt)
    imported=audit(a.workspace,a.current.parent,a.out)
    need(not imported['missing'],'Every actual CPU import must resolve: '+str(imported['missing']))
    need(all(not name.startswith(('sceAgc','sceVideoOut','sceSystemServiceLaunch','sceSystemServiceKill')) for name in imported['resolved']),
        'No GPU, display or title-control imports are allowed')
    names=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',str(image)],text=True)
    need(not any(re.match(r'^(vk[A-Z]|radv_|aco_|llama_|ggml_)',line) for line in names.splitlines()),'No driver or model implementation allowed')
    inputs=[record(path) for path in (source,restore,ROOT/'native/app/cold_rodata_probe.h',Path(__file__),
        ROOT/'tools/external_rodata_layout.py',a.out/'cold_rodata_manifest.h',a.out/'payload.S',script,sha_object)]
    receipt.update(completed=True,baseline_relink=False,CPU_only=True,driver_code_linked=False,model_engine_linked=False,
        driver_revision=old['driver_revision'],driver_profile=old['driver_profile'],source=record(source),commands=jobs,
        link_command=link,source_payload_reads=128,GPU_calls=0,source_workers=0,PS5_operations=0,
        context_controls=old['context_controls'],libc_parameter_controls=old['libc_parameter_controls'],named_descriptor_controls=5,
        unchanged_parser_controls_reused=record(a.control),real_module_import_audit=imported,new_inputs=inputs,
        external_rodata_probe=dict(layout=layout,payload=record(payload_path),application_path=application,fnv64=fnv,
            constructor_order=expected,whole_source_SHA256_required=True,physical_reserve_bytes=256<<20,
            ordinary_CPU_close_required=True,production_adopted=False))
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save(a.out/'result.private.json',receipt)
    print(json.dumps(dict(completed=True,external_bytes=len(payload),constructors=len(ctors),
        original_loaded_bytes_reconstructed_exactly=True,driver_code_linked=False,PS5_operations=0)))


if __name__=='__main__':main()
