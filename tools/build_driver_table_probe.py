#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded CPU fixture for all exact NIR constants; never execute it."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from audit_native_imports import audit
from driver_table_storage import validate
from shader_storage import record
from kernel_vm_preflight import load_qualified_session
from rebind_cpu_context import headers
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','manifest','donor','session','runtime','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.manifest.read_text());m=validate(a.manifest,m['source_archive']['path'])
    donor=json.loads(a.donor.read_text());session,_=load_qualified_session(a.session)
    if not donor.get('CPU_only')or donor.get('GPU_calls')!=0:raise ValueError('A CPU-only build donor is required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16)
    context=headers(session,json.loads(a.runtime.read_text()),nonce);old=a.donor.parent
    (a.out/'qualified_context_guard.c').write_bytes((old/'qualified_context_guard.c').read_bytes())
    (a.out/'close_context.h').write_text(context['close_context.h'],newline='\n')
    prefix='/data/ai/moss-qwen-driver-tables-'+nonce
    (a.out/'driver_table_probe_context.h').write_text('#pragma once\n#define TABLE_PROBE_LOG '+json.dumps(prefix+'.log')+'\n#define TABLE_MANIFEST_SHA '+json.dumps(record(a.manifest)['sha256'])+'\n',newline='\n')
    asm='.section .qwen_driver_tables,"aw",@nobits\n.balign 16384\n.global __qwen_driver_tables_start\n__qwen_driver_tables_start:\n'
    for r in m['tables']:
        asm+='.balign '+str(max(1,r['alignment']))+'\n.global '+r['symbol']+'\n'+r['symbol']+':\n.space '+str(r['bytes'])+'\n'
    asm+='.balign 16384\n.global __qwen_driver_tables_end\n__qwen_driver_tables_end:\n.section .note.GNU-stack,"",@progbits\n'
    (a.out/'targets.S').write_text(asm,newline='\n')
    base=[[v.replace(str(old),str(a.out))for v in c]for c in donor['commands']]
    for c,source in zip(base[:2],('driver_table_probe.c','driver_table_probe.cpp')):
        c[c.index('-c')+1]=str(ROOT/'native/qwen_flash_next'/source)
    def compile_source(source,obj):
        c=list(base[1]);c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(a.out/obj)
        if str(source).endswith('.S'):
            for value in('-std=c++17','-fexceptions','-fcxx-exceptions','-frtti','-Werror'):
                if value in c:c.remove(value)
        return c
    extra=[compile_source(m['registry']['path'],'registry.o'),compile_source(m['assembly']['path'],'packed.o'),compile_source(a.out/'targets.S','targets.o')]
    link=base[-1];at=link.index('--start-group');link[at:at]=[str(a.out/n)for n in('registry.o','packed.o','targets.o')]
    # Ordinary archive scan links only the immutable zlib codec members.
    link.insert(link.index('--end-group'),m['source_archive']['path'])
    commands=base[:3]+extra+[link];image=Path(link[link.index('-o')+1])
    fixed={Path(__file__),a.donor,a.manifest,a.session,a.runtime,Path(m['source_archive']['path']),
        ROOT/'native/app/driver_table_restore.h',ROOT/'native/app/driver_tables.h',ROOT/'native/thirdparty/zlib/zlib.h',
        ROOT/'native/thirdparty/zlib/zconf.h',Path(m['pool']['path']),*a.out.glob('*.h'),a.out/'qualified_context_guard.c'}
    fixed|={Path(row['path'])for row in donor['inputs_before']if Path(row['path']).suffix in('.a','.so','.exe','.x')}
    for c in commands:
        if '-c'in c:fixed.add(Path(c[c.index('-c')+1]))
    fixed|={Path(v)for v in link if Path(v).is_file()and Path(v).suffix=='.o'}
    before=[record(v)for v in sorted(fixed)]
    (a.out/'intent.private.json').write_text(json.dumps(dict(inputs=before,commands=commands,PS5_operations=0),indent=2)+'\n')
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,env=env,timeout=120);(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3500:])
    if before!=[record(v)for v in sorted(fixed)]:raise ValueError('A frozen CPU table input changed')
    llvm=Path(base[1][0]).parent
    dynamic=subprocess.check_output([str(llvm/'llvm-readelf.exe'),'--dynamic',str(image)],text=True)
    receipt=dict(artifact=record(image),inputs_before=before,runtime_providers=re.findall(r'Shared library: \[([^\]]+)\]',dynamic))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n');imports=audit(a.workspace,a.cache,a.out)
    if imports['missing']or 'sceKernelMprotect'not in imports['resolved']:raise ValueError('Every actual import must resolve')
    if any(v.startswith(('sceLnc','sceKernelAio','sceAgc','sceVideoOut'))for v in imports['resolved']):raise ValueError('Title mutation, AIO and GPU imports are forbidden')
    symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(v in symbols for v in('llama_model_load','llama_decode','vkCreate','radv_','aco_','nir_opt_algebraic')):
        raise ValueError('Model or compiler execution leaked into the data fixture')
    receipt.update(schema='ps5-qwen-driver-table-CPU-build-v1',inputs_before=before,commands=commands,nonce=nonce,
        manifest=record(a.manifest),table_count=len(m['tables']),raw_bytes=m['original_table_bytes'],packed_bytes=m['packed_bytes'],
        actual_imports=imports,remote_elf=prefix+'.elf',remote_log=prefix+'.log',CPU_only=True,
        prelaunch_pages=2434,prelaunch_formula='1154 operational + 1024 BSS/codec allowance + 256 variation',
        maximum_seconds=60,model_loaded=False,GPU_calls=0,title_launches=0,PS5_operations=0)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_table_build_passed=True,bytes=image.stat().st_size,tables=len(m['tables']),PS5_operations=0)))
if __name__=='__main__':main()
