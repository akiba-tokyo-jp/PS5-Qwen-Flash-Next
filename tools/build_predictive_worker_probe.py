#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the actual persistent worker's read-only CPU probe without execution."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from audit_native_imports import audit
from build_preservation_integrity import record
from kernel_vm_preflight import load_qualified_session
from rebind_cpu_context import headers
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','donor','plan','session','runtime','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    donor=json.loads(a.donor.read_text());plan=json.loads(a.plan.read_text());session,_=load_qualified_session(a.session)
    if(plan.get('schema')!='ps5-qwen-ready-original-plan-v1'or not donor.get('CPU_only')or donor.get('GPU_calls')!=0):
        raise ValueError('An exact original-role plan and completed CPU-only build donor are required')
    nonce=secrets.token_hex(16);generated=headers(session,json.loads(a.runtime.read_text()),nonce)
    old=a.donor.parent;guard=old/'qualified_context_guard.c'
    (a.out/'qualified_context_guard.c').write_bytes(guard.read_bytes())
    (a.out/'close_context.h').write_text(generated['close_context.h'],newline='\n')
    prefix='/data/ai/moss-qwen-predictive-worker-'+nonce
    text='#pragma once\n#define PREDICTIVE_LOG '+json.dumps(prefix+'.log')+'\n'
    text+='#define PREDICTIVE_PLAN_SHA '+json.dumps(record(a.plan)['sha256'])+'\n'
    text+='struct predictive_source {const char *path;uint64_t identity[10];uint64_t offset;unsigned residue;const char *raw,*envelope;};\n'
    text+='static const struct predictive_source predictive_sources[3]={\n'
    entries=[]
    for role in range(3):
        m=plan['matrices'][role*10];f=plan['files'][m['source']]
        if(len(f['identity'])!=10 or f['bytes']!=f['identity'][5]or f['bytes']>512<<20 or
            m['offset']%16384 or m['offset']+3293184>f['bytes']or not 0<m['residue']<16384 or
            any(type(m[k])is not str or len(m[k])!=64 or any(c not in '0123456789abcdef'for c in m[k])for k in('raw','envelope'))):
            raise ValueError('Every original role requires its sealed bounded source and full byte hashes')
        text+='{'+json.dumps(f['path'])+',{'+','.join(str(v)+'ULL'for v in f['identity'])+'},'
        text+=str(m['offset'])+'ULL,'+str(m['residue'])+','+json.dumps(m['raw'])+','+json.dumps(m['envelope'])+'},\n'
        entries.append(dict(matrix=m,file=f))
    text+='};\n';(a.out/'predictive_worker_context.h').write_text(text,newline='\n')
    commands=[[v.replace(str(old),str(a.out))for v in c]for c in donor['commands']]
    commands=commands[:3]+[commands[-1]]
    commands[0][commands[0].index('-c')+1]=str(ROOT/'native/qwen_flash_next/predictive_worker_probe.c')
    commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/predictive_worker_probe.cpp')
    commands[-1].remove(str(a.out/'original-source.o'))
    image=Path(commands[-1][commands[-1].index('-o')+1])
    fixed={Path(__file__),a.donor,a.plan,a.session,a.runtime,guard}
    fixed|=set((ROOT/'native/app').glob('*.h'))|set(a.out.glob('*.h'))|{a.out/'qualified_context_guard.c',ROOT/'native/qwen_flash_next/source_contention_probe_io.h'}
    for c in commands:
        if '-c'in c:fixed.add(Path(c[c.index('-c')+1]))
    fixed|={Path(row['path'])for row in donor['inputs_before']if Path(row['path']).suffix in('.a','.so','.exe','.x')}
    fixed|={Path(v)for v in commands[-1]if Path(v).is_file()and Path(v).suffix=='.o'}
    before=[record(f)for f in sorted(fixed)]
    (a.out/'intent.private.json').write_text(json.dumps(dict(inputs=before,commands=commands,CPU_only=True,
        Direct_bytes=9912320,maximum_jobs=4,maximum_read_concurrency=1,console_operations=0),indent=2)+'\n')
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-4000:])
    if before!=[record(f)for f in sorted(fixed)]:raise ValueError('A frozen CPU probe input changed')
    llvm=Path(commands[0][0]).parent
    dynamic=subprocess.check_output([str(llvm/'llvm-readelf.exe'),'--dynamic',str(image)],text=True)
    providers=re.findall(r'Shared library: \[([^\]]+)\]',dynamic)
    receipt=dict(artifact=record(image),inputs_before=before,runtime_providers=providers)
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    imports=audit(a.workspace,a.cache,a.out)
    if imports['missing']or 'pread'not in imports['resolved']:raise ValueError('Every actual strong native import must resolve')
    if any(k.startswith(('sceKernelAio','sceLnc','sceAgc','sceVideoOut'))for k in imports['resolved']):
        raise ValueError('AIO, title mutation and GPU imports are forbidden')
    names=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(s in names for s in('llama_model_load','llama_decode','ggml_backend_graph_compute','vkCreate','radv_','aco_')):
        raise ValueError('GPU or model code leaked into the CPU-only worker probe')
    receipt.update(schema='ps5-qwen-predictive-worker-CPU-build-v1',nonce=nonce,commands=commands,
        real_module_import_audit=imports,private_plan=record(a.plan),source_entries=entries,
        remote_elf=prefix+'.elf',remote_log=prefix+'.log',CPU_only=True,Direct_bytes=9912320,
        maximum_seconds=60,prelaunch_pages=2434,maximum_jobs=4,maximum_read_concurrency=1,
        GPU_calls=0,title_launches=0,console_operations=0,CI_runs=0)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_worker_build_passed=True,bytes=image.stat().st_size,missing_imports=0,PS5_operations=0)))
if __name__=='__main__':main()
