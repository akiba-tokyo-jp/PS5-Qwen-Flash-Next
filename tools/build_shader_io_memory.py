#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an isolated native shader I/O control; never execute or publish a title."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('qualified-process-build','qualified-preservation-build','process-completion','preservation-completion',
              'libc-provider','policy','active-context','reservation','out'):
        p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--direct-window',action='store_true')
    p.add_argument('--kernel-provider',type=Path)
    p.add_argument('--direct-qualification',type=Path)
    a=p.parse_args()
    m=json.loads(a.qualified_process_build.read_text());base=a.qualified_process_build.parent
    prior=json.loads(a.qualified_preservation_build.read_text())
    # Only sources from positively executed, unchanged controls are donors.
    for donor in (m,prior):
        if record(donor['artifact']['path'])!=donor['artifact']:raise ValueError('Qualified image changed')
    for donor,path in ((m,a.process_completion),(prior,a.preservation_completion)):
        completion=json.loads(path.read_text())
        if completion.get('completed')is not True or record(completion['raw']['path'])!=completion['raw']:
            raise ValueError('Positive unchanged native completion required')
        raw=Path(completion['raw']['path']).read_text()
        ends=[line for line in raw.splitlines()if line.startswith('END ')]
        if len(ends)!=1 or 'success=1 'not in ends[0]or 'nonce='+donor['nonce']not in ends[0]:
            raise ValueError('Completion nonce differs from compiled image')
    if record(base/'qualified_context_guard.c') not in m['inputs']:raise ValueError('Process guard changed')
    policy=json.loads(a.policy.read_text());f=policy['native_shader_storage']['external_file']
    if f['bytes']!=8258588 or f['input_window_bytes']!=49152 or not re.fullmatch('[0-9a-f]{64}',f['sha256']):
        raise ValueError('Original shader input contract differs')
    if not f['path'].startswith('/app0/qwen-runtime/'):raise ValueError('Owned resource required')
    remote='/data/ai/native-moss-image-sft/PPSA99190'+f['path'][len('/app0'):]
    context=json.loads(a.active_context.read_text());pointer=json.loads(a.reservation.read_text())
    if Path(pointer['context']).resolve()!=a.active_context.resolve() or any(context[k]for k in ('native_running','gateway_running','model_loaded')):
        raise ValueError('An idle held reservation is required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16)
    prefix='/data/ai/moss-qwen-shader-io-'+nonce
    (a.out/'qualified_context_guard.c').write_bytes((base/'qualified_context_guard.c').read_bytes())
    header=(base/'close_context.h').read_text().replace(m['nonce'],nonce)
    (a.out/'close_context.h').write_text(header,newline='\n')
    header='#define SHADER_IO_LOG '+json.dumps(prefix+'.log')+'\n#define SHADER_IO_PATH '+json.dumps(remote)+'\n'
    header+='#define SHADER_IO_BYTES '+str(f['bytes'])+'ULL\n#define SHADER_IO_SHA256 '+json.dumps(f['sha256'])+'\n'
    header+='#define SHADER_IO_DIRECT '+str(int(a.direct_window))+'\n'
    (a.out/'shader_io_context.h').write_text(header,newline='\n')
    source=ROOT/'native/qwen_flash_next/shader_io_memory_probe.c'
    commands=[[x.replace(str(base),str(a.out))for x in c]for c in m['commands']]
    commands[0][commands[0].index('-c')+1]=str(source)
    inputs=[Path(__file__),source,ROOT/'native/app/kernel_memory_trace.h',a.qualified_process_build,a.qualified_preservation_build,
        a.process_completion,a.preservation_completion,a.libc_provider,
        a.policy,a.active_context,a.reservation,a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'shader_io_context.h']
    if a.direct_window:
        if a.kernel_provider is None:raise ValueError('Actual kernel provider required for owned Direct window')
        if a.direct_qualification is None:raise ValueError('Positive CPU-only Direct qualification required')
        proof=json.loads(a.direct_qualification.read_text());raw=record(proof['raw']['path'])
        if proof.get('completed')is not True or raw!=proof['raw']:raise ValueError('Unchanged Direct qualification required')
        text=Path(raw['path']).read_text()
        for line in ('DIRECT_ALLOC_BEFORE bytes=8388608','DIRECT_ALLOC_RETURNED rc=0','DIRECT_MAP_RETURNED rc=0',
            'DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0'):
            if text.splitlines().count(line)!=1:raise ValueError('Prior bounded Direct lifecycle differs')
        ends=[line for line in text.splitlines()if line.startswith('END ')]
        if len(ends)!=1 or 'success=1 'not in ends[0]or 'Direct_released=1 GPU_calls=0 title_launches=0 automatic_retry=0'not in ends[0]:
            raise ValueError('Positive CPU-only Direct retirement required')
        inputs.extend((a.kernel_provider,a.direct_qualification,Path(raw['path'])))
    # Retain all unchanged compiled API/header/archive providers from the donor.
    for command in commands:
        for x in command:
            q=Path(x)
            if q.is_file() and q.suffix in ('.exe','.a','.so','.h','.c','.cpp','.o') and a.out not in q.parents:inputs.append(q)
    fixed=[record(q)for q in sorted(set(inputs))]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2400:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[0][0]).parent/'llvm-nm.exe'
    imports=subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True)
    names={line.split()[0]for line in imports.splitlines()if line.split()}
    known=set(m['actual_imports'])|set(prior['actual_native_imports'])
    new=names-known
    # Compiler-introduced comparisons use the real strong public libc export.
    # They do not require another title launch to qualify an ordinary libc API.
    direct_API={'sceKernelAllocateDirectMemory','sceKernelGetDirectMemorySize','sceKernelAvailableDirectMemorySize',
        'sceKernelMapDirectMemory','sceKernelMunmap','sceKernelReleaseDirectMemory','sceKernelAvailableFlexibleMemorySize','usleep'}if a.direct_window else set()
    if new-{'memcmp','usleep'}-direct_API:raise ValueError('Unqualified imports: '+str(sorted(new-{'memcmp','usleep'}-direct_API)))
    dynamic=subprocess.check_output([str(nm.parent/'llvm-readelf.exe'),'--dynamic',str(a.libc_provider)],text=True)
    if 'Library soname: [libSceLibcInternal.sprx]'not in dynamic:raise ValueError('Actual libc provider required')
    exported=subprocess.check_output([str(nm),'-D','--defined-only','--format=posix',str(a.libc_provider)],text=True)
    exports={line.split()[0]for line in exported.splitlines()if line.split()}
    if not new-direct_API<=exports:raise ValueError('A required strong libc export is missing')
    if a.direct_window:
        dynamic=subprocess.check_output([str(nm.parent/'llvm-readelf.exe'),'--dynamic',str(a.kernel_provider)],text=True)
        if 'Library soname: [libkernel.sprx]'not in dynamic:raise ValueError('Actual strong public kernel provider required')
        raw=subprocess.check_output([str(nm),'-D','--defined-only','--format=posix',str(a.kernel_provider)],text=True)
        kernel_exports={line.split()[0]for line in raw.splitlines()if line.split()}
        if not names.intersection(direct_API)<=kernel_exports:raise ValueError('Required Direct API export missing')
    if any(re.search(r'sceAgc|LaunchApp|KillApp|ptrace|mmap|\bkill\b',n)for n in names)or(not a.direct_window and names.intersection(direct_API)):
        raise ValueError('Unexpected execution or allocation API')
    if fixed!=[record(q)for q in sorted(set(inputs))]:raise ValueError('A frozen input changed')
    result=dict(schema='ps5-qwen-shader-io-memory-build-v1',nonce=nonce,artifact=record(artifact),inputs=fixed,commands=commands,
        actual_native_imports=sorted(names),imports_subset_of_executed_controls=not new,
        additional_actual_libc_exports=sorted(new-direct_API),actual_libc_provider=record(a.libc_provider),
        additional_actual_kernel_exports=sorted(new.intersection(direct_API)),
        remote_elf=prefix+'.elf',remote_log=prefix+'.log',file_bytes=f['bytes'],file_SHA256=f['sha256'],input_window_bytes=49152,
        reads=169,markers=338,quiet_observations=6,matched_idle_ns=2000000,extra_floor_pages=256,
        static_aligned_window=not a.direct_window,owned_Direct_window=a.direct_window,owned_Direct_bytes=131072 if a.direct_window else 0,
        Direct_alignment=65536 if a.direct_window else 0,
        tracked_Direct_heap=False,registry_initialized=False,codec_initialized=False,
        title_launches=0,GPU_calls=0,automatic_retries=0,PS5_operations=0,CI_runs=0)
    (a.out/'manifest.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(built=True,bytes=result['artifact']['bytes'],reads=169,markers=338,unqualified_imports=0,title_launches=0,GPU_calls=0)),flush=True)
if __name__=='__main__':main()
