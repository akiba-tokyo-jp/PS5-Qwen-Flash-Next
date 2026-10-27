#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one bounded actual-reader CPU payload; never connect, deploy or execute."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from build_preservation_integrity import record
from kernel_vm_preflight import load_qualified_session
from rebind_cpu_context import headers
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('workspace','cache','donor','qualified-native','plan','session','runtime','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    donor=json.loads(a.donor.read_bytes());prior=json.loads(a.qualified_native.read_bytes());session,_=load_qualified_session(a.session)
    nonce=secrets.token_hex(16);generated=headers(session,json.loads(a.runtime.read_bytes()),nonce)
    (a.out/'close_context.h').write_text(generated['close_context.h'],newline='\n')
    old=a.donor.parent;guard=old/'qualified_context_guard.c';(a.out/guard.name).write_bytes(guard.read_bytes())
    prefix='/data/ai/moss-qwen-original-CPU-'+nonce
    (a.out/'ready_CPU_context.h').write_text('#pragma once\n#define READY_CPU_LOG '+json.dumps(prefix+'.log')+'\n',newline='\n')
    raw=a.plan.read_bytes();sha=record(a.plan)['sha256']
    if len(raw)>65536 or json.loads(raw).get('schema')!='ps5-qwen-ready-original-plan-v1':raise ValueError('Bounded original-source manifest required')
    (a.out/'ready_original_plan.inc').write_text('static constexpr char ready_original_manifest[]='+json.dumps(raw.decode('ascii'))+';\nstatic constexpr char ready_original_manifest_sha256[]="'+sha+'";\n',newline='\n')
    commands=[[x.replace(str(old),str(a.out))for x in c]for c in donor['commands']]
    c=commands[0];c[c.index('-c')+1]=str(ROOT/'native/qwen_flash_next/ready_original_CPU_probe.c')
    cpp=commands[1];cpp[cpp.index('-c')+1]=str(ROOT/'native/qwen_flash_next/ready_original_CPU.cpp')
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    for command in commands[:3]:command+=['-ffunction-sections','-fdata-sections']
    cpp+=['-I',str(a.out),'-I',str(up/'ggml/include'),'-isystem',str(up/'vendor'),'-I',str(up/'vendor/hash')]
    reader=cpp.copy();reader[reader.index('-c')+1]=str(ROOT/'native/app/ready_original_source.cpp');reader[reader.index('-o')+1]=str(a.out/'original-source.o');reader+=['-DQWEN_READY_ORIGINAL_PLAN=1']
    link=commands[-1];link.insert(link.index('--start-group'),str(a.out/'original-source.o'));image=Path(link[link.index('-o')+1])
    commands.insert(-1,reader)
    fixed={Path(__file__),a.donor,a.qualified_native,a.plan,a.session,a.runtime,guard,*sorted((ROOT/'native/app').glob('*.h'))}
    for command in commands:
        if '-c'in command:fixed.add(Path(command[command.index('-c')+1]))
    fixed|=set(a.out.glob('*.h'))|{a.out/'ready_original_plan.inc',a.out/'qualified_context_guard.c'}
    for x in link:
        path=Path(x)
        if path.is_file()and path.suffix in('.o','.a','.so','.exe','.x'):fixed.add(path)
    # Strong public module stubs prove every actual payload import. They are
    # evidence providers, not injected replacement weak stubs.
    fixed|={Path(r['path'])for r in prior['inputs_before']if r['path'].endswith('.so')and not r['path'].endswith('_stub_weak.so')}
    payload_lib=a.workspace/'toolchain/ps5-payload-sdk/target/lib'
    fixed|={payload_lib/name for name in('libc.a','libkernel_web.so','libSceLibcInternal.so','libSceNet.so','libSceSystemService.so')}
    fixed_rows=[record(x)for x in sorted(fixed)]
    (a.out/'intent.private.json').write_text(json.dumps(dict(commands=commands,inputs=fixed_rows,console_operations=0),indent=2)+'\n')
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,command in enumerate(commands):
        r=subprocess.run(command,capture_output=True,timeout=120,env=env);(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('CPU source build '+str(i)+': '+r.stderr.decode(errors='replace')[-4500:])
    if fixed_rows!=[record(x)for x in sorted(fixed)]:raise ValueError('A frozen CPU payload input changed')
    llvm=Path(cpp[0]).parent
    dynamic=subprocess.check_output([str(llvm/'llvm-readelf.exe'),'--dynamic',str(image)],text=True)
    providers=re.findall(r'Shared library: \[([^\]]+)\]',dynamic)
    receipt=dict(artifact=record(image),inputs_before=fixed_rows,runtime_providers=providers)
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    imported=audit(a.workspace,a.cache,a.out)
    if imported['missing']:raise ValueError('Missing real imports: '+str(imported['missing']))
    names=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(word in names for word in('ggml_backend_graph_compute','llama_decode','llama_model_load','qwen_native_gpu_initialize','vkCreate','radv_','aco_')):
        raise ValueError('Model or Vulkan implementation leaked into CPU source payload')
    if any(x.startswith(('sceAgc','sceVideoOut','sceLnc'))or x=='sceSystemServiceKillApp'for x in imported['resolved']):raise ValueError('GPU/title mutation import in CPU source payload')
    for symbol in('ReadyOriginalSource::fill_CPU_group','compiled_ready_original_plan','ReadyOriginalSource::close_returned_CPU_failure'):
        if symbol not in names:raise ValueError('Actual reader symbol missing: '+symbol)
    receipt.update(schema='ps5-qwen-ready-original-CPU-build-v1',nonce=nonce,commands=commands,real_module_import_audit=imported,
        private_plan=record(a.plan),compiled_plan_sha256=sha,remote_elf=prefix+'.elf',remote_log=prefix+'.log',
        current_boot=session['boot'],actual_reader_implementation=True,CPU_only=True,Direct_bytes=2*3293184+32768,
        preallocation_extra_pages=768,round_widths=[1,2,2,1,1,2,2,1],maximum_seconds=60,
        GPU_calls=0,title_launches=0,model_loaded=False,production_adopted=False,console_operations=0,CI_runs=0)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_only_link_passed=True,bytes=image.stat().st_size,missing_imports=0,actual_reader_linked=True,console_operations=0)),flush=True)
if __name__=='__main__':main()
