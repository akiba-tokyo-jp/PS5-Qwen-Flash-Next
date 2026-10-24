#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a Direct-integrity controller and one CPU-only qualification; never execute."""
import argparse,hashlib,json,os,re,secrets,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(path):
    path=Path(path).resolve();return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','launch-plan','active-context','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();load=lambda path:json.loads(path.read_text())
    plan=load(a.launch_plan);state=load(a.active_context)
    assert state['original_restored']and not state['native_running']and not state['model_loaded']
    original=Path(plan['source_controller']['path']);assert record(original)==plan['source_controller']
    source=original.read_text();start=source.index('static int digest_matches(');end=source.index('static int exact_text(',start)
    replacement='#include "launch_integrity_native.h"\nstatic int digest_matches(const char *p,size_t n,const char *h){return qwen_launch_digest_matches(p,n,h);}\n'
    modified=source[:start]+replacement+source[end:]
    assert modified.replace(replacement,source[start:end],1)==source
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    observed=[record(a.launch_plan),record(a.active_context)]
    plan_snapshot=a.out/'preparation-plan.private.json';context_snapshot=a.out/'preparation-context.private.json'
    plan_snapshot.write_bytes(a.launch_plan.read_bytes());context_snapshot.write_bytes(a.active_context.read_bytes())
    headers=[ROOT/'native/qwen_flash_next/launch_integrity.h',ROOT/'native/qwen_flash_next/launch_integrity_native.h']
    inputs=[Path(__file__),plan_snapshot,context_snapshot,original,*headers,ROOT/'tests/launch_integrity.c']
    inputs += [Path(row['path'])for row in plan['header_inputs']]
    before=[record(path)for path in inputs]
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    steps=[]
    def run(label,cmd):
        result=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,result.stderr.decode(errors='replace')[-2500:]
        steps.append(dict(name=label,returncode=0));print(label+' passed',flush=True)
    exe=a.out/'launch-integrity.exe'
    run('actual_stream_compile',[host/'clang.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',headers[0].parent,ROOT/'tests/launch_integrity.c','-o',exe])
    run('actual_stream_controls',[exe])
    base=Path(plan['launcher']['path']).parent
    for row in plan['header_inputs']:
        src=Path(row['path']);assert record(src)==row;(a.out/src.name).write_bytes(src.read_bytes())
    nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-launch-integrity-'+nonce
    session=a.out/'session_context.h';text=session.read_text()
    text,n=re.subn(r'^#define LAUNCH_LOG_PREFIX .*$', '#define LAUNCH_LOG_PREFIX '+json.dumps(remote),text,flags=re.M);assert n==1
    session.write_text(text,newline='\n')
    generated=a.out/'direct-controller.c';generated.write_text(modified,newline='\n')
    commands=[[arg.replace(str(base),str(a.out))for arg in cmd]for cmd in plan['commands']]
    assert len(commands)==3
    commands[1]=[str(generated)if arg==str(original)else arg for arg in commands[1]]
    assert str(generated)in commands[1]
    commands[1]+=['-I',str(headers[0].parent),'-MD','-MF',str(a.out/'native-headers.d')]
    for i,cmd in enumerate(commands):run('controller_'+str(i),cmd)
    controller=a.out/Path(plan['launcher']['path']).name
    # The qualification main only reads the inactive original SELF once. GC
    # must remove the controller's launch/close/mount entry points entirely.
    original_SELF=state['original_SELF'];canonical='/data/ai/native-moss-image-sft/PPSA99190/eboot.bin'
    probe=a.out/'CPU-probe.c'
    probe.write_text('#define MOSS_RUNTIME_PREP 1\n#include "direct-controller.c"\n'+r'''
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    journal=open(LAUNCH_LOG_PREFIX "-CPU.log",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(journal<0)return 3;
    int ok=0;
    if(!report("BEGIN nonce=@NONCE@ CPU_only=1 title_launches=0 GPU_calls=0")||constructors!=1||getuid()!=1||geteuid()!=0||!live_context()||!idle()||!no_native_owner())goto done;
    uint32_t free_before=0,free_after=0;size_t count=4;uint64_t begun=qwen_launch_now(NULL);
    if(!begun||sysctlbyname("vm.stats.vm0.v_free_count",&free_before,&count,NULL,0)||count!=4)goto done;
    if(!report("HASH_BEFORE canonical_original_SELF=1")||!qwen_launch_digest_matches(@PATH@,@BYTES@ULL,@SHA@))goto done;
    count=4;uint64_t ended=qwen_launch_now(NULL);
    if(ended<begun||sysctlbyname("vm.stats.vm0.v_free_count",&free_after,&count,NULL,0)||count!=4)goto done;
    if(!report("HASH_COMPLETE canonical_original_SELF=1 kernel_free_before=%u kernel_free_after=%u elapsed_ns=%llu",free_before,free_after,(unsigned long long)(ended-begun))||!live_context()||!idle()||!no_native_owner())goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=@NONCE@ title_launches=0 GPU_calls=0 input_window_bytes=%u no_retry=1",ok,QWEN_LAUNCH_WINDOW))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}
'''.replace('@NONCE@',nonce).replace('@PATH@',json.dumps(canonical)).replace('@BYTES@',str(original_SELF['bytes'])).replace('@SHA@',json.dumps(original_SELF['sha256'])),newline='\n')
    probe_object=a.out/'CPU-probe.o';probe_elf=a.out/'CPU-probe.elf'
    compile_probe=[str(probe)if arg==str(generated)else str(probe_object)if arg==str(a.out/'launch.o')else arg for arg in commands[1]]
    compile_probe += ['-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable']
    link_probe=[str(probe_elf)if arg==str(controller)else str(probe_object)if arg==str(a.out/'launch.o')else arg for arg in commands[2]]
    run('CPU_probe_compile',compile_probe);run('CPU_probe_link',link_probe)
    llvm=Path(commands[0][0]).parent
    required=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D','--undefined-only','--format=posix',str(probe_elf)],text=True)
    names=[line.split()[0]for line in required.splitlines()if line.strip()]
    assert all(not any(term in name for term in ('LaunchApp','KillApp','ptrace','mmap','mprotect','mount','sceAgc','AllocateDirect'))for name in names)
    assert {'pread','sysctlbyname','clock_gettime','fcntl'}<=set(names)
    sdk=a.workspace/'toolchain/ps5-payload-sdk/target/lib';providers={}
    for library in [sdk/name for name in ('libkernel.so','libkernel_sys.so','libkernel_web.so',
            'libSceLibcInternal.so','libSceSystemService.so','libSceAppInstUtil.so','libSceUserService.so')]:
        exported=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D','--defined-only','--format=posix',str(library)],text=True)
        for line in exported.splitlines():
            fields=line.split()
            if len(fields)>1:providers.setdefault(fields[0],library)
    assert not(set(names)-providers.keys()),sorted(set(names)-providers.keys())
    assert before==[record(path)for path in inputs]
    assert observed==[record(a.launch_plan),record(a.active_context)]
    dependencies=(a.out/'native-headers.d').read_text().replace('\\\n',' ').split(': ',1)[1].split()
    extra=[Path(path)for path in dependencies]
    extra += [Path(arg)for cmd in commands for arg in cmd if Path(arg).is_file()and Path(arg).suffix in ('.c','.h','.exe','.o')and Path(arg).name not in ('launch.o','sha256.o')]
    extra += [providers[name]for name in names]
    receipt=dict(schema='ps5-qwen-launch-Direct-integrity-build-v1',state='host_checked_not_console_executed',
        inputs=before+[record(path)for path in sorted(set(extra))],steps=steps,commands=commands,
        controller=record(controller),CPU_probe=record(probe_elf),generated_controller=record(generated),
        owner_service_title_session_guards_unchanged=True,only_controller_change='digest_matches input adapter',
        observed_preparation_inputs=observed,controller_journal_prefix=remote,
        byte_count_SHA256_stable_identity_and_EOF_required=True,original_SELF=original_SELF,
        input_window_bytes=1<<20,automatic_retries=0,title_launches=0,GPU_calls=0,console_requests=0,
        nonce=nonce,remote_probe=remote+'-CPU.elf',remote_log=remote+'-CPU.log',
        actual_CPU_probe_imports={name:providers[name].name for name in names})
    (a.out/'manifest.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Direct integrity controller and CPU-only probe built; no console requests or title/GPU execution.')
if __name__=='__main__':main()
