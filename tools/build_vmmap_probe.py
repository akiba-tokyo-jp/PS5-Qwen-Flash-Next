#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build/check a bounded read-only owner-bound VM map probe; never execute it."""
import argparse,hashlib,json,os,re,secrets,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(path):
    path=Path(path).resolve();return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','controller-manifest','session','process-abi-overlay','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    control=json.loads(a.controller_manifest.read_text());session=json.loads(a.session.read_text())
    assert record(control['source_path'])['sha256']==control['source_sha256']
    assert session['native_eboot_count']==0 and session['runningBigApp']==-1 and session['double_snapshot_equal']
    source=ROOT/'native/qwen_flash_next/vmmap_probe.c';header=ROOT/'native/qwen_flash_next/vmmap_metadata.h'
    priority=a.process_abi_overlay/'sys/priority.h'
    assert priority.is_file(), 'The qualified process ABI overlay is required'
    paths=[source,header,ROOT/'tests/vmmap_metadata.c',ROOT/'tests/vmmap_query.c',Path(__file__),a.controller_manifest,a.session,priority]
    before=[record(f)for f in paths];steps=[]
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    def run(label,cmd):
        r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr);steps.append(dict(name=label,returncode=r.returncode))
        assert r.returncode==0,r.stderr.decode('utf-8','replace')[-3000:];print(label+' passed',flush=True)
    text=source.read_text()
    pieces=[text[text.index('static struct {unsigned char before[64]'):text.index('static int report(')],
        text[text.index('static int guards('):text.index('static int64_t number(')],
        text[text.index('static int vmmap_once('):text.index('\nint main(',text.index('static int vmmap_once('))]]
    (a.out/'actual_vmmap_query.h').write_text('\n'.join(pieces),encoding='utf-8')
    for name in ('vmmap_metadata','vmmap_query'):
        exe=a.out/(name+'.exe')
        run(name+'_compile',[host/'clang.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',header.parent,'-I',a.out,ROOT/'tests'/(name+'.c'),'-o',exe])
        run(name+'_controls',[exe])
    nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-vmmap-'+nonce
    (a.out/'vmmap_probe_context.h').write_text('#define VMMAP_NONCE '+json.dumps(nonce)+'\n#define VMMAP_LOG_PATH '+json.dumps(remote+'.log')+
        '\n#define VMMAP_BOOT_SEC '+str(session['boot'][0])+'LL\n#define VMMAP_BOOT_USEC '+str(session['boot'][1])+'LL\n',newline='\n')
    copied=a.out/'vmmap_probe.c';copied.write_bytes(source.read_bytes());obj=a.out/'vmmap_probe.o';elf=a.out/'vmmap_probe.elf'
    base=Path(control['elf']).parent
    mapping={str(Path(control['source_path'])):str(copied),str(base/'control-permissions.o'):str(obj),str(Path(control['elf'])):str(elf)}
    commands=[[mapping.get(part,part.replace(str(base),str(a.out)))for part in cmd]for cmd in control['commands']]
    assert len(commands)==2
    commands[0]+=['-I',str(header.parent),'-I',str(a.process_abi_overlay),'-MD','-MF',str(a.out/'native-headers.d')]
    commands[1]+=['-lSceSystemService']
    for i,command in enumerate(commands):run('native_'+str(i),command)
    llvm=Path(commands[0][0]).parent;sdk=a.workspace/'toolchain/ps5-payload-sdk/target/lib'
    providers={}
    for name in ('libkernel.so','libkernel_sys.so','libkernel_web.so','libSceLibcInternal.so','libSceSystemService.so'):
        module=sdk/name
        dynamic=subprocess.check_output([str(llvm/'llvm-readelf.exe'),'--dynamic',str(module)],text=True)
        soname=re.search(r'Library soname: \[([^\]]+)\]',dynamic)[1]
        symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D','--defined-only','--format=posix',str(module)],text=True)
        for line in symbols.splitlines():
            fields=line.split()
            if len(fields)>1:providers.setdefault(fields[0],soname)
    required=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D','--undefined-only','--format=posix',str(elf)],text=True)
    required=[line.split()[0]for line in required.splitlines()if line.strip()]
    assert not(set(required)-providers.keys()),sorted(set(required)-providers.keys())
    assert all(not any(word in name for word in ('KillApp','LoadExec','LaunchApp','mprotect','mmap','ptrace'))for name in required)
    assert before==[record(f)for f in paths]
    # Bind the actual compiler, retained CRT objects, SDK headers and providers.
    build_inputs=[Path(arg)for cmd in commands for arg in cmd if Path(arg).is_file()and Path(arg).suffix in ('.exe','.o')and Path(arg)!=obj]
    dependencies=(a.out/'native-headers.d').read_text().replace('\\\n',' ')
    # Clang's dependency output uses escaped spaces; all qualified input roots
    # here are space-free. Refuse ambiguous dependency syntax rather than omit it.
    assert '\\ 'not in dependencies
    deps=dependencies.split(': ',1)[1].split()
    build_inputs += [Path(item)for item in deps]
    build_inputs += [sdk/name for name in ('libkernel.so','libkernel_sys.so','libkernel_web.so','libSceLibcInternal.so','libSceSystemService.so')]
    build_inputs=[record(f)for f in sorted(set(build_inputs))]
    receipt=dict(schema='ps5-qwen-owner-vmmap-probe-v1',state='host_checked_compiled_not_console_executed',
        inputs=before+[record(a.out/'vmmap_probe_context.h')]+build_inputs,steps=steps,commands=commands,artifact=record(elf),nonce=nonce,
        process_ABI_bytes=1096,process_ABI_overlay=record(priority),
        remote_elf=remote+'.elf',remote_log=remote+'.log',boot=session['boot'],
        maximum_VM_queries=2,maximum_metadata_bytes=1<<20,maximum_metadata_records=4096,
        weak_stubs_accepted_as_providers=False,actual_runtime_imports={name:providers[name]for name in required},
        source_payload_reads=0,target_process_memory_reads=0,allocation_or_mapping_changes=0,GPU_calls=0,
        title_launches=0,title_close_calls=0,automatic_retries=0,console_requests=0)
    (a.out/'manifest.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Owner-bound VM map parser/query/native import controls passed; no console requests.')
if __name__=='__main__':main()
