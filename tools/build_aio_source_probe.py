#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded CPU AIO comparison; never connect, publish or execute."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess

from audit_native_imports import audit
from build_preservation_integrity import record
from kernel_vm_preflight import load_qualified_session
from rebind_cpu_context import headers

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','donor','plan','session','runtime','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    donor=json.loads(a.donor.read_text());plan=json.loads(a.plan.read_text())
    session,_=load_qualified_session(a.session);nonce=secrets.token_hex(16)
    generated=headers(session,json.loads(a.runtime.read_text()),nonce)
    old=a.donor.parent;guard=old/'qualified_context_guard.c'
    (a.out/'qualified_context_guard.c').write_bytes(guard.read_bytes())
    (a.out/'close_context.h').write_text(generated['close_context.h'],newline='\n')
    if (plan.get('schema')!='ps5-qwen-ready-original-plan-v1' or
            not donor.get('CPU_only') or donor.get('GPU_calls')!=0):
        raise ValueError('Qualified actual-reader CPU donor and exact original plan required')
    first=plan['matrices'][0]
    second=next(m for m in plan['matrices'] if m['source']!=first['source'])
    prefix='/data/ai/moss-qwen-AIO-'+nonce
    text='#pragma once\n#define AIO_SOURCE_LOG '+json.dumps(prefix+'.log')+'\n'
    text+='#define AIO_SOURCE_PLAN_SHA '+json.dumps(record(a.plan)['sha256'])+'\n'
    text+='struct aio_source {const char *path;uint64_t identity[10];uint64_t offset;unsigned residue;const char *raw,*envelope;};\n'
    text+='static const struct aio_source aio_sources[2]={\n'
    for m in (first,second):
        f=plan['files'][m['source']]
        if (len(f['identity'])!=10 or f['bytes']!=f['identity'][5] or f['bytes']>512<<20 or
                m['offset']%16384 or m['offset']+3293184>f['bytes']):
            raise ValueError('Bounded exact sealed original source required')
        text+='{'+json.dumps(f['path'])+',{'+','.join(str(v)+'ULL'for v in f['identity'])+'},'
        text+=str(m['offset'])+'ULL,'+str(m['residue'])+','+json.dumps(m['raw'])+','+json.dumps(m['envelope'])+'},\n'
    text+='};\n';(a.out/'aio_source_context.h').write_text(text,newline='\n')
    commands=[[v.replace(str(old),str(a.out))for v in c]for c in donor['commands']]
    commands=commands[:3]+[commands[-1]]
    commands[0][commands[0].index('-c')+1]=str(ROOT/'native/qwen_flash_next/aio_source_probe.c')
    commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/source_contention_probe_cpp.cpp')
    commands[-1].remove(str(a.out/'original-source.o'))
    image=Path(commands[-1][commands[-1].index('-o')+1])
    fixed={Path(__file__),a.donor,a.plan,a.session,a.runtime,guard}
    fixed|=set((ROOT/'native/app').glob('*.h'))
    fixed|={ROOT/'native/qwen_flash_next'/n for n in ('aio_read_abi.h','aio_read_lifecycle.h','source_contention_probe_io.h')}
    fixed|=set(a.out.glob('*.h'))|{a.out/'qualified_context_guard.c'}
    for c in commands:
        if '-c'in c:fixed.add(Path(c[c.index('-c')+1]))
    fixed|={Path(row['path'])for row in donor['inputs_before']if Path(row['path']).suffix in ('.a','.so','.exe','.x')}
    fixed|={Path(v)for v in commands[-1]if Path(v).is_file()and Path(v).suffix=='.o'}
    before=[record(f)for f in sorted(fixed)]
    (a.out/'intent.private.json').write_text(json.dumps(dict(inputs=before,commands=commands,
        scope='CPU-only paired pread versus AIO, invalid-fd prerequisite, two original BF16 envelopes',
        ABI_reference='SvenGDK/SharpProspero@5dfdb4b0b166e83dc9ae275001afb695f12c7174:src/SharpProspero/Interop/Kernel/KernelAio.cs',
        no_kernel_or_mount_changes=True,console_operations=0),indent=2)+'\n')
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for index,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env)
        (a.out/f'build-{index}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-4000:])
    if before!=[record(f)for f in sorted(fixed)]:raise ValueError('A frozen CPU build input changed')
    llvm=Path(commands[0][0]).parent
    import re
    dynamic=subprocess.check_output([str(llvm/'llvm-readelf.exe'),'--dynamic',str(image)],text=True)
    providers=re.findall(r'Shared library: \[([^\]]+)\]',dynamic)
    receipt=dict(artifact=record(image),inputs_before=before,runtime_providers=providers)
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    imports=audit(a.workspace,a.cache,a.out)
    required={'sceKernelAioInitializeParam','sceKernelAioInitializeImpl','sceKernelAioSubmitReadCommands',
              'sceKernelAioWaitRequest','sceKernelAioDeleteRequest','pread'}
    if imports['missing']or not required<=imports['resolved'].keys():raise ValueError('Actual strong AIO/native imports required')
    forbidden=('sceKernelAioCancel','sceKernelAioDeleteRequests','sceKernelAioSubmitWrite','sceKernelAioWaitRequests','sceLnc','sceAgc','sceVideoOut')
    if any(k.startswith(forbidden)for k in imports['resolved']):raise ValueError('Forbidden mutation, multi-ID retirement or GPU import')
    names=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(s in names for s in ('llama_model_load','llama_decode','ggml_backend_graph_compute','vkCreate','radv_','aco_')):
        raise ValueError('GPU/model implementation leaked into CPU-only payload')
    receipt.update(schema='ps5-qwen-AIO-source-CPU-build-v1',nonce=nonce,commands=commands,
        real_module_import_audit=imports,private_plan=record(a.plan),remote_elf=prefix+'.elf',remote_log=prefix+'.log',
        CPU_only=True,Direct_bytes=6619136,preallocation_extra_pages=1024,prelaunch_pages=2178,
        maximum_seconds=60,round_modes=[0,1,1,0,0,1,1,0],maximum_AIO_requests=2,
        maximum_IDs_per_batch=1,maximum_wait_microseconds=10000000,
        source_entries=[dict(matrix=m,file=plan['files'][m['source']])for m in (first,second)],
        no_kernel_or_mount_changes=True,GPU_calls=0,title_launches=0,console_operations=0,CI_runs=0)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_AIO_build_passed=True,bytes=image.stat().st_size,strong_AIO_imports_verified=True,
                         missing_imports=0,PS5_operations=0)))


if __name__=='__main__':main()
